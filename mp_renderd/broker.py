import os
import multiprocessing
import time
import collections
import Queue
import threading
import uuid

from mp_renderd.queue import STOP, fan_in_queue, RenderQueue, Task

import logging
log = logging.getLogger(__name__)

class BaseWorker(multiprocessing.Process):
    def __init__(self, in_queue, out_queue):
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.id = uuid.uuid4().hex
        multiprocessing.Process.__init__(self)
        self.daemon = True

    def dispatch(self, task):
        task.worker_id = self.id
        self.in_queue.put(task)

    def run(self):
        log.debug('proc %d started', os.getpid())
        while True:
            try:
                if not self.handle_task_message():
                    return
            except KeyboardInterrupt:
                return

    def handle_task_message(self):
        task = self.in_queue.get()
        if task == STOP:
            return False

        req_doc = task.doc
        command = req_doc.get('command', 'None')
        method = getattr(self, 'do_' + command, None)
        if not method:
            resp = {
                'status': 'error',
                'error_message': 'unknown command: %s' % command
            }
        else:
            try:
                resp = method(req_doc)
                if resp is None:
                    resp = {}
            except Exception, ex:
                resp = {
                    'status': 'error',
                    'error_message': repr(ex)
                }
            else:
                if not resp.get('status'):
                    resp['status'] = 'ok'

        # resp['id'] = req_doc['id']
        # resp['uid'] = req_doc['uid']
        # resp['_worker_id'] = req_doc['_worker_id']

        task.doc = resp
        self.out_queue.put(task)
        return True


class SleepWorker(BaseWorker):
    def __init__(self, **kw):
        BaseWorker.__init__(self, **kw)

    def do_sleep(self, doc):
        time.sleep(doc['time'])
        return {}

class SeedWorker(BaseWorker):
    def __init__(self, caches, base_config, **kw):
        self.caches = caches
        self.base_config = base_config
        BaseWorker.__init__(self, **kw)

    def do_tile(self, doc):
        from mapproxy.util import local_base_config

        cache = self.caches.get(doc['cache_identifier'])
        if not cache:
            return {
                'status': 'error',
                'error_message': 'unknown cache %s' % doc['cache_identifier']
            }

        tiles = [tuple(coord) for coord in doc['tiles'] if coord]
        with local_base_config(self.base_config):
            cache.load_tile_coords(tiles)

class WorkerPool(object):
    """
    Starts and manages a pool of worker processes.

    :param worker_factory: factory for the worker processes.
        should be a function that takes ``task_address`` and
        ``result_address`` and returns a ``multiprocessing.Process``
    :param pool_size: number of parallel worker processes



    Manages a pool of *n* workers. Each worker has its own input queue
    so that we can send tasks to explicit workers (i.e. workers where we
    know that they are idle).

    `get()` returns the input queue from one of the available (idle)
    workers. `put()` moves the queue back ot the list of available processes.

    """
    def __init__(self, worker_factory, pool_size=2):
        self.processes = {}
        self.pool_size = pool_size
        self.worker_factory = worker_factory
        self.result_queue = None
        self.available = set()
        self.inuse = set()
        self.result_queue = multiprocessing.Queue()
        self.start_processes()

    def is_available(self):
        return bool(self.available)

    def get(self):
        worker = self.available.pop()
        self.inuse.add(worker)
        return worker

    def put(self, worker_id):
        worker = self.processes[worker_id][1]
        self.inuse.remove(worker)
        self.available.add(worker)

    def start_processes(self):
        assert self.result_queue
        log.debug('starting processes')
        for i in xrange(self.pool_size - len(self.processes)):
            task_queue = multiprocessing.Queue()
            p = self.worker_factory(in_queue=task_queue, out_queue=self.result_queue)
            p.start()
            self.processes[p.id] = (task_queue, p)
            self.available.add(p)

    def clear_dead_processes(self):
        for proc in self.processes[:]:
            if not proc.is_alive():
                self.available.remove(proc.id)
                self.processes.remove(proc.id)

    def check_processes(self):
        self.clear_dead_processes()
        self.start_processes()

    def terminate_processes(self):
        log.debug('terminating processes')
        for proc in self.processes:
            proc.terminate()
        self.processes.clear()
        self.available.clear()


STOP_BROKER = '696054488d18402b9155a531e0a31714'

class Broker(threading.Thread):
    def __init__(self, worker, render_queue):
        threading.Thread.__init__(self)
        self.task_in_queue = Queue.Queue()
        self.render_queue = render_queue

        self.response_queues = {}
        self.worker = worker
        self.result_queue = self.worker.result_queue

        self.read_queue = fan_in_queue([self.result_queue, self.task_in_queue])

    def dispatch(self, task, response_queue):
        self.task_in_queue.put((task, response_queue))

    def shutdown(self):
        self.task_in_queue.put(STOP_BROKER)

    def run(self):
        shutdown = False
        while True:
            src, data = self.read_queue.get()

            # new tasks
            if src == self.task_in_queue:
                if data == STOP_BROKER:
                    shutdown = True
                else:
                    task, resp_queue = data
                    log.info('new task (prio: %s): %s %s ', task.priority, task.id, task.doc)
                    self.response_queues[task.request_id] = resp_queue
                    self.render_queue.add(task)

            # results from workers
            elif src == self.result_queue:
                log.info('result from %s (prio: %s): %s %s', data.worker_id, data.priority, data.id, data.doc)
                self.worker.put(data.worker_id)
                orig_requests = self.render_queue.remove(data.id)
                for req in orig_requests:
                    response_queue = self.response_queues.pop(req.request_id)
                    response_queue.put(data)

            while True:
                if self.render_queue.has_new_tasks() and self.worker.is_available():
                    task = self.render_queue.next()
                    if self.render_queue.already_running(task):
                        continue
                    w = self.worker.get()
                    w.dispatch(task)
                break

            if not self.render_queue.running and not self.render_queue.has_new_tasks() and shutdown:
                break



def main():

    logging.basicConfig(level=logging.DEBUG)

    worker_pool = WorkerPool(SleepWorker, 2)

    b = Broker(worker_pool)
    b.start()

    response_queue = Queue.Queue()

    n = 5

    # for i in range(n):
    #     if i % 2:
    #         b.dispatch(Task(i+1, {'command': 'sleep', 'time': 0.5}, priority=10), response_queue=response_queue)
    #     else:
    #         b.dispatch(Task(i, {'command': 'sleep', 'time': 0.05}, priority=20), response_queue=response_queue)
    #     time.sleep(0.02)

    # for i in range(n):
    #     if i % 2:
    #         b.dispatch(Task(i+1, {'command': 'sleep', 'time': 0.2}, priority=10), response_queue=response_queue)
    #     else:
    #         b.dispatch(Task(i, {'command': 'sleep', 'time': 0.02}, priority=20), response_queue=response_queue)
    #     time.sleep(0.02)

    for i in range(n):
        b.dispatch(Task(i, {'command': 'sleep', 'time': 0.5}, priority=20), response_queue=response_queue)
        b.dispatch(Task(i, {'command': 'sleep', 'time': 0.05}, priority=30), response_queue=response_queue)
        time.sleep(0.02)

    for i in range(n*2):
        response_queue.get()
    b.shutdown()

    # for i in range(n):
        # print b.result_queue.get()

if __name__ == '__main__':
    main()
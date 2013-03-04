import multiprocessing
import time
import collections
import Queue
import threading

from mp_renderd.queue import STOP, fan_in_queue, RenderQueue, Task

import logging
log = logging.getLogger(__name__)

class Worker(multiprocessing.Process):
    def __init__(self, in_queue, out_queue):
        self.in_queue = in_queue
        self.out_queue = out_queue
        multiprocessing.Process.__init__(self)
        self.daemon = True

    def run(self):
        while True:
            wait = self.in_queue.get()
            if wait == STOP:
                break
            # print 'processing', wait
            time.sleep(wait.doc)
            self.out_queue.put(wait)

WorkerData = collections.namedtuple('WorkerData', ['queue', 'process'])

# class AvailableWorkers(object):
#     def __init__(self, workers):
#         self.workers = dict((hash(w), w) for w in workers)
#         self.available = set(workers)
#         self.inuse = set()




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
            p = self.worker_factory(task_queue, self.result_queue)
            p.start()
            self.processes[hash(p)] = (task_queue, p)
            self.available.add(p)

    def clear_dead_processes(self):
        for proc in self.processes[:]:
            if not proc.is_alive():
                self.available.remove(hash(proc))
                self.processes.remove(proc)

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
    def __init__(self, worker):
        threading.Thread.__init__(self)
        self.task_in_queue = Queue.Queue()
        self.render_queue = RenderQueue([0, 0, 10, 20])

        self.response_queues = {}
        self.worker = worker
        self.result_queue = self.worker.result_queue

        self.read_queue = fan_in_queue([self.result_queue, self.task_in_queue])

    def dispatch(self, task):
        self.task_in_queue.put(task)

    def shutdown(self):
        self.task_in_queue.put(STOP_BROKER)

    def run(self):
        shutdown = False
        while True:
            src, data = self.read_queue.get()

            if src == self.result_queue:
                print 'result', data
                worker_id = data.sender
                self.worker.put(worker_id)
                self.render_queue.remove(data.id)
                response_queue = self.response_queues.pop(data._uid)
                response_queue.put(data)

            elif src == self.task_in_queue:
                if data == STOP_BROKER:
                    shutdown = True
                else:
                    resp_queue = data.resp_queue
                    data.resp_queue = None
                    self.response_queues[data._uid] = resp_queue
                    self.render_queue.add(data)

            if self.render_queue.has_new_tasks() and self.worker.is_available():
                w = self.worker.get()
                task = self.render_queue.next()
                task.sender = hash(w)
                w.in_queue.put(task)

            if not self.render_queue.running and not self.render_queue.has_new_tasks() and shutdown:
                break



def main():

    worker_pool = WorkerPool(Worker, 10)

    b = Broker(worker_pool)
    b.start()

    resp_queue = Queue.Queue()

    n = 30

    for i in range(n):
        if i % 2:
            b.dispatch(Task(i, 0.5, priority=10, resp_queue=resp_queue))
        else:
            b.dispatch(Task(i, 0.05, priority=20, resp_queue=resp_queue))

    for i in range(n):
        if i % 2:
            b.dispatch(Task(i, 0.2, priority=10, resp_queue=resp_queue))
        else:
            b.dispatch(Task(i, 0.02, priority=20, resp_queue=resp_queue))

    for i in range(n*2):
        print resp_queue.get()
    b.shutdown()

    # for i in range(n):
        # print b.result_queue.get()

if __name__ == '__main__':
    main()
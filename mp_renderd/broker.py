import time
import Queue
import threading

from mp_renderd.queue import fan_in_queue

import logging
log = logging.getLogger(__name__)

STOP_BROKER = '696054488d18402b9155a531e0a31714'

class Broker(threading.Thread):
    check_interval = 30

    def __init__(self, worker, render_queue):
        threading.Thread.__init__(self)
        self.daemon = True
        self.task_in_queue = Queue.Queue()
        self.render_queue = render_queue

        self.response_queues = {}
        self.worker = worker
        self.result_queue = self.worker.result_queue

        self.read_queue = fan_in_queue([self.result_queue, self.task_in_queue])

    def dispatch(self, task, response_queue=None):
        if response_queue is None:
            q = Queue.Queue()
            self.task_in_queue.put((task, q))
            return q.get()
        else:
            self.task_in_queue.put((task, response_queue))

    def dispatch_background(self, task):
        self.task_in_queue.put((task, None))

    def shutdown(self):
        self.task_in_queue.put(STOP_BROKER)

    def run(self):
        shutdown = False
        next_check = time.time() + self.check_interval
        while True:
            if next_check < time.time():
                self.worker.check_processes()
                next_check = time.time() + self.check_interval

            try:
                src, data = self.read_queue.get(timeout=10)
            except Queue.Empty:
                continue

            # new tasks
            if src == self.task_in_queue:
                if data == STOP_BROKER:
                    shutdown = True
                else:
                    task, resp_queue = data
                    log.debug('new task (prio: %s): %s %s ', task.priority, task.id, task.doc)
                    self.response_queues[task.request_id] = resp_queue
                    self.render_queue.add(task)

            # results from workers
            elif src == self.result_queue:
                log.debug('result from %s (prio: %s): %s %s', data.worker_id, data.priority, data.id, data.doc)
                self.worker.put(data.worker_id)
                orig_requests = self.render_queue.remove(data.id)
                for req in orig_requests:
                    response_queue = self.response_queues.pop(req.request_id)
                    if response_queue:
                        response_queue.put(data)

            while True:
                # distribute tasks to workers
                if self.render_queue.has_new_tasks() and self.worker.is_available():
                    task = self.render_queue.next()
                    if self.render_queue.already_running(task):
                        log.info('task %s already running - running: %d - waiting: %d',
                            task.id, self.render_queue.running, self.render_queue.waiting)
                        continue
                    log.info('distributing task %s (prio: %s) - running: %d - waiting: %d',
                        task.id, task.priority, self.render_queue.running, self.render_queue.waiting)
                    w = self.worker.get()
                    w.dispatch(task)
                break

            if not self.render_queue.running and not self.render_queue.has_new_tasks() and shutdown:
                break

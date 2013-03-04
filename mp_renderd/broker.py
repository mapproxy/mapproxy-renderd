import multiprocessing
import time
import collections
import Queue
import threading

from mp_renderd.queue import STOP, fan_in_queue, RenderQueue, Task

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

class AvailableWorkers(object):
    def __init__(self, workers):
        self.workers = dict((hash(w), w) for w in workers)
        self.available = set(workers)
        self.inuse = set()

    def is_available(self):
        return bool(self.available)

    def get(self):
        worker = self.available.pop()
        self.inuse.add(worker)
        return worker

    def put(self, worker_id):
        worker = self.workers[worker_id]
        self.inuse.remove(worker)
        self.available.add(worker)

STOP_BROKER = '696054488d18402b9155a531e0a31714'

class Broker(threading.Thread):
    def __init__(self, worker_cls, num_worker=4):
        threading.Thread.__init__(self)
        self.worker_cls = worker_cls
        self.num_worker = num_worker
        self.result_queue = multiprocessing.Queue()
        self.task_in_queue = Queue.Queue()
        self.render_queue = RenderQueue([0, 0, 10, 20])
        self.read_queue = fan_in_queue([self.result_queue, self.task_in_queue])
        workers = []

        for i in range(num_worker):
            q = multiprocessing.Queue()
            w = worker_cls(q, self.result_queue)
            w.start()
            workers.append(w)

        self.worker = AvailableWorkers(workers)

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

            elif src == self.task_in_queue:
                if data == STOP_BROKER:
                    shutdown = True
                else:
                    self.render_queue.add(data)

            if self.render_queue.has_new_tasks() and self.worker.is_available():
                w = self.worker.get()
                task = self.render_queue.move_next_to_running()
                task.sender = hash(w)
                w.in_queue.put(task)

            if not self.render_queue.running and not self.render_queue.has_new_tasks() and shutdown:
                break

def main():
    b = Broker(Worker)
    b.start()


    n = 30

    for i in range(n):
        if i % 2:
            b.dispatch(Task(i, 0.5, priority=10))
        else:
            b.dispatch(Task(i, 0.05, priority=20))

    for i in range(n):
        if i % 2:
            b.dispatch(Task(i, 0.5, priority=10))
        else:
            b.dispatch(Task(i, 0.05, priority=20))


    b.shutdown()

    # for i in range(n):
        # print b.result_queue.get()

if __name__ == '__main__':
    main()
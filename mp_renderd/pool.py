import multiprocessing

import logging
log = logging.getLogger(__name__)

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
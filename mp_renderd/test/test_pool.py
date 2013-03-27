import multiprocessing
import uuid
import time
from mp_renderd.pool import WorkerPool

class DummyWorker(multiprocessing.Process):
    def __init__(self, in_queue, out_queue):
        self.id = uuid.uuid4().hex
        multiprocessing.Process.__init__(self)

    def run(self):
        time.sleep(0.1)

def test_clear_check_processes():
    pool = WorkerPool(DummyWorker, 2)
    assert pool.is_available()
    time.sleep(.2)
    pool.clear_dead_processes()
    assert not pool.is_available()
    pool.check_processes()
    assert pool.is_available()

def test_available_worker():
    pool = WorkerPool(DummyWorker, 2)

    assert pool.is_available()
    w1 = pool.get()
    assert pool.is_available()

    w2 = pool.get()
    assert not pool.is_available()

    try:
        pool.get()
    except KeyError:
        pass
    else:
        assert False, 'expected KeyError'

    assert w1 != w2

    pool.put(w2.id)
    assert pool.is_available()

    w3 = pool.get()
    assert not pool.is_available()

    assert w2 is w3

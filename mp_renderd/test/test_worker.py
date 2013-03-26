import multiprocessing
import uuid
from mp_renderd.pool import WorkerPool

class DummyWorker(multiprocessing.Process):
    def __init__(self, in_queue, out_queue):
        self.id = uuid.uuid4().hex
        multiprocessing.Process.__init__(self)

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

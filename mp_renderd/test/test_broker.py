import os
import time
import Queue
import tempfile
import shutil
import random

from mp_renderd.broker import BaseWorker, Broker, WorkerPool
from mp_renderd.queue import RenderQueue
from mp_renderd.queue import Task

from nose.tools import eq_

import logging
log = logging.getLogger(__name__)

class TestWorker(BaseWorker):
    def do_nothing(self, doc):
        return {}

    def do_echo(self, doc):
        return doc

    def do_sleep(self, doc):
        log.debug('sleeping %s', doc['time'])
        time.sleep(doc['time'])
        return doc

    def do_touch_file(self, doc):
        open(doc['filename'], 'w').close()
        return {}

    def do_exception(self, doc):
        raise Exception('foo')

class TestBroker(object):
    def setup(self):
        queue = RenderQueue([0, 0, 0, 50])
        worker = WorkerPool(TestWorker, 4)
        self.broker = Broker(worker=worker, render_queue=queue)
        self.broker.start()

    def teardown(self):
        self.broker.stop()

    def test_worker_exception(self):
        resp = self.broker.dispatch(Task(1, {'command': 'exception'}))
        eq_(resp.doc['status'], 'error')
        assert 'foo' in resp.doc['error_message']

    def test_synchronous(self):
        resp = self.broker.dispatch(Task(1, {'command': 'echo'}))
        eq_(resp.doc, {'status': 'ok', 'command': 'echo'})

    def test_asychronous(self):
        q = Queue.Queue()

        # tasks with same prio should come in right order
        for i in range(10):
            self.broker.dispatch(Task(i, {'command': 'sleep', 'time': 0.01 * i}, priority=0), q)

        results = []
        for i in range(10):
            resp = q.get()
            assert resp.doc['status'] == 'ok'
            results.append(resp.id)

        assert results == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

        for i in range(10):
            self.broker.dispatch(Task(i, {'command': 'sleep', 'time': 0.01 * i}, priority=i), q)

        results = []
        for i in range(10):
            resp = q.get()
            assert resp.doc['status'] == 'ok'
            results.append(resp.id)

        assert results != [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    def test_background(self):
        tmp = tempfile.mkdtemp()
        try:
            for i in range(10):
                self.broker.dispatch_background(Task(i, {'command': 'touch_file', 'filename': os.path.join(tmp, str(i))}, priority=10))

            # dispatch_background should return immediately, so we should not have all files
            assert sorted(os.listdir(tmp)) != ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

            # send blocking low priority task to wait for all background tasks
            self.broker.dispatch(Task(99, {'command': 'sleep', 'time': 0.05}, priority=0))

            # now we should have all files
            assert sorted(os.listdir(tmp)) == ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

        finally:
            shutil.rmtree(tmp)

    def test_fuzz(self):
        q = Queue.Queue()
        for i in range(100):
            self.broker.dispatch(
                Task(i, {'command': 'sleep', 'time': random.uniform(0.001, 0.05)}, priority=random.randint(1, 100)),
                q)
            if random.random() < 0.1:
                self.broker.dispatch_background(
                Task(i+100, {'command': 'exception'}, priority=random.randint(1, 100)))

        results = []
        for i in range(100):
            resp = q.get()
            assert resp.doc['status'] == 'ok'
            results.append(resp.id)

        assert sorted(results) == list(range(100))


    def test_same_ids(self):
        q = Queue.Queue()

        for i in range(20):
            # add task with same id, task with higher prio and shorter sleep time
            # should do the "work" in most cases
            # other task will get the response from the task that ran
            self.broker.dispatch(
                Task(i, {'command': 'sleep', 'time': 0.01}, priority=(i*2)+1),
                q)
            self.broker.dispatch(
                Task(i, {'command': 'sleep', 'time': 0.5}, priority=i*2),
                q)

        results = []
        times = {0.01: 0, 0.5: 0}
        for i in range(2*20):
            resp = q.get()
            assert resp.doc['status'] == 'ok'
            times[resp.doc['time']] += 1
            results.append(resp.id)


        assert sorted(results) == sorted(list(range(20)) * 2)
        # check that at most 10 tasks where not combined
        assert times[0.5] <= 10, "timing related test, check again"


    def test_parallel(self):
        # simulate 1000 waiting clients
        queues = []
        for i in range(1000):
            queues.append(Queue.Queue())
            self.broker.dispatch(
                Task(99999, {'command': 'sleep', 'time': 1}, priority=10), queues[-1])
            self.broker.dispatch_background(
                Task(i, {'command': 'echo'}, priority=10))


        for q in queues:
            resp = q.get()
            assert resp.doc['status'] == 'ok'
            assert resp.id == 99999

# This file is part of the MapProxy project.
# Copyright (C) 2013 Omniscale GmbH & Co. KG <http://omniscale.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import multiprocessing

from mp_renderd.queue import STOP
from mp_renderd.task import Task

from nose.tools import eq_
from mp_renderd.worker import BaseWorker
from mp_renderd.worker import SeedWorker

class SleepWorker(BaseWorker):
    def do_sleep(self, doc):
        time.sleep(doc['time'])
        return {}

class TestSleepWorker(object):
    def setup(self):
        self.in_queue = multiprocessing.Queue(2)
        self.out_queue = multiprocessing.Queue(2)
        self.worker = SleepWorker(in_queue=self.in_queue, out_queue=self.out_queue)

    def test_start_stop(self):
        self.worker.start()
        assert self.worker.is_alive()

        self.in_queue.put(STOP)
        time.sleep(0.1)
        assert not self.worker.is_alive()

    def test_dispatch(self):
        self.worker.dispatch(Task('foo', doc={'command': 'sleep', 'time': 0}))
        assert self.worker.handle_task_message()
        result = self.out_queue.get()
        eq_(result.doc, {'status': 'ok'})

class TestBaseWorker(object):
    def setup(self):
        self.in_queue = multiprocessing.Queue(2)
        self.out_queue = multiprocessing.Queue(2)
        self.worker = BaseWorker(in_queue=self.in_queue, out_queue=self.out_queue)

    def test_dispatch_unknown_command(self):
        self.worker.dispatch(Task('foo', doc={'command': 'foo'}))
        assert self.worker.handle_task_message()
        result = self.out_queue.get()
        eq_(result.doc, {
            'status': 'error',
            'error_message': 'unknown command: foo',
        })
    def test_stop(self):
        self.worker.in_queue.put(STOP)
        assert not self.worker.handle_task_message()

class ExceptionWorker(BaseWorker):
    def do_exception(self, doc):
        raise ValueError('foo')

class TestSleepWorker(object):
    def setup(self):
        self.in_queue = multiprocessing.Queue(2)
        self.out_queue = multiprocessing.Queue(2)
        self.worker = ExceptionWorker(in_queue=self.in_queue, out_queue=self.out_queue)

    def test_dispatch(self):
        self.worker.dispatch(Task('foo', doc={'command': 'exception'}))
        assert self.worker.handle_task_message()
        result = self.out_queue.get()
        eq_(result.doc['status'], 'error')
        eq_(result.doc['error_message'], "exception while processing 'exception': foo")
        assert 'raise ValueError' in result.doc['error_detail']

class DummyCache(object):
    def __init__(self):
        self.requested_tiles = []

    def load_tile_coords(self, tiles):
        self.requested_tiles.extend(tiles)

class TestSeedWorker(object):
    def setup(self):
        self.in_queue = multiprocessing.Queue(2)
        self.out_queue = multiprocessing.Queue(2)
        self.caches = {
            'test_cache': DummyCache()
        }
        self.worker = SeedWorker(
            caches=self.caches,
            base_config={},
            in_queue=self.in_queue,
            out_queue=self.out_queue,
        )

    def test_create_tile(self):
        self.worker.dispatch(Task('foo', doc={'command': 'tile', 'cache_identifier': 'test_cache', 'tiles': [[0, 0, 0]]}))
        assert self.worker.handle_task_message()
        result = self.out_queue.get()
        eq_(result.doc, {'status': 'ok'})
        eq_(self.caches['test_cache'].requested_tiles, [(0, 0, 0)])

    def test_create_tile_unknown_cache(self):
        self.worker.dispatch(Task('foo', doc={'command': 'tile', 'cache_identifier': 'unknown', 'tiles': [[0, 0, 0]]}))
        assert self.worker.handle_task_message()
        result = self.out_queue.get()
        eq_(result.doc, {'status': 'error', 'error_message': "unknown cache 'unknown'"})

        eq_(self.caches['test_cache'].requested_tiles, [])



    def test_start_create_tiles_stop(self):
        # use manager.list to receive requested_tiles from worker process
        manager = multiprocessing.Manager()
        self.caches['test_cache'].requested_tiles = manager.list()
        self.worker.start()

        self.worker.dispatch(Task('foo', doc={'command': 'tile', 'cache_identifier': 'test_cache', 'tiles': [[0, 0, 0]]}))
        self.worker.dispatch(Task('foo', doc={'command': 'tile', 'cache_identifier': 'test_cache', 'tiles': [[5, 0, 0], [5, 1, 0], [5, 2, 0]]}))
        self.worker.dispatch(Task('foo', doc={'command': 'tile', 'cache_identifier': 'test_cache', 'tiles': [[2, 3, 4]]}))
        self.in_queue.put(STOP)

        for _ in range(3):
            result = self.out_queue.get()
            eq_(result.doc, {'status': 'ok'})

        eq_(list(self.caches['test_cache'].requested_tiles), [(0, 0, 0), (5, 0, 0), (5, 1, 0), (5, 2, 0), (2, 3, 4)])
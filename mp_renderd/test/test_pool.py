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

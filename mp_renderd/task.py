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

import uuid

class Task(object):
    """
    Task for worker.

    :param sender: opaque object to identify response receiver
    :param id: id for this task. identical tasks should share the same id,
        (e.g. requests for the same meta tile)
    :param doc: the task as JSON
    """
    def __init__(self, id, doc, resp_queue=None, priority=None):
        self.id = id
        self.doc = doc
        self.priority = priority
        self.resp_queue = resp_queue
        self.request_id = uuid.uuid4().hex
        self.worker_id = None

    def __repr__(self):
        return '<Task id=%s, priority=%s>' % (self.id, self.priority)

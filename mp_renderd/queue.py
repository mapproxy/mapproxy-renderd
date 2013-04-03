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

import heapq
import time
import threading
import Queue

class RenderQueue(object):
    def __init__(self, process_min_priorities, default_priority=50):
        process_min_priorities = sorted(process_min_priorities)
        self._min_priority = process_min_priorities[0]
        assert default_priority >= self._min_priority
        self.running_tasks = RunningTasks(process_min_priorities)
        self.tasks = PriorityTaskQueue(default_priority)

    @property
    def running(self):
        return len(self.running_tasks)

    @property
    def waiting(self):
        return len(self.tasks)

    def add(self, task):
        assert task.priority is None or task.priority >= self._min_priority
        self.tasks.add(task)

    def remove(self, task_id):
        return self.running_tasks.remove(task_id)

    def has_new_tasks(self):
        if not self.tasks:
            return False
        next_task = self.tasks.peek()
        return self.running_tasks.process_available(next_task)

    def has_running_tasks(self):
        """
        Return ``True`` if there is at least one running task.
        """
        return self.running_tasks

    def already_running(self, task):
        """
        Return ``True`` if a task with ``task.id`` is already running.
        Returns ``False`` if only `task` itself runs with that ``id``.
        """
        return task in self.running_tasks

    def next(self):
        """
        Returns the next task to run. Marks the task as running.
        """
        assert self.has_new_tasks()
        task = self.tasks.pop()
        self.running_tasks.add(task)
        return task

class RunningTasks(object):
    """
    Store running tasks and group them by ``task.id``.
    """
    def __init__(self, process_min_priorities):
        self.running = {}
        self.process_min_priorities = sorted(process_min_priorities)

    def __contains__(self, task):
        if task.id not in self.running:
            return False
        if task in self.running[task.id]:
            # exclude task
            return len(self.running[task.id]) >= 2
        else:
            return len(self.running[task.id]) >= 1

    def process_available(self, task):
        num_running = len(self.running)
        num_procs = len(self.process_min_priorities)
        if num_running >= num_procs:
            return False

        required_priority = self.process_min_priorities[num_running]
        return required_priority <= task.priority

    def add(self, task):
        """
        Mark a new task as running.
        """
        self.running.setdefault(task.id, []).append(task)

    def remove(self, id):
        """
        Remove running tasks by id. Returns a list of all tasks
        with that `id`.
        """
        return self.running.pop(id)

    def __len__(self):
        return len(self.running)

class PriorityTaskQueue(object):
    """
    Queue for tasks. Tasks are ordered by priority (highest first)
    then date (oldest first).
    """
    def __init__(self, default_priority=50):
        self._tasks = []
        self.default_priority = default_priority

    def add(self, task):
        if task.priority is None:
            task.priority = self.default_priority

        # self._tasks is a min-heap
        # invert priority to get that a large value is a high priority
        heapq.heappush(self._tasks, (-task.priority, time.time(), task))

    def pop(self):
        """
        Return the task with the highes priority (oldest first).
        """
        if not self._tasks:
            raise IndexError('pop from empty PriorityTaskQueue')
        prio_, time_, task = heapq.heappop(self._tasks)
        return task

    def peek(self):
        """
        Return the task with the highes priority (oldest first)
        without removing it from the queue.
        """
        if not self._tasks:
            raise IndexError('peek from empty PriorityTaskQueue')
        return self._tasks[0][2]

    def __len__(self):
        return len(self._tasks)


# random but static sentiel for queue shutdown
STOP = '91bc1c48397845b3b1738d9df3666c94'

class QueueForwarder(threading.Thread):
    def __init__(self, in_queue, out_queue):
        self.in_queue = in_queue
        self.out_queue = out_queue
        threading.Thread.__init__(self)
        self.daemon = True

    def run(self):
        while True:
            item = self.in_queue.get()
            self.out_queue.put((self.in_queue, item))
            if item == STOP:
                break

class QueueFanIn(threading.Thread):
    def __init__(self, in_queues, out_queue):
        self.in_queues = set(in_queues)
        self.out_queue = out_queue
        self._tmp_queue = Queue.Queue()
        threading.Thread.__init__(self)
        self.daemon = True

        for q in self.in_queues:
            QueueForwarder(q, self._tmp_queue).start()

    def run(self):
        while True:
            item = self._tmp_queue.get()
            if item[1] == STOP:
                self.in_queues.remove(item[0])
                if not self.in_queues:
                    self.out_queue.put(STOP)
                    break
            else:
                self.out_queue.put(item)

def fan_in_queue(queues):
    out = Queue.Queue()
    QueueFanIn(queues, out).start()
    return out

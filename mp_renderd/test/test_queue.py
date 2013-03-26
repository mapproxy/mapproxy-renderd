from mp_renderd.queue import PriorityTaskQueue, RunningTasks, RenderQueue
from mp_renderd.task import Task

from nose.tools import raises, eq_

def task(name, priority=None):
    return Task(id=name, doc=name, priority=priority)

class TestPriorityTaskQueue(object):
    def test_empty(self):
        q = PriorityTaskQueue()
        assert bool(q) == False

    def test_len(self):
        q = PriorityTaskQueue()
        eq_(len(q), 0)
        q.add(task('foo'))
        eq_(len(q), 1)
        q.add(task('bar'))
        eq_(len(q), 2)
        q.pop()
        eq_(len(q), 1)
        q.pop()
        eq_(len(q), 0)

    @raises(IndexError)
    def test_pop_empty(self):
        q = PriorityTaskQueue()
        q.pop()

    def test_add_prio(self):
        q = PriorityTaskQueue() # default_priority = 50
        q.add(task('high1', 100))
        q.add(task('default'))
        q.add(task('high2', 100))
        q.add(task('low', 50)) # same as default but later
        q.add(task('high3', 100))

        eq_(q.pop().id, 'high1')
        eq_(q.pop().id, 'high2')
        eq_(q.pop().id, 'high3')
        eq_(q.pop().id, 'default')
        q.add(task('high4', 100))
        eq_(q.pop().id, 'high4')
        eq_(q.pop().id, 'low')

        assert bool(q) == False

    def test_default_prio(self):
        q = PriorityTaskQueue(100)
        q.add(task('default'))
        q.add(task('low', 50))
        q.add(task('high', 110))

        eq_(q.pop().id, 'high')
        eq_(q.pop().id, 'default')
        eq_(q.pop().id, 'low')

        assert bool(q) == False

class TestRunningTasks(object):

    @raises(KeyError)
    def test_remove_unknown_id(self):
        r = RunningTasks([0, 0, 0])
        r.remove('foo')

    def test_add(self):
        r = RunningTasks([0, 0, 0])
        eq_(len(r), 0)
        r.add(task('bar'))
        eq_(len(r), 1)

        tasks = r.remove('bar')
        eq_(tasks[0].id, 'bar')
        eq_(len(r), 0)

    def test_add_waitinglist(self):
        r = RunningTasks([0, 0, 0])

        t = task('foo')
        assert t not in r
        r.add(task('foo'))
        r.add(task('foo'))
        r.add(task('foo'))

        eq_(len(r), 1)

        tasks = r.remove('foo')
        eq_(len(tasks), 3)

    def test_process_available(self):
        r = RunningTasks([0, 0, 10, 60])

        # []
        assert r.process_available(task('low1', 0))
        r.add(task('low1', 0))
        r.add(task('low2', 0))

        # [low1, low2]
        assert not r.process_available(task('low3', 0))
        assert r.process_available(task('mid', 10))
        r.add(task('mid', 10))

        # [low1, low2, mid]
        assert not r.process_available(task('mid', 10))
        assert not r.process_available(task('mid', 59))
        assert r.process_available(task('high1', 60))
        r.add(task('high1', 60))

        # [low1, low2, mid, high1]
        assert not r.process_available(task('high2', 100))
        r.remove('mid')

        # [low1, low2, high1]
        assert r.process_available(task('high2', 60))
        r.add(task('high2', 60))

        # [low1, low2, high1, high2]
        r.remove('low1')
        # [low2, high1, high2]
        assert not r.process_available(task('low1', 0))
        assert not r.process_available(task('mid', 10))

        r.remove('low2')
        r.remove('high1')
        r.remove('high2')

        # []
        assert r.process_available(task('low1', 0))

class TestRenderQueue(object):

    def test_move_without_matching_next(self):
        q = RenderQueue([0], default_priority=50)
        q.add(task('low1', 0))
        q.add(task('low2', 0))
        q.next()

        assert not q.has_new_tasks()
        try:
            q.next()
        except AssertionError:
            pass
        else:
            raise False, 'Expected AssertionError'

    @raises(AssertionError)
    def test_min_priority_check(self):
        q = RenderQueue([10], default_priority=50)
        q.add(task('foo', 0))

    def test_already_running(self):
        q = RenderQueue([0, 0], default_priority=50)
        t1 = task('foo', 0)
        t2 = task('foo', 0)
        q.add(t1)
        q.add(t2)
        eq_(q.running, 0)
        eq_(q.waiting, 2)

        assert not q.already_running(t1)
        assert not q.already_running(t2)
        eq_(q.next(), t1)
        eq_(q.running, 1)
        eq_(q.waiting, 1)

        assert not q.already_running(t1)
        assert q.already_running(t2)
        eq_(q.next(), t2)
        eq_(q.running, 1)
        eq_(q.waiting, 0)

        eq_(q.remove('foo'), [t1, t2])
        assert not q.already_running(t1)
        eq_(q.running, 0)
        eq_(q.waiting, 0)

    def test_render_queue(self):
        q = RenderQueue([0, 10], default_priority=50)
        tl1, tl2, tl3 = task('low1', 2), task('low2', 1), task('low3', 0)
        tm1, tm2 = task('mid1'), task('mid2', 60) # default
        assert not q.has_new_tasks()
        q.add(tl1)
        assert q.has_new_tasks()
        q.add(tl2)
        q.add(tl3)
        # [low1, low2, low3], []
        eq_(q.waiting, 3)

        eq_(q.next(), tl1)
        assert not q.has_new_tasks()
        # [low2, low3], [low1]
        eq_(q.waiting, 2)
        eq_(q.running, 1)

        q.add(tm1)
        q.add(tm2)
        # [tm2, tm1, low2, low3], [low1]
        assert q.has_new_tasks()
        eq_(q.next(), tm2)
        assert not q.has_new_tasks()
        # [tm1, low2, low3], [low1, tm2]

        q.remove(tl1.id)
        # [tm1, low2, low3], [tm2]
        assert q.has_new_tasks()
        eq_(q.next(), tm1)
        # [low2, low3], [tm2, tm1]

        assert not q.has_new_tasks()
        q.remove(tm1.id)
        # [low2, low3], [tm2]
        assert not q.has_new_tasks()

        q.remove(tm2.id)
        # [low2, low3], []
        assert q.has_new_tasks()
        eq_(q.next(), tl2)
        assert not q.has_new_tasks()
        q.remove(tl2.id)
        assert q.has_new_tasks()
        eq_(q.next(), tl3)


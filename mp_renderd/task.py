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

import os
import multiprocessing
import time
import uuid

from mp_renderd.queue import STOP

import logging
log = logging.getLogger(__name__)

class BaseWorker(multiprocessing.Process):
    def __init__(self, in_queue, out_queue):
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.id = uuid.uuid4().hex
        multiprocessing.Process.__init__(self)
        self.daemon = True

    def dispatch(self, task):
        task.worker_id = self.id
        self.in_queue.put(task)

    def run(self):
        log.debug('proc %d started', os.getpid())
        while True:
            try:
                if not self.handle_task_message():
                    return
            except KeyboardInterrupt:
                return

    def handle_task_message(self):
        task = self.in_queue.get()
        if task == STOP:
            return False

        req_doc = task.doc
        command = req_doc.get('command', 'None')
        method = getattr(self, 'do_' + command, None)
        if not method:
            resp = {
                'status': 'error',
                'error_message': 'unknown command: %s' % command
            }
        else:
            try:
                resp = method(req_doc)
                if resp is None:
                    resp = {}
            except Exception, ex:
                resp = {
                    'status': 'error',
                    'error_message': repr(ex)
                }
            else:
                if not resp.get('status'):
                    resp['status'] = 'ok'

        # resp['id'] = req_doc['id']
        # resp['uid'] = req_doc['uid']
        # resp['_worker_id'] = req_doc['_worker_id']

        task.doc = resp
        self.out_queue.put(task)
        return True


class SleepWorker(BaseWorker):
    def __init__(self, **kw):
        BaseWorker.__init__(self, **kw)

    def do_sleep(self, doc):
        time.sleep(doc['time'])
        return {}

class SeedWorker(BaseWorker):
    def __init__(self, caches, base_config, **kw):
        self.caches = caches
        self.base_config = base_config
        BaseWorker.__init__(self, **kw)

    def do_sleep(self, doc):
        time.sleep(doc['time'])
        return {}

    def do_echo(self, doc):
        return doc

    def do_tile(self, doc):
        from mapproxy.util import local_base_config

        cache = self.caches.get(doc['cache_identifier'])
        if not cache:
            return {
                'status': 'error',
                'error_message': 'unknown cache %s' % doc['cache_identifier']
            }

        tiles = [tuple(coord) for coord in doc['tiles'] if coord]
        with local_base_config(self.base_config):
            cache.load_tile_coords(tiles)
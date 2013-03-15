import uuid
import json
import textwrap

from mp_renderd.queue import Task
from mapproxy.request.base import Request as _Request
from mapproxy.response import Response

import logging
log = logging.getLogger(__name__)


try:
    from cherrypy.wsgiserver import CherryPyWSGIServer; CherryPyWSGIServer
except ImportError:
    from mp_renderd.ext.wsgiserver import CherryPyWSGIServer

__all__ = ['CherryPyWSGIServer', 'Request']

class Request(_Request):
    _body = None

    def body(self):
        if self._body is None:
            body_length = int(self.environ.get('CONTENT_LENGTH', 0))
            self._body = self.environ['wsgi.input'].read(body_length)
        return self._body

class RenderdApp(object):
    def __init__(self, broker):
        self.broker = broker

    def __call__(self, environ, start_response):
        req = Request(environ)
        try:
            if req.path == '/':
                resp = self.do_request(req)
            elif req.path == '/status':
                resp = self.do_status(req)
            else:
                resp = Response(json.dumps({'status': 'error', 'error_message': 'endpoint not found'}),
                    content_type='application/json', status=404)
        except Exception, ex:
            resp = Response(json.dumps({'status': 'error', 'error_message': 'internal error: %s' % ex.args[0]}),
                content_type='application/json', status=500)

        return resp(environ, start_response)

    def do_request(self, req):
        req = json.loads(req.body())
        log.info('got request: %s', req)

        req_id = req.get('id')
        if not req_id:
            req_id = uuid.uuid4().hex
        resp = self.broker.dispatch(Task(req_id, req, priority=req.get('priority', 10)))
        log.info('got resp: %s', resp)
        return Response(json.dumps(resp.doc), content_type='application/json')

    def do_status(self, req):
        body = """\
        running: %d
        waiting: %d
        worker: %d
        """ % (
            self.broker.render_queue.running,
            self.broker.render_queue.waiting,
            self.broker.worker.pool_size,
        )
        body = textwrap.dedent(body)

        return Response(body, content_type='text/plain')

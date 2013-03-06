from mapproxy.request.base import Request as _Request

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


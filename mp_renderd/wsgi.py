from mapproxy.request.base import Request as _Request

__all__ = ['Request']

class Request(_Request):
    _body = None

    def body(self):
        if self._body is None:
            body_length = int(self.environ.get('CONTENT_LENGTH', 0))
            self._body = self.environ['wsgi.input'].read(body_length)

        return self._body


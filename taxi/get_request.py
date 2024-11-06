"""
https://stackoverflow.com/questions/4716330/accessing-the-users-request-in-a-post-save-signal
"""
from threading import current_thread
from django.utils.deprecation import MiddlewareMixin

_requests = {}


def current_request():
    return _requests.get(current_thread().ident, None)


class RequestMiddleware(MiddlewareMixin):

    def process_request(self, request):
        _requests[current_thread().ident] = request

    def process_response(self, request, response):
        # when response is ready, request should be flushed
        _requests.pop(current_thread().ident, None)
        return response


    def process_exception(self, request, exception):
        # if an exception has happened, request should be flushed too
         _requests.pop(current_thread().ident, None)
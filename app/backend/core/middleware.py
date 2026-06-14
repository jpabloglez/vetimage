"""Core middleware: request-id propagation for log correlation + tracing."""
from .observability import set_request_id, get_request_id, new_request_id

REQUEST_ID_HEADER = 'X-Request-ID'


class RequestIDMiddleware:
    """
    Assign a request id to every request and echo it on the response.

    Honours an inbound `X-Request-ID` (e.g. set by a reverse proxy / load
    balancer) so a single id can be traced across services; otherwise generates
    one. The id is stored in a context var (see core.observability) so all log
    records emitted during the request carry it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.META.get('HTTP_X_REQUEST_ID', '').strip()
        request_id = incoming or new_request_id()
        set_request_id(request_id)
        request.request_id = request_id

        response = self.get_response(request)

        response[REQUEST_ID_HEADER] = get_request_id()
        return response

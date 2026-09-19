"""Core middleware: request-id propagation for log correlation + tracing,
and the security response headers Django doesn't set on its own."""
from django.conf import settings

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


class SecurityHeadersMiddleware:
    """
    Add the response security headers Django's SecurityMiddleware doesn't cover.

    Scope note: this only protects Django-rendered pages — the admin, Swagger
    UI, ReDoc, and the DRF browsable API. The React SPA is served by a separate
    container, so its CSP is set there (see app/frontend/vite.config.ts) and
    must be reproduced by whatever serves the built bundle in production.

    CSP is **enforced** by default (CSP_ENFORCE=False falls back to report-only,
    which is the right setting while shaking out a new directive). It was
    report-only until a browser run over the admin, Swagger UI, ReDoc and the
    DRF browsable API measured what actually violated it; see
    `tests/test_csp.py` and settings for what that found.

    The docs pages get a slightly wider policy than everything else — Swagger
    and ReDoc load two CDN images and spawn a blob-backed worker. That widening
    is scoped to those two URLs rather than folded into the base policy,
    because the same policy covers the Django admin, and quietly relaxing the
    admin to satisfy a docs page is how a CSP ends up present but pointless.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.enforce = getattr(settings, 'CSP_ENFORCE', False)
        self.policy = getattr(settings, 'CONTENT_SECURITY_POLICY', '')
        self.docs_policy = getattr(settings, 'CONTENT_SECURITY_POLICY_DOCS', '') or self.policy
        self.docs_paths = tuple(getattr(settings, 'CSP_DOCS_PATHS', ()))

    def __call__(self, request):
        response = self.get_response(request)

        if self.policy:
            header = (
                'Content-Security-Policy' if self.enforce
                else 'Content-Security-Policy-Report-Only'
            )
            is_docs = self.docs_paths and request.path.startswith(self.docs_paths)
            response.setdefault(header, self.docs_policy if is_docs else self.policy)

        # Don't leak the full URL (which can carry tokens or record ids) to
        # third-party origins on outbound navigation.
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        # This is a medical imaging tool; it needs none of these device APIs.
        response.setdefault(
            'Permissions-Policy',
            'geolocation=(), microphone=(), camera=(), payment=(), usb=()',
        )
        return response

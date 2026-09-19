"""
Receiver for CSP violation reports.

A Content-Security-Policy that reports nowhere is only as good as the last
person who happened to have devtools open. Both of this project's policies
shipped report-only for months with no `report-uri`, so the "clean report-only
run" their comments asked for before enforcing was never something anyone could
actually observe — which is why the flip sat undone.

With enforcement on, the stakes invert: a directive that is too narrow no
longer degrades to a console warning, it breaks the page. This endpoint is what
makes that failure visible — in the logs, correlated by request id, next to
everything else.

It is deliberately log-only. A model would need a migration, a retention
policy, and a purge job for data that is high-volume, low-value once read, and
attacker-influenced. The observability stack already ships structured JSON logs
and optional Sentry; violations belong there.
"""

import json
import logging

from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

#: Browsers post reports under their own content types, never as normal JSON.
#: `application/csp-report` is the classic `report-uri` body (Firefox, Safari);
#: `application/reports+json` is the Reporting API batch (Chrome).
REPORT_CONTENT_TYPES = (
    'application/csp-report',
    'application/reports+json',
    'application/json',
)

#: Cap what we copy out of a report. The fields are attacker-influenced — a
#: hostile page can post whatever it likes here — so they are truncated before
#: they reach a log line, and never interpolated anywhere but a log value.
MAX_FIELD = 300


class CSPReportThrottle(AnonRateThrottle):
    scope = 'csp_report'


def _clip(value):
    if value is None:
        return None
    text = value if isinstance(value, str) else str(value)
    return text[:MAX_FIELD]


def _normalise(payload):
    """
    Flatten either report shape into one dict, or return None if it is neither.

    Returning None rather than raising matters: this endpoint is posted to by
    browsers we do not control and by anyone who finds the URL, and it must
    never turn junk into a 500 (which would be noise in exactly the channel
    this exists to keep clean).
    """
    if not isinstance(payload, dict):
        return None

    # report-uri shape: {"csp-report": {...}}
    body = payload.get('csp-report')
    if isinstance(body, dict):
        return {
            'directive': _clip(body.get('effective-directive') or body.get('violated-directive')),
            'blocked': _clip(body.get('blocked-uri')),
            'document': _clip(body.get('document-uri')),
            'source': _clip(body.get('source-file')),
            'line': body.get('line-number'),
            'disposition': _clip(body.get('disposition')),
        }

    # Reporting API shape: {"type": "csp-violation", "body": {...}}
    if payload.get('type') == 'csp-violation' and isinstance(payload.get('body'), dict):
        body = payload['body']
        return {
            'directive': _clip(body.get('effectiveDirective')),
            'blocked': _clip(body.get('blockedURL')),
            'document': _clip(body.get('documentURL') or payload.get('url')),
            'source': _clip(body.get('sourceFile')),
            'line': body.get('lineNumber'),
            'disposition': _clip(body.get('disposition')),
        }

    return None


@extend_schema(
    tags=['Security'],
    request=OpenApiTypes.OBJECT,
    responses={204: None},
    description=(
        'Receives Content-Security-Policy violation reports from browsers. '
        'Not called by application code; the browser posts here on its own '
        'when a policy directive is violated.'
    ),
)
class CSPReportView(APIView):
    """
    Accepts a browser's CSP violation report and logs it.

    Always answers 204, including for a body it cannot parse. A browser has
    nothing useful to do with an error here, and returning one only invites
    retries.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [CSPReportThrottle]
    parser_classes = []  # Read the raw body; browsers do not send normal JSON.

    def post(self, request, *args, **kwargs):
        content_type = (request.content_type or '').split(';')[0].strip()
        if content_type and content_type not in REPORT_CONTENT_TYPES:
            return Response(status=status.HTTP_204_NO_CONTENT)

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return Response(status=status.HTTP_204_NO_CONTENT)

        # Chrome batches several reports into one array.
        reports = payload if isinstance(payload, list) else [payload]
        for entry in reports[:20]:
            violation = _normalise(entry)
            if not violation:
                continue
            logger.warning(
                'CSP violation: %s blocked %s on %s',
                violation['directive'], violation['blocked'], violation['document'],
                extra={'csp_violation': violation},
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

"""
Observability helpers: request-id propagation + structured JSON logging.

A per-request id (from an inbound `X-Request-ID` header or freshly generated)
is stored in a context var so every log line emitted while handling the request
can be correlated, and is echoed back on the response. `JSONFormatter` renders
log records as one JSON object per line for ingestion by log aggregators.
"""
import datetime as _dt
import json
import logging
import uuid
from contextvars import ContextVar

# Context var survives across async/sync boundaries within a single request.
_request_id_ctx: ContextVar[str] = ContextVar('request_id', default='-')


def set_request_id(value: str) -> None:
    _request_id_ctx.set(value or '-')


def get_request_id() -> str:
    return _request_id_ctx.get()


def new_request_id() -> str:
    return uuid.uuid4().hex


class RequestIDFilter(logging.Filter):
    """Inject the current request id onto every log record as `request_id`."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class JSONFormatter(logging.Formatter):
    """Render a log record as a single-line JSON object."""

    # Standard LogRecord attributes we don't want duplicated in `extra`.
    _RESERVED = set(vars(logging.makeLogRecord({})).keys()) | {
        'message', 'asctime', 'request_id', 'taskName',
    }

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            'timestamp': _dt.datetime.fromtimestamp(
                record.created, _dt.timezone.utc
            ).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': getattr(record, 'request_id', '-'),
        }
        if record.exc_info:
            payload['exc_info'] = self.formatException(record.exc_info)
        # Surface any structured `extra={...}` fields.
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith('_'):
                try:
                    json.dumps(value)
                    payload[key] = value
                except (TypeError, ValueError):
                    payload[key] = repr(value)
        return json.dumps(payload, default=str)

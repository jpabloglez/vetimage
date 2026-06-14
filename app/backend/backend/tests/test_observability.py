"""
Tests for observability: request-id middleware + JSON log formatter.
"""
import json
import logging

import pytest
from rest_framework.test import APIClient

from core.observability import (
    JSONFormatter, RequestIDFilter, get_request_id, set_request_id, new_request_id,
)


@pytest.mark.django_db
class TestRequestIDMiddleware:
    def test_response_carries_generated_request_id(self):
        # Any endpoint works; health is unauthenticated.
        resp = APIClient().get('/api/health/')
        rid = resp.headers.get('X-Request-ID')
        assert rid and rid != '-'

    def test_inbound_request_id_is_echoed(self):
        resp = APIClient().get('/api/health/', HTTP_X_REQUEST_ID='trace-abc-123')
        assert resp.headers.get('X-Request-ID') == 'trace-abc-123'


class TestJSONFormatter:
    def test_formats_record_as_json_with_request_id(self):
        set_request_id('rid-42')
        record = logging.LogRecord(
            name='vetimage', level=logging.INFO, pathname=__file__, lineno=1,
            msg='hello %s', args=('world',), exc_info=None,
        )
        RequestIDFilter().filter(record)
        out = json.loads(JSONFormatter().format(record))
        assert out['message'] == 'hello world'
        assert out['level'] == 'INFO'
        assert out['logger'] == 'vetimage'
        assert out['request_id'] == 'rid-42'
        assert 'timestamp' in out

    def test_extra_fields_surface_in_json(self):
        record = logging.LogRecord(
            name='x', level=logging.WARNING, pathname=__file__, lineno=1,
            msg='m', args=(), exc_info=None,
        )
        record.task_id = 'task-7'
        out = json.loads(JSONFormatter().format(record))
        assert out['task_id'] == 'task-7'

    def test_request_id_default_when_unset(self):
        set_request_id('')  # reset
        assert get_request_id() == '-'
        assert new_request_id() != new_request_id()

"""
Tests for health check endpoints.
"""

import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


# ===========================================================================
# Liveness
# ===========================================================================


@pytest.mark.django_db
class TestHealthLiveness:

    def test_returns_200(self, client):
        response = client.get(reverse('health-liveness'))
        assert response.status_code == status.HTTP_200_OK

    def test_no_auth_required(self, client):
        """Endpoint must be accessible without credentials."""
        response = client.get(reverse('health-liveness'))
        assert response.status_code == status.HTTP_200_OK

    def test_response_has_status_field(self, client):
        response = client.get(reverse('health-liveness'))
        assert response.data['status'] == 'ok'


# ===========================================================================
# Readiness
# ===========================================================================


@pytest.mark.django_db
class TestHealthReadiness:

    def test_ready_when_services_up(self, client):
        response = client.get(reverse('health-readiness'))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'ok'

    @patch('backend.health.connection')
    def test_503_when_db_unavailable(self, mock_conn, client):
        mock_conn.ensure_connection.side_effect = Exception('DB down')
        response = client.get(reverse('health-readiness'))
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert 'database' in response.data['errors']

    @patch('backend.health.cache')
    def test_503_when_redis_unavailable(self, mock_cache, client):
        mock_cache.set.side_effect = Exception('Redis down')
        response = client.get(reverse('health-readiness'))
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert 'cache' in response.data['errors']

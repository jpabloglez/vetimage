"""
API tests for the DICOM gateway endpoints (transfer monitoring + PACS lookup).
"""
import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestPacsLookup:
    """pacs_lookup is AllowAny (called by the gateway node)."""

    def test_missing_ae_title_returns_400(self):
        resp = APIClient().get('/api/dicom-gateway/pacs/lookup/')
        assert resp.status_code == 400
        assert 'error' in resp.data

    def test_unknown_ae_title_returns_404(self):
        resp = APIClient().get('/api/dicom-gateway/pacs/lookup/?ae_title=DOES_NOT_EXIST')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestTransferMonitoring:
    def test_monitor_requires_auth(self):
        resp = APIClient().get('/api/dicom-gateway/transfers/monitor/')
        assert resp.status_code in (401, 403)

    def test_stats_requires_auth(self):
        resp = APIClient().get('/api/dicom-gateway/transfers/stats/')
        assert resp.status_code in (401, 403)

    def test_monitor_authenticated_ok(self, auth_client):
        resp = auth_client.get('/api/dicom-gateway/transfers/monitor/')
        assert resp.status_code == 200
        # Paginated payload
        assert 'results' in resp.data or isinstance(resp.data, list)

    def test_stats_authenticated_ok(self, auth_client):
        resp = auth_client.get('/api/dicom-gateway/transfers/stats/')
        assert resp.status_code == 200

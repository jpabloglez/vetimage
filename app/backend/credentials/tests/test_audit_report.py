"""
Tests for the Audit Trail Report Generator.
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from credentials.models import AuditLog
from credentials.audit_report_service import AuditReportService


def _create_log(user, event_type='login_success', risk_score=0, is_suspicious=False):
    """Helper to create an AuditLog entry."""
    return AuditLog.objects.create(
        user=user,
        event_type=event_type,
        ip_address='127.0.0.1',
        risk_score=risk_score,
        is_suspicious=is_suspicious,
    )


@pytest.mark.django_db
class TestAuditReportService:

    def test_preview_returns_json(self, user):
        """build_audit_report returns structured JSON."""
        _create_log(user)

        service = AuditReportService()
        result = service.build_audit_report({}, user)

        assert result['report_type'] == 'Audit Trail Report'
        assert 'sections' in result
        assert 'summary' in result

    def test_date_filter(self, user):
        """query_logs filters by date range."""
        _create_log(user)

        service = AuditReportService()
        future = timezone.now() + timezone.timedelta(days=1)
        logs = service.query_logs({'date_from': future})
        assert logs.count() == 0

    def test_user_filter(self, user, other_user):
        """query_logs filters by user_id."""
        _create_log(user)
        _create_log(other_user, event_type='login_failed')

        service = AuditReportService()
        logs = service.query_logs({'user_id': user.id})
        assert logs.count() == 1

    def test_event_type_filter(self, user):
        """query_logs filters by event_type."""
        _create_log(user, event_type='login_success')
        _create_log(user, event_type='logout')

        service = AuditReportService()
        logs = service.query_logs({'event_type': 'logout'})
        assert logs.count() == 1

    def test_empty_logs(self, user):
        """build_audit_report handles no logs gracefully."""
        service = AuditReportService()
        result = service.build_audit_report({}, user)

        assert result['sections'][0]['data']['total_events'] == 0

    def test_summary_stats(self, user):
        """Summary statistics include totals and breakdown."""
        _create_log(user, event_type='login_success')
        _create_log(user, event_type='login_failed', risk_score=80, is_suspicious=True)

        service = AuditReportService()
        result = service.build_audit_report({}, user)

        stats = result['sections'][0]['data']
        assert stats['total_events'] == 2
        assert stats['high_risk_events'] == 1
        assert stats['suspicious_events'] == 1


@pytest.mark.django_db
class TestAuditReportAPI:

    def test_preview_api(self, auth_client, user):
        """GET preview returns JSON."""
        _create_log(user)

        response = auth_client.get('/api/credentials/audit-report/preview/')
        assert response.status_code == 200
        assert response.data['report_type'] == 'Audit Trail Report'

    def test_pdf_download(self, auth_client, user):
        """GET download returns a PDF."""
        _create_log(user)

        response = auth_client.get('/api/credentials/audit-report/download/')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'

    def test_requires_auth(self):
        """Unauthenticated requests are rejected."""
        client = APIClient()
        response = client.get('/api/credentials/audit-report/preview/')
        assert response.status_code == 401

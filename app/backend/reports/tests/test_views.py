"""
Tests for Reports API views.
"""

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestReportViewSet:
    """Tests for the ReportViewSet."""

    def test_list_reports_authenticated(self, auth_client, report):
        """Authenticated user can list their reports."""
        response = auth_client.get('/api/reports/')
        assert response.status_code == 200
        results = response.data['results']
        assert len(results) == 1
        assert results[0]['id'] == str(report.id)

    def test_list_reports_unauthenticated(self, api_client):
        """Unauthenticated requests are rejected."""
        response = api_client.get('/api/reports/')
        assert response.status_code == 401

    def test_create_report_from_completed_task(self, auth_client, completed_task):
        """Can create a report from a completed task."""
        response = auth_client.post('/api/reports/', {
            'analysis_task_id': str(completed_task.id),
        }, format='json')
        assert response.status_code == 201
        assert 'Test Model' in response.data['title']
        assert response.data['content']['report_type'] == 'AI Analysis Report'
        assert len(response.data['content']['sections']) > 0

    def test_create_report_from_incomplete_task(self, auth_client, analysis_task):
        """Cannot create a report from a non-completed task."""
        response = auth_client.post('/api/reports/', {
            'analysis_task_id': str(analysis_task.id),
        }, format='json')
        assert response.status_code == 400

    def test_create_report_for_other_users_task(self, completed_task, other_user):
        """Cannot create a report from another user's task."""
        client = APIClient()
        client.force_authenticate(user=other_user)
        response = client.post('/api/reports/', {
            'analysis_task_id': str(completed_task.id),
        }, format='json')
        assert response.status_code == 400

    def test_retrieve_report_detail(self, auth_client, report):
        """Can retrieve a single report's detail."""
        response = auth_client.get(f'/api/reports/{report.id}/')
        assert response.status_code == 200
        assert response.data['id'] == str(report.id)
        assert 'content' in response.data
        assert response.data['analysis_task_id'] is not None

    def test_download_pdf(self, auth_client, report):
        """Can download a report as PDF."""
        response = auth_client.get(f'/api/reports/{report.id}/pdf/')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        # PDF magic bytes
        assert response.content[:4] == b'%PDF'

    def test_download_pdf_other_user(self, report, other_user):
        """Other user cannot download someone else's report."""
        client = APIClient()
        client.force_authenticate(user=other_user)
        response = client.get(f'/api/reports/{report.id}/pdf/')
        assert response.status_code == 404

    def test_approve_report_signoff(self, auth_client, report):
        """Veterinarian sign-off approves the report and marks it FINAL."""
        assert report.status == 'DRAFT'
        response = auth_client.post(f'/api/reports/{report.id}/approve/')
        assert response.status_code == 200
        assert response.data['status'] == 'FINAL'
        assert response.data['is_approved'] is True
        assert response.data['approved_at'] is not None

        # Unapprove reverts to DRAFT
        response = auth_client.post(f'/api/reports/{report.id}/unapprove/')
        assert response.status_code == 200
        assert response.data['status'] == 'DRAFT'
        assert response.data['is_approved'] is False

    def test_pdf_includes_signoff_block(self, auth_client, report):
        """Generated PDF embeds the draft/sign-off notice."""
        response = auth_client.get(f'/api/reports/{report.id}/pdf/')
        assert response.status_code == 200
        assert response.content[:4] == b'%PDF'

    def test_cannot_share_unapproved_report(self, auth_client, report):
        """Owners must never see an unreviewed draft — sharing requires approval."""
        response = auth_client.post(f'/api/reports/{report.id}/share/')
        assert response.status_code == 400

    def test_share_after_approval_and_public_access(self, auth_client, report):
        """Approve → share → owner can read a sanitised public payload."""
        auth_client.post(f'/api/reports/{report.id}/approve/')
        share = auth_client.post(f'/api/reports/{report.id}/share/')
        assert share.status_code == 200
        token = share.data['share_token']
        assert share.data['share_path'] == f'/shared/{token}'

        # Public, unauthenticated access
        from rest_framework.test import APIClient
        public = APIClient()
        resp = public.get(f'/api/reports/shared/{token}/')
        assert resp.status_code == 200
        # Sanitised owner payload — signalment + findings, no internal IDs
        assert 'patient_info' in resp.data
        assert 'findings' in resp.data
        assert 'analysis_task_id' not in resp.data
        assert resp.data['approved_at'] is not None

    def test_unshare_revokes_public_access(self, auth_client, report):
        auth_client.post(f'/api/reports/{report.id}/approve/')
        token = auth_client.post(f'/api/reports/{report.id}/share/').data['share_token']
        auth_client.post(f'/api/reports/{report.id}/unshare/')
        from rest_framework.test import APIClient
        resp = APIClient().get(f'/api/reports/shared/{token}/')
        assert resp.status_code == 404

    def test_unapprove_revokes_share(self, auth_client, report):
        auth_client.post(f'/api/reports/{report.id}/approve/')
        token = auth_client.post(f'/api/reports/{report.id}/share/').data['share_token']
        auth_client.post(f'/api/reports/{report.id}/unapprove/')
        from rest_framework.test import APIClient
        resp = APIClient().get(f'/api/reports/shared/{token}/')
        assert resp.status_code == 404

    def test_filter_reports_by_study(self, auth_client, report):
        """Can filter reports by study_uid query param."""
        study_uid = report.study.study_instance_uid
        response = auth_client.get(f'/api/reports/?study_uid={study_uid}')
        assert response.status_code == 200
        assert len(response.data['results']) == 1

        # Non-matching UID should return empty
        response = auth_client.get('/api/reports/?study_uid=9.9.9.9.9')
        assert response.status_code == 200
        assert len(response.data['results']) == 0

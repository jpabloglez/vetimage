"""
Tests for credentials app ViewSets.

Covers: UserSessionViewSet, AuditLogViewSet, APIKeyScopeViewSet, EnhancedAPIKeyViewSet
"""

import uuid
import pytest
from unittest.mock import patch
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from credentials.models import (
    UserSession,
    AuditLog,
    APIKeyScope,
    EnhancedAPIKey,
    APIKeyUsageLog,
)
from users.models import UserAPIKey

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(
        email='admin@example.com',
        password='AdminPass123!',
        role=3,
    )
    user.is_staff = True
    user.save(update_fields=['is_staff'])
    return user


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        email='regular@example.com',
        password='RegularPass123!',
        role=1,
    )


@pytest.fixture
def regular_client(regular_user):
    client = APIClient()
    client.force_authenticate(user=regular_user)
    return client


@pytest.fixture
def user_session(regular_user):
    return UserSession.objects.create(
        user=regular_user,
        ip_address='127.0.0.1',
        device_type='desktop',
        expires_at=timezone.now() + timedelta(days=1),
        is_active=True,
    )


@pytest.fixture
def other_user_session(admin_user):
    """Session belonging to a different user."""
    return UserSession.objects.create(
        user=admin_user,
        ip_address='10.0.0.1',
        device_type='desktop',
        expires_at=timezone.now() + timedelta(days=1),
        is_active=True,
    )


@pytest.fixture
def audit_log(regular_user):
    """Create an audit log entry (bypass immutability by using super().save)."""
    log = AuditLog(
        user=regular_user,
        event_type='login_success',
        ip_address='127.0.0.1',
        request_path='/users/login/',
        request_method='POST',
        is_suspicious=False,
        risk_score=0,
    )
    # Bypass the immutability guard on save for test setup
    super(AuditLog, log).save()
    return log


@pytest.fixture
def suspicious_audit_log(regular_user):
    log = AuditLog(
        user=regular_user,
        event_type='suspicious_activity',
        ip_address='192.168.1.1',
        request_path='/users/login/',
        request_method='POST',
        is_suspicious=True,
        risk_score=80,
    )
    super(AuditLog, log).save()
    return log


@pytest.fixture
def api_scope(db):
    return APIKeyScope.objects.create(
        name='dicom:read',
        display_name='DICOM Read',
        description='Read DICOM data',
        category='dicom',
        allowed_endpoints=['/api/dicom/.*'],
        allowed_methods=['GET'],
        is_active=True,
    )


@pytest.fixture
def user_api_key(regular_user):
    return UserAPIKey.objects.create(
        user=regular_user,
        name='Test Key',
        key_hash='a' * 64,
        key_prefix='oml_test',
    )


@pytest.fixture
def enhanced_api_key(user_api_key):
    return EnhancedAPIKey.objects.create(
        api_key=user_api_key,
        rate_limit_per_minute=60,
        rate_limit_per_hour=3600,
        rate_limit_per_day=86400,
    )


@pytest.fixture
def admin_api_key(admin_user):
    return UserAPIKey.objects.create(
        user=admin_user,
        name='Admin Key',
        key_hash='b' * 64,
        key_prefix='oml_admn',
    )


@pytest.fixture
def admin_enhanced_api_key(admin_api_key):
    return EnhancedAPIKey.objects.create(
        api_key=admin_api_key,
        rate_limit_per_minute=60,
        rate_limit_per_hour=3600,
        rate_limit_per_day=86400,
    )


# ===========================================================================
# UserSessionViewSet Tests
# ===========================================================================


@pytest.mark.django_db
class TestUserSessionViewSet:

    def test_list_sessions_authenticated(self, regular_client, user_session):
        url = reverse('credentials:session-list')
        response = regular_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Should return at least the fixture session
        assert len(response.data['results']) >= 1

    def test_list_sessions_unauthenticated(self, api_client):
        url = reverse('credentials:session-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_session_detail(self, regular_client, user_session):
        url = reverse('credentials:session-detail', args=[str(user_session.id)])
        response = regular_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(user_session.id)

    @patch('credentials.views.terminate_session_by_id', return_value=True)
    def test_destroy_session(self, mock_terminate, regular_client, user_session):
        url = reverse('credentials:session-detail', args=[str(user_session.id)])
        response = regular_client.delete(url, {}, format='json')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_terminate.assert_called_once()

    def test_current_session_without_jwt(self, regular_client):
        """force_authenticate does not set request.auth, so should get 400."""
        url = reverse('credentials:session-current')
        response = regular_client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_only_own_sessions(self, regular_client, user_session, other_user_session):
        url = reverse('credentials:session-list')
        response = regular_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        session_ids = [s['id'] for s in response.data['results']]
        assert str(user_session.id) in session_ids
        assert str(other_user_session.id) not in session_ids

    def test_destroy_nonexistent_session(self, regular_client):
        fake_id = uuid.uuid4()
        url = reverse('credentials:session-detail', args=[str(fake_id)])
        response = regular_client.delete(url, {}, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# AuditLogViewSet Tests
# ===========================================================================


@pytest.mark.django_db
class TestAuditLogViewSet:

    def test_list_logs_authenticated(self, regular_client, audit_log):
        url = reverse('credentials:auditlog-list')
        response = regular_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_list_logs_unauthenticated(self, api_client):
        url = reverse('credentials:auditlog-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_log_detail(self, regular_client, audit_log):
        url = reverse('credentials:auditlog-detail', args=[audit_log.pk])
        response = regular_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_event_type(self, regular_client, audit_log, suspicious_audit_log):
        url = reverse('credentials:auditlog-list')
        response = regular_client.get(url, {'event_type': 'login_success'})
        assert response.status_code == status.HTTP_200_OK
        for entry in response.data['results']:
            assert entry['event_type'] == 'login_success'

    def test_filter_suspicious_only(self, regular_client, audit_log, suspicious_audit_log):
        url = reverse('credentials:auditlog-list')
        response = regular_client.get(url, {'suspicious_only': 'true'})
        assert response.status_code == status.HTTP_200_OK
        for entry in response.data['results']:
            assert entry['is_suspicious'] is True

    def test_export_csv_admin_success(self, admin_client, audit_log):
        url = reverse('credentials:auditlog-export')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Type'] == 'text/csv'
        assert 'attachment' in response['Content-Disposition']

    def test_export_csv_non_admin_forbidden(self, regular_client, audit_log):
        url = reverse('credentials:auditlog-export')
        response = regular_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ===========================================================================
# APIKeyScopeViewSet Tests
# ===========================================================================


@pytest.mark.django_db
class TestAPIKeyScopeViewSet:

    def test_list_scopes_admin(self, admin_client, api_scope):
        url = reverse('credentials:scope-list')
        response = admin_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_scope_admin(self, admin_client):
        url = reverse('credentials:scope-list')
        data = {
            'name': 'ai:submit',
            'display_name': 'AI Submit',
            'description': 'Submit AI analysis jobs',
            'category': 'ai',
            'allowed_endpoints': ['/api/ai-analysis/.*'],
            'allowed_methods': ['POST'],
        }
        response = admin_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert APIKeyScope.objects.filter(name='ai:submit').exists()

    def test_update_scope_admin(self, admin_client, api_scope):
        url = reverse('credentials:scope-detail', args=[api_scope.pk])
        data = {
            'name': api_scope.name,
            'display_name': 'Updated DICOM Read',
            'description': api_scope.description,
            'category': api_scope.category,
            'allowed_endpoints': api_scope.allowed_endpoints,
            'allowed_methods': api_scope.allowed_methods,
        }
        response = admin_client.put(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        api_scope.refresh_from_db()
        assert api_scope.display_name == 'Updated DICOM Read'

    def test_delete_scope_admin(self, admin_client, api_scope):
        url = reverse('credentials:scope-detail', args=[api_scope.pk])
        response = admin_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not APIKeyScope.objects.filter(pk=api_scope.pk).exists()

    def test_list_scopes_non_admin_forbidden(self, regular_client):
        url = reverse('credentials:scope-list')
        response = regular_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ===========================================================================
# EnhancedAPIKeyViewSet Tests
# ===========================================================================


@pytest.mark.django_db
class TestEnhancedAPIKeyViewSet:

    def test_list_keys_authenticated(self, regular_client, enhanced_api_key):
        url = reverse('credentials:apikey-list')
        response = regular_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_list_keys_unauthenticated(self, api_client):
        url = reverse('credentials:apikey-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_key_detail(self, regular_client, enhanced_api_key):
        url = reverse('credentials:apikey-detail', args=[enhanced_api_key.pk])
        response = regular_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_usage_stats_endpoint(self, regular_client, enhanced_api_key):
        url = reverse('credentials:apikey-usage', args=[enhanced_api_key.pk])
        response = regular_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'total_requests' in response.data

    def test_usage_logs_endpoint(self, regular_client, enhanced_api_key):
        url = reverse('credentials:apikey-usage-logs', args=[enhanced_api_key.pk])
        response = regular_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_reset_quota_admin_success(self, admin_client, admin_enhanced_api_key):
        url = reverse('credentials:apikey-reset-quota', args=[admin_enhanced_api_key.pk])
        response = admin_client.post(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'quota_reset_at' in response.data

    def test_reset_quota_non_admin_forbidden(self, regular_client, enhanced_api_key):
        url = reverse('credentials:apikey-reset-quota', args=[enhanced_api_key.pk])
        response = regular_client.post(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

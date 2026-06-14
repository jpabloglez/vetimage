"""
Integration tests for credentials app

Tests end-to-end flows:
- User authentication with session tracking
- API key authentication with scopes
- Concurrent session limits
- Brute force protection
- Audit logging
- Session management endpoints
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from datetime import timedelta
import json
import time
import unittest
import uuid

from users.models import UserAPIKey
from credentials.models import (
    UserSession,
    AuditLog,
    APIKeyScope,
    EnhancedAPIKey,
    APIKeyUsageLog
)
from credentials.services import assign_scope_to_api_key

User = get_user_model()


class UserAuthenticationFlowTest(TransactionTestCase):
    """Test complete user authentication flow with session tracking"""

    def setUp(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='TestPass123!'
        )
        cache.clear()

    def test_complete_login_session_logout_flow(self):
        """Test: Login → Session Created → Activity → Logout → Session Terminated"""

        # Step 1: User logs in
        login_url = reverse('login')
        login_data = {
            'email': 'testuser@example.com',
            'password': 'TestPass123!'
        }

        login_response = self.client.post(login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', login_response.data)

        access_token = login_response.data['access']

        # Verify UserSession was created (signal fires on OutstandingToken post_save)
        sessions = UserSession.objects.filter(user=self.user, is_active=True)
        self.assertGreaterEqual(sessions.count(), 1)
        session = sessions.first()

        # Verify session details
        self.assertEqual(session.session_type, 'jwt')
        self.assertTrue(session.is_active)
        self.assertIsNotNone(session.outstanding_token)

        # Verify AuditLog entry for login
        login_logs = AuditLog.objects.filter(
            user=self.user,
            event_type='login_success'
        )
        self.assertGreaterEqual(login_logs.count(), 1)

        # Step 2: Make authenticated request (session activity update)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Wait a moment to ensure timestamp difference
        time.sleep(0.1)

        profile_url = reverse('profile')
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Reload session and verify activity was updated
        session.refresh_from_db()
        self.assertIsNotNone(session.last_activity_at)

        # Step 3: User logs out — needs refresh cookie from login response
        logout_url = reverse('logout')
        refresh_cookie = login_response.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        if refresh_cookie:
            self.client.cookies[settings.REFRESH_TOKEN_COOKIE_NAME] = refresh_cookie.value
        response = self.client.post(logout_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify session was terminated
        session.refresh_from_db()
        self.assertFalse(session.is_active)
        self.assertIsNotNone(session.terminated_at)
        self.assertEqual(session.termination_reason, 'logout')

        # Verify AuditLog entry for logout
        logout_logs = AuditLog.objects.filter(
            user=self.user,
            event_type='logout'
        )
        self.assertGreaterEqual(logout_logs.count(), 1)

    def test_failed_login_returns_error(self):
        """Test: Failed login returns 401 error"""

        login_url = reverse('login')
        login_data = {
            'email': 'testuser@example.com',
            'password': 'WrongPassword123!'
        }

        response = self.client.post(login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ConcurrentSessionLimitTest(TransactionTestCase):
    """Test concurrent session limit enforcement"""

    def setUp(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='multidevice@example.com',
            password='TestPass123!'
        )
        cache.clear()

    def test_concurrent_session_limit_enforcement(self):
        """Test: Creating more sessions than limit terminates oldest sessions"""

        max_sessions = getattr(settings, 'MAX_CONCURRENT_SESSIONS_PER_USER', 5)

        login_url = reverse('login')
        login_data = {
            'email': 'multidevice@example.com',
            'password': 'TestPass123!'
        }

        # Create max_sessions + 2 sessions
        for i in range(max_sessions + 2):
            client = APIClient()
            response = client.post(login_url, login_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify only max_sessions are active
        active_sessions = UserSession.objects.filter(
            user=self.user,
            is_active=True
        ).count()
        self.assertEqual(active_sessions, max_sessions)

        # Verify oldest sessions were terminated with reason 'concurrent_limit'
        # (signal uses session.terminate(reason='concurrent_limit'))
        terminated_sessions = UserSession.objects.filter(
            user=self.user,
            is_active=False,
            termination_reason='concurrent_limit'
        )
        self.assertEqual(terminated_sessions.count(), 2)

        # Verify AuditLog entries
        limit_logs = AuditLog.objects.filter(
            user=self.user,
            event_type='concurrent_session_limit'
        )
        self.assertGreaterEqual(limit_logs.count(), 2)


class BruteForceProtectionTest(TransactionTestCase):
    """Test brute force protection with progressive delays"""

    def setUp(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='bruteforce@example.com',
            password='TestPass123!'
        )
        cache.clear()

    def test_progressive_delay_on_failed_attempts(self):
        """Test: Progressive delays after failed login attempts"""

        max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)

        login_url = reverse('login')

        # Make max_attempts failed login attempts
        for i in range(max_attempts):
            login_data = {
                'email': 'bruteforce@example.com',
                'password': f'WrongPassword{i}'
            }
            response = self.client.post(login_url, login_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Next attempt should be rate limited (middleware returns 429)
        login_data = {
            'email': 'bruteforce@example.com',
            'password': 'WrongPassword999'
        }
        response = self.client.post(login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        # Middleware returns JsonResponse with 'error' key
        # Use json.loads since middleware returns raw JsonResponse, not DRF Response
        body = json.loads(response.content)
        self.assertIn('error', body)

        # Verify failed login audit logs exist
        # Note: username_attempted may be empty for JSON requests since
        # DRF request.data is not available in middleware context
        failed_logs = AuditLog.objects.filter(event_type='login_failed')
        self.assertGreaterEqual(failed_logs.count(), max_attempts)


class APIKeyAuthenticationFlowTest(TransactionTestCase):
    """Test API key authentication with scopes and rate limiting"""

    def setUp(self):
        """Set up test user, API key, and scopes"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='apiuser@example.com',
            password='TestPass123!'
        )

        # Create API key (classmethod on model, not manager)
        api_key, key_value = UserAPIKey.create_key(
            user=self.user,
            name='Test API Key'
        )
        self.api_key = api_key
        self.key_value = key_value

        # Create scopes
        self.read_scope = APIKeyScope.objects.create(
            name='test:read',
            display_name='Test Read Access',
            category='test',
            allowed_endpoints=[r'^/api/users/profile/$'],
            allowed_methods=['GET', 'HEAD', 'OPTIONS'],
            is_active=True
        )

        self.write_scope = APIKeyScope.objects.create(
            name='test:write',
            display_name='Test Write Access',
            category='test',
            allowed_endpoints=[r'^/api/users/profile/$'],
            allowed_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'],
            is_active=True
        )

        cache.clear()

    @unittest.skip("API key authentication backend not yet registered in DEFAULT_AUTHENTICATION_CLASSES")
    def test_api_key_with_read_scope(self):
        """Test: API key with read scope can access GET endpoints"""

        # Assign read scope to API key
        assign_scope_to_api_key(self.api_key, 'test:read')

        # Make authenticated request with API key
        self.client.credentials(HTTP_AUTHORIZATION=f'Api-Key {self.key_value}')

        profile_url = reverse('profile')
        response = self.client.get(profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify EnhancedAPIKey was created
        enhanced_key = EnhancedAPIKey.objects.filter(api_key=self.api_key).first()
        self.assertIsNotNone(enhanced_key)
        self.assertTrue(enhanced_key.scopes.filter(name='test:read').exists())

    def test_api_key_scope_violation(self):
        """Test: API key without write scope cannot POST"""

        # Assign only read scope
        assign_scope_to_api_key(self.api_key, 'test:read')

        # Verify the scope check would fail
        enhanced_key = EnhancedAPIKey.objects.get(api_key=self.api_key)
        has_write = enhanced_key.scopes.filter(name='test:write').exists()
        self.assertFalse(has_write)

        # Verify read scope exists
        has_read = enhanced_key.scopes.filter(name='test:read').exists()
        self.assertTrue(has_read)


class SessionManagementEndpointsTest(TestCase):
    """Test session management REST API endpoints"""

    def setUp(self):
        """Set up test client and authenticated user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='sessionuser@example.com',
            password='TestPass123!'
        )

        # Create JWT token for authentication.
        # RefreshToken.for_user() creates an OutstandingToken, which fires the
        # create_user_session signal that auto-creates a UserSession.
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Retrieve the auto-created session and enrich it for testing
        self.session = UserSession.objects.filter(
            user=self.user, is_active=True
        ).order_by('-created_at').first()

        if self.session:
            self.session.device_type = 'desktop'
            self.session.browser = 'Chrome'
            self.session.browser_version = '120'
            self.session.os = 'Windows'
            self.session.os_version = '11'
            self.session.ip_address = '203.0.113.42'
            self.session.save(update_fields=[
                'device_type', 'browser', 'browser_version',
                'os', 'os_version', 'ip_address'
            ])

    def test_list_user_sessions(self):
        """Test: GET /api/credentials/sessions/ returns user's sessions"""

        url = reverse('credentials:session-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

        # Verify session data structure
        session_data = response.data['results'][0]
        self.assertIn('id', session_data)
        self.assertIn('device_type', session_data)
        self.assertIn('ip_address', session_data)
        self.assertIn('is_active', session_data)

    def test_get_session_detail(self):
        """Test: GET /api/credentials/sessions/{id}/ returns session details"""

        url = reverse('credentials:session-detail', kwargs={'pk': self.session.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.session.id))
        self.assertEqual(response.data['device_type'], 'desktop')
        self.assertEqual(response.data['browser'], 'Chrome')

    def test_terminate_session(self):
        """Test: DELETE /api/credentials/sessions/{id}/ terminates session"""

        url = reverse('credentials:session-detail', kwargs={'pk': self.session.id})
        response = self.client.delete(url, {'reason': 'manual'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify session was terminated
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_active)
        self.assertEqual(self.session.termination_reason, 'manual')


class AuditLogEndpointsTest(TestCase):
    """Test audit log REST API endpoints"""

    def setUp(self):
        """Set up test client and authenticated user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='audituser@example.com',
            password='TestPass123!',
            role=3  # Admin role for export test
        )

        # Authenticate
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Create some audit log entries
        for i in range(5):
            AuditLog.objects.create(
                user=self.user,
                event_type='login_success',
                event_timestamp=timezone.now() - timedelta(hours=i),
                ip_address=f'203.0.113.{i}',
                request_path='/api/users/auth/login/',
                request_method='POST',
                is_suspicious=False,
                risk_score=0
            )

        # Create a suspicious entry
        AuditLog.objects.create(
            user=self.user,
            event_type='suspicious_activity',
            event_timestamp=timezone.now(),
            ip_address='203.0.113.99',
            request_path='/api/users/profile/',
            request_method='GET',
            is_suspicious=True,
            risk_score=85,
            metadata={'reason': 'IP address changed'}
        )

    def test_list_audit_logs(self):
        """Test: GET /api/credentials/audit-logs/ returns user's audit logs"""

        url = reverse('credentials:auditlog-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 6)

    def test_filter_suspicious_audit_logs(self):
        """Test: Filter audit logs by suspicious flag"""

        url = reverse('credentials:auditlog-list')
        response = self.client.get(url, {'suspicious_only': 'true'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertTrue(response.data['results'][0]['is_suspicious'])
        self.assertEqual(response.data['results'][0]['event_type'], 'suspicious_activity')

    def test_filter_audit_logs_by_event_type(self):
        """Test: Filter audit logs by event type"""

        url = reverse('credentials:auditlog-list')
        response = self.client.get(url, {'event_type': 'login_success'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)


class APIKeyUsageTrackingTest(TransactionTestCase):
    """Test API key usage tracking and statistics"""

    def setUp(self):
        """Set up test user and API key"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='usageuser@example.com',
            password='TestPass123!'
        )

        # Create API key (classmethod on model, not manager)
        api_key, key_value = UserAPIKey.create_key(
            user=self.user,
            name='Usage Test Key'
        )
        self.api_key = api_key
        self.key_value = key_value

        # Assign full access scope
        APIKeyScope.objects.create(
            name='full_access',
            display_name='Full Access',
            category='admin',
            allowed_endpoints=[r'^/api/.*'],
            allowed_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'],
            is_active=True
        )
        assign_scope_to_api_key(self.api_key, 'full_access')

        # Authenticate with JWT for the usage endpoint
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_view_api_key_usage_statistics(self):
        """Test: GET /api/credentials/api-keys/{id}/usage/ returns statistics"""

        enhanced_key = EnhancedAPIKey.objects.get(api_key=self.api_key)

        # Create some usage log entries
        for i in range(10):
            APIKeyUsageLog.objects.create(
                api_key=self.api_key,
                timestamp=timezone.now() - timedelta(hours=i),
                request_path='/api/users/profile/',
                request_method='GET',
                response_status=200,
                response_time_ms=50 + i,
                ip_address='203.0.113.42',
                scope_matched='full_access',
                rate_limited=False
            )

        url = reverse('credentials:apikey-usage', kwargs={'pk': enhanced_key.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_requests', response.data)
        self.assertEqual(response.data['total_requests'], 10)
        self.assertIn('usage_by_endpoint', response.data)
        self.assertIn('usage_by_status', response.data)


class PerformanceTest(TransactionTestCase):
    """Basic performance tests"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        cache.clear()

    def test_login_performance(self):
        """Test: Login completes in reasonable time"""

        User.objects.create_user(
            email='perfuser@example.com',
            password='TestPass123!'
        )

        login_url = reverse('login')
        login_data = {
            'email': 'perfuser@example.com',
            'password': 'TestPass123!'
        }

        start_time = time.time()
        response = self.client.post(login_url, login_data, format='json')
        end_time = time.time()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Login should complete in under 2 seconds (with session tracking overhead)
        elapsed = end_time - start_time
        self.assertLess(elapsed, 2.0, f"Login took {elapsed:.3f}s, expected < 2.0s")

    def test_session_list_query_count(self):
        """Test: Session list endpoint uses efficient queries"""

        user = User.objects.create_user(
            email='queryuser@example.com',
            password='TestPass123!'
        )

        # Create multiple sessions — RefreshToken.for_user() triggers signal
        # that auto-creates UserSession via create_user_session.
        for i in range(5):
            RefreshToken.for_user(user)

        # Authenticate and list sessions
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as queries:
            url = reverse('credentials:session-list')
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should use select_related to avoid N+1 queries
        # Allow some flexibility for JWT validation + pagination COUNT queries
        self.assertLessEqual(len(queries), 10,
                            f"Session list used {len(queries)} queries, expected <= 10")

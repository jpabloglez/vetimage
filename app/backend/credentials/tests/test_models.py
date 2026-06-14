"""
Unit tests for credentials models
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid

from credentials.models import (
    UserSession,
    AuditLog,
    APIKeyScope,
    EnhancedAPIKey,
    APIKeyUsageLog
)
from users.models import UserAPIKey
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserSessionModelTest(TestCase):
    """Tests for UserSession model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@vetimage.com',
            password='testpass123',
            role=1
        )

    def test_create_user_session(self):
        """Test creating a user session"""
        session = UserSession.objects.create(
            user=self.user,
            session_type='jwt',
            ip_address='192.168.1.1',
            device_type='desktop',
            browser='Chrome',
            browser_version='120.0',
            os='Windows',
            os_version='11',
            expires_at=timezone.now() + timedelta(days=7)
        )

        self.assertIsNotNone(session.id)
        self.assertIsInstance(session.id, uuid.UUID)
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.session_type, 'jwt')
        self.assertTrue(session.is_active)
        self.assertFalse(session.is_suspicious)

    def test_is_valid_active_session(self):
        """Test is_valid() for active, non-expired session"""
        session = UserSession.objects.create(
            user=self.user,
            session_type='jwt',
            ip_address='192.168.1.1',
            expires_at=timezone.now() + timedelta(hours=1)
        )

        self.assertTrue(session.is_valid())

    def test_is_valid_expired_session(self):
        """Test is_valid() for expired session"""
        session = UserSession.objects.create(
            user=self.user,
            session_type='jwt',
            ip_address='192.168.1.1',
            expires_at=timezone.now() - timedelta(hours=1)
        )

        self.assertFalse(session.is_valid())

    def test_is_valid_terminated_session(self):
        """Test is_valid() for terminated session"""
        session = UserSession.objects.create(
            user=self.user,
            session_type='jwt',
            ip_address='192.168.1.1',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        session.terminate(reason='logout')

        self.assertFalse(session.is_valid())

    def test_terminate_session(self):
        """Test terminating a session"""
        session = UserSession.objects.create(
            user=self.user,
            session_type='jwt',
            ip_address='192.168.1.1',
            expires_at=timezone.now() + timedelta(hours=1)
        )

        session.terminate(reason='logout')

        self.assertFalse(session.is_active)
        self.assertEqual(session.termination_reason, 'logout')
        self.assertIsNotNone(session.terminated_at)

    def test_update_activity(self):
        """Test updating session activity"""
        session = UserSession.objects.create(
            user=self.user,
            session_type='jwt',
            ip_address='192.168.1.1',
            expires_at=timezone.now() + timedelta(hours=1)
        )

        original_activity = session.last_activity_at

        # Wait a tiny bit and update
        import time
        time.sleep(0.01)
        session.update_activity()

        # Refresh from database
        session.refresh_from_db()
        self.assertGreater(session.last_activity_at, original_activity)

    def test_session_str_representation(self):
        """Test __str__ method"""
        session = UserSession.objects.create(
            user=self.user,
            session_type='jwt',
            ip_address='192.168.1.1',
            expires_at=timezone.now() + timedelta(hours=1)
        )

        expected_str = f"{self.user.email} - {session.device_type} - {session.ip_address}"
        self.assertEqual(str(session), expected_str)

    def test_active_manager(self):
        """Test active sessions manager"""
        # Create active session
        active_session = UserSession.objects.create(
            user=self.user,
            session_type='jwt',
            ip_address='192.168.1.1',
            expires_at=timezone.now() + timedelta(hours=1)
        )

        # Create terminated session
        terminated_session = UserSession.objects.create(
            user=self.user,
            session_type='jwt',
            ip_address='192.168.1.2',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        terminated_session.terminate()

        # Get active sessions
        active_sessions = UserSession.objects.active()

        self.assertEqual(active_sessions.count(), 1)
        self.assertEqual(active_sessions.first().id, active_session.id)

    def test_suspicious_manager(self):
        """Test suspicious sessions manager"""
        # Create normal session
        normal_session = UserSession.objects.create(
            user=self.user,
            session_type='jwt',
            ip_address='192.168.1.1',
            expires_at=timezone.now() + timedelta(hours=1)
        )

        # Create suspicious session
        suspicious_session = UserSession.objects.create(
            user=self.user,
            session_type='jwt',
            ip_address='192.168.1.2',
            is_suspicious=True,
            suspicious_reason='IP change detected',
            expires_at=timezone.now() + timedelta(hours=1)
        )

        # Get suspicious sessions
        suspicious_sessions = UserSession.objects.suspicious()

        self.assertEqual(suspicious_sessions.count(), 1)
        self.assertEqual(suspicious_sessions.first().id, suspicious_session.id)


class AuditLogModelTest(TestCase):
    """Tests for AuditLog model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@vetimage.com',
            password='testpass123',
            role=1
        )

    def test_create_audit_log(self):
        """Test creating an audit log entry"""
        log = AuditLog.objects.create(
            user=self.user,
            event_type='login_success',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0...',
            request_path='/api/auth/login/',
            request_method='POST'
        )

        self.assertIsNotNone(log.id)
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.event_type, 'login_success')
        self.assertIsNotNone(log.event_timestamp)
        self.assertFalse(log.is_suspicious)
        self.assertEqual(log.risk_score, 0)

    def test_audit_log_immutable_save(self):
        """Test that audit logs cannot be modified after creation"""
        log = AuditLog.objects.create(
            user=self.user,
            event_type='login_success',
            ip_address='192.168.1.1'
        )

        # Try to modify
        log.event_type = 'logout'

        with self.assertRaises(ValueError) as context:
            log.save()

        self.assertIn('immutable', str(context.exception).lower())

    def test_audit_log_cannot_delete(self):
        """Test that audit logs cannot be deleted"""
        log = AuditLog.objects.create(
            user=self.user,
            event_type='login_success',
            ip_address='192.168.1.1'
        )

        with self.assertRaises(ValueError) as context:
            log.delete()

        self.assertIn('cannot be deleted', str(context.exception).lower())

    def test_failed_login_with_no_user(self):
        """Test audit log for failed login (no user)"""
        log = AuditLog.objects.create(
            user=None,  # User not found
            username_attempted='nonexistent@example.com',
            event_type='login_failed',
            ip_address='192.168.1.1',
            metadata={'reason': 'User not found'}
        )

        self.assertIsNone(log.user)
        self.assertEqual(log.username_attempted, 'nonexistent@example.com')
        self.assertEqual(log.event_type, 'login_failed')

    def test_suspicious_event_with_risk_score(self):
        """Test audit log with suspicious flag and risk score"""
        log = AuditLog.objects.create(
            user=self.user,
            event_type='suspicious_activity',
            ip_address='192.168.1.1',
            is_suspicious=True,
            risk_score=85,
            metadata={'reason': 'Multiple failed login attempts'}
        )

        self.assertTrue(log.is_suspicious)
        self.assertEqual(log.risk_score, 85)
        self.assertEqual(log.metadata['reason'], 'Multiple failed login attempts')

    def test_audit_log_str_representation(self):
        """Test __str__ method"""
        log = AuditLog.objects.create(
            user=self.user,
            event_type='login_success',
            ip_address='192.168.1.1'
        )

        expected_str = f"login_success - {self.user.email} - {log.event_timestamp}"
        self.assertEqual(str(log), expected_str)

    def test_failed_logins_manager(self):
        """Test failed logins manager"""
        # Create success log
        success_log = AuditLog.objects.create(
            user=self.user,
            event_type='login_success',
            ip_address='192.168.1.1'
        )

        # Create failed logs
        failed_log1 = AuditLog.objects.create(
            user=None,
            username_attempted='test@vetimage.com',
            event_type='login_failed',
            ip_address='192.168.1.1'
        )

        failed_log2 = AuditLog.objects.create(
            user=None,
            username_attempted='test@vetimage.com',
            event_type='login_failed',
            ip_address='192.168.1.1'
        )

        # Get failed logins
        failed_logins = AuditLog.objects.failed_logins()

        self.assertEqual(failed_logins.count(), 2)

    def test_suspicious_events_manager(self):
        """Test suspicious events manager"""
        # Create normal event
        normal_log = AuditLog.objects.create(
            user=self.user,
            event_type='login_success',
            ip_address='192.168.1.1'
        )

        # Create suspicious event
        suspicious_log = AuditLog.objects.create(
            user=self.user,
            event_type='suspicious_activity',
            ip_address='192.168.1.1',
            is_suspicious=True,
            risk_score=75
        )

        # Get suspicious events
        suspicious_events = AuditLog.objects.suspicious_events()

        self.assertEqual(suspicious_events.count(), 1)
        self.assertEqual(suspicious_events.first().id, suspicious_log.id)


class APIKeyScopeModelTest(TestCase):
    """Tests for APIKeyScope model"""

    def test_create_scope(self):
        """Test creating an API key scope"""
        scope = APIKeyScope.objects.create(
            name='dicom:read',
            display_name='DICOM Read Access',
            description='Read-only access to DICOM endpoints',
            category='dicom',
            allowed_endpoints=[r'^/api/dicom/.*', r'^/api/dicom-images/.*'],
            allowed_methods=['GET', 'HEAD', 'OPTIONS']
        )

        self.assertEqual(scope.name, 'dicom:read')
        self.assertEqual(scope.category, 'dicom')
        self.assertTrue(scope.is_active)
        self.assertEqual(len(scope.allowed_endpoints), 2)
        self.assertEqual(len(scope.allowed_methods), 3)

    def test_matches_request_allowed(self):
        """Test matches_request() for allowed requests"""
        scope = APIKeyScope.objects.create(
            name='dicom:read',
            display_name='DICOM Read Access',
            description='Read-only access',
            category='dicom',
            allowed_endpoints=[r'^/api/dicom/.*'],
            allowed_methods=['GET']
        )

        # Should match
        self.assertTrue(scope.matches_request('/api/dicom/studies/', 'GET'))
        self.assertTrue(scope.matches_request('/api/dicom/series/123/', 'GET'))

    def test_matches_request_wrong_method(self):
        """Test matches_request() for wrong HTTP method"""
        scope = APIKeyScope.objects.create(
            name='dicom:read',
            display_name='DICOM Read Access',
            description='Read-only access',
            category='dicom',
            allowed_endpoints=[r'^/api/dicom/.*'],
            allowed_methods=['GET']
        )

        # Wrong method
        self.assertFalse(scope.matches_request('/api/dicom/studies/', 'POST'))
        self.assertFalse(scope.matches_request('/api/dicom/studies/', 'DELETE'))

    def test_matches_request_wrong_endpoint(self):
        """Test matches_request() for wrong endpoint"""
        scope = APIKeyScope.objects.create(
            name='dicom:read',
            display_name='DICOM Read Access',
            description='Read-only access',
            category='dicom',
            allowed_endpoints=[r'^/api/dicom/.*'],
            allowed_methods=['GET']
        )

        # Wrong endpoint
        self.assertFalse(scope.matches_request('/api/users/profile/', 'GET'))
        self.assertFalse(scope.matches_request('/api/ai-analysis/submit/', 'GET'))

    def test_scope_str_representation(self):
        """Test __str__ method"""
        scope = APIKeyScope.objects.create(
            name='dicom:read',
            display_name='DICOM Read Access',
            description='Read-only access',
            category='dicom',
            allowed_endpoints=[r'^/api/dicom/.*'],
            allowed_methods=['GET']
        )

        self.assertEqual(str(scope), 'dicom:read - DICOM Read Access')


class EnhancedAPIKeyModelTest(TestCase):
    """Tests for EnhancedAPIKey model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@vetimage.com',
            password='testpass123',
            role=1
        )

        # Create UserAPIKey
        self.user_api_key = UserAPIKey.objects.create(
            user=self.user,
            key_prefix='oml_test',
            key_hash='dummy_hash_for_testing'
        )

        # Create scopes
        self.dicom_read_scope = APIKeyScope.objects.create(
            name='dicom:read',
            display_name='DICOM Read',
            description='Read DICOM data',
            category='dicom',
            allowed_endpoints=[r'^/api/dicom/.*'],
            allowed_methods=['GET']
        )

        self.ai_submit_scope = APIKeyScope.objects.create(
            name='ai:submit',
            display_name='AI Submit',
            description='Submit AI analysis',
            category='ai',
            allowed_endpoints=[r'^/api/ai-analysis/submit/.*'],
            allowed_methods=['POST']
        )

    def test_create_enhanced_api_key(self):
        """Test creating an enhanced API key"""
        enhanced_key = EnhancedAPIKey.objects.create(
            api_key=self.user_api_key,
            rate_limit_per_minute=60,
            rate_limit_per_hour=3600,
            rate_limit_per_day=86400
        )

        self.assertEqual(enhanced_key.api_key, self.user_api_key)
        self.assertEqual(enhanced_key.rate_limit_per_minute, 60)
        self.assertEqual(enhanced_key.total_requests, 0)
        self.assertIsNone(enhanced_key.last_request_at)

    def test_has_scope(self):
        """Test has_scope() method"""
        enhanced_key = EnhancedAPIKey.objects.create(
            api_key=self.user_api_key
        )
        enhanced_key.scopes.add(self.dicom_read_scope)

        self.assertTrue(enhanced_key.has_scope('dicom:read'))
        self.assertFalse(enhanced_key.has_scope('ai:submit'))

    def test_can_access_with_scope(self):
        """Test can_access() with valid scope"""
        enhanced_key = EnhancedAPIKey.objects.create(
            api_key=self.user_api_key
        )
        enhanced_key.scopes.add(self.dicom_read_scope)

        self.assertTrue(enhanced_key.can_access('/api/dicom/studies/', 'GET'))

    def test_can_access_without_scope(self):
        """Test can_access() without required scope"""
        enhanced_key = EnhancedAPIKey.objects.create(
            api_key=self.user_api_key
        )
        enhanced_key.scopes.add(self.dicom_read_scope)

        # Trying to access AI endpoint without ai:submit scope
        self.assertFalse(enhanced_key.can_access('/api/ai-analysis/submit/', 'POST'))

    def test_check_rate_limit_under_limit(self):
        """Test check_rate_limit() when under limit"""
        enhanced_key = EnhancedAPIKey.objects.create(
            api_key=self.user_api_key,
            rate_limit_per_minute=60,
            current_minute_count=30,
            quota_reset_at=timezone.now() + timedelta(minutes=1)  # Set future reset time
        )

        allowed, reason = enhanced_key.check_rate_limit()

        self.assertTrue(allowed)
        self.assertEqual(reason, 'allowed')

    def test_check_rate_limit_exceeded_minute(self):
        """Test check_rate_limit() when minute limit exceeded"""
        enhanced_key = EnhancedAPIKey.objects.create(
            api_key=self.user_api_key,
            rate_limit_per_minute=60,
            current_minute_count=60,
            quota_reset_at=timezone.now() + timedelta(minutes=1)  # Set future reset time
        )

        allowed, reason = enhanced_key.check_rate_limit()

        self.assertFalse(allowed)
        self.assertIn('minute', reason.lower())

    def test_check_rate_limit_exceeded_hour(self):
        """Test check_rate_limit() when hour limit exceeded"""
        enhanced_key = EnhancedAPIKey.objects.create(
            api_key=self.user_api_key,
            rate_limit_per_hour=3600,
            current_hour_count=3600,
            quota_reset_at=timezone.now() + timedelta(hours=1)  # Set future reset time
        )

        allowed, reason = enhanced_key.check_rate_limit()

        self.assertFalse(allowed)
        self.assertIn('hour', reason.lower())

    def test_check_rate_limit_exceeded_day(self):
        """Test check_rate_limit() when day limit exceeded"""
        enhanced_key = EnhancedAPIKey.objects.create(
            api_key=self.user_api_key,
            rate_limit_per_day=86400,
            current_day_count=86400,
            quota_reset_at=timezone.now() + timedelta(days=1)  # Set future reset time
        )

        allowed, reason = enhanced_key.check_rate_limit()

        self.assertFalse(allowed)
        self.assertIn('day', reason.lower())

    def test_check_rate_limit_unlimited(self):
        """Test check_rate_limit() with unlimited (0) limits"""
        enhanced_key = EnhancedAPIKey.objects.create(
            api_key=self.user_api_key,
            rate_limit_per_minute=0,
            rate_limit_per_hour=0,
            rate_limit_per_day=0,
            current_minute_count=99999,
            current_hour_count=99999,
            current_day_count=99999,
            quota_reset_at=timezone.now() + timedelta(days=1)  # Set future reset time
        )

        allowed, reason = enhanced_key.check_rate_limit()

        self.assertTrue(allowed)
        self.assertEqual(reason, 'allowed')

    def test_increment_usage(self):
        """Test increment_usage() method"""
        enhanced_key = EnhancedAPIKey.objects.create(
            api_key=self.user_api_key,
            total_requests=0,
            current_minute_count=0,
            current_hour_count=0,
            current_day_count=0
        )

        enhanced_key.increment_usage()

        # Refresh from database
        enhanced_key.refresh_from_db()

        self.assertEqual(enhanced_key.total_requests, 1)
        self.assertEqual(enhanced_key.current_minute_count, 1)
        self.assertEqual(enhanced_key.current_hour_count, 1)
        self.assertEqual(enhanced_key.current_day_count, 1)
        self.assertIsNotNone(enhanced_key.last_request_at)

    def test_reset_quotas(self):
        """Test reset_quotas() method"""
        enhanced_key = EnhancedAPIKey.objects.create(
            api_key=self.user_api_key,
            current_minute_count=50,
            current_hour_count=500,
            current_day_count=5000
        )

        enhanced_key.reset_quotas()

        # Refresh from database
        enhanced_key.refresh_from_db()

        self.assertEqual(enhanced_key.current_minute_count, 0)
        self.assertEqual(enhanced_key.current_hour_count, 0)
        self.assertEqual(enhanced_key.current_day_count, 0)


class APIKeyUsageLogModelTest(TestCase):
    """Tests for APIKeyUsageLog model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@vetimage.com',
            password='testpass123',
            role=1
        )

        # Create UserAPIKey
        self.user_api_key = UserAPIKey.objects.create(
            user=self.user,
            key_prefix='oml_test',
            key_hash='dummy_hash_for_testing'
        )

    def test_create_usage_log(self):
        """Test creating a usage log entry"""
        usage_log = APIKeyUsageLog.objects.create(
            api_key=self.user_api_key,
            request_path='/api/dicom/studies/',
            request_method='GET',
            response_status=200,
            response_time_ms=150,
            ip_address='192.168.1.1',
            request_size_bytes=0,
            response_size_bytes=2048,
            scope_matched='dicom:read'
        )

        self.assertEqual(usage_log.api_key, self.user_api_key)
        self.assertEqual(usage_log.request_path, '/api/dicom/studies/')
        self.assertEqual(usage_log.request_method, 'GET')
        self.assertEqual(usage_log.response_status, 200)
        self.assertEqual(usage_log.response_time_ms, 150)
        self.assertFalse(usage_log.rate_limited)

    def test_usage_log_rate_limited(self):
        """Test usage log for rate-limited request"""
        usage_log = APIKeyUsageLog.objects.create(
            api_key=self.user_api_key,
            request_path='/api/dicom/studies/',
            request_method='GET',
            response_status=429,  # Too Many Requests
            response_time_ms=10,
            ip_address='192.168.1.1',
            rate_limited=True
        )

        self.assertTrue(usage_log.rate_limited)
        self.assertEqual(usage_log.response_status, 429)

    def test_usage_log_str_representation(self):
        """Test __str__ method"""
        usage_log = APIKeyUsageLog.objects.create(
            api_key=self.user_api_key,
            request_path='/api/dicom/studies/',
            request_method='GET',
            response_status=200,
            response_time_ms=150,
            ip_address='192.168.1.1'
        )

        expected_str = f"{self.user_api_key.key_prefix}... - GET /api/dicom/studies/"
        self.assertEqual(str(usage_log), expected_str)

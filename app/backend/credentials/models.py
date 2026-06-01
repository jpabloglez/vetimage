"""
Credentials App Models

Enhanced authentication system with session tracking, audit logging,
and API key management with scopes and rate limiting.
"""

import uuid
import re
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import F

# Import simplejwt models for JWT token correlation
try:
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
except ImportError:
    OutstandingToken = None

from .managers import UserSessionManager, AuditLogManager


class UserSession(models.Model):
    """
    Tracks active user sessions with enhanced metadata.
    Linked to simplejwt's OutstandingToken for JWT correlation.
    """

    # Primary identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sessions',
        db_index=True,
        help_text='User that owns this session'
    )

    # JWT correlation
    outstanding_token = models.OneToOneField(
        'token_blacklist.OutstandingToken',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='session_tracking',
        help_text='Associated JWT token (null for API key sessions)'
    )

    # Session metadata
    session_type = models.CharField(
        max_length=20,
        choices=[
            ('jwt', 'JWT Token'),
            ('api_key', 'API Key'),
        ],
        default='jwt',
        db_index=True,
        help_text='Type of authentication used'
    )

    # Device and client information
    user_agent = models.TextField(
        blank=True,
        help_text='Full User-Agent header'
    )
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('desktop', 'Desktop'),
            ('mobile', 'Mobile'),
            ('tablet', 'Tablet'),
            ('api', 'API/Automated'),
            ('unknown', 'Unknown'),
        ],
        default='unknown',
        db_index=True,
        help_text='Detected device type'
    )
    browser = models.CharField(max_length=100, blank=True)
    browser_version = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=100, blank=True, verbose_name='Operating System')
    os_version = models.CharField(max_length=50, blank=True)

    # Network information
    ip_address = models.GenericIPAddressField(
        db_index=True,
        help_text='Client IP address'
    )
    ip_country = models.CharField(
        max_length=2,
        blank=True,
        help_text='ISO country code'
    )
    ip_city = models.CharField(max_length=100, blank=True)

    # Session lifecycle
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='Session creation timestamp'
    )
    last_activity_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text='Last activity timestamp'
    )
    expires_at = models.DateTimeField(
        db_index=True,
        help_text='Session expiration timestamp'
    )
    terminated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Session termination timestamp'
    )

    # Session status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether session is currently active'
    )
    termination_reason = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('logout', 'User Logout'),
            ('expired', 'Token Expired'),
            ('revoked', 'Manually Revoked'),
            ('concurrent_limit', 'Concurrent Session Limit'),
            ('security', 'Security Issue Detected'),
        ],
        help_text='Reason for session termination'
    )

    # Security flags
    is_suspicious = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Flagged by anomaly detection'
    )
    suspicious_reason = models.TextField(
        blank=True,
        help_text='Reason for suspicious flag'
    )

    # Custom manager
    objects = UserSessionManager()

    class Meta:
        db_table = 'credentials_user_sessions'
        ordering = ['-created_at']
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        indexes = [
            models.Index(fields=['user', 'is_active', '-created_at']),
            models.Index(fields=['user', 'ip_address']),
            models.Index(fields=['-last_activity_at']),
            models.Index(fields=['is_suspicious', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.device_type} - {self.ip_address}"

    def is_valid(self):
        """Check if session is currently valid"""
        if not self.is_active:
            return False
        if self.terminated_at:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True

    def terminate(self, reason='logout'):
        """Terminate the session"""
        self.is_active = False
        self.terminated_at = timezone.now()
        self.termination_reason = reason
        self.save(update_fields=['is_active', 'terminated_at', 'termination_reason'])

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity_at = timezone.now()
        self.save(update_fields=['last_activity_at'])


class AuditLog(models.Model):
    """
    Immutable audit trail for authentication and authorization events.
    Designed for compliance and forensic analysis.
    """

    # Primary identification
    id = models.BigAutoField(primary_key=True)

    # User (nullable for failed login attempts)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        db_index=True,
        help_text='User involved in the event (null for failed logins)'
    )
    username_attempted = models.CharField(
        max_length=255,
        blank=True,
        help_text='Email/username used in attempt (even if user not found)'
    )

    # Event details
    event_type = models.CharField(
        max_length=50,
        choices=[
            # Authentication events
            ('login_success', 'Login Success'),
            ('login_failed', 'Login Failed'),
            ('logout', 'Logout'),
            ('token_refresh', 'Token Refresh'),
            ('token_expired', 'Token Expired'),
            ('token_blacklisted', 'Token Blacklisted'),

            # Password events
            ('password_change', 'Password Change'),
            ('password_reset_request', 'Password Reset Request'),
            ('password_reset_complete', 'Password Reset Complete'),

            # API Key events
            ('apikey_auth', 'API Key Authentication'),
            ('apikey_created', 'API Key Created'),
            ('apikey_revoked', 'API Key Revoked'),
            ('apikey_expired', 'API Key Expired'),

            # Session events
            ('session_created', 'Session Created'),
            ('session_terminated', 'Session Terminated'),
            ('concurrent_session_limit', 'Concurrent Session Limit Hit'),

            # Security events
            ('suspicious_activity', 'Suspicious Activity Detected'),
            ('rate_limit_exceeded', 'Rate Limit Exceeded'),
            ('invalid_token', 'Invalid Token Used'),
            ('scope_violation', 'API Key Scope Violation'),
        ],
        db_index=True,
        help_text='Type of event'
    )

    event_timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='When the event occurred'
    )

    # Request context
    ip_address = models.GenericIPAddressField(
        db_index=True,
        help_text='Client IP address'
    )
    user_agent = models.TextField(
        blank=True,
        help_text='User agent string'
    )
    request_path = models.CharField(
        max_length=255,
        blank=True,
        help_text='API endpoint path'
    )
    request_method = models.CharField(
        max_length=10,
        blank=True,
        help_text='HTTP method'
    )

    # Session correlation
    session = models.ForeignKey(
        UserSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text='Associated session'
    )

    # Additional context (JSON)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional event-specific data'
    )

    # Security flags
    is_suspicious = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Event flagged as suspicious'
    )
    risk_score = models.IntegerField(
        default=0,
        help_text='Calculated risk score (0-100)'
    )

    # Custom manager
    objects = AuditLogManager()

    class Meta:
        db_table = 'credentials_audit_logs'
        ordering = ['-event_timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['user', '-event_timestamp']),
            models.Index(fields=['event_type', '-event_timestamp']),
            models.Index(fields=['ip_address', '-event_timestamp']),
            models.Index(fields=['is_suspicious', '-event_timestamp']),
        ]
        permissions = [
            ('view_audit_logs', 'Can view audit logs'),
            ('export_audit_logs', 'Can export audit logs'),
        ]

    def __str__(self):
        user_str = self.user.email if self.user else self.username_attempted
        return f"{self.event_type} - {user_str} - {self.event_timestamp}"

    def save(self, *args, **kwargs):
        """Enforce immutability after creation"""
        if self.pk:
            raise ValueError("AuditLog entries are immutable and cannot be modified")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of audit logs"""
        raise ValueError("AuditLog entries cannot be deleted")


class APIKeyScope(models.Model):
    """
    Defines permission scopes that can be assigned to API keys.
    Enables fine-grained access control for automated systems.
    """

    # Identification
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text='Unique scope identifier (e.g., "dicom:read", "ai:submit")'
    )
    display_name = models.CharField(
        max_length=200,
        help_text='Human-readable name'
    )
    description = models.TextField(
        help_text='What this scope allows'
    )

    # Scope category
    category = models.CharField(
        max_length=50,
        choices=[
            ('dicom', 'DICOM Operations'),
            ('ai', 'AI Analysis'),
            ('users', 'User Management'),
            ('admin', 'Administrative'),
        ],
        db_index=True,
        help_text='Scope category'
    )

    # Permission specification
    allowed_endpoints = models.JSONField(
        default=list,
        help_text='List of URL patterns this scope grants access to'
    )
    allowed_methods = models.JSONField(
        default=list,
        help_text='Allowed HTTP methods (GET, POST, etc.)'
    )

    # Metadata
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this scope is currently active'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'credentials_api_key_scopes'
        ordering = ['category', 'name']
        verbose_name = 'API Key Scope'
        verbose_name_plural = 'API Key Scopes'

    def __str__(self):
        return f"{self.name} - {self.display_name}"

    def matches_request(self, path, method):
        """Check if this scope allows the given request"""
        # Check method
        if self.allowed_methods and method not in self.allowed_methods:
            return False

        # Check path patterns
        for pattern in self.allowed_endpoints:
            if re.match(pattern, path):
                return True
        return False


class EnhancedAPIKey(models.Model):
    """
    Enhancement to users.UserAPIKey with scopes and rate limiting.
    Links 1:1 with existing UserAPIKey for backward compatibility.
    """

    # Link to existing UserAPIKey
    api_key = models.OneToOneField(
        'users.UserAPIKey',
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='enhanced',
        help_text='Associated UserAPIKey'
    )

    # Scopes (permissions)
    scopes = models.ManyToManyField(
        APIKeyScope,
        related_name='api_keys',
        blank=True,
        help_text='Permissions granted to this API key'
    )

    # Rate limiting
    rate_limit_per_minute = models.IntegerField(
        default=60,
        help_text='Maximum requests per minute (0 = unlimited)'
    )
    rate_limit_per_hour = models.IntegerField(
        default=3600,
        help_text='Maximum requests per hour (0 = unlimited)'
    )
    rate_limit_per_day = models.IntegerField(
        default=86400,
        help_text='Maximum requests per day (0 = unlimited)'
    )

    # Quota tracking
    current_minute_count = models.IntegerField(
        default=0,
        help_text='Current minute request count'
    )
    current_hour_count = models.IntegerField(
        default=0,
        help_text='Current hour request count'
    )
    current_day_count = models.IntegerField(
        default=0,
        help_text='Current day request count'
    )
    quota_reset_at = models.DateTimeField(
        default=timezone.now,
        help_text='When quotas were last reset'
    )

    # Usage statistics
    total_requests = models.BigIntegerField(
        default=0,
        help_text='Total requests made with this key'
    )
    last_request_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of last request'
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'credentials_enhanced_api_keys'
        verbose_name = 'Enhanced API Key'
        verbose_name_plural = 'Enhanced API Keys'

    def __str__(self):
        return f"Enhanced {self.api_key}"

    def has_scope(self, scope_name):
        """Check if this API key has a specific scope"""
        return self.scopes.filter(name=scope_name, is_active=True).exists()

    def can_access(self, path, method):
        """Check if this API key can access the given endpoint"""
        for scope in self.scopes.filter(is_active=True):
            if scope.matches_request(path, method):
                return True
        return False

    def check_rate_limit(self):
        """
        Check if rate limit is exceeded.
        Returns (allowed: bool, reason: str)
        """
        now = timezone.now()

        # Reset counters if needed
        if now > self.quota_reset_at:
            self.reset_quotas()

        # Check limits
        if self.rate_limit_per_minute > 0 and self.current_minute_count >= self.rate_limit_per_minute:
            return False, 'minute_limit_exceeded'
        if self.rate_limit_per_hour > 0 and self.current_hour_count >= self.rate_limit_per_hour:
            return False, 'hour_limit_exceeded'
        if self.rate_limit_per_day > 0 and self.current_day_count >= self.rate_limit_per_day:
            return False, 'day_limit_exceeded'

        return True, 'allowed'

    def increment_usage(self):
        """Increment usage counters"""
        self.current_minute_count = F('current_minute_count') + 1
        self.current_hour_count = F('current_hour_count') + 1
        self.current_day_count = F('current_day_count') + 1
        self.total_requests = F('total_requests') + 1
        self.last_request_at = timezone.now()
        self.save()
        self.refresh_from_db()  # Refresh to get actual values

    def reset_quotas(self):
        """Reset rate limit counters"""
        self.current_minute_count = 0
        self.current_hour_count = 0
        self.current_day_count = 0
        self.quota_reset_at = timezone.now() + timezone.timedelta(minutes=1)
        self.save()


class APIKeyUsageLog(models.Model):
    """
    Detailed request-level tracking for API key usage.
    Used for analytics, billing, and debugging.
    """

    # Primary identification
    id = models.BigAutoField(primary_key=True)

    # API key reference
    api_key = models.ForeignKey(
        'users.UserAPIKey',
        on_delete=models.CASCADE,
        related_name='usage_logs',
        db_index=True,
        help_text='API key that made the request'
    )

    # Request details
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='When the request was made'
    )
    request_path = models.CharField(
        max_length=255,
        db_index=True,
        help_text='API endpoint accessed'
    )
    request_method = models.CharField(
        max_length=10,
        help_text='HTTP method'
    )
    response_status = models.IntegerField(
        help_text='HTTP response status code'
    )
    response_time_ms = models.IntegerField(
        help_text='Response time in milliseconds'
    )

    # Network info
    ip_address = models.GenericIPAddressField(
        help_text='Client IP address'
    )

    # Usage metrics
    request_size_bytes = models.IntegerField(
        default=0,
        help_text='Request body size in bytes'
    )
    response_size_bytes = models.IntegerField(
        default=0,
        help_text='Response body size in bytes'
    )

    # Scope used
    scope_matched = models.CharField(
        max_length=100,
        blank=True,
        help_text='Which scope was used for this request'
    )

    # Rate limiting
    rate_limited = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether this request was rate limited'
    )

    class Meta:
        db_table = 'credentials_api_key_usage_logs'
        ordering = ['-timestamp']
        verbose_name = 'API Key Usage Log'
        verbose_name_plural = 'API Key Usage Logs'
        indexes = [
            models.Index(fields=['api_key', '-timestamp']),
            models.Index(fields=['request_path', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f"{self.api_key.key_prefix}... - {self.request_method} {self.request_path}"


class Notification(models.Model):
    """
    In-app notification for users.
    Created on analysis completion/failure and other system events.
    """

    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True,
    )
    message = models.TextField()
    notification_type = models.CharField(
        max_length=10,
        choices=NOTIFICATION_TYPES,
        default='info',
    )
    is_read = models.BooleanField(default=False, db_index=True)
    link = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'credentials_notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"{self.notification_type}: {self.message[:60]}"

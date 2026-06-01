"""
DRF Serializers for credentials app
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    UserSession,
    AuditLog,
    APIKeyScope,
    EnhancedAPIKey,
    APIKeyUsageLog,
    Notification,
)
from users.models import UserAPIKey

User = get_user_model()


class UserSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for UserSession model.

    Provides session information with device fingerprint and security details.
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)
    is_current = serializers.SerializerMethodField()
    session_duration = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = [
            'id',
            'user_email',
            'session_type',
            'device_type',
            'browser',
            'browser_version',
            'os',
            'os_version',
            'ip_address',
            'ip_country',
            'ip_city',
            'created_at',
            'last_activity_at',
            'expires_at',
            'terminated_at',
            'is_active',
            'termination_reason',
            'is_suspicious',
            'suspicious_reason',
            'is_current',
            'session_duration',
        ]
        read_only_fields = [
            'id',
            'user_email',
            'session_type',
            'device_type',
            'browser',
            'browser_version',
            'os',
            'os_version',
            'ip_address',
            'ip_country',
            'ip_city',
            'created_at',
            'last_activity_at',
            'expires_at',
            'terminated_at',
            'is_active',
            'termination_reason',
            'is_suspicious',
            'suspicious_reason',
            'is_current',
            'session_duration',
        ]

    def get_is_current(self, obj):
        """Check if this is the current session"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'auth'):
            return False

        # Try to match by JWT token
        if hasattr(request.auth, 'payload'):
            jti = request.auth.payload.get('jti')
            if obj.outstanding_token:
                return str(obj.outstanding_token.jti) == str(jti)

        return False

    def get_session_duration(self, obj):
        """Calculate session duration in seconds"""
        if obj.terminated_at:
            return int((obj.terminated_at - obj.created_at).total_seconds())
        else:
            from django.utils import timezone
            return int((timezone.now() - obj.created_at).total_seconds())


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for AuditLog model.

    Read-only serializer for audit log entries.
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'user_email',
            'username_attempted',
            'event_type',
            'event_type_display',
            'event_timestamp',
            'ip_address',
            'user_agent',
            'request_path',
            'request_method',
            'metadata',
            'is_suspicious',
            'risk_score',
        ]
        read_only_fields = [
            'id',
            'user_email',
            'username_attempted',
            'event_type',
            'event_type_display',
            'event_timestamp',
            'ip_address',
            'user_agent',
            'request_path',
            'request_method',
            'metadata',
            'is_suspicious',
            'risk_score',
        ]


class APIKeyScopeSerializer(serializers.ModelSerializer):
    """
    Serializer for APIKeyScope model.

    Provides scope information with endpoint patterns.
    """
    api_keys_count = serializers.SerializerMethodField()

    class Meta:
        model = APIKeyScope
        fields = [
            'id',
            'name',
            'display_name',
            'description',
            'category',
            'allowed_endpoints',
            'allowed_methods',
            'is_active',
            'api_keys_count',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'api_keys_count']

    def get_api_keys_count(self, obj):
        """Count how many API keys use this scope"""
        return obj.api_keys.count()


class EnhancedAPIKeySerializer(serializers.ModelSerializer):
    """
    Serializer for EnhancedAPIKey model.

    Provides API key information with scopes and rate limits.
    """
    api_key_prefix = serializers.CharField(source='api_key.key_prefix', read_only=True)
    user_email = serializers.EmailField(source='api_key.user.email', read_only=True)
    scopes = APIKeyScopeSerializer(many=True, read_only=True)
    scope_names = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    current_usage = serializers.SerializerMethodField()
    rate_limit_status = serializers.SerializerMethodField()

    class Meta:
        model = EnhancedAPIKey
        fields = [
            'api_key_prefix',
            'user_email',
            'scopes',
            'scope_names',
            'rate_limit_per_minute',
            'rate_limit_per_hour',
            'rate_limit_per_day',
            'current_usage',
            'rate_limit_status',
            'total_requests',
            'last_request_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'api_key_prefix',
            'user_email',
            'scopes',
            'current_usage',
            'rate_limit_status',
            'total_requests',
            'last_request_at',
            'created_at',
            'updated_at',
        ]

    def get_current_usage(self, obj):
        """Get current usage counts"""
        return {
            'minute': obj.current_minute_count,
            'hour': obj.current_hour_count,
            'day': obj.current_day_count,
            'quota_reset_at': obj.quota_reset_at,
        }

    def get_rate_limit_status(self, obj):
        """Check rate limit status"""
        allowed, reason = obj.check_rate_limit()
        return {
            'allowed': allowed,
            'reason': reason,
        }

    def update(self, instance, validated_data):
        """Update enhanced API key, handling scope assignment"""
        scope_names = validated_data.pop('scope_names', None)

        # Update rate limits
        instance = super().update(instance, validated_data)

        # Update scopes if provided
        if scope_names is not None:
            from .services import get_scope_by_name
            scopes = []
            for scope_name in scope_names:
                scope = get_scope_by_name(scope_name)
                if scope:
                    scopes.append(scope)

            instance.scopes.set(scopes)

        return instance


class APIKeyUsageLogSerializer(serializers.ModelSerializer):
    """
    Serializer for APIKeyUsageLog model.

    Read-only serializer for API key usage logs.
    """
    api_key_prefix = serializers.CharField(source='api_key.key_prefix', read_only=True)

    class Meta:
        model = APIKeyUsageLog
        fields = [
            'id',
            'api_key_prefix',
            'timestamp',
            'request_path',
            'request_method',
            'response_status',
            'response_time_ms',
            'ip_address',
            'request_size_bytes',
            'response_size_bytes',
            'scope_matched',
            'rate_limited',
        ]
        read_only_fields = [
            'id',
            'api_key_prefix',
            'timestamp',
            'request_path',
            'request_method',
            'response_status',
            'response_time_ms',
            'ip_address',
            'request_size_bytes',
            'response_size_bytes',
            'scope_matched',
            'rate_limited',
        ]


class SessionTerminateSerializer(serializers.Serializer):
    """
    Serializer for session termination request.
    """
    reason = serializers.ChoiceField(
        choices=[
            ('manual', 'Manual Termination'),
            ('security', 'Security Issue'),
            ('other', 'Other'),
        ],
        default='manual'
    )


class APIKeyUsageStatsSerializer(serializers.Serializer):
    """
    Serializer for API key usage statistics.
    """
    api_key_id = serializers.IntegerField(read_only=True)
    api_key_prefix = serializers.CharField(read_only=True)
    total_requests = serializers.IntegerField(read_only=True)
    last_request_at = serializers.DateTimeField(read_only=True)

    rate_limits = serializers.DictField(read_only=True)
    current_usage = serializers.DictField(read_only=True)
    scopes = serializers.ListField(child=serializers.CharField(), read_only=True)

    usage_by_endpoint = serializers.ListField(read_only=True)
    usage_by_status = serializers.ListField(read_only=True)

    class Meta:
        fields = [
            'api_key_id',
            'api_key_prefix',
            'total_requests',
            'last_request_at',
            'rate_limits',
            'current_usage',
            'scopes',
            'usage_by_endpoint',
            'usage_by_status',
        ]


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""

    class Meta:
        model = Notification
        fields = [
            'id',
            'message',
            'notification_type',
            'is_read',
            'created_at',
            'link',
        ]
        read_only_fields = ['id', 'message', 'notification_type', 'created_at', 'link']

"""
Django Admin for credentials app
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg, Sum
import json

from .models import (
    UserSession,
    AuditLog,
    APIKeyScope,
    EnhancedAPIKey,
    APIKeyUsageLog
)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """Admin interface for UserSession model"""

    list_display = [
        'id',
        'user_link',
        'session_type',
        'device_type',
        'browser_display',
        'os_display',
        'ip_address',
        'location_display',
        'created_at',
        'last_activity_at',
        'status_display',
        'suspicious_flag'
    ]

    list_filter = [
        'is_active',
        'session_type',
        'device_type',
        'is_suspicious',
        'created_at',
        'termination_reason'
    ]

    search_fields = [
        'user__email',
        'ip_address',
        'ip_country',
        'ip_city',
        'user_agent'
    ]

    readonly_fields = [
        'id',
        'user',
        'outstanding_token',
        'session_type',
        'user_agent',
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
        'termination_reason',
        'audit_logs_display'
    ]

    fieldsets = (
        ('Session Information', {
            'fields': ('id', 'user', 'session_type', 'is_active', 'outstanding_token')
        }),
        ('Device & Browser', {
            'fields': ('user_agent', 'device_type', 'browser', 'browser_version', 'os', 'os_version')
        }),
        ('Network Information', {
            'fields': ('ip_address', 'ip_country', 'ip_city')
        }),
        ('Lifecycle', {
            'fields': ('created_at', 'last_activity_at', 'expires_at', 'terminated_at', 'termination_reason')
        }),
        ('Security', {
            'fields': ('is_suspicious', 'suspicious_reason'),
            'classes': ('collapse',)
        }),
        ('Related Audit Logs', {
            'fields': ('audit_logs_display',),
            'classes': ('collapse',)
        })
    )

    actions = ['revoke_sessions', 'flag_as_suspicious']

    def user_link(self, obj):
        """Display user as clickable link"""
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = 'User'

    def browser_display(self, obj):
        """Display browser with version"""
        if obj.browser:
            return f"{obj.browser} {obj.browser_version}" if obj.browser_version else obj.browser
        return '-'
    browser_display.short_description = 'Browser'

    def os_display(self, obj):
        """Display OS with version"""
        if obj.os:
            return f"{obj.os} {obj.os_version}" if obj.os_version else obj.os
        return '-'
    os_display.short_description = 'OS'

    def location_display(self, obj):
        """Display location"""
        parts = []
        if obj.ip_city:
            parts.append(obj.ip_city)
        if obj.ip_country:
            parts.append(obj.ip_country)
        return ', '.join(parts) if parts else '-'
    location_display.short_description = 'Location'

    def status_display(self, obj):
        """Display active status with color"""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">●</span> Active'
            )
        else:
            return format_html(
                '<span style="color: red;">●</span> Terminated'
            )
    status_display.short_description = 'Status'

    def suspicious_flag(self, obj):
        """Display suspicious flag"""
        if obj.is_suspicious:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠ SUSPICIOUS</span>'
            )
        return '-'
    suspicious_flag.short_description = 'Security'

    def audit_logs_display(self, obj):
        """Display related audit logs"""
        logs = obj.audit_logs.all()[:10]
        if not logs:
            return "No audit logs"

        html = '<ul style="margin: 0; padding-left: 20px;">'
        for log in logs:
            html += f'<li>{log.event_timestamp.strftime("%Y-%m-%d %H:%M:%S")} - {log.get_event_type_display()}</li>'
        html += '</ul>'
        return mark_safe(html)
    audit_logs_display.short_description = 'Recent Audit Logs'

    def revoke_sessions(self, request, queryset):
        """Bulk revoke sessions"""
        count = 0
        for session in queryset.filter(is_active=True):
            session.terminate(reason='revoked')
            count += 1
        self.message_user(request, f'{count} session(s) revoked successfully.')
    revoke_sessions.short_description = 'Revoke selected sessions'

    def flag_as_suspicious(self, request, queryset):
        """Flag sessions as suspicious"""
        count = queryset.update(is_suspicious=True, suspicious_reason='Flagged by admin')
        self.message_user(request, f'{count} session(s) flagged as suspicious.')
    flag_as_suspicious.short_description = 'Flag as suspicious'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model (read-only)"""

    list_display = [
        'id',
        'event_timestamp',
        'event_type',
        'user_link',
        'username_attempted',
        'ip_address',
        'request_path',
        'suspicious_display',
        'risk_score_display'
    ]

    list_filter = [
        'event_type',
        'is_suspicious',
        'event_timestamp',
        ('risk_score', admin.EmptyFieldListFilter)
    ]

    search_fields = [
        'user__email',
        'username_attempted',
        'ip_address',
        'request_path'
    ]

    readonly_fields = [
        'id',
        'user',
        'username_attempted',
        'event_type',
        'event_timestamp',
        'ip_address',
        'user_agent',
        'request_path',
        'request_method',
        'session',
        'metadata_display',
        'is_suspicious',
        'risk_score'
    ]

    fieldsets = (
        ('Event Information', {
            'fields': ('id', 'event_type', 'event_timestamp', 'user', 'username_attempted')
        }),
        ('Request Context', {
            'fields': ('ip_address', 'user_agent', 'request_path', 'request_method')
        }),
        ('Session', {
            'fields': ('session',)
        }),
        ('Metadata', {
            'fields': ('metadata_display',),
            'classes': ('collapse',)
        }),
        ('Security', {
            'fields': ('is_suspicious', 'risk_score')
        })
    )

    def has_add_permission(self, request):
        """Prevent manual creation"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion"""
        return False

    def user_link(self, obj):
        """Display user as clickable link"""
        if obj.user:
            url = reverse('admin:users_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return '-'
    user_link.short_description = 'User'

    def suspicious_display(self, obj):
        """Display suspicious flag"""
        if obj.is_suspicious:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠ YES</span>'
            )
        return '-'
    suspicious_display.short_description = 'Suspicious'

    def risk_score_display(self, obj):
        """Display risk score with color coding"""
        if obj.risk_score == 0:
            return '-'

        if obj.risk_score >= 75:
            color = 'red'
        elif obj.risk_score >= 50:
            color = 'orange'
        else:
            color = 'green'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.risk_score
        )
    risk_score_display.short_description = 'Risk Score'

    def metadata_display(self, obj):
        """Display metadata JSON formatted"""
        if not obj.metadata:
            return "No metadata"

        formatted_json = json.dumps(obj.metadata, indent=2)
        return format_html('<pre style="margin: 0;">{}</pre>', formatted_json)
    metadata_display.short_description = 'Metadata'


@admin.register(APIKeyScope)
class APIKeyScopeAdmin(admin.ModelAdmin):
    """Admin interface for APIKeyScope model"""

    list_display = [
        'name',
        'display_name',
        'category',
        'active_display',
        'api_keys_count',
        'created_at'
    ]

    list_filter = [
        'category',
        'is_active',
        'created_at'
    ]

    search_fields = [
        'name',
        'display_name',
        'description'
    ]

    readonly_fields = ['created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'display_name', 'description', 'category', 'is_active')
        }),
        ('Access Control', {
            'fields': ('allowed_endpoints', 'allowed_methods'),
            'description': 'Define which endpoints and HTTP methods this scope grants access to.'
        }),
        ('Metadata', {
            'fields': ('created_at',)
        })
    )

    actions = ['activate_scopes', 'deactivate_scopes']

    def active_display(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Active</span>'
            )
        return format_html(
            '<span style="color: gray;">✗ Inactive</span>'
        )
    active_display.short_description = 'Status'

    def api_keys_count(self, obj):
        """Count API keys using this scope"""
        count = obj.api_keys.count()
        return format_html(
            '<span style="font-weight: bold;">{}</span> key(s)',
            count
        )
    api_keys_count.short_description = 'API Keys'

    def activate_scopes(self, request, queryset):
        """Bulk activate scopes"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} scope(s) activated.')
    activate_scopes.short_description = 'Activate selected scopes'

    def deactivate_scopes(self, request, queryset):
        """Bulk deactivate scopes"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} scope(s) deactivated.')
    deactivate_scopes.short_description = 'Deactivate selected scopes'


@admin.register(EnhancedAPIKey)
class EnhancedAPIKeyAdmin(admin.ModelAdmin):
    """Admin interface for EnhancedAPIKey model"""

    list_display = [
        'api_key_display',
        'user_link',
        'scopes_display',
        'rate_limits_display',
        'total_requests',
        'last_request_at',
        'created_at'
    ]

    list_filter = [
        'created_at',
        'scopes'
    ]

    search_fields = [
        'api_key__user__email',
        'api_key__key_prefix'
    ]

    readonly_fields = [
        'api_key',
        'total_requests',
        'last_request_at',
        'created_at',
        'updated_at',
        'quota_status_display'
    ]

    filter_horizontal = ['scopes']

    fieldsets = (
        ('API Key', {
            'fields': ('api_key',)
        }),
        ('Scopes', {
            'fields': ('scopes',),
            'description': 'Select which permissions this API key has.'
        }),
        ('Rate Limits', {
            'fields': (
                'rate_limit_per_minute',
                'rate_limit_per_hour',
                'rate_limit_per_day'
            ),
            'description': 'Set to 0 for unlimited. Current quota usage shown below.'
        }),
        ('Current Quota Usage', {
            'fields': ('quota_status_display',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_requests', 'last_request_at', 'created_at', 'updated_at')
        })
    )

    actions = ['reset_quotas', 'assign_full_access']

    def api_key_display(self, obj):
        """Display API key prefix"""
        return obj.api_key.key_prefix
    api_key_display.short_description = 'API Key'

    def user_link(self, obj):
        """Display user as clickable link"""
        url = reverse('admin:users_user_change', args=[obj.api_key.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.api_key.user.email)
    user_link.short_description = 'User'

    def scopes_display(self, obj):
        """Display assigned scopes"""
        scopes = obj.scopes.all()[:5]
        if not scopes:
            return format_html('<span style="color: gray;">No scopes</span>')

        scope_names = [s.name for s in scopes]
        if obj.scopes.count() > 5:
            scope_names.append(f'... +{obj.scopes.count() - 5} more')

        return ', '.join(scope_names)
    scopes_display.short_description = 'Scopes'

    def rate_limits_display(self, obj):
        """Display rate limits"""
        limits = []
        if obj.rate_limit_per_minute > 0:
            limits.append(f'{obj.rate_limit_per_minute}/min')
        if obj.rate_limit_per_hour > 0:
            limits.append(f'{obj.rate_limit_per_hour}/hr')
        if obj.rate_limit_per_day > 0:
            limits.append(f'{obj.rate_limit_per_day}/day')

        return ', '.join(limits) if limits else 'Unlimited'
    rate_limits_display.short_description = 'Rate Limits'

    def quota_status_display(self, obj):
        """Display current quota usage"""
        html = '<table style="border-collapse: collapse; width: 100%;">'
        html += '<tr><th style="text-align: left; padding: 5px; border-bottom: 1px solid #ddd;">Period</th>'
        html += '<th style="text-align: left; padding: 5px; border-bottom: 1px solid #ddd;">Usage</th>'
        html += '<th style="text-align: left; padding: 5px; border-bottom: 1px solid #ddd;">Limit</th></tr>'

        # Minute
        if obj.rate_limit_per_minute > 0:
            usage_pct = (obj.current_minute_count / obj.rate_limit_per_minute) * 100
            color = 'red' if usage_pct > 90 else 'orange' if usage_pct > 75 else 'green'
            html += f'<tr><td style="padding: 5px;">Minute</td>'
            html += f'<td style="padding: 5px;"><span style="color: {color}; font-weight: bold;">{obj.current_minute_count}</span></td>'
            html += f'<td style="padding: 5px;">{obj.rate_limit_per_minute}</td></tr>'

        # Hour
        if obj.rate_limit_per_hour > 0:
            usage_pct = (obj.current_hour_count / obj.rate_limit_per_hour) * 100
            color = 'red' if usage_pct > 90 else 'orange' if usage_pct > 75 else 'green'
            html += f'<tr><td style="padding: 5px;">Hour</td>'
            html += f'<td style="padding: 5px;"><span style="color: {color}; font-weight: bold;">{obj.current_hour_count}</span></td>'
            html += f'<td style="padding: 5px;">{obj.rate_limit_per_hour}</td></tr>'

        # Day
        if obj.rate_limit_per_day > 0:
            usage_pct = (obj.current_day_count / obj.rate_limit_per_day) * 100
            color = 'red' if usage_pct > 90 else 'orange' if usage_pct > 75 else 'green'
            html += f'<tr><td style="padding: 5px;">Day</td>'
            html += f'<td style="padding: 5px;"><span style="color: {color}; font-weight: bold;">{obj.current_day_count}</span></td>'
            html += f'<td style="padding: 5px;">{obj.rate_limit_per_day}</td></tr>'

        html += '</table>'
        html += f'<p style="margin-top: 10px;"><small>Last reset: {obj.quota_reset_at.strftime("%Y-%m-%d %H:%M:%S")}</small></p>'

        return mark_safe(html)
    quota_status_display.short_description = 'Current Quota Usage'

    def reset_quotas(self, request, queryset):
        """Reset rate limit quotas"""
        count = 0
        for key in queryset:
            key.reset_quotas()
            count += 1
        self.message_user(request, f'Reset quotas for {count} API key(s).')
    reset_quotas.short_description = 'Reset rate limit quotas'

    def assign_full_access(self, request, queryset):
        """Assign full_access scope to selected keys"""
        try:
            full_access = APIKeyScope.objects.get(name='full_access')
            count = 0
            for key in queryset:
                key.scopes.add(full_access)
                count += 1
            self.message_user(request, f'Assigned full_access scope to {count} API key(s).')
        except APIKeyScope.DoesNotExist:
            self.message_user(request, 'Error: full_access scope does not exist.', level='error')
    assign_full_access.short_description = 'Assign full_access scope'


@admin.register(APIKeyUsageLog)
class APIKeyUsageLogAdmin(admin.ModelAdmin):
    """Admin interface for APIKeyUsageLog model (read-only)"""

    list_display = [
        'id',
        'timestamp',
        'api_key_display',
        'request_path',
        'request_method',
        'response_status_display',
        'response_time_ms',
        'ip_address',
        'rate_limited_display'
    ]

    list_filter = [
        'request_method',
        'response_status',
        'rate_limited',
        'timestamp'
    ]

    search_fields = [
        'api_key__key_prefix',
        'api_key__user__email',
        'request_path',
        'ip_address'
    ]

    readonly_fields = [
        'id',
        'api_key',
        'timestamp',
        'request_path',
        'request_method',
        'response_status',
        'response_time_ms',
        'ip_address',
        'request_size_bytes',
        'response_size_bytes',
        'scope_matched',
        'rate_limited'
    ]

    fieldsets = (
        ('Request Information', {
            'fields': ('id', 'api_key', 'timestamp', 'request_path', 'request_method', 'ip_address')
        }),
        ('Response', {
            'fields': ('response_status', 'response_time_ms')
        }),
        ('Bandwidth', {
            'fields': ('request_size_bytes', 'response_size_bytes')
        }),
        ('Access Control', {
            'fields': ('scope_matched', 'rate_limited')
        })
    )

    def has_add_permission(self, request):
        """Prevent manual creation"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion"""
        return False

    def api_key_display(self, obj):
        """Display API key prefix"""
        return obj.api_key.key_prefix
    api_key_display.short_description = 'API Key'

    def response_status_display(self, obj):
        """Display response status with color"""
        if 200 <= obj.response_status < 300:
            color = 'green'
        elif 300 <= obj.response_status < 400:
            color = 'blue'
        elif 400 <= obj.response_status < 500:
            color = 'orange'
        else:
            color = 'red'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.response_status
        )
    response_status_display.short_description = 'Status'

    def rate_limited_display(self, obj):
        """Display rate limited flag"""
        if obj.rate_limited:
            return format_html(
                '<span style="color: red; font-weight: bold;">⚠ YES</span>'
            )
        return '-'
    rate_limited_display.short_description = 'Rate Limited'

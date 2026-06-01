"""
Django Admin for DICOM Gateway Models
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import PACSConfiguration, DICOMTransaction, AuditEvent, GatewayHealth


@admin.register(PACSConfiguration)
class PACSConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for PACS configurations"""

    list_display = [
        'name',
        'ae_title',
        'manufacturer',
        'host',
        'port',
        'node_user_display',
        'receiving_org_display',
        'connection_status_badge',
        'is_active',
        'last_connected',
    ]
    list_filter = ['is_active', 'connection_status', 'auto_analyze_enabled', 'receiving_organization', 'manufacturer']
    search_fields = ['name', 'ae_title', 'host', 'node_user__email', 'manufacturer', 'node']
    readonly_fields = ['id', 'connection_status', 'last_connected', 'last_error', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'ae_title', 'description', 'manufacturer', 'node', 'is_active')
        }),
        ('Network Configuration', {
            'fields': ('host', 'port', 'max_pdu_length', 'timeout')
        }),
        ('User Mapping', {
            'fields': ('node_user', 'receiving_organization'),
            'description': 'Configure which user should receive DICOM transfers from this PACS. '
                          'The user must have an active API key. Organization is inherited from user profile.'
        }),
        ('Security', {
            'fields': ('tls_enabled', 'tls_cert_path', 'allowed_source_ips'),
            'classes': ('collapse',)
        }),
        ('Workflow Automation', {
            'fields': ('auto_retrieve_enabled', 'auto_analyze_enabled', 'default_model_key'),
            'classes': ('collapse',)
        }),
        ('Status & Audit', {
            'fields': ('connection_status', 'last_connected', 'last_error', 'created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    def connection_status_badge(self, obj):
        """Display connection status as colored badge"""
        colors = {
            'connected': 'green',
            'disconnected': 'gray',
            'error': 'red',
        }
        color = colors.get(obj.connection_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_connection_status_display()
        )
    connection_status_badge.short_description = 'Status'

    def node_user_display(self, obj):
        """Display node user with API key status"""
        if obj.node_user:
            # Check if user has active API key
            from users.models import UserAPIKey
            has_api_key = UserAPIKey.objects.filter(
                user=obj.node_user,
                is_active=True
            ).exists()

            if has_api_key:
                return format_html(
                    '<span style="color: green;">✓ {} (API key active)</span>',
                    obj.node_user.email
                )
            else:
                return format_html(
                    '<span style="color: red;">✗ {} (No API key!)</span>',
                    obj.node_user.email
                )
        return format_html('<span style="color: orange;">⚠ Gateway Service</span>')
    node_user_display.short_description = 'Node User'

    def receiving_org_display(self, obj):
        """Display receiving organization"""
        if obj.receiving_organization:
            return obj.receiving_organization.centre
        elif obj.node_user:
            try:
                return format_html(
                    '{} <span style="color: gray;">(inherited)</span>',
                    obj.node_user.profile.organization.centre
                )
            except:
                return format_html('<span style="color: gray;">(no organization)</span>')
        return '-'
    receiving_org_display.short_description = 'Organization'

    def save_model(self, request, obj, form, change):
        """Set created_by on creation"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DICOMTransaction)
class DICOMTransactionAdmin(admin.ModelAdmin):
    """Admin interface for DICOM transactions"""

    list_display = [
        'started_at',
        'transaction_type',
        'direction',
        'source_ae',
        'pacs_config_display',
        'source_ip',
        'study_instance_uid',
        'status_badge',
        'duration_display',
    ]
    list_filter = [
        'transaction_type',
        'direction',
        'status',
        'modality',
        'started_at',
    ]
    search_fields = [
        'study_instance_uid',
        'series_instance_uid',
        'sop_instance_uid',
        'source_ae',
        'source_ip',
    ]
    readonly_fields = [
        'id',
        'started_at',
        'completed_at',
        'duration_ms',
        'file_size_bytes',
    ]
    date_hierarchy = 'started_at'

    fieldsets = (
        ('Transaction', {
            'fields': ('id', 'transaction_type', 'direction', 'pacs_config')
        }),
        ('Source/Destination', {
            'fields': ('source_ae', 'source_ip', 'dest_ae')
        }),
        ('Identifiers', {
            'fields': (
                'study_instance_uid',
                'series_instance_uid',
                'sop_instance_uid',
                'patient_id_hash'
            )
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'duration_ms')
        }),
        ('Metadata', {
            'fields': ('file_size_bytes', 'modality', 'metadata'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'success': 'green',
            'failure': 'red',
            'pending': 'orange',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def duration_display(self, obj):
        """Display duration in human-readable format"""
        if obj.duration_ms:
            if obj.duration_ms < 1000:
                return f"{obj.duration_ms}ms"
            else:
                return f"{obj.duration_ms / 1000:.2f}s"
        return "-"
    duration_display.short_description = 'Duration'

    def pacs_config_display(self, obj):
        """Display PACS configuration as link"""
        if obj.pacs_config:
            return format_html(
                '<a href="/admin/dicom_gateway/pacsconfiguration/{}/change/">{}</a>',
                obj.pacs_config.id,
                obj.pacs_config.name
            )
        return format_html('<span style="color: gray;">-</span>')
    pacs_config_display.short_description = 'PACS Config'


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """Admin interface for audit events"""

    list_display = [
        'timestamp',
        'event_type',
        'user',
        'component',
        'success_badge',
        'study_uid',
    ]
    list_filter = [
        'event_type',
        'component',
        'success',
        'timestamp',
    ]
    search_fields = [
        'study_uid',
        'patient_id_hash',
        'user__username',
        'action_description',
    ]
    readonly_fields = [
        'id',
        'timestamp',
        'user',
        'user_role',
        'source_ip',
        'event_type',
        'component',
    ]
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('Event', {
            'fields': ('id', 'event_type', 'action_description', 'timestamp')
        }),
        ('Who', {
            'fields': ('user', 'user_role', 'source_ip')
        }),
        ('Where', {
            'fields': ('component',)
        }),
        ('Context', {
            'fields': ('study_uid', 'patient_id_hash', 'related_object_type', 'related_object_id')
        }),
        ('Outcome', {
            'fields': ('success', 'error_message')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )

    def success_badge(self, obj):
        """Display success status as colored badge"""
        if obj.success:
            return format_html('<span style="color: green;">✓ Success</span>')
        else:
            return format_html('<span style="color: red;">✗ Failed</span>')
    success_badge.short_description = 'Outcome'

    def has_add_permission(self, request):
        """Disable manual creation of audit events"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable deletion of audit events (immutable)"""
        return False


@admin.register(GatewayHealth)
class GatewayHealthAdmin(admin.ModelAdmin):
    """Admin interface for gateway health metrics"""

    list_display = [
        'timestamp',
        'is_running',
        'cpu_percent',
        'memory_percent',
        'disk_free_gb',
        'success_rate',
        'total_received',
    ]
    list_filter = ['is_running', 'timestamp']
    readonly_fields = [
        'timestamp',
        'is_running',
        'scp_status',
        'api_status',
        'cpu_percent',
        'memory_used_gb',
        'memory_percent',
        'disk_free_gb',
        'disk_used_percent',
        'total_received',
        'total_success',
        'total_failed',
        'success_rate',
        'active_associations',
        'queue_depth',
    ]
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        """Disable manual creation"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion of old metrics"""
        return True

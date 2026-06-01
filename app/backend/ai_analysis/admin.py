"""
Django Admin for AI Analysis Models

Provides admin interfaces for:
- AIModel: Configure and manage AI models
- AnalysisTask: View and manage analysis tasks
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import AIModel, AnalysisTask


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    """
    Admin interface for AIModel.

    Allows admins to:
    - Add/edit AI model configurations
    - View model parameters and settings
    - Enable/disable models
    """

    list_display = [
        'key',
        'name',
        'model_type',
        'version',
        'status_badge',
        'endpoint_url',
        'created_at',
    ]

    list_filter = [
        'is_active',
        'model_type',
        'created_at',
    ]

    search_fields = [
        'key',
        'name',
        'description',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
    ]

    fieldsets = [
        ('Identity', {
            'fields': ('name', 'key', 'version', 'description')
        }),
        ('Configuration', {
            'fields': ('endpoint_url', 'connector_class')
        }),
        ('Model Metadata', {
            'fields': (
                'model_type',
                'supported_modalities',
                'required_parameters',
                'default_parameters',
            )
        }),
        ('Operational Settings', {
            'fields': (
                'timeout_seconds',
                'max_retries',
                'retry_delay_seconds',
            )
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    ]

    def status_badge(self, obj):
        """Display active status as colored badge"""
        if obj.is_active:
            color = 'green'
            text = 'Active'
        else:
            color = 'red'
            text = 'Inactive'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            text
        )

    status_badge.short_description = 'Status'


@admin.register(AnalysisTask)
class AnalysisTaskAdmin(admin.ModelAdmin):
    """
    Admin interface for AnalysisTask.

    Allows admins to:
    - View all analysis tasks
    - Monitor task status and progress
    - View error messages
    - See timing information
    """

    list_display = [
        'id_short',
        'model_name',
        'created_by',
        'status_badge',
        'created_at',
        'processing_time',
        'retry_count',
    ]

    list_filter = [
        'status',
        'model',
        'created_at',
    ]

    search_fields = [
        'id',
        'created_by__username',
        'created_by__email',
        'model__name',
    ]

    readonly_fields = [
        'id',
        'created_by',
        'input_image',
        'model',
        'parameters',
        'celery_task_id',
        'service_job_id',
        'webhook_secret',
        'created_at',
        'dispatched_at',
        'started_processing_at',
        'completed_at',
        'processing_duration_display',
        'total_duration_display',
    ]

    fieldsets = [
        ('Task Identity', {
            'fields': ('id', 'created_by', 'created_at')
        }),
        ('Configuration', {
            'fields': ('model', 'input_image', 'parameters')
        }),
        ('Status', {
            'fields': (
                'status',
                'celery_task_id',
                'service_job_id',
                'retry_count',
            )
        }),
        ('Timing', {
            'fields': (
                'dispatched_at',
                'started_processing_at',
                'completed_at',
                'processing_duration_display',
                'total_duration_display',
            )
        }),
        ('Results', {
            'fields': ('result_file_path', 'result_metadata')
        }),
        ('Error Info', {
            'fields': ('error_message',)
        }),
        ('Security', {
            'fields': ('webhook_secret',),
            'classes': ('collapse',)
        }),
    ]

    def has_add_permission(self, request):
        """Disable adding tasks via admin (use API instead)"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Disable deleting tasks via admin (for audit trail)"""
        return False

    def id_short(self, obj):
        """Display first 8 characters of UUID"""
        return str(obj.id)[:8] + '...'

    id_short.short_description = 'Task ID'

    def model_name(self, obj):
        """Display model name"""
        return obj.model.name if obj.model else '(deleted)'

    model_name.short_description = 'AI Model'

    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'PENDING': '#ffa500',      # orange
            'QUEUED': '#1e90ff',       # dodgerblue
            'DISPATCHED': '#00bfff',   # deepskyblue
            'PROCESSING': '#4169e1',   # royalblue
            'COMPLETED': '#28a745',    # green
            'FAILED': '#dc3545',       # red
            'TIMEOUT': '#ff6347',      # tomato
            'CANCELLED': '#6c757d',    # grey
        }

        color = colors.get(obj.status, '#000')

        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.status
        )

    status_badge.short_description = 'Status'

    def processing_time(self, obj):
        """Display processing duration"""
        duration = obj.processing_duration
        if duration:
            return f"{duration:.1f}s"
        return '-'

    processing_time.short_description = 'Processing Time'

    def processing_duration_display(self, obj):
        """Display processing duration in readable format"""
        duration = obj.processing_duration
        if duration:
            return f"{duration:.2f} seconds"
        return 'N/A'

    processing_duration_display.short_description = 'Processing Duration'

    def total_duration_display(self, obj):
        """Display total duration in readable format"""
        duration = obj.total_duration
        if duration:
            return f"{duration:.2f} seconds"
        return 'N/A'

    total_duration_display.short_description = 'Total Duration'

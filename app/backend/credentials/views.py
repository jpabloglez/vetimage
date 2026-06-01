"""
REST API views for credentials app

Provides endpoints for:
- Session management (list, detail, terminate)
- Audit log viewing
- API key scope management
- API key usage statistics
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from datetime import timedelta
import csv
from django.http import HttpResponse
import logging

from .models import (
    UserSession,
    AuditLog,
    APIKeyScope,
    EnhancedAPIKey,
    APIKeyUsageLog,
    Notification,
)
from .serializers import (
    UserSessionSerializer,
    AuditLogSerializer,
    APIKeyScopeSerializer,
    EnhancedAPIKeySerializer,
    APIKeyUsageLogSerializer,
    SessionTerminateSerializer,
    APIKeyUsageStatsSerializer,
    NotificationSerializer,
)
from .services import (
    terminate_session_by_id,
    get_active_sessions_for_user,
    get_user_audit_logs
)
from .permissions import IsOwnerOrAdmin, IsAdminOrManager

logger = logging.getLogger(__name__)


class UserSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing and managing user sessions.

    Endpoints:
    - GET /api/credentials/sessions/ - List user's active sessions
    - GET /api/credentials/sessions/{id}/ - Get session details
    - DELETE /api/credentials/sessions/{id}/ - Revoke a session
    - GET /api/credentials/sessions/current/ - Get current session info
    """
    serializer_class = UserSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return sessions for the current user only"""
        return UserSession.objects.filter(
            user=self.request.user
        ).select_related(
            'outstanding_token'
        ).order_by('-created_at')

    def destroy(self, request, *args, **kwargs):
        """Revoke a session by terminating it"""
        session = self.get_object()

        # Validate ownership
        if session.user != request.user:
            return Response(
                {'error': 'You can only revoke your own sessions'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Parse termination reason
        serializer = SessionTerminateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('reason', 'manual')

        # Terminate session
        success = terminate_session_by_id(str(session.id), reason=reason)

        if success:
            return Response(
                {'message': 'Session terminated successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
        else:
            return Response(
                {'error': 'Failed to terminate session'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get information about the current session"""
        # Try to find current session by JWT token
        if not hasattr(request, 'auth') or request.auth is None:
            return Response(
                {'error': 'Not authenticated with JWT'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find session by JWT jti
        if hasattr(request.auth, 'payload'):
            jti = request.auth.payload.get('jti')
            if jti:
                session = UserSession.objects.filter(
                    user=request.user,
                    outstanding_token__jti=jti,
                    is_active=True
                ).first()

                if session:
                    serializer = self.get_serializer(session)
                    return Response(serializer.data)

        return Response(
            {'error': 'Current session not found'},
            status=status.HTTP_404_NOT_FOUND
        )


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs.

    Endpoints:
    - GET /api/credentials/audit-logs/ - List user's audit logs
    - GET /api/credentials/audit-logs/{id}/ - Get audit log details
    - GET /api/credentials/audit-logs/export/ - Export audit logs (CSV, admin only)
    """
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    filterset_fields = ['event_type', 'is_suspicious']
    ordering_fields = ['event_timestamp', 'risk_score']
    ordering = ['-event_timestamp']

    def get_queryset(self):
        """Return audit logs for the current user"""
        queryset = AuditLog.objects.filter(
            user=self.request.user
        ).select_related('user', 'session')

        # Filter by event type if provided
        event_type = self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)

        # Filter suspicious only if requested
        suspicious_only = self.request.query_params.get('suspicious_only', '').lower() == 'true'
        if suspicious_only:
            queryset = queryset.filter(is_suspicious=True)

        # Date range filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date:
            queryset = queryset.filter(event_timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(event_timestamp__lte=end_date)

        return queryset

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrManager])
    def export(self, request):
        """Export audit logs to CSV"""
        # Get filtered queryset
        queryset = self.filter_queryset(self.get_queryset())

        # Limit to last 10,000 records for performance
        queryset = queryset[:10000]

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'User Email', 'Username Attempted', 'Event Type', 'Event Timestamp',
            'IP Address', 'Request Path', 'Request Method', 'Is Suspicious', 'Risk Score'
        ])

        for log in queryset:
            writer.writerow([
                log.id,
                log.user.email if log.user else '',
                log.username_attempted or '',
                log.get_event_type_display(),
                log.event_timestamp.isoformat(),
                log.ip_address or '',
                log.request_path or '',
                log.request_method or '',
                'Yes' if log.is_suspicious else 'No',
                log.risk_score or 0
            ])

        return response


class APIKeyScopeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing API key scopes.

    Only accessible by admin users.

    Endpoints:
    - GET /api/credentials/scopes/ - List all scopes
    - POST /api/credentials/scopes/ - Create new scope
    - GET /api/credentials/scopes/{id}/ - Get scope details
    - PUT /api/credentials/scopes/{id}/ - Update scope
    - DELETE /api/credentials/scopes/{id}/ - Delete scope
    """
    queryset = APIKeyScope.objects.all().order_by('category', 'name')
    serializer_class = APIKeyScopeSerializer
    permission_classes = [IsAdminUser]
    pagination_class = PageNumberPagination
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'display_name', 'description']


class EnhancedAPIKeyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing and managing enhanced API keys.

    Endpoints:
    - GET /api/credentials/api-keys/ - List user's API keys
    - GET /api/credentials/api-keys/{id}/ - Get API key details
    - PATCH /api/credentials/api-keys/{id}/ - Update API key (scopes, rate limits)
    - GET /api/credentials/api-keys/{id}/usage/ - Get usage statistics
    - GET /api/credentials/api-keys/{id}/usage-logs/ - List usage logs
    - POST /api/credentials/api-keys/{id}/reset-quota/ - Reset rate limit quota
    """
    serializer_class = EnhancedAPIKeySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        """Return API keys for the current user"""
        queryset = EnhancedAPIKey.objects.filter(
            api_key__user=self.request.user
        ).select_related(
            'api_key', 'api_key__user'
        ).prefetch_related('scopes')

        return queryset

    def update(self, request, *args, **kwargs):
        """Allow partial updates to API key"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Validate ownership (non-admin users can only update their own keys)
        if not request.user.is_staff and instance.api_key.user != request.user:
            return Response(
                {'error': 'You can only update your own API keys'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Handle PATCH requests"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def usage(self, request, pk=None):
        """Get usage statistics for an API key"""
        enhanced_key = self.get_object()

        # Validate ownership
        if not request.user.is_staff and enhanced_key.api_key.user != request.user:
            return Response(
                {'error': 'You can only view your own API key usage'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get time range from query params (default: last 30 days)
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        # Get usage logs for this API key
        usage_logs = APIKeyUsageLog.objects.filter(
            api_key=enhanced_key.api_key,
            timestamp__gte=start_date
        )

        # Aggregate statistics
        total_requests = usage_logs.count()

        usage_by_endpoint = usage_logs.values('request_path').annotate(
            count=Count('id'),
            avg_response_ms=Avg('response_time_ms')
        ).order_by('-count')[:10]

        usage_by_status = usage_logs.values('response_status').annotate(
            count=Count('id')
        ).order_by('response_status')

        # Prepare response data
        data = {
            'api_key_id': enhanced_key.api_key.id,
            'api_key_prefix': enhanced_key.api_key.key_prefix,
            'total_requests': total_requests,
            'last_request_at': enhanced_key.last_request_at,
            'rate_limits': {
                'per_minute': enhanced_key.rate_limit_per_minute,
                'per_hour': enhanced_key.rate_limit_per_hour,
                'per_day': enhanced_key.rate_limit_per_day,
            },
            'current_usage': {
                'minute': enhanced_key.current_minute_count,
                'hour': enhanced_key.current_hour_count,
                'day': enhanced_key.current_day_count,
                'quota_reset_at': enhanced_key.quota_reset_at,
            },
            'scopes': [scope.name for scope in enhanced_key.scopes.all()],
            'usage_by_endpoint': list(usage_by_endpoint),
            'usage_by_status': list(usage_by_status),
        }

        serializer = APIKeyUsageStatsSerializer(data)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='usage-logs')
    def usage_logs(self, request, pk=None):
        """List detailed usage logs for an API key"""
        enhanced_key = self.get_object()

        # Validate ownership
        if not request.user.is_staff and enhanced_key.api_key.user != request.user:
            return Response(
                {'error': 'You can only view your own API key usage logs'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get usage logs
        logs = APIKeyUsageLog.objects.filter(
            api_key=enhanced_key.api_key
        ).order_by('-timestamp')[:100]  # Last 100 requests

        serializer = APIKeyUsageLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser], url_path='reset-quota')
    def reset_quota(self, request, pk=None):
        """Reset rate limit quota for an API key (admin only)"""
        enhanced_key = self.get_object()

        # Reset quotas
        enhanced_key.reset_quotas()

        logger.info(
            f"Admin {request.user.email} reset quota for API key {enhanced_key.api_key.key_prefix}"
        )

        return Response({
            'message': 'Rate limit quota reset successfully',
            'api_key_prefix': enhanced_key.api_key.key_prefix,
            'quota_reset_at': enhanced_key.quota_reset_at
        })


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user notifications.

    Endpoints:
    - GET /api/credentials/notifications/ - List notifications (last 50)
    - POST /api/credentials/notifications/{id}/mark_read/ - Mark as read
    - POST /api/credentials/notifications/mark_all_read/ - Mark all as read
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:50]

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)
        return Response({'status': 'ok'})

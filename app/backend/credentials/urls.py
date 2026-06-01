"""
URL routing for credentials app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserSessionViewSet,
    AuditLogViewSet,
    APIKeyScopeViewSet,
    EnhancedAPIKeyViewSet,
    NotificationViewSet,
)
from .views_audit_report import AuditReportPreviewView, AuditReportDownloadView
from .views_analytics import UserActivityViewSet

app_name = 'credentials'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'sessions', UserSessionViewSet, basename='session')
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')
router.register(r'scopes', APIKeyScopeViewSet, basename='scope')
router.register(r'api-keys', EnhancedAPIKeyViewSet, basename='apikey')
router.register(r'user-activity', UserActivityViewSet, basename='user-activity')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('audit-report/preview/', AuditReportPreviewView.as_view(), name='audit-report-preview'),
    path('audit-report/download/', AuditReportDownloadView.as_view(), name='audit-report-download'),
    path('', include(router.urls)),
]

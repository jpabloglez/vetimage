"""Reports URL Configuration"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReportViewSet, PublicSharedReportView
from .views_templates import ReportTemplateViewSet

router = DefaultRouter()
router.register('templates', ReportTemplateViewSet, basename='report-templates')
router.register('', ReportViewSet, basename='reports')

app_name = 'reports'

urlpatterns = [
    # Public owner-facing shared report — must precede the router so 'shared'
    # is not captured as a report id.
    path('shared/<uuid:token>/', PublicSharedReportView.as_view(), name='public-shared-report'),
    path('', include(router.urls)),
]

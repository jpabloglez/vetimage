"""Reports URL Configuration"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReportViewSet
from .views_templates import ReportTemplateViewSet

router = DefaultRouter()
router.register('templates', ReportTemplateViewSet, basename='report-templates')
router.register('', ReportViewSet, basename='reports')

app_name = 'reports'

urlpatterns = [
    path('', include(router.urls)),
]

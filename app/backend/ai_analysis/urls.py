"""
URL Configuration for AI Analysis API

Defines routes for:
- AI model registry
- Analysis task management
- Webhook receiver
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AIModelViewSet,
    AnalysisTaskViewSet,
    WebhookReceiverView,
    ModelRecommendationView,
    TaskResultFilesView,
    DicomSegConvertView,
    TaskDicomSegToNiftiView,
)
from .views_statistics import StatisticsViewSet
from .views_metrics import ModelMetricsViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'models', AIModelViewSet, basename='aimodel')
router.register(r'tasks', AnalysisTaskViewSet, basename='task')
router.register(r'statistics', StatisticsViewSet, basename='statistics')
router.register(r'model-metrics', ModelMetricsViewSet, basename='model-metrics')

# URL patterns
urlpatterns = [
    # Router endpoints:
    # GET  /api/ai-analysis/models/               - List all active AI models
    # GET  /api/ai-analysis/models/{key}/         - Get model details
    # GET  /api/ai-analysis/tasks/                - List user's tasks
    # POST /api/ai-analysis/tasks/                - Create new task
    # GET  /api/ai-analysis/tasks/{id}/           - Get task details
    # DELETE /api/ai-analysis/tasks/{id}/         - Cancel task
    # POST /api/ai-analysis/tasks/{id}/retry/     - Retry failed task
    # GET  /api/ai-analysis/statistics/data/      - Get filtered statistics data
    # GET  /api/ai-analysis/statistics/aggregated/ - Get aggregated statistics
    # GET  /api/ai-analysis/statistics/filters_options/ - Get available filter options
    path('', include(router.urls)),

    # Model recommendations
    # POST /api/ai-analysis/recommend/            - Get model recommendations
    path(
        'recommend/',
        ModelRecommendationView.as_view(),
        name='model-recommendations'
    ),

    # Webhook receiver (no authentication, uses webhook_secret)
    # POST /api/ai-analysis/webhook/{task_id}/    - Receive webhook from AI service
    path(
        'webhook/<uuid:task_id>/',
        WebhookReceiverView.as_view(),
        name='webhook-receiver'
    ),

    # Result file listing and download for completed tasks
    # GET /api/ai-analysis/tasks/{task_id}/results/           - list files
    # GET /api/ai-analysis/tasks/{task_id}/results/?file=name - download file
    path(
        'tasks/<uuid:task_id>/results/',
        TaskResultFilesView.as_view(),
        name='task-result-files'
    ),

    # DICOM SEG ↔ NIfTI conversion endpoints
    # POST /api/ai-analysis/dicom-seg/convert/               - upload DICOM SEG → ZIP of NIfTI
    # GET  /api/ai-analysis/tasks/{task_id}/seg-to-nifti/    - task's SEG result → ZIP of NIfTI
    path(
        'dicom-seg/convert/',
        DicomSegConvertView.as_view(),
        name='dicom-seg-convert'
    ),
    path(
        'tasks/<uuid:task_id>/seg-to-nifti/',
        TaskDicomSegToNiftiView.as_view(),
        name='task-seg-to-nifti'
    ),
]

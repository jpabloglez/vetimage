"""
API Views for AI Analysis Orchestration

This module provides REST API endpoints for:
- Listing available AI models
- Creating and monitoring analysis tasks
- Retrying failed tasks
- Receiving webhook callbacks from AI services
"""

import io
import os
import shutil
import zipfile

from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta
from .models import AIModel, AnalysisTask
from .serializers import (
    AIModelSerializer,
    AIModelListSerializer,
    AnalysisTaskSerializer,
    AnalysisTaskListSerializer,
    AnalysisTaskMonitorSerializer,
    CreateTaskSerializer,
    WebhookPayloadSerializer,
)
from .tasks import dispatch_ai_job
from .services.webhook_handler import WebhookHandler
from .services.model_recommender import ModelRecommender
from dicom_images.models import MedicalImage
import logging

logger = logging.getLogger(__name__)


class AIModelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for listing available AI models.

    GET /api/ai-analysis/models/ - List all active models
    GET /api/ai-analysis/models/{key}/ - Get model details

    Only active models are exposed.
    Public access allowed for browsing models before login.
    """

    queryset = AIModel.objects.filter(is_active=True)
    permission_classes = [AllowAny]
    lookup_field = 'key'

    def get_serializer_class(self):
        """Use lightweight serializer for list, full for detail"""
        if self.action == 'list':
            return AIModelListSerializer
        return AIModelSerializer

    def get_queryset(self):
        """
        Active models, optionally filtered by veterinary species and/or modality.

        ?species=canine  → models validated for canine (or species-agnostic models
                           with an empty supported_species list).
        ?modality=CR     → models that support the given DICOM modality.
        """
        qs = AIModel.objects.filter(is_active=True)

        species = self.request.query_params.get('species')
        if species:
            # JSONField array containment; also include species-agnostic models.
            qs = qs.filter(
                Q(supported_species__contains=[species]) | Q(supported_species=[])
            )

        modality = self.request.query_params.get('modality')
        if modality:
            qs = qs.filter(supported_modalities__contains=[modality])

        return qs


class AnalysisTaskViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing analysis tasks.

    GET /api/ai-analysis/tasks/ - List user's tasks
    POST /api/ai-analysis/tasks/ - Create new task
    GET /api/ai-analysis/tasks/{id}/ - Get task details
    DELETE /api/ai-analysis/tasks/{id}/ - Cancel task
    POST /api/ai-analysis/tasks/{id}/retry/ - Retry failed task

    Users can only see and manage their own tasks.
    """

    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    pagination_class = PageNumberPagination

    def get_queryset(self):
        """Filter tasks to only show user's own tasks"""
        return AnalysisTask.objects.filter(
            created_by=self.request.user
        ).select_related(
            'model', 'created_by',
            'input_image__series__study',
        )

    def get_serializer_class(self):
        """Use lightweight serializer for list, full for detail"""
        if self.action == 'list':
            return AnalysisTaskListSerializer
        return AnalysisTaskSerializer

    @extend_schema(
        summary='AI findings for a study',
        description='Flattened decision-support findings from this user\'s '
                    'completed analysis tasks for a study, for overlay on the '
                    'viewer. Each finding may include a normalized bbox [x,y,w,h].',
        parameters=[OpenApiParameter('study', OpenApiTypes.STR, required=True,
                                     description='study_instance_uid')],
        tags=['AI Analysis'],
    )
    @action(detail=False, methods=['get'], url_path='study-findings')
    def study_findings(self, request):
        """Return findings (with optional bbox) for a study's completed tasks."""
        study_uid = request.query_params.get('study')
        if not study_uid:
            return Response({'error': 'study query param is required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        tasks = self.get_queryset().filter(
            input_image__series__study__study_instance_uid=study_uid,
            status='COMPLETED',
        )
        findings = []
        for task in tasks:
            for f in (task.result_metadata or {}).get('findings', []):
                if not isinstance(f, dict):
                    continue
                findings.append({
                    **f,
                    'task_id': str(task.id),
                    'model': task.model.name if task.model else None,
                })
        return Response({'study_instance_uid': study_uid, 'findings': findings})

    def create(self, request):
        """
        Create new analysis task.

        POST /api/ai-analysis/tasks/
        Body: {
            "model_key": "mirage-v1",
            "input_image_id": 123,
            "parameters": {
                "modality": "t1",
                "target_image_id": 124
            }
        }
        """
        # Validate request data
        serializer = CreateTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get model
        model = AIModel.objects.get(
            key=serializer.validated_data['model_key'],
            is_active=True
        )

        # Get input image and verify ownership
        input_image = get_object_or_404(
            MedicalImage,
            id=serializer.validated_data['input_image_id'],
            series__study__uploaded_by=request.user  # Security: verify ownership
        )

        # Gate: model requires prior anonymization
        if model.requires_anonymization:
            from dicom_images.models import AnonymizationJob
            study = input_image.series.study
            has_anon = AnonymizationJob.objects.filter(
                study=study,
                status='COMPLETED',
                profile__in=['full', 'research'],
            ).exists()
            if not has_anon:
                return Response(
                    {
                        'error': (
                            "This model requires the study to be anonymized first. "
                            "Run the Anonymizer tool with 'Full' or 'Research' profile "
                            "for this study and try again."
                        )
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

        # Create task
        task = AnalysisTask.objects.create(
            model=model,
            input_image=input_image,
            created_by=request.user,
            parameters=serializer.validated_data['parameters'],
            priority=serializer.validated_data.get('priority', 'routine'),
        )

        logger.info(
            f"User {request.user.id} created task {task.id} "
            f"for model {model.key}"
        )

        # Dispatch based on configuration (per-model flag takes priority over global setting)
        if task.model.use_orchestrator or settings.USE_ORCHESTRATOR:
            # Allow connectors to prepare/convert inputs (e.g., DICOM → NIfTI)
            try:
                from .connectors.factory import ConnectorFactory
                connector = ConnectorFactory.create(task.model)
                extra_params = connector.prepare_input(task)
                if extra_params:
                    task.parameters = {**task.parameters, **extra_params}
                    task.save(update_fields=['parameters'])
            except Exception as e:
                logger.warning(f"prepare_input for task {task.id} failed: {e}")

            # Use orchestrator
            from .orchestrator_client import OrchestratorClient

            try:
                client = OrchestratorClient()
                result = client.submit_job(task)

                task.orchestrator_job_id = result['job_id']
                task.status = 'DISPATCHED'
                task.dispatched_at = timezone.now()
                task.save(update_fields=['orchestrator_job_id', 'status', 'dispatched_at'])

                logger.info(f"Task {task.id} submitted to orchestrator: {result['job_id']}")
                client.close()

            except Exception as e:
                logger.error(f"Orchestrator submission failed: {e}")
                task.status = 'FAILED'
                task.error_message = f"Orchestrator error: {str(e)}"
                task.completed_at = timezone.now()
                task.save(update_fields=['status', 'error_message', 'completed_at'])
        else:
            # Legacy Celery dispatch
            dispatch_ai_job.delay(str(task.id))

        # Return created task
        response_data = AnalysisTaskSerializer(task).data
        modality_warning = serializer.validated_data.pop('_modality_warning', None)
        if modality_warning:
            response_data['warning'] = modality_warning
        return Response(response_data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        """
        Cancel a task (if not already completed).

        DELETE /api/ai-analysis/tasks/{id}/

        Only pending/processing tasks can be cancelled.
        """
        task = self.get_object()

        # Check if task can be cancelled
        if task.is_terminal:
            return Response(
                {'error': f'Cannot cancel task in {task.status} state'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark as cancelled
        task.status = 'CANCELLED'
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'completed_at'])

        logger.info(f"User {request.user.id} cancelled task {task.id}")

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """
        Retry a failed or timed-out task.

        POST /api/ai-analysis/tasks/{id}/retry/

        Only tasks in FAILED or TIMEOUT status can be retried,
        and only if retry_count < max_retries.
        """
        task = self.get_object()

        # Check if task can be retried
        if task.status not in ['FAILED', 'TIMEOUT']:
            return Response(
                {'error': 'Can only retry failed or timed-out tasks'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not task.can_retry:
            return Response(
                {
                    'error': f'Maximum retries ({task.model.max_retries}) exceeded'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Reset task state
        task.status = 'PENDING'
        task.error_message = ''
        task.retry_count += 1
        task.celery_task_id = None
        task.service_job_id = None
        task.orchestrator_job_id = None
        task.dispatched_at = None
        task.started_processing_at = None
        task.completed_at = None
        task.save()

        logger.info(
            f"User {request.user.id} retrying task {task.id} "
            f"(attempt {task.retry_count}/{task.model.max_retries})"
        )

        # Dispatch based on configuration (per-model flag takes priority over global setting)
        if task.model.use_orchestrator or settings.USE_ORCHESTRATOR:
            # Allow connectors to re-prepare inputs on retry (e.g., DICOM → NIfTI)
            try:
                from .connectors.factory import ConnectorFactory
                connector = ConnectorFactory.create(task.model)
                extra_params = connector.prepare_input(task)
                if extra_params:
                    task.parameters = {**task.parameters, **extra_params}
                    task.save(update_fields=['parameters'])
            except Exception as e:
                logger.warning(f"prepare_input on retry for task {task.id} failed: {e}")

            from .orchestrator_client import OrchestratorClient

            try:
                client = OrchestratorClient()
                result = client.submit_job(task)

                task.orchestrator_job_id = result['job_id']
                task.status = 'DISPATCHED'
                task.dispatched_at = timezone.now()
                task.save(update_fields=['orchestrator_job_id', 'status', 'dispatched_at'])

                client.close()
            except Exception as e:
                logger.error(f"Retry failed: {e}")
                task.status = 'FAILED'
                task.error_message = str(e)
                task.save(update_fields=['status', 'error_message'])
        else:
            # Legacy Celery dispatch
            dispatch_ai_job.delay(str(task.id))

        return Response(AnalysisTaskSerializer(task).data)

    @action(detail=False, methods=['get'])
    def monitor(self, request):
        """
        Enhanced task listing for Monitor page with colleague visibility.

        GET /api/ai-analysis/tasks/monitor/

        Query Parameters:
        - date_from: ISO datetime (default: 24h ago)
        - date_to: ISO datetime (default: now)
        - status: PENDING|QUEUED|PROCESSING|COMPLETED|FAILED|TIMEOUT|CANCELLED
        - scope: own|colleagues|department|team (default: own)
        - model_key: filter by AI model
        - page: pagination page number
        - page_size: items per page (default: 50, max: 200)

        Returns paginated list of tasks with privacy-aware colleague information.
        """
        # Parse date range (default: last 24 hours)
        date_to = request.query_params.get('date_to')
        date_from = request.query_params.get('date_from')

        if date_to:
            date_to = timezone.datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        else:
            date_to = timezone.now()

        if date_from:
            date_from = timezone.datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        else:
            date_from = date_to - timedelta(hours=24)

        # Base queryset: user's own tasks
        queryset = AnalysisTask.objects.filter(
            created_by=request.user,
            created_at__gte=date_from,
            created_at__lte=date_to
        )

        # Expand scope if requested
        scope = request.query_params.get('scope', 'own')

        if scope != 'own':
            try:
                profile = request.user.userprofile

                if not profile.organization:
                    # No organization, can't see colleague tasks
                    pass
                else:
                    # Build colleague filter
                    colleague_filter = Q(
                        created_by__userprofile__organization=profile.organization,
                        created_by__userprofile__is_sharing_jobs_with_colleagues=True,
                        created_at__gte=date_from,
                        created_at__lte=date_to
                    )

                    # Additional scope filters
                    if scope == 'department' and profile.department:
                        colleague_filter &= Q(created_by__userprofile__department=profile.department)
                    elif scope == 'team' and profile.team_name:
                        colleague_filter &= Q(created_by__userprofile__team_name=profile.team_name)

                    # Combine with own tasks
                    queryset = AnalysisTask.objects.filter(
                        Q(created_by=request.user, created_at__gte=date_from, created_at__lte=date_to) |
                        colleague_filter
                    )
            except Exception as e:
                logger.warning(f"Error expanding scope for user {request.user.id}: {e}")
                # Fall back to own tasks only

        # Apply additional filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        model_key = request.query_params.get('model_key')
        if model_key:
            queryset = queryset.filter(model__key=model_key)

        # Optimize query
        queryset = queryset.select_related(
            'model',
            'created_by__userprofile'
        ).order_by('-created_at')

        # Paginate
        paginator = PageNumberPagination()
        paginator.page_size = min(
            int(request.query_params.get('page_size', 50)),
            200  # Max 200 items per page
        )

        paginated_tasks = paginator.paginate_queryset(queryset, request)
        serializer = AnalysisTaskMonitorSerializer(
            paginated_tasks,
            many=True,
            context={'request': request}
        )

        logger.info(
            f"User {request.user.id} retrieved monitor view: "
            f"scope={scope}, count={queryset.count()}"
        )

        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Aggregate statistics for dashboard cards.

        GET /api/ai-analysis/tasks/stats/

        Query Parameters:
        - date_from: ISO datetime (default: 24h ago)
        - date_to: ISO datetime (default: now)
        - scope: own|colleagues|department|team (default: own)

        Returns:
        {
            "total_jobs": 150,
            "by_status": {
                "COMPLETED": 120,
                "FAILED": 5,
                "PROCESSING": 3,
                "PENDING": 12,
                "QUEUED": 10
            },
            "by_model": {
                "mirage-v1": 80,
                "other-model": 70
            },
            "avg_processing_time_seconds": 285.4,
            "success_rate": 0.96
        }
        """
        # Parse date range (default: last 24 hours)
        date_to = request.query_params.get('date_to')
        date_from = request.query_params.get('date_from')

        if date_to:
            date_to = timezone.datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        else:
            date_to = timezone.now()

        if date_from:
            date_from = timezone.datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        else:
            date_from = date_to - timedelta(hours=24)

        # Apply same filtering logic as monitor()
        queryset = AnalysisTask.objects.filter(
            created_by=request.user,
            created_at__gte=date_from,
            created_at__lte=date_to
        )

        scope = request.query_params.get('scope', 'own')

        if scope != 'own':
            try:
                profile = request.user.userprofile

                if profile.organization:
                    colleague_filter = Q(
                        created_by__userprofile__organization=profile.organization,
                        created_by__userprofile__is_sharing_jobs_with_colleagues=True,
                        created_at__gte=date_from,
                        created_at__lte=date_to
                    )

                    if scope == 'department' and profile.department:
                        colleague_filter &= Q(created_by__userprofile__department=profile.department)
                    elif scope == 'team' and profile.team_name:
                        colleague_filter &= Q(created_by__userprofile__team_name=profile.team_name)

                    queryset = AnalysisTask.objects.filter(
                        Q(created_by=request.user, created_at__gte=date_from, created_at__lte=date_to) |
                        colleague_filter
                    )
            except Exception:
                pass

        # Calculate aggregates
        total_jobs = queryset.count()

        # Group by status
        by_status = {}
        status_counts = queryset.values('status').annotate(count=Count('id'))
        for item in status_counts:
            by_status[item['status']] = item['count']

        # Group by model
        by_model = {}
        model_counts = queryset.values('model__key').annotate(count=Count('id'))
        for item in model_counts:
            model_key = item['model__key'] or 'unknown'
            by_model[model_key] = item['count']

        # Calculate average processing time (only completed tasks)
        completed_tasks = queryset.filter(
            status='COMPLETED',
            started_processing_at__isnull=False,
            completed_at__isnull=False
        )

        avg_processing_time = None
        if completed_tasks.exists():
            # Calculate duration for each task and average
            durations = [
                (task.completed_at - task.started_processing_at).total_seconds()
                for task in completed_tasks
                if task.started_processing_at and task.completed_at
            ]
            if durations:
                avg_processing_time = sum(durations) / len(durations)

        # Calculate success rate
        success_rate = 0.0
        completed_count = by_status.get('COMPLETED', 0)
        failed_count = by_status.get('FAILED', 0)
        total_finished = completed_count + failed_count

        if total_finished > 0:
            success_rate = completed_count / total_finished

        stats_data = {
            'total_jobs': total_jobs,
            'by_status': by_status,
            'by_model': by_model,
            'avg_processing_time_seconds': avg_processing_time,
            'success_rate': success_rate
        }

        logger.info(
            f"User {request.user.id} retrieved stats: "
            f"scope={scope}, total={total_jobs}"
        )

        return Response(stats_data, status=status.HTTP_200_OK)


class WebhookReceiverView(APIView):
    """
    Receive webhook callbacks from AI services.

    POST /api/ai-analysis/webhook/{task_id}/
    Body: {
        "status": "COMPLETED",
        "result_file_path": "media/ai_results/...",
        "metadata": {...},
        "webhook_secret": "secret-token"
    }

    Security:
    - No JWT authentication (AI service doesn't have user token)
    - Authentication via unique webhook_secret per task
    - Only valid status transitions allowed
    """

    permission_classes = [AllowAny]  # Security via webhook_secret

    def post(self, request, task_id):
        """
        Process webhook callback.

        Args:
            task_id: UUID of the task
            request.data: Webhook payload
        """
        # Validate payload structure
        serializer = WebhookPayloadSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                f"Invalid webhook payload for task {task_id}: "
                f"{serializer.errors}"
            )
            return Response(
                {'error': 'Invalid webhook payload', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract webhook secret
        secret = serializer.validated_data.get('webhook_secret')
        if not secret:
            return Response(
                {'error': 'Missing webhook_secret'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process webhook
        try:
            result = WebhookHandler.process_webhook(
                task_id,
                serializer.validated_data,
                secret
            )

            logger.info(f"Webhook processed successfully for task {task_id}")

            return Response(result, status=status.HTTP_200_OK)

        except ValueError as e:
            # Validation or security errors
            logger.warning(
                f"Webhook rejected for task {task_id}: {str(e)}"
            )
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            # Unexpected errors
            logger.error(
                f"Webhook processing error for task {task_id}: {str(e)}",
                exc_info=True
            )
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ModelRecommendationView(APIView):
    """
    API endpoint for getting AI model recommendations based on image metadata.

    POST /api/ai-analysis/recommend/
    Body: {
        "image_id": 123  # OR "metadata": {...}
    }

    Returns ranked list of compatible models with scores and match reasons.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Get model recommendations for an image.

        Accepts either image_id (fetches metadata from DB) or raw metadata dict.
        """
        image_id = request.data.get('image_id')
        metadata = request.data.get('metadata')

        # Must provide either image_id or metadata
        if not image_id and not metadata:
            return Response(
                {'error': 'Must provide either image_id or metadata'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # If image_id provided, fetch metadata from database
        if image_id:
            try:
                image = MedicalImage.objects.get(
                    id=image_id,
                    series__study__uploaded_by=request.user  # Security: verify ownership
                )

                # Use DICOM tags as metadata
                metadata = image.dicom_tags or {}

                # Ensure required fields exist
                if 'format' not in metadata:
                    metadata['format'] = 'dicom'  # Assume DICOM for stored images

            except MedicalImage.DoesNotExist:
                return Response(
                    {'error': 'Image not found or access denied'},
                    status=status.HTTP_404_NOT_FOUND
                )

        # Validate metadata has minimum required fields
        if not isinstance(metadata, dict):
            return Response(
                {'error': 'Metadata must be a dictionary'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get recommendations
        try:
            recommendations = ModelRecommender.recommend_models(
                metadata=metadata,
                min_score=0  # Return all scored models
            )

            # Serialize recommendations
            serialized_recommendations = []
            for rec in recommendations:
                serialized_recommendations.append({
                    'model': AIModelListSerializer(rec['model']).data,
                    'compatibility_score': rec['compatibility_score'],
                    'match_reasons': rec['match_reasons'],
                    'warnings': rec['warnings'],
                })

            logger.info(
                f"User {request.user.id} requested recommendations, "
                f"found {len(serialized_recommendations)} compatible models"
            )

            return Response(
                {'recommended_models': serialized_recommendations},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(
                f"Error generating recommendations: {str(e)}",
                exc_info=True
            )
            return Response(
                {'error': 'Failed to generate recommendations'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TaskResultFilesView(APIView):
    """
    List or download result files for a completed analysis task.

    GET /api/ai-analysis/tasks/{task_id}/results/
        → Returns list of available output files from result_metadata.output_keys

    GET /api/ai-analysis/tasks/{task_id}/results/?file=aseg.auto_noCCseg.mgz
        → Downloads the named file from the task's result directory
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = get_object_or_404(AnalysisTask, id=task_id, created_by=request.user)

        if task.status != 'COMPLETED' or not task.result_file_path:
            return Response(
                {'error': 'No results available for this task'},
                status=status.HTTP_404_NOT_FOUND
            )

        # result_file_path is the base directory (e.g. /fastsurfer_output/.../mri)
        # The subject root is one level up
        base_dir = os.path.dirname(task.result_file_path)
        output_keys = (task.result_metadata or {}).get('output_keys', [])

        filename = request.query_params.get('file')

        if not filename:
            # Return metadata: list of downloadable files
            available = []
            for key in output_keys:
                # Search for the file anywhere under base_dir
                for root, _dirs, files in os.walk(base_dir):
                    if key in files:
                        rel = os.path.relpath(os.path.join(root, key), base_dir)
                        available.append({'key': key, 'rel_path': rel})
                        break
            return Response({
                'task_id': str(task.id),
                'result_base_dir': task.result_file_path,
                'files': available,
            })

        # Sanitize filename: allow only the basename (no path traversal)
        safe_name = os.path.basename(filename)
        if not safe_name or safe_name != filename:
            return Response({'error': 'Invalid filename'}, status=status.HTTP_400_BAD_REQUEST)

        # Search for the file under the subject root directory
        for root, _dirs, files in os.walk(base_dir):
            if safe_name in files:
                filepath = os.path.join(root, safe_name)
                return FileResponse(
                    open(filepath, 'rb'),
                    as_attachment=True,
                    filename=safe_name,
                )

        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)


class DicomSegConvertView(APIView):
    """
    Convert an uploaded DICOM SEG file to NIfTI using dcmqi ``segimage2itkimage``.

    POST /api/ai-analysis/dicom-seg/convert/

    Request (multipart/form-data):
        file            — DICOM SEG file (.dcm) [required]
        merge_segments  — "true" | "false"  (default: "true")
        prefix          — output filename prefix  (default: "seg")

    Response (application/zip):
        ZIP archive containing:
          - One or more ``<prefix>[_<N>].nii`` files (NIfTI volumes)
          - Companion ``<prefix>[_<N>].json`` metadata files

    Error responses:
        400 — missing file or invalid parameter
        422 — segimage2itkimage failed (non-DICOM SEG input, corrupt file, etc.)
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        from pathlib import Path
        from .services.dicom_seg import convert_dicom_seg_to_nifti

        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response(
                {"error": "No file provided. Send a DICOM SEG file as 'file'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        merge_segments = request.data.get("merge_segments", "true").lower() != "false"
        prefix = request.data.get("prefix", "seg").strip() or "seg"

        # Save upload to a temp location
        import tempfile
        tmp_dir = Path(tempfile.mkdtemp(prefix="dicom_seg_upload_"))
        input_path = tmp_dir / "input.dcm"

        try:
            with open(input_path, "wb") as fh:
                for chunk in uploaded.chunks():
                    fh.write(chunk)

            try:
                segments, output_dir = convert_dicom_seg_to_nifti(
                    dicom_seg_path=input_path,
                    prefix=prefix,
                    merge_segments=merge_segments,
                )
            except FileNotFoundError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            except RuntimeError as exc:
                return Response(
                    {"error": f"Conversion failed: {exc}"},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            # Build ZIP in memory from all output files
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for seg in segments:
                    zf.write(seg["nifti_path"], seg["nifti_path"].name)
                    if seg["metadata_path"] and seg["metadata_path"].is_file():
                        zf.write(seg["metadata_path"], seg["metadata_path"].name)

            # Cleanup output dir (files are now in the ZIP)
            shutil.rmtree(output_dir, ignore_errors=True)

            zip_buffer.seek(0)
            stem = uploaded.name.rsplit(".", 1)[0] if "." in uploaded.name else uploaded.name
            zip_name = f"{stem}_nifti.zip"

            return FileResponse(
                zip_buffer,
                as_attachment=True,
                filename=zip_name,
                content_type="application/zip",
            )

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class TaskDicomSegToNiftiView(APIView):
    """
    Convert the DICOM SEG result of a completed analysis task back to NIfTI.

    GET /api/ai-analysis/tasks/{task_id}/seg-to-nifti/?merge_segments=true

    The task must:
      - Belong to the authenticated user
      - Have status COMPLETED
      - Have ``result_metadata.dicom_seg_orthanc_id`` set (populated by
        ``create_dicom_seg_task`` after SEG creation)

    Query params:
        merge_segments — "true" | "false"  (default: "true")
        prefix         — output filename prefix  (default: "seg")

    Response (application/zip):
        ZIP archive with NIfTI files and companion JSON metadata.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        from pathlib import Path
        from .services.dicom_seg import convert_dicom_seg_to_nifti
        from .services.orthanc_client import download_dicom_instance

        task = get_object_or_404(AnalysisTask, id=task_id, created_by=request.user)

        if task.status != "COMPLETED":
            return Response(
                {"error": "Task is not completed yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        orthanc_instance_id = (task.result_metadata or {}).get("dicom_seg_orthanc_id")
        if not orthanc_instance_id:
            return Response(
                {
                    "error": (
                        "No DICOM SEG has been generated for this task. "
                        "The task model must have a non-empty label_map for SEG creation."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        merge_segments = request.query_params.get("merge_segments", "true").lower() != "false"
        prefix = request.query_params.get("prefix", "seg").strip() or "seg"

        import tempfile
        tmp_dir = Path(tempfile.mkdtemp(prefix="seg_to_nifti_"))
        input_path = tmp_dir / "seg.dcm"

        try:
            try:
                download_dicom_instance(orthanc_instance_id, input_path)
            except Exception as exc:
                return Response(
                    {"error": f"Could not retrieve DICOM SEG from Orthanc: {exc}"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            try:
                segments, output_dir = convert_dicom_seg_to_nifti(
                    dicom_seg_path=input_path,
                    prefix=prefix,
                    merge_segments=merge_segments,
                )
            except RuntimeError as exc:
                return Response(
                    {"error": f"Conversion failed: {exc}"},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for seg in segments:
                    zf.write(seg["nifti_path"], seg["nifti_path"].name)
                    if seg["metadata_path"] and seg["metadata_path"].is_file():
                        zf.write(seg["metadata_path"], seg["metadata_path"].name)

            shutil.rmtree(output_dir, ignore_errors=True)

            zip_buffer.seek(0)
            zip_name = f"task_{str(task.id)[:8]}_nifti.zip"

            return FileResponse(
                zip_buffer,
                as_attachment=True,
                filename=zip_name,
                content_type="application/zip",
            )

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

"""
Statistics API endpoints for analysis data review.

Provides filtered access to analysis task data with:
- Organization boundary enforcement
- Advanced filtering (date, model, demographics, metrics)
- Aggregated statistics
- Privacy-compliant data (patient names excluded)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Avg, Sum, Q, F
from django.db.models.functions import TruncDate, TruncHour, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import datetime, timedelta

from .models import AnalysisTask
from .serializers_statistics import StatisticsTaskSerializer, StatisticsAggregatedSerializer
from dicom_images.models import MedicalStudy, MedicalSeries, MedicalImage


class StatisticsViewSet(viewsets.ViewSet):
    """
    ViewSet for statistics endpoints.

    Provides filtered access to analysis data with organization-level security.
    All responses exclude patient names for privacy compliance.
    """

    permission_classes = [IsAuthenticated]

    def _build_queryset(self, request):
        """
        Build filtered queryset with organization boundary enforcement.

        Security: Users can ONLY access data from their own organization.

        Supported filters:
        - date_from, date_to: Date range
        - model_keys: List of AI model keys
        - statuses: List of task statuses
        - patient_ids: List of patient IDs
        - patient_sex: List of patient sex values
        - patient_age_min, patient_age_max: Age range
        - modalities: List of imaging modalities
        - body_parts: List of body parts
        - organization_ids: List of organization IDs (admin only)
        """
        user = request.user

        # CRITICAL SECURITY: Base queryset filtered by user's organization
        queryset = AnalysisTask.objects.filter(
            input_image__series__study__uploaded_by__userprofile__organization=user.userprofile.organization
        ).select_related(
            'model',
            'input_image__series__study',
            'input_image__series__study__uploaded_by__userprofile__organization',
            'created_by__userprofile'
        )

        # Date range filters
        date_from = request.query_params.get('date_from')
        if date_from:
            try:
                date_from_parsed = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                queryset = queryset.filter(created_at__gte=date_from_parsed)
            except (ValueError, AttributeError):
                pass

        date_to = request.query_params.get('date_to')
        if date_to:
            try:
                date_to_parsed = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                # Add 1 day to include the entire end date
                date_to_parsed = date_to_parsed + timedelta(days=1)
                queryset = queryset.filter(created_at__lt=date_to_parsed)
            except (ValueError, AttributeError):
                pass

        # Model filters
        model_keys = request.query_params.getlist('model_keys')
        if model_keys:
            queryset = queryset.filter(model__key__in=model_keys)

        # Status filters
        statuses = request.query_params.getlist('statuses')
        if statuses:
            queryset = queryset.filter(status__in=statuses)

        # Patient ID filters
        patient_ids = request.query_params.getlist('patient_ids')
        if patient_ids:
            queryset = queryset.filter(
                input_image__series__study__patient_id__in=patient_ids
            )

        # Patient sex filter
        patient_sex = request.query_params.getlist('patient_sex')
        if patient_sex:
            queryset = queryset.filter(
                input_image__series__study__patient_sex__in=patient_sex
            )

        # Patient age filter (computed from birth date)
        patient_age_min = request.query_params.get('patient_age_min')
        if patient_age_min:
            try:
                age_min = int(patient_age_min)
                # Calculate max birth date for minimum age
                max_birth_date = timezone.now().date() - timedelta(days=int(age_min * 365.25))
                queryset = queryset.filter(
                    input_image__series__study__patient_birth_date__lte=max_birth_date
                )
            except (ValueError, TypeError):
                pass

        patient_age_max = request.query_params.get('patient_age_max')
        if patient_age_max:
            try:
                age_max = int(patient_age_max)
                # Calculate min birth date for maximum age
                min_birth_date = timezone.now().date() - timedelta(days=int((age_max + 1) * 365.25))
                queryset = queryset.filter(
                    input_image__series__study__patient_birth_date__gte=min_birth_date
                )
            except (ValueError, TypeError):
                pass

        # Modality filter
        modalities = request.query_params.getlist('modalities')
        if modalities:
            queryset = queryset.filter(
                input_image__series__modality__in=modalities
            )

        # Body part filter
        body_parts = request.query_params.getlist('body_parts')
        if body_parts:
            queryset = queryset.filter(
                input_image__series__body_part_examined__in=body_parts
            )

        # TODO: Metric threshold filters (filter on result_metadata JSONField)
        # Example: dice_score_min, confidence_min, etc.
        # This requires JSONField queries which vary by database backend

        return queryset

    @action(detail=False, methods=['get'])
    def data(self, request):
        """
        Get filtered task records with demographics.

        Returns paginated list of analysis tasks with:
        - AI model information
        - Patient demographics (ID, sex, age - NO NAMES)
        - Study/image metadata
        - AI metrics from results
        - Processing information

        Query parameters: See _build_queryset() for supported filters
        Additional parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 50, max: 200)
        """
        queryset = self._build_queryset(request)

        # Order by creation date (newest first)
        queryset = queryset.order_by('-created_at')

        # Paginate
        paginator = PageNumberPagination()
        page_size = request.query_params.get('page_size', 50)
        try:
            page_size = min(int(page_size), 200)  # Cap at 200
        except (ValueError, TypeError):
            page_size = 50

        paginator.page_size = page_size
        paginated = paginator.paginate_queryset(queryset, request)

        # Serialize (patient names excluded)
        serializer = StatisticsTaskSerializer(
            paginated,
            many=True,
            context={'request': request}
        )

        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def aggregated(self, request):
        """
        Get aggregated statistics for filtered data.

        Returns:
        - time_series: Tasks per day/hour
        - processing_time_distribution: List of processing times
        - model_usage: Task counts by model
        - status_breakdown: Task counts by status
        - summary: Overall statistics

        Query parameters: Same filters as data() endpoint
        Additional parameters:
        - time_grouping: 'day' or 'hour' (default: 'day')
        """
        queryset = self._build_queryset(request)

        # Time grouping parameter
        time_grouping = request.query_params.get('time_grouping', 'day')

        # Time series: tasks per day or hour
        if time_grouping == 'hour':
            time_series_qs = queryset.annotate(
                date=TruncHour('created_at')
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date')
        else:  # default to day
            time_series_qs = queryset.annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date')

        time_series = [
            {
                'date': item['date'].isoformat(),
                'count': item['count']
            }
            for item in time_series_qs
        ]

        # Processing time distribution (completed tasks only)
        processing_times_qs = queryset.filter(
            status='COMPLETED',
            completed_at__isnull=False,
            created_at__isnull=False
        )

        processing_times = []
        for task in processing_times_qs:
            duration = (task.completed_at - task.created_at).total_seconds()
            processing_times.append(round(duration, 2))

        # Model usage counts
        model_usage_qs = queryset.values(
            'model__name',
            'model__key'
        ).annotate(
            count=Count('id')
        ).order_by('-count')

        model_usage = [
            {
                'model_name': item['model__name'],
                'model_key': item['model__key'],
                'count': item['count']
            }
            for item in model_usage_qs
        ]

        # Status breakdown
        status_breakdown_qs = queryset.values('status').annotate(
            count=Count('id')
        )

        status_breakdown = {
            item['status']: item['count']
            for item in status_breakdown_qs
        }

        # Summary statistics
        total_tasks = queryset.count()
        completed_tasks = queryset.filter(status='COMPLETED').count()
        failed_tasks = queryset.filter(status='FAILED').count()

        # Average processing time (completed tasks only)
        avg_processing_time = None
        if processing_times:
            avg_processing_time = round(sum(processing_times) / len(processing_times), 2)

        response_data = {
            'time_series': time_series,
            'processing_time_distribution': processing_times,
            'model_usage': model_usage,
            'status_breakdown': status_breakdown,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'average_processing_time': avg_processing_time,
        }

        serializer = StatisticsAggregatedSerializer(response_data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def filters_options(self, request):
        """
        Get available filter options for the current user's organization.

        Returns lists of available:
        - models (with keys and names)
        - modalities
        - body_parts
        - patient_sex values
        - statuses

        This helps populate filter dropdowns in the UI.
        """
        user = request.user

        # Base queryset for user's organization
        base_queryset = AnalysisTask.objects.filter(
            input_image__series__study__uploaded_by__userprofile__organization=user.userprofile.organization
        )

        # Available models
        models = base_queryset.values(
            'model__key',
            'model__name',
            'model__model_type'
        ).distinct().order_by('model__name')

        models_list = [
            {
                'key': item['model__key'],
                'name': item['model__name'],
                'type': item['model__model_type']
            }
            for item in models
        ]

        # Available modalities
        modalities = base_queryset.values_list(
            'input_image__series__modality',
            flat=True
        ).distinct().order_by('input_image__series__modality')
        modalities_list = [m for m in modalities if m]

        # Available body parts
        body_parts = base_queryset.values_list(
            'input_image__series__body_part_examined',
            flat=True
        ).distinct().order_by('input_image__series__body_part_examined')
        body_parts_list = [bp for bp in body_parts if bp]

        # Available patient sex values
        patient_sex_values = base_queryset.values_list(
            'input_image__series__study__patient_sex',
            flat=True
        ).distinct()
        patient_sex_list = [ps for ps in patient_sex_values if ps]

        # Available statuses
        statuses = ['PENDING', 'RUNNING', 'COMPLETED', 'FAILED']

        return Response({
            'models': models_list,
            'modalities': modalities_list,
            'body_parts': body_parts_list,
            'patient_sex': patient_sex_list,
            'statuses': statuses,
        })

    @action(detail=False, methods=['get'], url_path='study_analytics')
    def study_analytics(self, request):
        """
        Study-level analytics: modality distribution, upload trends, storage usage.

        Query parameters:
        - period: 'daily', 'weekly', or 'monthly' (default: 'daily')
        - date_from, date_to: date range filters
        """
        user = request.user
        org = user.userprofile.organization

        # Base study queryset scoped to organization
        studies_qs = MedicalStudy.objects.filter(
            uploaded_by__userprofile__organization=org
        )

        # Date filters
        date_from = request.query_params.get('date_from')
        if date_from:
            try:
                parsed = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                studies_qs = studies_qs.filter(uploaded_at__gte=parsed)
            except (ValueError, AttributeError):
                pass

        date_to = request.query_params.get('date_to')
        if date_to:
            try:
                parsed = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                studies_qs = studies_qs.filter(uploaded_at__lt=parsed + timedelta(days=1))
            except (ValueError, AttributeError):
                pass

        # 1. Modality distribution (from series)
        series_qs = MedicalSeries.objects.filter(
            study__uploaded_by__userprofile__organization=org
        )
        if date_from:
            try:
                parsed = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                series_qs = series_qs.filter(study__uploaded_at__gte=parsed)
            except (ValueError, AttributeError):
                pass
        if date_to:
            try:
                parsed = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                series_qs = series_qs.filter(study__uploaded_at__lt=parsed + timedelta(days=1))
            except (ValueError, AttributeError):
                pass

        modality_dist = list(
            series_qs.values('modality')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # 2. Upload trends (daily/weekly/monthly)
        period = request.query_params.get('period', 'daily')
        trunc_fn = {
            'weekly': TruncWeek,
            'monthly': TruncMonth,
        }.get(period, TruncDate)

        upload_trends = list(
            studies_qs.annotate(period=trunc_fn('uploaded_at'))
            .values('period')
            .annotate(count=Count('id'))
            .order_by('period')
        )
        upload_trends = [
            {'date': item['period'].isoformat(), 'count': item['count']}
            for item in upload_trends
        ]

        # 3. Storage usage over time (cumulative)
        storage_by_period = list(
            studies_qs.annotate(period=trunc_fn('uploaded_at'))
            .values('period')
            .annotate(size=Sum('total_size_bytes'))
            .order_by('period')
        )
        cumulative = 0
        storage_usage = []
        for item in storage_by_period:
            cumulative += item['size'] or 0
            storage_usage.append({
                'date': item['period'].isoformat(),
                'cumulative_bytes': cumulative,
                'period_bytes': item['size'] or 0,
            })

        # Summary
        total_studies = studies_qs.count()
        total_storage = studies_qs.aggregate(total=Sum('total_size_bytes'))['total'] or 0

        return Response({
            'modality_distribution': modality_dist,
            'upload_trends': upload_trends,
            'storage_usage': storage_usage,
            'total_studies': total_studies,
            'total_storage_bytes': total_storage,
        })

    @action(detail=False, methods=['get'])
    def population(self, request):
        """
        Population-level insights: age distribution, gender distribution, common findings.

        Returns:
        - age_histogram: Age brackets with counts
        - gender_distribution: Patient sex counts
        - top_findings: Most common AI findings from completed tasks
        """
        user = request.user
        org = user.userprofile.organization

        # Studies scoped to organization
        studies_qs = MedicalStudy.objects.filter(
            uploaded_by__userprofile__organization=org
        )

        # 1. Gender distribution
        gender_dist = list(
            studies_qs.exclude(patient_sex='')
            .values('patient_sex')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

        # 2. Age histogram (decade brackets)
        today = timezone.now().date()
        age_brackets = [
            {'label': '0-9', 'min': 0, 'max': 9},
            {'label': '10-19', 'min': 10, 'max': 19},
            {'label': '20-29', 'min': 20, 'max': 29},
            {'label': '30-39', 'min': 30, 'max': 39},
            {'label': '40-49', 'min': 40, 'max': 49},
            {'label': '50-59', 'min': 50, 'max': 59},
            {'label': '60-69', 'min': 60, 'max': 69},
            {'label': '70-79', 'min': 70, 'max': 79},
            {'label': '80-89', 'min': 80, 'max': 89},
            {'label': '90+', 'min': 90, 'max': 200},
        ]

        studies_with_dob = studies_qs.filter(patient_birth_date__isnull=False)
        age_histogram = []
        for bracket in age_brackets:
            max_birth = today - timedelta(days=int(bracket['min'] * 365.25))
            min_birth = today - timedelta(days=int((bracket['max'] + 1) * 365.25))
            count = studies_with_dob.filter(
                patient_birth_date__lte=max_birth,
                patient_birth_date__gt=min_birth,
            ).count()
            age_histogram.append({
                'bracket': bracket['label'],
                'count': count,
            })

        # 3. Top findings from AI results
        completed_tasks = AnalysisTask.objects.filter(
            input_image__series__study__uploaded_by__userprofile__organization=org,
            status='COMPLETED',
            result_metadata__isnull=False,
        ).exclude(result_metadata={})

        findings_counter = {}
        for task in completed_tasks[:500]:  # Limit for performance
            metadata = task.result_metadata or {}
            # Extract findings from various result formats
            findings = metadata.get('findings', [])
            if isinstance(findings, list):
                for finding in findings:
                    desc = finding.get('description', '') if isinstance(finding, dict) else str(finding)
                    if desc:
                        findings_counter[desc] = findings_counter.get(desc, 0) + 1

            predicted_class = metadata.get('predicted_class')
            if predicted_class:
                findings_counter[str(predicted_class)] = findings_counter.get(str(predicted_class), 0) + 1

        top_findings = sorted(
            [{'finding': k, 'count': v} for k, v in findings_counter.items()],
            key=lambda x: x['count'],
            reverse=True,
        )[:20]

        return Response({
            'age_histogram': age_histogram,
            'gender_distribution': gender_dist,
            'top_findings': top_findings,
            'total_patients': studies_qs.values('patient_id').distinct().count(),
        })

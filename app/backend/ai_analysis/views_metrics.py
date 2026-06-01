"""
Per-model performance metrics API.

Provides per-model aggregated stats (processing time, success/failure rates)
and time-series trends for model performance over time.
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Avg, Q, F, ExpressionWrapper, FloatField
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import datetime, timedelta

from .models import AnalysisTask


class ModelMetricsViewSet(viewsets.ViewSet):
    """
    Per-model performance metrics.

    list/ — aggregated stats per model
    trends/ — time-series trends per model
    """

    permission_classes = [IsAuthenticated]

    def _base_queryset(self, request):
        """Organization-scoped queryset."""
        user = request.user
        return AnalysisTask.objects.filter(
            input_image__series__study__uploaded_by__userprofile__organization=user.userprofile.organization
        ).select_related('model')

    def _apply_date_filters(self, qs, request):
        date_from = request.query_params.get('date_from')
        if date_from:
            try:
                parsed = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                qs = qs.filter(created_at__gte=parsed)
            except (ValueError, AttributeError):
                pass

        date_to = request.query_params.get('date_to')
        if date_to:
            try:
                parsed = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                qs = qs.filter(created_at__lt=parsed + timedelta(days=1))
            except (ValueError, AttributeError):
                pass
        return qs

    def list(self, request):
        """
        Per-model aggregated metrics.

        Returns per model:
        - total_tasks, completed, failed
        - avg_processing_time_seconds
        - failure_rate_percent
        """
        qs = self._apply_date_filters(self._base_queryset(request), request)

        metrics = list(
            qs.values('model__key', 'model__name')
            .annotate(
                total=Count('id'),
                completed=Count('id', filter=Q(status='COMPLETED')),
                failed=Count('id', filter=Q(status='FAILED')),
                timeout=Count('id', filter=Q(status='TIMEOUT')),
            )
            .order_by('-total')
        )

        # Compute avg processing time and failure rate per model
        for m in metrics:
            completed_tasks = qs.filter(
                model__key=m['model__key'],
                status='COMPLETED',
                completed_at__isnull=False,
            )
            durations = []
            for task in completed_tasks[:200]:
                if task.completed_at and task.created_at:
                    durations.append((task.completed_at - task.created_at).total_seconds())

            m['avg_processing_time'] = (
                round(sum(durations) / len(durations), 2) if durations else None
            )
            m['failure_rate'] = (
                round((m['failed'] + m['timeout']) / m['total'] * 100, 1)
                if m['total'] > 0 else 0
            )

        return Response(metrics)

    @action(detail=False, methods=['get'])
    def trends(self, request):
        """
        Time-series performance trends per model.

        Query params:
        - model_key: filter to specific model
        - date_from, date_to: date range
        """
        qs = self._apply_date_filters(self._base_queryset(request), request)

        model_key = request.query_params.get('model_key')
        if model_key:
            qs = qs.filter(model__key=model_key)

        daily = list(
            qs.annotate(date=TruncDate('created_at'))
            .values('date', 'model__key', 'model__name')
            .annotate(
                total=Count('id'),
                completed=Count('id', filter=Q(status='COMPLETED')),
                failed=Count('id', filter=Q(status='FAILED')),
            )
            .order_by('date', 'model__key')
        )

        result = []
        for item in daily:
            entry = {
                'date': item['date'].isoformat(),
                'model_key': item['model__key'],
                'model_name': item['model__name'],
                'total': item['total'],
                'completed': item['completed'],
                'failed': item['failed'],
                'success_rate': (
                    round(item['completed'] / item['total'] * 100, 1)
                    if item['total'] > 0 else 0
                ),
            }
            result.append(entry)

        return Response(result)

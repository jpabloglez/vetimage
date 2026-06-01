"""
User activity analytics API.

Provides per-user stats: upload count, analysis count, storage consumed, last active.
Admin-only list endpoint; current user's own stats via me/ action.
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Max, Q
from django.contrib.auth import get_user_model

from dicom_images.models import MedicalStudy
from ai_analysis.models import AnalysisTask
from .models import AuditLog

User = get_user_model()


def _build_user_stats(user_ids):
    """
    Return a dict keyed by user_id with aggregated activity stats.
    Uses two queries total regardless of number of users (vs. O(n×5) before).
    """
    study_stats = (
        MedicalStudy.objects
        .filter(uploaded_by_id__in=user_ids)
        .values('uploaded_by_id')
        .annotate(
            upload_count=Count('id'),
            total_storage=Sum('total_size_bytes'),
            last_upload=Max('uploaded_at'),
        )
    )
    task_stats = (
        AnalysisTask.objects
        .filter(created_by_id__in=user_ids)
        .values('created_by_id')
        .annotate(
            analysis_count=Count('id'),
            completed_count=Count('id', filter=Q(status='COMPLETED')),
            failed_count=Count('id', filter=Q(status='FAILED')),
            last_analysis=Max('created_at'),
        )
    )

    study_by_user = {r['uploaded_by_id']: r for r in study_stats}
    task_by_user = {r['created_by_id']: r for r in task_stats}

    result = {}
    for uid in user_ids:
        s = study_by_user.get(uid, {})
        t = task_by_user.get(uid, {})
        last_upload = s.get('last_upload')
        last_analysis = t.get('last_analysis')
        last_active = max(filter(None, [last_upload, last_analysis]), default=None)
        result[uid] = {
            'upload_count': s.get('upload_count', 0),
            'total_storage_bytes': s.get('total_storage') or 0,
            'analysis_count': t.get('analysis_count', 0),
            'completed_analyses': t.get('completed_count', 0),
            'failed_analyses': t.get('failed_count', 0),
            'last_upload_at': last_upload.isoformat() if last_upload else None,
            'last_analysis_at': last_analysis.isoformat() if last_analysis else None,
            'last_active_at': last_active.isoformat() if last_active else None,
        }
    return result


class UserActivityViewSet(viewsets.ViewSet):
    """
    User activity analytics.

    list/ — per-user aggregate stats (admin only)
    me/   — current user's own stats
    """

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        Per-user activity stats. Admin/staff only.
        Scoped to same organization.
        """
        if not request.user.is_staff:
            return Response(
                {'error': 'Admin access required'},
                status=403,
            )

        org = request.user.userprofile.organization
        users = list(
            User.objects.filter(userprofile__organization=org).values('id', 'email')
        )
        user_ids = [u['id'] for u in users]
        stats_by_user = _build_user_stats(user_ids)

        result = [
            {'user_id': u['id'], 'email': u['email'], **stats_by_user.get(u['id'], {})}
            for u in users
        ]
        result.sort(key=lambda x: x.get('analysis_count', 0), reverse=True)
        return Response(result)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Current user's own activity stats."""
        stats = _build_user_stats([request.user.id])
        data = {'user_id': request.user.id, 'email': request.user.email,
                **stats.get(request.user.id, {})}
        return Response(data)

"""
Platform-admin endpoints — the cross-clinic view, for VetImage staff.

This is the **only** module permitted to read across clinics. Everywhere else
an unscoped query is a bug (see `dicom_images.scoping`). Three rules keep that
exception honest:

* **Gated on `is_staff`**, never on the clinical `role` field. A clinic admin
  administers their own clinic; platform staff work for VetImage. See
  `core.permissions`.
* **Read-only over clinical data.** Staff never create or approve a clinical
  record, so nothing here is ever written under a customer's identity. The one
  write is registering a clinic, which creates an empty tenant and invites its
  first administrator rather than provisioning an account for them.
* **Aggregates, not content.** Counts, timestamps and clinic names — never
  patient names, findings or images.
"""

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Max, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_analysis.models import AnalysisTask
from core.permissions import IsPlatformStaff
from core.query_params import bounded_int

from .models import Clinic, ClinicInvitation
from .serializers_admin import (
    AdminClinicCreateSerializer,
    AdminClinicDetailSerializer,
    AdminClinicSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()

# A statistics window has to be bounded — an unbounded date range invites a
# full-table scan from anyone who can reach the endpoint.
DEFAULT_STATS_DAYS = 30
MAX_STATS_DAYS = 365


class AdminClinicViewSet(viewsets.ModelViewSet):
    """The clinic registry: every tenant on the platform, with usage counts."""

    permission_classes = [IsAuthenticated, IsPlatformStaff]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminClinicCreateSerializer
        if self.action == 'retrieve':
            return AdminClinicDetailSerializer
        return AdminClinicSerializer

    def get_queryset(self):
        """
        Counts are annotated, not computed per row — a property per metric on a
        page of N clinics would cost N queries per metric.

        `distinct=True` on every count is load-bearing: these joins fan out
        against each other, so two plain aggregates over the same multi-valued
        path multiply instead of counting.
        """
        qs = Clinic.objects.filter(deleted_at__isnull=True).select_related('user')

        study_path = 'staff__user__studies'
        return qs.annotate(
            _members=Count('staff', distinct=True),
            _owners=Count('owners', distinct=True),
            _patients=Count('owners__animals', distinct=True),
            _studies=Count(study_path, distinct=True),
            _analyses=Count(
                f'{study_path}__series__images__analysis_tasks', distinct=True,
            ),
            _last_activity=Max(f'{study_path}__uploaded_at'),
        ).order_by('name')

    @extend_schema(
        summary='Register a clinic and invite its first administrator',
        request=AdminClinicCreateSerializer,
        responses={201: OpenApiTypes.OBJECT},
        tags=['Admin'],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        admin_email = serializer.validated_data.pop('admin_email')
        clinic = Clinic.objects.create(
            user=request.user,          # bookkeeping only; grants nothing
            name=serializer.validated_data['name'],
            address=serializer.validated_data.get('address', ''),
            city=serializer.validated_data.get('city', ''),
            billing_address=serializer.validated_data.get('billing_address', ''),
            billing_code=serializer.validated_data.get('billing_code', ''),
        )

        # The customer sets their own password; staff never hold it.
        invitation = ClinicInvitation.objects.create(
            clinic=clinic,
            email=admin_email,
            role=3,
            invited_by=request.user,
        )

        logger.info(
            'Platform admin %s registered clinic %s and invited %s',
            request.user.id, clinic.id, admin_email,
        )
        return Response(
            {
                'id': clinic.id,
                'name': clinic.name,
                'admin_email': admin_email,
                'invitation_path': f'/invite/{invitation.token}',
                'invitation_expires_at': invitation.expires_at,
            },
            status=status.HTTP_201_CREATED,
        )


class AdminStatisticsView(APIView):
    """
    Live platform-wide analysis statistics.

    Computed on read rather than rolled up nightly: at current volume the
    aggregate is cheap, and a rollup table would trade freshness and a whole
    migration for savings that do not exist yet. The date window is bounded so
    that stays true.

    Per-clinic figures are not served here — each clinic sees its own on the
    Monitor page, scoped to them.
    """

    permission_classes = [IsAuthenticated, IsPlatformStaff]

    @extend_schema(
        summary='Cross-clinic analysis statistics',
        parameters=[
            OpenApiParameter('days', OpenApiTypes.INT, description='Window size, 1–365 (default 30).'),
            OpenApiParameter('clinic', OpenApiTypes.INT, description='Limit to one clinic.'),
            OpenApiParameter('model', OpenApiTypes.STR, description='Limit to one AI model key.'),
            OpenApiParameter('status', OpenApiTypes.STR, description='Limit to one task status.'),
        ],
        responses={200: OpenApiTypes.OBJECT},
        tags=['Admin'],
    )
    def get(self, request):
        days = bounded_int(
            request.query_params.get('days'),
            default=DEFAULT_STATS_DAYS, minimum=1, maximum=MAX_STATS_DAYS,
        )
        since = timezone.now() - timedelta(days=days)

        tasks = AnalysisTask.objects.filter(created_at__gte=since)

        clinic_id = bounded_int(request.query_params.get('clinic'), default=0, minimum=0)
        if clinic_id:
            tasks = tasks.filter(
                input_image__series__study__uploaded_by__userprofile__clinic_id=clinic_id,
            )

        model_key = (request.query_params.get('model') or '').strip()
        if model_key:
            tasks = tasks.filter(model__key=model_key)

        task_status = (request.query_params.get('status') or '').strip().upper()
        if task_status:
            tasks = tasks.filter(status=task_status)

        succeeded = Q(status='COMPLETED')
        failed = Q(status__in=['FAILED', 'TIMEOUT', 'CANCELLED'])

        totals = tasks.aggregate(
            total=Count('id'),
            succeeded=Count('id', filter=succeeded),
            failed=Count('id', filter=failed),
        )
        completed = totals['succeeded'] + totals['failed']
        totals['success_rate'] = (
            round(totals['succeeded'] / completed * 100, 1) if completed else None
        )

        over_time = list(
            tasks.annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(
                total=Count('id'),
                succeeded=Count('id', filter=succeeded),
                failed=Count('id', filter=failed),
            )
            .order_by('day')
        )

        by_model = list(
            tasks.values('model__key', 'model__name')
            .annotate(
                total=Count('id'),
                succeeded=Count('id', filter=succeeded),
                failed=Count('id', filter=failed),
            )
            .order_by('-total')
        )

        by_clinic = list(
            tasks.values(
                'input_image__series__study__uploaded_by__userprofile__clinic_id',
                'input_image__series__study__uploaded_by__userprofile__clinic__name',
            )
            .annotate(total=Count('id'))
            .order_by('-total')[:20]
        )

        by_status = list(
            tasks.values('status').annotate(total=Count('id')).order_by('-total')
        )

        return Response({
            'window_days': days,
            'since': since,
            'totals': totals,
            'over_time': over_time,
            'by_model': [
                {
                    'model_key': row['model__key'],
                    'name': row['model__name'],
                    'total': row['total'],
                    'succeeded': row['succeeded'],
                    'failed': row['failed'],
                }
                for row in by_model
            ],
            'by_clinic': [
                {
                    'clinic_id': row[
                        'input_image__series__study__uploaded_by__userprofile__clinic_id'
                    ],
                    'name': row[
                        'input_image__series__study__uploaded_by__userprofile__clinic__name'
                    ],
                    'total': row['total'],
                }
                for row in by_clinic
            ],
            'by_status': by_status,
        })


class AdminPlatformSummaryView(APIView):
    """Headline counts for the top of the Admin panel."""

    permission_classes = [IsAuthenticated, IsPlatformStaff]

    @extend_schema(
        summary='Platform-wide headline counts',
        responses={200: OpenApiTypes.OBJECT},
        tags=['Admin'],
    )
    def get(self, request):
        from dicom_images.models import MedicalStudy
        from patients.models import AnimalPatient, Owner
        from reports.models import Report

        last_30 = timezone.now() - timedelta(days=30)
        return Response({
            'clinics': Clinic.objects.filter(deleted_at__isnull=True).count(),
            'users': User.objects.filter(is_active=True).count(),
            'owners': Owner.objects.count(),
            'patients': AnimalPatient.objects.count(),
            'studies': MedicalStudy.objects.count(),
            'analyses': AnalysisTask.objects.count(),
            'analyses_last_30d': AnalysisTask.objects.filter(created_at__gte=last_30).count(),
            'reports': Report.objects.count(),
            'pending_invitations': ClinicInvitation.objects.filter(
                accepted_at__isnull=True,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).count(),
        })

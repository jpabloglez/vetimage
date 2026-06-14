"""
Reports Views
"""

import uuid

from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiTypes

from .models import Report
from .serializers import (
    CreateReportSerializer,
    ReportSerializer,
    ReportListSerializer,
    PublicReportSerializer,
)
from .services.report_builder import ReportBuilder
from .services.pdf_generator import PDFReportGenerator


@extend_schema(tags=['Reports'])
class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for managing veterinary reports."""

    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    lookup_field = 'id'

    def get_queryset(self):
        qs = (
            Report.objects
            .filter(created_by=self.request.user)
            .select_related('analysis_task__model', 'study')
        )
        # Optional filter by study UID for comparison
        study_uid = self.request.query_params.get('study_uid')
        if study_uid:
            qs = qs.filter(study__study_instance_uid=study_uid)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return ReportListSerializer
        if self.action == 'create':
            return CreateReportSerializer
        return ReportSerializer

    def create(self, request, *args, **kwargs):
        serializer = CreateReportSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        from ai_analysis.models import AnalysisTask

        task = AnalysisTask.objects.select_related(
            'model', 'input_image__series__study'
        ).get(id=serializer.validated_data['analysis_task_id'])

        study = task.input_image.series.study

        # Check if a template was specified
        template = None
        template_id = serializer.validated_data.get('template_id')
        if template_id:
            from .models import ReportTemplate
            from .services.template_engine import TemplateEngine

            try:
                template = ReportTemplate.objects.get(id=template_id)
            except ReportTemplate.DoesNotExist:
                return Response(
                    {'error': 'Template not found.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            engine = TemplateEngine()
            content = engine.apply_template(template, task)
        else:
            builder = ReportBuilder()
            content = builder.build_from_task(task)

        model_name = task.model.name if task.model else 'AI'
        report = Report.objects.create(
            analysis_task=task,
            study=study,
            created_by=request.user,
            template=template,
            title=f"{model_name} Analysis Report — {study.patient_id}",
            content=content,
            status='DRAFT',
        )

        return Response(
            ReportSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary='Download report PDF',
        responses={(200, 'application/pdf'): OpenApiTypes.BINARY},
        tags=['Reports'],
    )
    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, id=None):
        """Download the report as a PDF."""
        report = self.get_object()
        generator = PDFReportGenerator()
        pdf_buffer = generator.generate(report)

        response = HttpResponse(
            pdf_buffer.getvalue(),
            content_type='application/pdf',
        )
        filename = f"report_{str(report.id)[:8]}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @extend_schema(
        summary='Approve report (veterinarian sign-off)',
        request=None, responses=ReportSerializer, tags=['Reports'],
    )
    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, id=None):
        """
        Veterinarian sign-off: mark the report reviewed/approved and FINAL.
        Human-in-the-loop gate — AI drafts are not valid until approved.
        """
        from django.utils import timezone
        report = self.get_object()
        report.approved_by = request.user
        report.approved_at = timezone.now()
        report.status = 'FINAL'
        report.save(update_fields=['approved_by', 'approved_at', 'status', 'updated_at'])
        return Response(ReportSerializer(report).data)

    @extend_schema(
        summary='Revert report to draft (revoke sign-off)',
        request=None, responses=ReportSerializer, tags=['Reports'],
    )
    @action(detail=True, methods=['post'], url_path='unapprove')
    def unapprove(self, request, id=None):
        """Revert a report to DRAFT (e.g. to amend after sign-off)."""
        report = self.get_object()
        report.approved_by = None
        report.approved_at = None
        report.status = 'DRAFT'
        # Revoke any owner share — an unapproved report must not be viewable.
        report.share_token = None
        report.shared_at = None
        report.save(update_fields=[
            'approved_by', 'approved_at', 'status', 'share_token', 'shared_at', 'updated_at',
        ])
        return Response(ReportSerializer(report).data)

    @extend_schema(
        summary='Create owner share link (approved reports only)',
        request=None,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description='{ "share_token": "...", "share_path": "/shared/..." }',
            ),
            400: OpenApiResponse(description='Report is not approved'),
        },
        tags=['Reports'],
    )
    @action(detail=True, methods=['post'], url_path='share')
    def share(self, request, id=None):
        """
        Create an owner share link. Only APPROVED reports can be shared — owners
        must never see an unreviewed AI draft. Returns the share token/path.
        """
        from django.utils import timezone
        report = self.get_object()
        if not report.is_approved:
            return Response(
                {'error': 'Only approved reports can be shared with owners.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not report.share_token:
            report.share_token = uuid.uuid4()
            report.shared_at = timezone.now()
            report.save(update_fields=['share_token', 'shared_at', 'updated_at'])
        return Response({
            'share_token': str(report.share_token),
            'share_path': f'/shared/{report.share_token}',
        })

    @extend_schema(
        summary='Revoke owner share link',
        request=None, responses=OpenApiTypes.OBJECT, tags=['Reports'],
    )
    @action(detail=True, methods=['post'], url_path='unshare')
    def unshare(self, request, id=None):
        """Revoke an owner share link."""
        report = self.get_object()
        report.share_token = None
        report.shared_at = None
        report.save(update_fields=['share_token', 'shared_at', 'updated_at'])
        return Response({'success': True})


@extend_schema(
    summary='Public owner view of a shared report',
    description='Read-only, sanitised view of an approved report via its share '
                'token. No authentication — the unguessable token is the key.',
    responses={
        200: PublicReportSerializer,
        404: OpenApiResponse(description='Report not found, not approved, or unshared'),
    },
    tags=['Reports'],
    auth=[],
)
class PublicSharedReportView(APIView):
    """
    Public, read-only, owner-facing view of a shared+approved report.

    Auth is the unguessable share token in the URL (the standard pattern for
    sharing results with pet owners). Returns a sanitised, plain-language
    payload only — never internal IDs, model internals, or unapproved drafts.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        try:
            report = Report.objects.get(share_token=token)
        except (Report.DoesNotExist, ValueError, Exception):
            return Response({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)
        # Defensive: only ever expose approved, shared reports.
        if not report.is_approved or not report.share_token:
            return Response({'error': 'Report not available'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PublicReportSerializer(report).data)

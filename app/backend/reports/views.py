"""
Reports Views
"""

from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Report
from .serializers import (
    CreateReportSerializer,
    ReportSerializer,
    ReportListSerializer,
)
from .services.report_builder import ReportBuilder
from .services.pdf_generator import PDFReportGenerator


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for managing medical reports."""

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

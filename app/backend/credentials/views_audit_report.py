"""
Audit Trail Report Views
"""

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from credentials.serializers_audit_report import AuditReportFilterSerializer
from credentials.audit_report_service import AuditReportService


class AuditReportPreviewView(APIView):
    """GET — preview audit report as JSON."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = AuditReportFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        service = AuditReportService()
        report_content = service.build_audit_report(
            filters=serializer.validated_data,
            user=request.user,
        )

        return Response(report_content)


class AuditReportDownloadView(APIView):
    """GET — download audit report as PDF."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = AuditReportFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        service = AuditReportService()
        pdf_buffer = service.generate_pdf(
            filters=serializer.validated_data,
            user=request.user,
        )

        response = HttpResponse(
            pdf_buffer.getvalue(),
            content_type='application/pdf',
        )
        response['Content-Disposition'] = 'attachment; filename="audit_report.pdf"'
        return response

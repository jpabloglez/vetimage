"""
Format Conversion Views
"""

from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dicom_images.models import ConversionJob
from dicom_images.serializers_conversion import (
    CreateConversionJobSerializer,
    ConversionJobSerializer,
)
from dicom_images.tasks import convert_format_task


class ConversionJobViewSet(viewsets.ModelViewSet):
    """ViewSet for format conversion jobs."""

    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    lookup_field = 'id'

    def get_queryset(self):
        return ConversionJob.objects.filter(
            created_by=self.request.user
        ).select_related('created_by', 'study')

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateConversionJobSerializer
        return ConversionJobSerializer

    def create(self, request, *args, **kwargs):
        serializer = CreateConversionJobSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        job = ConversionJob.objects.create(
            study_id=data.get('study_id'),
            series_ids=data.get('series_ids', []),
            target_format=data['target_format'],
            created_by=request.user,
            status='PENDING',
        )

        convert_format_task.delay(str(job.id))

        return Response(
            ConversionJobSerializer(job).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, id=None):
        """Download the converted file if job is completed."""
        job = self.get_object()

        if job.status != 'COMPLETED':
            return Response(
                {'error': 'Job is not yet completed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_path = Path(settings.MEDIA_ROOT) / job.result_file_path
        if not file_path.exists():
            return Response(
                {'error': 'Output file not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Determine content type
        if file_path.suffix == '.zip':
            content_type = 'application/zip'
        elif file_path.suffix == '.gz':
            content_type = 'application/gzip'
        else:
            content_type = 'application/octet-stream'

        return FileResponse(
            open(file_path, 'rb'),
            content_type=content_type,
            as_attachment=True,
            filename=file_path.name,
        )

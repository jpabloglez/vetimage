"""
Batch Operations Views
"""

from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dicom_images.models import BatchJob
from dicom_images.serializers_batch import (
    CreateBatchJobSerializer,
    BatchJobSerializer,
)
from dicom_images.tasks import batch_operation_task


class BatchOperationViewSet(viewsets.ModelViewSet):
    """ViewSet for batch operation jobs."""

    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    lookup_field = 'id'

    def get_queryset(self):
        return BatchJob.objects.filter(
            created_by=self.request.user
        ).select_related('created_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateBatchJobSerializer
        return BatchJobSerializer

    def create(self, request, *args, **kwargs):
        serializer = CreateBatchJobSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        job = BatchJob.objects.create(
            operation=data['operation'],
            study_ids=data['study_ids'],
            model_key=data.get('model_key', ''),
            parameters=data.get('parameters', {}),
            created_by=request.user,
            status='PENDING',
        )

        batch_operation_task.delay(str(job.id))

        return Response(
            BatchJobSerializer(job).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, id=None):
        """Download the export ZIP if job is completed."""
        job = self.get_object()

        if job.status != 'COMPLETED':
            return Response(
                {'error': 'Job is not yet completed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if job.operation != 'export' or not job.result_file_path:
            return Response(
                {'error': 'No downloadable file for this job.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file_path = Path(settings.MEDIA_ROOT) / job.result_file_path
        if not file_path.exists():
            return Response(
                {'error': 'Output file not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return FileResponse(
            open(file_path, 'rb'),
            content_type='application/zip',
            as_attachment=True,
            filename=file_path.name,
        )

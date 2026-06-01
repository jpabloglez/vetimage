"""
DICOM Anonymization Views
"""

import os
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dicom_images.models import AnonymizationJob
from dicom_images.serializers_anonymization import (
    CreateAnonymizationJobSerializer,
    AnonymizationJobSerializer,
)
from dicom_images.tasks import anonymize_study_task


class AnonymizationJobViewSet(viewsets.ModelViewSet):
    """ViewSet for DICOM anonymization jobs."""

    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    lookup_field = 'id'

    def get_queryset(self):
        return AnonymizationJob.objects.filter(
            created_by=self.request.user
        ).select_related('created_by', 'study')

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateAnonymizationJobSerializer
        return AnonymizationJobSerializer

    def create(self, request, *args, **kwargs):
        serializer = CreateAnonymizationJobSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        job = AnonymizationJob.objects.create(
            study_id=data.get('study_id'),
            image_ids=data.get('image_ids', []),
            profile=data['profile'],
            output_format=data.get('output_format', 'dicom_zip'),
            created_by=request.user,
            status='PENDING',
        )

        # Dispatch background task
        anonymize_study_task.delay(str(job.id))

        return Response(
            AnonymizationJobSerializer(job).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, id=None):
        """Download the anonymized ZIP if job is completed."""
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

        return FileResponse(
            open(file_path, 'rb'),
            content_type='application/zip',
            as_attachment=True,
            filename=file_path.name,
        )

"""
DICOM Tag Editor Views
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dicom_images.models import MedicalImage
from dicom_images.serializers_tag_editor import (
    DicomTagQuerySerializer,
    DicomTagUpdateSerializer,
)
from dicom_images.services.tag_editor import DicomTagEditorService


class DicomTagListView(APIView):
    """GET — list DICOM tags for an image, with optional search."""

    permission_classes = [IsAuthenticated]

    def get(self, request, image_id):
        query_ser = DicomTagQuerySerializer(data=request.query_params)
        query_ser.is_valid(raise_exception=True)

        service = DicomTagEditorService()
        try:
            tags = service.get_tags(
                image_id=image_id,
                user=request.user,
                search=query_ser.validated_data.get('search'),
            )
        except MedicalImage.DoesNotExist:
            return Response(
                {'error': 'Image not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({'tags': tags})


class DicomTagUpdateView(APIView):
    """PATCH — update tag values on a DICOM image."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, image_id):
        serializer = DicomTagUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = DicomTagEditorService()
        try:
            refreshed = service.update_tags(
                image_id=image_id,
                tag_updates=serializer.validated_data['tags'],
                user=request.user,
            )
        except MedicalImage.DoesNotExist:
            return Response(
                {'error': 'Image not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as exc:
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({'tags': refreshed})

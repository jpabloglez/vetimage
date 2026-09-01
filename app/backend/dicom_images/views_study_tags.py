"""
Study Tag Review Views

GET/PATCH the key identity tags (PatientName, PatientID, AccessionNumber)
for a whole study — the "review DICOM tags" step after upload, before AI
dispatch.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dicom_images.models import MedicalStudy
from dicom_images.serializers_study_tags import StudyTagReviewSerializer
from dicom_images.services.study_tag_review import StudyTagReviewService
from dicom_images.scoping import visible_studies


class StudyTagReviewView(APIView):
    """
    GET   /api/dicom/studies/{study_uid}/tags/
    PATCH /api/dicom/studies/{study_uid}/tags/   body: {patient_name?, patient_id?, accession_number?}
    """

    permission_classes = [IsAuthenticated]

    def _get_study(self, request, study_uid):
        study = visible_studies(request.user).filter(
            study_instance_uid=study_uid,
        ).order_by('-uploaded_at').first()
        if study is None:
            raise MedicalStudy.DoesNotExist
        return study

    @extend_schema(
        summary="Get a study's reviewable identity tags",
        responses={200: StudyTagReviewSerializer, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request, study_uid):
        try:
            study = self._get_study(request, study_uid)
        except MedicalStudy.DoesNotExist:
            return Response({'error': 'Study not found'}, status=status.HTTP_404_NOT_FOUND)

        service = StudyTagReviewService()
        return Response(service.get_review_fields(study))

    @extend_schema(
        summary="Confirm/correct a study's identity tags across all instances",
        request=StudyTagReviewSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
        examples=[OpenApiExample('Correct PatientID', value={'patient_id': 'REX-2024-001'})],
    )
    def patch(self, request, study_uid):
        try:
            study = self._get_study(request, study_uid)
        except MedicalStudy.DoesNotExist:
            return Response({'error': 'Study not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = StudyTagReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = StudyTagReviewService()
        files_updated, files_total = service.update_review_fields(
            study, serializer.validated_data,
        )

        return Response({
            'success': True,
            'study_instance_uid': study.study_instance_uid,
            'files_updated': files_updated,
            'files_total': files_total,
            **service.get_review_fields(study),
        })

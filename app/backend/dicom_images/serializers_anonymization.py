"""
DICOM Anonymization Serializers
"""

from rest_framework import serializers
from dicom_images.models import AnonymizationJob
from dicom_images.services.anonymization import AnonymizationProfile


class CreateAnonymizationJobSerializer(serializers.Serializer):
    """Validates input for creating an anonymization job."""

    study_id = serializers.IntegerField(required=False)
    image_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )
    profile = serializers.ChoiceField(
        choices=AnonymizationProfile.VALID_PROFILES
    )
    output_format = serializers.ChoiceField(
        choices=['dicom_zip', 'nifti_bids', 'png_bids'],
        default='dicom_zip',
    )

    def validate(self, data):
        if not data.get('study_id') and not data.get('image_ids'):
            raise serializers.ValidationError(
                "Either 'study_id' or 'image_ids' must be provided."
            )
        if data.get('study_id') and data.get('image_ids'):
            raise serializers.ValidationError(
                "Provide either 'study_id' or 'image_ids', not both."
            )
        if data.get('output_format') in ('nifti_bids', 'png_bids') and data.get('image_ids'):
            raise serializers.ValidationError(
                "BIDS output formats require 'study_id', not 'image_ids'."
            )
        return data

    def validate_study_id(self, value):
        from dicom_images.models import MedicalStudy

        request = self.context.get('request')
        if not MedicalStudy.objects.filter(
            id=value, uploaded_by=request.user
        ).exists():
            raise serializers.ValidationError('Study not found.')
        return value

    def validate_image_ids(self, value):
        from dicom_images.models import MedicalImage

        request = self.context.get('request')
        count = MedicalImage.objects.filter(
            id__in=value,
            series__study__uploaded_by=request.user,
        ).count()
        if count != len(value):
            raise serializers.ValidationError(
                'One or more image IDs not found or not owned by you.'
            )
        return value


class AnonymizationJobSerializer(serializers.ModelSerializer):
    """Read-only serializer for anonymization job status."""

    class Meta:
        model = AnonymizationJob
        fields = [
            'id', 'study', 'image_ids', 'profile', 'output_format', 'status',
            'result_file_path', 'error_message',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

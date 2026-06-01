"""
Format Conversion Serializers
"""

from rest_framework import serializers
from dicom_images.models import ConversionJob


class CreateConversionJobSerializer(serializers.Serializer):
    """Validates input for creating a conversion job."""

    study_id = serializers.IntegerField(required=False)
    series_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False,
    )
    target_format = serializers.ChoiceField(
        choices=['jpeg', 'png', 'nifti'],
    )

    def validate(self, data):
        if not data.get('study_id') and not data.get('series_ids'):
            raise serializers.ValidationError(
                "Either 'study_id' or 'series_ids' must be provided."
            )
        if data.get('target_format') == 'nifti' and not data.get('series_ids'):
            raise serializers.ValidationError(
                "NIfTI conversion requires 'series_ids'."
            )
        return data

    def validate_study_id(self, value):
        from dicom_images.models import MedicalStudy

        request = self.context.get('request')
        if not MedicalStudy.objects.filter(
            id=value, uploaded_by=request.user,
        ).exists():
            raise serializers.ValidationError('Study not found.')
        return value

    def validate_series_ids(self, value):
        from dicom_images.models import MedicalSeries

        request = self.context.get('request')
        count = MedicalSeries.objects.filter(
            id__in=value, study__uploaded_by=request.user,
        ).count()
        if count != len(value):
            raise serializers.ValidationError(
                'One or more series IDs not found or not owned by you.'
            )
        return value


class ConversionJobSerializer(serializers.ModelSerializer):
    """Read-only serializer for conversion job status."""

    class Meta:
        model = ConversionJob
        fields = [
            'id', 'study', 'series_ids', 'target_format', 'status',
            'result_file_path', 'error_message',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

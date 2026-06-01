"""
Batch Operations Serializers
"""

from rest_framework import serializers
from dicom_images.models import BatchJob


class CreateBatchJobSerializer(serializers.Serializer):
    """Validates input for creating a batch job."""

    study_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1,
    )
    operation = serializers.ChoiceField(
        choices=['export', 'delete', 'analyze'],
    )
    model_key = serializers.CharField(required=False, allow_blank=True)
    parameters = serializers.DictField(required=False, default=dict)

    def validate(self, data):
        if data['operation'] == 'analyze' and not data.get('model_key'):
            raise serializers.ValidationError(
                "'model_key' is required for analyze operations."
            )
        return data

    def validate_study_ids(self, value):
        from dicom_images.models import MedicalStudy

        request = self.context.get('request')
        count = MedicalStudy.objects.filter(
            id__in=value, uploaded_by=request.user,
        ).count()
        if count != len(value):
            raise serializers.ValidationError(
                'One or more study IDs not found or not owned by you.'
            )
        return value


class BatchJobSerializer(serializers.ModelSerializer):
    """Read-only serializer for batch job status."""

    class Meta:
        model = BatchJob
        fields = [
            'id', 'operation', 'study_ids', 'model_key', 'parameters',
            'status', 'result_file_path', 'result_summary',
            'error_message', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

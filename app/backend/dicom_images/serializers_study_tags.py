"""
Study Tag Review Serializers
"""

from rest_framework import serializers


class StudyTagReviewSerializer(serializers.Serializer):
    """Read/write shape for the study-level tag review step."""
    patient_name = serializers.CharField(max_length=255, allow_blank=True, required=False)
    patient_id = serializers.CharField(max_length=100, allow_blank=True, required=False)
    accession_number = serializers.CharField(max_length=100, allow_blank=True, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                'At least one of patient_name, patient_id, accession_number is required.'
            )
        return attrs

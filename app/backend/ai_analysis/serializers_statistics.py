"""
Statistics serializers for analysis data review.

CRITICAL PRIVACY REQUIREMENT:
- Patient names MUST be excluded from all responses
- Only patient IDs are exposed
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from .models import AnalysisTask


class StatisticsTaskSerializer(serializers.ModelSerializer):
    """
    Task record with demographics, EXCLUDING patient names.

    This serializer is designed for the Statistics page and explicitly
    excludes patient_name to comply with privacy requirements.
    """

    # Model information
    model_name = serializers.CharField(source='model.name', read_only=True)
    model_key = serializers.CharField(source='model.key', read_only=True)
    model_type = serializers.CharField(source='model.model_type', read_only=True)

    # Patient demographics (PATIENT IDs ONLY, NO NAMES)
    patient_id = serializers.CharField(
        source='input_image.series.study.patient_id',
        read_only=True,
        allow_null=True
    )
    patient_sex = serializers.CharField(
        source='input_image.series.study.patient_sex',
        read_only=True,
        allow_null=True
    )
    patient_age = serializers.SerializerMethodField()

    # Study/Image metadata
    study_date = serializers.DateField(
        source='input_image.series.study.study_date',
        read_only=True,
        allow_null=True
    )
    study_description = serializers.CharField(
        source='input_image.series.study.study_description',
        read_only=True,
        allow_null=True
    )
    modality = serializers.CharField(
        source='input_image.series.modality',
        read_only=True,
        allow_null=True
    )
    body_part = serializers.CharField(
        source='input_image.series.body_part_examined',
        read_only=True,
        allow_null=True
    )

    # Organization (for filtering and display)
    organization_name = serializers.CharField(
        source='input_image.series.study.uploaded_by.userprofile.organization.centre',
        read_only=True,
        allow_null=True
    )

    # Processing information
    processing_duration = serializers.SerializerMethodField()

    # AI metrics (extracted from result_metadata JSONField)
    ai_metrics = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisTask
        fields = [
            'id',
            'model_name',
            'model_key',
            'model_type',
            'status',
            'created_at',
            'completed_at',
            'processing_duration',
            'patient_id',  # PATIENT ID ONLY - NO patient_name field
            'patient_sex',
            'patient_age',
            'study_date',
            'study_description',
            'modality',
            'body_part',
            'organization_name',
            'ai_metrics',
        ]
        # NOTE: patient_name is deliberately EXCLUDED for privacy compliance

    def get_patient_age(self, obj):
        """
        Compute patient age from birth date.

        Returns None if birth date is not available.
        """
        try:
            birth_date = obj.input_image.series.study.patient_birth_date
            if not birth_date:
                return None

            today = timezone.now().date()
            age = today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )
            return age
        except (AttributeError, TypeError):
            return None

    def get_processing_duration(self, obj):
        """
        Get processing duration in seconds.

        Returns None if task is not completed or times are missing.
        """
        if obj.status != 'COMPLETED' or not obj.completed_at or not obj.created_at:
            return None

        duration = (obj.completed_at - obj.created_at).total_seconds()
        return round(duration, 2)

    def get_ai_metrics(self, obj):
        """
        Extract key metrics from result_metadata JSONField.

        Metrics vary based on model type:
        - Segmentation: dice_score, volume, etc.
        - Classification: confidence, predicted_class, etc.
        """
        metadata = obj.result_metadata or {}

        # Extract metrics based on model type
        if obj.model.model_type == 'segmentation':
            return {
                'dice_score': metadata.get('dice_score'),
                'segmented_volume': metadata.get('segmented_volume'),
                'iou': metadata.get('iou'),
                'hausdorff_distance': metadata.get('hausdorff_distance'),
            }
        elif obj.model.model_type == 'classification':
            return {
                'confidence': metadata.get('confidence'),
                'predicted_class': metadata.get('predicted_class'),
                'top_k_predictions': metadata.get('top_k_predictions'),
            }
        elif obj.model.model_type == 'detection':
            return {
                'num_detections': metadata.get('num_detections'),
                'average_confidence': metadata.get('average_confidence'),
                'detection_boxes': metadata.get('detection_boxes'),
            }

        # Return raw metadata if model type is unknown
        return metadata


class StatisticsAggregatedSerializer(serializers.Serializer):
    """
    Serializer for aggregated statistics data.

    Used for time series, distributions, and summary statistics.
    """

    # Time series data
    time_series = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )

    # Distribution data
    processing_time_distribution = serializers.ListField(
        child=serializers.FloatField(),
        required=False
    )

    # Model usage statistics
    model_usage = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )

    # Status breakdown
    status_breakdown = serializers.DictField(
        child=serializers.IntegerField(),
        required=False
    )

    # Summary statistics
    total_tasks = serializers.IntegerField(required=False)
    completed_tasks = serializers.IntegerField(required=False)
    failed_tasks = serializers.IntegerField(required=False)
    average_processing_time = serializers.FloatField(required=False)

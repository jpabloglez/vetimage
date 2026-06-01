"""
Reports Serializers
"""

from rest_framework import serializers
from .models import Report


class CreateReportSerializer(serializers.Serializer):
    """Validates input for creating a report from an analysis task."""

    analysis_task_id = serializers.UUIDField()
    template_id = serializers.UUIDField(required=False)

    def validate_analysis_task_id(self, value):
        from ai_analysis.models import AnalysisTask

        try:
            task = AnalysisTask.objects.select_related(
                'model', 'input_image__series__study'
            ).get(id=value)
        except AnalysisTask.DoesNotExist:
            raise serializers.ValidationError('Analysis task not found.')

        if task.status != 'COMPLETED':
            raise serializers.ValidationError(
                'Report can only be generated from a completed analysis task.'
            )

        # Check ownership
        request = self.context.get('request')
        if request and task.created_by_id != request.user.id:
            raise serializers.ValidationError('Analysis task not found.')

        return value


class ReportSerializer(serializers.ModelSerializer):
    """Full report detail serializer."""

    analysis_task_id = serializers.UUIDField(source='analysis_task.id', read_only=True)
    study_uid = serializers.CharField(
        source='study.study_instance_uid', read_only=True
    )

    class Meta:
        model = Report
        fields = [
            'id', 'title', 'content', 'status',
            'analysis_task_id', 'study_uid',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class ReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for report list views."""

    model_name = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'id', 'title', 'status', 'model_name',
            'created_at',
        ]
        read_only_fields = fields

    def get_model_name(self, obj):
        task = obj.analysis_task
        if task and task.model:
            return task.model.name
        return 'Unknown'

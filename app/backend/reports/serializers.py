"""
Reports Serializers
"""

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
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
    is_approved = serializers.BooleanField(read_only=True)
    approved_by_email = serializers.EmailField(source='approved_by.email', read_only=True)
    is_shared = serializers.BooleanField(read_only=True)
    share_token = serializers.UUIDField(read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'title', 'content', 'status',
            'analysis_task_id', 'study_uid',
            'is_approved', 'approved_by_email', 'approved_at',
            'is_shared', 'share_token',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class ReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for report list views."""

    model_name = serializers.SerializerMethodField()
    patient_info = serializers.SerializerMethodField()
    is_approved = serializers.BooleanField(read_only=True)

    class Meta:
        model = Report
        fields = [
            'id', 'title', 'status', 'model_name', 'patient_info',
            'is_approved', 'created_at',
        ]
        read_only_fields = fields

    def get_model_name(self, obj) -> str:
        task = obj.analysis_task
        if task and task.model:
            return task.model.name
        return None

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_patient_info(self, obj):
        """Signalment header (patient_name, patient_id, owner, …) for list rows."""
        return (obj.content or {}).get('patient_info', {})


class PublicReportSerializer(serializers.ModelSerializer):
    """
    Owner-facing, read-only view of an APPROVED report. Plain-language and
    sanitised: no internal IDs, model internals, or task plumbing — just the
    signalment, findings, summary, the veterinarian's approval, and the
    decision-support disclaimer. Results are framed as explained by the vet.
    """
    approved_at = serializers.DateTimeField(read_only=True)
    clinic = serializers.SerializerMethodField()
    patient_info = serializers.SerializerMethodField()
    findings = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    disclaimer = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = [
            'title', 'patient_info', 'findings', 'summary',
            'disclaimer', 'approved_at', 'clinic',
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.STR)
    def get_clinic(self, obj):
        try:
            org = obj.created_by.userprofile.organization
            return org.centre if org else None
        except Exception:
            return None

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_patient_info(self, obj):
        return (obj.content or {}).get('patient_info', {})

    @extend_schema_field(serializers.ListSerializer(child=serializers.CharField()))
    def get_findings(self, obj):
        # Flatten findings sections to plain {description} items for owners.
        sections = (obj.content or {}).get('sections', [])
        out = []
        for s in sections:
            if s.get('type') == 'findings':
                for item in s.get('items', []):
                    desc = item.get('description') if isinstance(item, dict) else str(item)
                    if desc:
                        out.append(desc)
        return out

    @extend_schema_field(OpenApiTypes.STR)
    def get_summary(self, obj):
        return (obj.content or {}).get('summary', '')

    @extend_schema_field(OpenApiTypes.STR)
    def get_disclaimer(self, obj):
        return (obj.content or {}).get('disclaimer') or (
            'These results were reviewed and approved by your veterinarian. '
            'Please discuss them with your clinic — this summary is not a '
            'diagnosis and was assisted by software.'
        )
        return 'Unknown'

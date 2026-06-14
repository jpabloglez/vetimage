"""
Report Template Serializers
"""

from rest_framework import serializers
from .models import ReportTemplate


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Full report template serializer."""

    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'template_type', 'layout',
            'species_filter', 'modality_filter',
            'is_default', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'is_default', 'created_at', 'updated_at']


class CreateReportTemplateSerializer(serializers.ModelSerializer):
    """Serializer for creating custom templates."""

    class Meta:
        model = ReportTemplate
        fields = ['name', 'template_type', 'layout', 'species_filter', 'modality_filter']

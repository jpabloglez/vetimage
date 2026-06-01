"""
Audit Report Serializers
"""

from rest_framework import serializers


class AuditReportFilterSerializer(serializers.Serializer):
    """Validates query params for audit report filtering."""

    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    user_id = serializers.IntegerField(required=False)
    event_type = serializers.CharField(required=False)
    risk_score_min = serializers.IntegerField(
        required=False, min_value=0, max_value=100,
    )

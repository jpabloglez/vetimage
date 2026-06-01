"""
Serializers for DICOM Gateway Transfer Monitoring.

This module provides serializers for the DICOM transfer monitoring API,
enabling privacy-aware display of transfer data and statistics.
"""

from rest_framework import serializers
from .models import DICOMTransaction


class StudyTransferSerializer(serializers.Serializer):
    """
    Serializer for study-level DICOM transfer monitoring data.

    Aggregates individual DICOMTransaction records by study_instance_uid
    to provide a study-level view of transfer activity.

    Privacy: Uses hashed patient_id (SHA-256) instead of PHI.
    """

    # Study identifiers
    study_instance_uid = serializers.CharField(
        help_text="DICOM Study Instance UID"
    )
    patient_id_hash = serializers.CharField(
        help_text="SHA-256 hash of patient ID (privacy-compliant)",
        allow_blank=True
    )
    study_date = serializers.DateField(
        allow_null=True,
        help_text="Study date (YYYYMMDD)"
    )
    study_description = serializers.CharField(
        allow_blank=True,
        help_text="Study description"
    )

    # Source information
    source_pacs_name = serializers.CharField(
        allow_blank=True,
        help_text="Name of source PACS configuration"
    )
    source_ae = serializers.CharField(
        help_text="Source Application Entity (AE) title"
    )
    source_ip = serializers.IPAddressField(
        help_text="Source IP address"
    )

    # Transfer metrics
    total_instances = serializers.IntegerField(
        help_text="Total number of instances in transfer"
    )
    successful_instances = serializers.IntegerField(
        help_text="Number of successfully transferred instances"
    )
    failed_instances = serializers.IntegerField(
        help_text="Number of failed instance transfers"
    )
    pending_instances = serializers.IntegerField(
        help_text="Number of instances still pending transfer"
    )
    transfer_status = serializers.CharField(
        help_text="Overall transfer status: success|partial|in_progress|failed"
    )

    # Timing
    first_transfer_at = serializers.DateTimeField(
        help_text="Timestamp of first instance transfer"
    )
    last_transfer_at = serializers.DateTimeField(
        allow_null=True,
        help_text="Timestamp of last instance transfer (null if in progress)"
    )
    total_duration_ms = serializers.IntegerField(
        allow_null=True,
        help_text="Total transfer duration in milliseconds (null if in progress)"
    )

    # Size
    total_size_bytes = serializers.IntegerField(
        help_text="Total size of transferred data in bytes"
    )

    # Modality
    modality = serializers.CharField(
        allow_blank=True,
        help_text="DICOM modality (CT, MR, CR, etc.)"
    )

    # Organization info (for colleague visibility)
    uploaded_by_name = serializers.SerializerMethodField(
        help_text="Name of user who received the transfer (privacy-aware)"
    )
    uploaded_by_department = serializers.SerializerMethodField(
        help_text="Department of user who received the transfer (privacy-aware)"
    )

    def get_uploaded_by_name(self, obj):
        """
        Return user name with privacy controls.

        - Returns 'You' for current user
        - Returns full name if user has shared jobs with colleagues
        - Returns 'Private' otherwise
        """
        request = self.context.get('request')
        if not request:
            return 'Unknown'

        uploaded_by = obj.get('uploaded_by')
        if not uploaded_by:
            return 'System'

        # Current user's own transfer
        if uploaded_by.id == request.user.id:
            return 'You'

        # Check if user has shared jobs
        try:
            profile = uploaded_by.userprofile
            if profile.is_sharing_jobs_with_colleagues:
                return uploaded_by.get_full_name() or uploaded_by.email
            else:
                return 'Private'
        except:
            return 'Private'

    def get_uploaded_by_department(self, obj):
        """
        Return department with privacy controls.

        Returns department only if user has shared jobs with colleagues.
        """
        request = self.context.get('request')
        if not request:
            return None

        uploaded_by = obj.get('uploaded_by')
        if not uploaded_by:
            return None

        # Current user
        if uploaded_by.id == request.user.id:
            try:
                return uploaded_by.userprofile.department
            except:
                return None

        # Check sharing settings
        try:
            profile = uploaded_by.userprofile
            if profile.is_sharing_jobs_with_colleagues:
                return profile.department
            else:
                return None
        except:
            return None


class TransferStatsSerializer(serializers.Serializer):
    """
    Serializer for DICOM transfer statistics.

    Provides aggregate metrics for dashboard cards and charts.
    """

    # Overall metrics
    total_transfers = serializers.IntegerField(
        help_text="Total number of study transfers"
    )
    total_instances_received = serializers.IntegerField(
        help_text="Total number of DICOM instances received"
    )

    # Status breakdown
    successful_transfers = serializers.IntegerField(
        help_text="Number of fully successful transfers"
    )
    failed_transfers = serializers.IntegerField(
        help_text="Number of fully failed transfers"
    )
    partial_transfers = serializers.IntegerField(
        help_text="Number of partially successful transfers"
    )
    in_progress_transfers = serializers.IntegerField(
        help_text="Number of transfers currently in progress"
    )

    # Performance metrics
    success_rate = serializers.FloatField(
        help_text="Percentage of successful transfers (0.0 - 1.0)"
    )
    avg_transfer_time_seconds = serializers.FloatField(
        allow_null=True,
        help_text="Average transfer time in seconds (null if no completed transfers)"
    )
    total_data_received_bytes = serializers.IntegerField(
        help_text="Total data volume received in bytes"
    )

    # Breakdowns
    by_modality = serializers.DictField(
        child=serializers.IntegerField(),
        help_text="Transfer count by modality (e.g., {'CT': 50, 'MR': 30})"
    )
    by_source_pacs = serializers.DictField(
        child=serializers.IntegerField(),
        help_text="Transfer count by source PACS (e.g., {'PACS1': 40, 'PACS2': 40})"
    )
    by_status = serializers.DictField(
        child=serializers.IntegerField(),
        help_text="Transfer count by status"
    )


class DICOMTransactionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating DICOM transaction records from the gateway service.

    This endpoint is called by the DICOM gateway when it receives images
    to create audit trail records in the database.
    """

    class Meta:
        model = DICOMTransaction
        fields = [
            'transaction_type',
            'direction',
            'source_ae',
            'source_ip',
            'dest_ae',
            'study_instance_uid',
            'series_instance_uid',
            'sop_instance_uid',
            'patient_id_hash',
            'pacs_config',  # Added for PACS association
            'status',
            'error_message',
            'started_at',
            'completed_at',
            'duration_ms',
            'file_size_bytes',
            'modality',
            'metadata',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'error_message': {'required': False, 'allow_blank': True, 'allow_null': True},
            'completed_at': {'required': False, 'allow_null': True},
            'duration_ms': {'required': False, 'allow_null': True},
            'file_size_bytes': {'required': False, 'allow_null': True},
            'metadata': {'required': False, 'allow_null': True},
            'pacs_config': {'required': False, 'allow_null': True},
        }

    def create(self, validated_data):
        """Create a new DICOM transaction record."""
        return DICOMTransaction.objects.create(**validated_data)

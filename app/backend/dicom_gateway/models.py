"""
DICOM Gateway Models

Database models for gateway configuration, transaction tracking, and audit logging.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class PACSConfiguration(models.Model):
    """Configuration for connected PACS systems"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Identity
    name = models.CharField(max_length=200, help_text="Descriptive name for this PACS")
    ae_title = models.CharField(
        max_length=16,
        unique=True,
        help_text="DICOM Application Entity Title"
    )
    description = models.TextField(
        blank=True,
        help_text='Detailed description of this PACS system and its purpose'
    )
    manufacturer = models.CharField(
        max_length=100,
        blank=True,
        help_text='PACS manufacturer (e.g., "GE Healthcare", "Siemens", "Philips")'
    )
    node = models.CharField(
        max_length=100,
        blank=True,
        help_text='DICOM node name - distinct identifier from AE Title for routing purposes'
    )

    # Connection settings
    host = models.CharField(max_length=255, help_text="PACS hostname or IP address")
    port = models.IntegerField(
        default=11112,
        validators=[MinValueValidator(1024), MaxValueValidator(65535)]
    )

    # Network settings
    max_pdu_length = models.IntegerField(default=16384)
    timeout = models.IntegerField(default=30, help_text="Connection timeout in seconds")

    # Security
    tls_enabled = models.BooleanField(default=False)
    tls_cert_path = models.CharField(max_length=500, blank=True)
    allowed_source_ips = models.JSONField(
        default=list,
        help_text="List of allowed source IP addresses"
    )

    # Workflow settings
    auto_retrieve_enabled = models.BooleanField(
        default=False,
        help_text="Automatically retrieve studies from this PACS"
    )
    auto_analyze_enabled = models.BooleanField(
        default=False,
        help_text="Automatically trigger AI analysis for received studies"
    )
    default_model_key = models.CharField(
        max_length=100,
        blank=True,
        help_text="Default AI model for auto-analysis"
    )

    # Status
    is_active = models.BooleanField(default=True)
    connection_status = models.CharField(
        max_length=20,
        choices=[
            ('connected', 'Connected'),
            ('disconnected', 'Disconnected'),
            ('error', 'Error'),
        ],
        default='disconnected'
    )
    last_connected = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_pacs_configs'
    )

    # Routing configuration for incoming transfers
    node_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pacs_node_configs',
        help_text='User whose API key will be used for authenticating DICOM uploads from this PACS. '
                  'If not set, transfers will use the gateway service account.'
    )
    receiving_organization = models.ForeignKey(
        'users.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pacs_configs',
        help_text='Organization override (optional). If not set, uses node_user.profile.organization'
    )

    class Meta:
        verbose_name = "PACS Configuration"
        verbose_name_plural = "PACS Configurations"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.ae_title})"

    def clean(self):
        """Validate PACS configuration fields."""
        from django.core.exceptions import ValidationError

        # If node_user is set, ensure they have a valid profile
        if self.node_user:
            try:
                profile = self.node_user.profile
            except Exception:
                raise ValidationError({
                    'node_user': 'Selected user does not have a user profile. '
                                 'Create a profile for this user first.'
                })

    def save(self, *args, **kwargs):
        """Save PACS configuration with auto-population of organization."""
        # If node_user is set but receiving_organization is not, inherit from user profile
        if self.node_user and not self.receiving_organization:
            try:
                self.receiving_organization = self.node_user.profile.organization
            except Exception:
                pass  # User may not have profile or organization
        super().save(*args, **kwargs)

    def test_connection(self):
        """
        Test PACS connectivity with C-ECHO

        Returns:
            bool: True if connection successful
        """
        from pynetdicom import AE
        from pynetdicom.sop_class import Verification

        ae = AE(ae_title='OPENMEDLAB_TEST')
        ae.add_requested_context(Verification)

        try:
            assoc = ae.associate(self.host, self.port, ae_title=self.ae_title)

            if assoc.is_established:
                status = assoc.send_c_echo()
                assoc.release()

                if status.Status == 0x0000:
                    self.connection_status = 'connected'
                    self.last_connected = timezone.now()
                    self.last_error = ''
                    self.save()
                    return True

            self.connection_status = 'error'
            self.last_error = 'Failed to establish association'
            self.save()
            return False

        except Exception as e:
            self.connection_status = 'error'
            self.last_error = str(e)
            self.save()
            return False


class DICOMTransaction(models.Model):
    """Audit log for all DICOM network transactions"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pacs_config = models.ForeignKey(
        PACSConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )

    # Transaction details
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ('C-STORE', 'Store'),
            ('C-FIND', 'Find'),
            ('C-MOVE', 'Move'),
            ('C-GET', 'Get'),
            ('C-ECHO', 'Echo'),
        ],
        db_index=True
    )
    direction = models.CharField(
        max_length=10,
        choices=[('incoming', 'Incoming'), ('outgoing', 'Outgoing')],
        db_index=True
    )

    # Source/Destination
    source_ae = models.CharField(max_length=16)
    source_ip = models.GenericIPAddressField(db_index=True)
    dest_ae = models.CharField(max_length=16)

    # Study/Image identifiers
    study_instance_uid = models.CharField(max_length=64, db_index=True)
    series_instance_uid = models.CharField(max_length=64, blank=True)
    sop_instance_uid = models.CharField(max_length=64, blank=True)
    patient_id_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 hash of Patient ID (for privacy)"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failure', 'Failure'),
            ('pending', 'Pending'),
        ],
        db_index=True
    )
    error_message = models.TextField(blank=True, null=True)

    # Timing
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, help_text="Duration in milliseconds")

    # Metadata
    file_size_bytes = models.BigIntegerField(null=True)
    modality = models.CharField(max_length=16, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "DICOM Transaction"
        verbose_name_plural = "DICOM Transactions"
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['-started_at', 'status']),
            models.Index(fields=['study_instance_uid', 'transaction_type']),
            models.Index(fields=['patient_id_hash', '-started_at']),
        ]

    def __str__(self):
        return f"{self.transaction_type} from {self.source_ae} ({self.status})"

    def mark_completed(self, success=True, error_message=''):
        """Mark transaction as completed"""
        self.completed_at = timezone.now()
        self.status = 'success' if success else 'failure'
        self.error_message = error_message

        if self.started_at:
            duration = (self.completed_at - self.started_at).total_seconds()
            self.duration_ms = int(duration * 1000)

        self.save()


class AuditEvent(models.Model):
    """HIPAA-compliant audit logging for PHI access and system events"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Who
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    user_role = models.CharField(max_length=50)
    source_ip = models.GenericIPAddressField()

    # What
    event_type = models.CharField(
        max_length=50,
        choices=[
            ('dicom.receive', 'DICOM Image Received'),
            ('dicom.send', 'DICOM Image Sent'),
            ('phi.access', 'PHI Accessed'),
            ('phi.export', 'PHI Exported'),
            ('config.change', 'Configuration Changed'),
            ('pacs.connect', 'PACS Connection'),
            ('pacs.disconnect', 'PACS Disconnection'),
            ('analysis.create', 'Analysis Task Created'),
            ('security.unauthorized', 'Unauthorized Access Attempt'),
        ],
        db_index=True
    )
    action_description = models.TextField()

    # When
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Where
    component = models.CharField(
        max_length=50,
        choices=[
            ('gateway', 'DICOM Gateway'),
            ('backend', 'Backend API'),
            ('frontend', 'Frontend'),
        ]
    )

    # Context
    study_uid = models.CharField(max_length=64, blank=True, db_index=True)
    patient_id_hash = models.CharField(max_length=64, blank=True)
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.CharField(max_length=100, blank=True)

    # Outcome
    success = models.BooleanField(default=True, db_index=True)
    error_message = models.TextField(blank=True)

    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Audit Event"
        verbose_name_plural = "Audit Events"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp', 'event_type']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['study_uid', '-timestamp']),
            models.Index(fields=['success', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.event_type} at {self.timestamp} by {self.user or 'System'}"

    @classmethod
    def log_phi_access(cls, user, study_uid, patient_id, action, source_ip):
        """Log PHI access for HIPAA compliance"""
        import hashlib

        patient_id_hash = hashlib.sha256(patient_id.encode()).hexdigest()

        return cls.objects.create(
            user=user,
            user_role=getattr(user, 'role', 'unknown') if user else 'system',
            source_ip=source_ip,
            event_type='phi.access',
            action_description=action,
            component='gateway',
            study_uid=study_uid,
            patient_id_hash=patient_id_hash,
        )

    @classmethod
    def log_dicom_reception(cls, source_ae, source_ip, study_uid, patient_id, success=True, error=''):
        """Log DICOM image reception"""
        import hashlib

        patient_id_hash = hashlib.sha256(patient_id.encode()).hexdigest() if patient_id else ''

        return cls.objects.create(
            user_role='dicom_gateway',
            source_ip=source_ip,
            event_type='dicom.receive',
            action_description=f'DICOM image received from {source_ae}',
            component='gateway',
            study_uid=study_uid,
            patient_id_hash=patient_id_hash,
            success=success,
            error_message=error,
        )


class GatewayHealth(models.Model):
    """Health metrics for the DICOM gateway service"""

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Service status
    is_running = models.BooleanField(default=True)
    scp_status = models.CharField(max_length=20, default='running')
    api_status = models.CharField(max_length=20, default='running')

    # Resource metrics
    cpu_percent = models.FloatField()
    memory_used_gb = models.FloatField()
    memory_percent = models.FloatField()
    disk_free_gb = models.FloatField()
    disk_used_percent = models.FloatField()

    # Transaction metrics
    total_received = models.IntegerField(default=0)
    total_success = models.IntegerField(default=0)
    total_failed = models.IntegerField(default=0)
    success_rate = models.FloatField(default=100.0)

    # Active connections
    active_associations = models.IntegerField(default=0)
    queue_depth = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Gateway Health Metric"
        verbose_name_plural = "Gateway Health Metrics"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f"Health @ {self.timestamp}"

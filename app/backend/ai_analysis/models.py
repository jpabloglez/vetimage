"""
AI Analysis Models for MAIO (Medical AI Analysis Orchestrator)

This module defines the core models for managing AI analysis tasks:
- AIModel: Registry of available AI models/services
- AnalysisTask: Tracks individual analysis jobs through their lifecycle
"""

import uuid
import secrets
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


def generate_webhook_secret():
    """Generate a secure random webhook secret (64 hex characters)"""
    return secrets.token_hex(32)


class AIModel(models.Model):
    """
    Registry of available AI models and their configuration.

    Each AI model represents a microservice that can process medical images.
    Models are identified by a unique key and have associated connectors for communication.
    """

    MODEL_TYPE_CHOICES = [
        ('registration', 'Image Registration'),
        ('segmentation', 'Image Segmentation'),
        ('classification', 'Image Classification'),
        ('detection', 'Object Detection'),
        ('reconstruction', '3D Reconstruction'),
        ('other', 'Other'),
    ]

    # Identity
    name = models.CharField(
        max_length=100,
        help_text="Human-readable name (e.g., 'MIRAGE v1.0')"
    )
    key = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique identifier for API usage (e.g., 'mirage-v1')"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the model's capabilities"
    )
    version = models.CharField(
        max_length=20,
        help_text="Model version number"
    )

    # Configuration
    endpoint_url = models.URLField(
        help_text="Base URL of the AI service (e.g., 'http://mirage-service:8000')"
    )
    connector_class = models.CharField(
        max_length=200,
        help_text="Python path to connector class (e.g., 'ai_analysis.connectors.mirage.MirageConnector')"
    )

    # Model Metadata
    model_type = models.CharField(
        max_length=50,
        choices=MODEL_TYPE_CHOICES,
        default='other',
        help_text="Type of AI model"
    )
    supported_modalities = models.JSONField(
        default=list,
        help_text="List of supported DICOM modalities (e.g., ['MR', 'CT'])"
    )
    required_parameters = models.JSONField(
        default=dict,
        help_text="JSON schema of required parameters for this model"
    )
    default_parameters = models.JSONField(
        default=dict,
        help_text="Default parameter values"
    )

    # Operational Settings
    timeout_seconds = models.IntegerField(
        default=1800,
        help_text="Maximum processing time in seconds (default: 30 minutes)"
    )
    max_retries = models.IntegerField(
        default=3,
        help_text="Maximum number of retry attempts for failed tasks"
    )
    retry_delay_seconds = models.IntegerField(
        default=60,
        help_text="Delay between retry attempts in seconds"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this model is available for new tasks"
    )
    use_orchestrator = models.BooleanField(
        default=False,
        help_text="Route this model through the gRPC Orchestrator (True) or Celery REST dispatch (False)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ============================================================================
    # Open Medical AI Platform Metadata
    # ============================================================================

    # Authors & Attribution
    authors = models.JSONField(
        default=list,
        blank=True,
        help_text="List of authors/contributors (e.g., [{'name': 'John Doe', 'affiliation': 'Institution', 'email': 'john@example.com'}])"
    )
    organization = models.CharField(
        max_length=200,
        blank=True,
        help_text="Organization or institution that developed the model"
    )

    # Publications & References
    publication_title = models.CharField(
        max_length=500,
        blank=True,
        help_text="Title of the primary publication"
    )
    publication_journal = models.CharField(
        max_length=200,
        blank=True,
        help_text="Journal or conference name"
    )
    publication_year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Year of publication"
    )
    publication_doi = models.CharField(
        max_length=100,
        blank=True,
        help_text="DOI of the publication (e.g., '10.1000/xyz123')"
    )
    publication_url = models.URLField(
        blank=True,
        help_text="URL to the publication (e.g., PubMed, ArXiv)"
    )
    citation = models.TextField(
        blank=True,
        help_text="Formatted citation text"
    )

    # Code & Resources
    github_url = models.URLField(
        blank=True,
        help_text="GitHub repository URL"
    )
    paper_url = models.URLField(
        blank=True,
        help_text="Link to paper (ArXiv, bioRxiv, etc.)"
    )
    demo_url = models.URLField(
        blank=True,
        help_text="Link to online demo or interactive notebook"
    )
    model_card_url = models.URLField(
        blank=True,
        help_text="Link to detailed model card documentation"
    )

    # Licensing
    license_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="License name (e.g., 'MIT', 'Apache 2.0', 'GPL-3.0')"
    )
    license_url = models.URLField(
        blank=True,
        help_text="URL to full license text"
    )

    # Model Characteristics
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Searchable tags (e.g., ['brain', 'mri', 'deep-learning', 'pytorch'])"
    )
    medical_domains = models.JSONField(
        default=list,
        blank=True,
        help_text="Clinical domains (e.g., ['cardiology', 'radiology', 'orthopedics'])"
    )
    anatomical_regions = models.JSONField(
        default=list,
        blank=True,
        help_text="Anatomical regions (e.g., ['thorax', 'abdomen', 'limb'])"
    )
    supported_species = models.JSONField(
        default=list,
        blank=True,
        help_text="Veterinary species the model is validated for "
                  "(e.g., ['canine', 'feline']). Empty = species-agnostic / unspecified."
    )

    # Performance Metrics
    performance_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Performance metrics (e.g., {'dice': 0.92, 'accuracy': 0.95, 'auc': 0.88})"
    )
    validation_dataset = models.CharField(
        max_length=200,
        blank=True,
        help_text="Dataset used for validation"
    )
    training_dataset = models.CharField(
        max_length=200,
        blank=True,
        help_text="Dataset used for training"
    )

    # Use Cases & Examples
    use_cases = models.JSONField(
        default=list,
        blank=True,
        help_text="Example use cases or clinical applications"
    )
    limitations = models.TextField(
        blank=True,
        help_text="Known limitations or contraindications"
    )
    example_images = models.JSONField(
        default=list,
        blank=True,
        help_text="URLs to example input/output images"
    )

    # Community & Support
    documentation_url = models.URLField(
        blank=True,
        help_text="Link to full documentation"
    )
    support_url = models.URLField(
        blank=True,
        help_text="Link to support forum or issue tracker"
    )
    homepage_url = models.URLField(
        blank=True,
        help_text="Project homepage"
    )

    # Statistics
    download_count = models.IntegerField(
        default=0,
        help_text="Number of times model has been used"
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="User rating (0.00-5.00)"
    )

    # Connector-specific configuration
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Connector-specific key/value pairs. "
            "For NNUNetConnector: 'nnunet_dataset_id', 'nnunet_config', 'nnunet_folds'. "
            "For gRPC connectors: 'device', 'threads', etc."
        ),
    )

    # Segmentation Output
    label_map = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Mapping from integer label ID to anatomy name "
            "(e.g. {'1': 'liver', '2': 'spleen'}). "
            "Used for DICOM SEG creation and structured report generation."
        ),
    )

    # Data Governance
    requires_anonymization = models.BooleanField(
        default=False,
        help_text=(
            "When True, analysis tasks can only be created if the input study "
            "has a completed anonymization job with profile 'full' or 'research'."
        ),
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'AI Model'
        verbose_name_plural = 'AI Models'
        indexes = [
            models.Index(fields=['key', 'is_active']),
            models.Index(fields=['model_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.key})"

    def clean(self):
        """Validate model configuration"""
        # Validate connector class format
        if self.connector_class and '.' not in self.connector_class:
            raise ValidationError({
                'connector_class': 'Must be a valid Python path (e.g., module.ClassName)'
            })

        # Validate timeout is positive
        if self.timeout_seconds <= 0:
            raise ValidationError({
                'timeout_seconds': 'Timeout must be positive'
            })


class AnalysisTask(models.Model):
    """
    Tracks an individual AI analysis job through its lifecycle.

    Tasks follow this workflow:
    1. PENDING: Created, waiting to be queued
    2. QUEUED: Sent to Celery queue
    3. DISPATCHED: HTTP request sent to AI service
    4. PROCESSING: AI service is actively processing
    5. COMPLETED: Successfully finished
    6. FAILED: Error occurred
    7. TIMEOUT: Exceeded maximum processing time
    8. CANCELLED: User cancelled the task
    """

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('QUEUED', 'Queued'),
        ('DISPATCHED', 'Dispatched'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('TIMEOUT', 'Timeout'),
        ('CANCELLED', 'Cancelled'),
    ]

    # Triage priority for the worklist. STAT cases surface first, mirroring the
    # turnaround tiers veterinary teleradiology workflows use.
    PRIORITY_CHOICES = [
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
        ('stat', 'STAT'),
    ]

    # Identity (UUID for security - prevents enumeration attacks)
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Relationships
    input_image = models.ForeignKey(
        'dicom_images.MedicalImage',
        on_delete=models.CASCADE,
        related_name='analysis_tasks',
        help_text="Primary input image for analysis"
    )
    model = models.ForeignKey(
        AIModel,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tasks',
        help_text="AI model used for this task"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='analysis_tasks',
        help_text="User who created this task"
    )

    # Task Configuration
    parameters = models.JSONField(
        default=dict,
        help_text="Model-specific parameters for this analysis"
    )
    additional_inputs = models.JSONField(
        default=list,
        blank=True,
        help_text="Additional image IDs for multi-image tasks (future use)"
    )

    # Status Tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='routine',
        db_index=True,
        help_text="Triage priority for the worklist (routine / urgent / STAT)"
    )

    # Job IDs for tracking
    celery_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Celery task ID for tracking async execution"
    )
    service_job_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Job ID returned by AI service"
    )
    orchestrator_job_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Job ID returned by orchestrator service"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    dispatched_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the task was sent to AI service"
    )
    started_processing_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When AI service started processing"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the task finished (success or failure)"
    )

    # Results (Local Filesystem Paths)
    result_file_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Relative path to result file (e.g., 'ai_results/2024/12/25/uuid.nii.gz')"
    )
    result_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadata from AI service (processing time, model version, etc.)"
    )

    # Error Handling
    error_message = models.TextField(
        blank=True,
        help_text="Error message if task failed"
    )
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of retry attempts"
    )

    # Security (Webhook Authentication)
    webhook_secret = models.CharField(
        max_length=64,
        default=generate_webhook_secret,
        help_text="Secret token for webhook authentication"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Analysis Task'
        verbose_name_plural = 'Analysis Tasks'
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['model', 'status']),
            models.Index(fields=['created_by', 'status', '-created_at']),  # For efficient colleague job queries
            models.Index(fields=['created_at', 'model', 'status']),  # For Statistics time-based filtering
            models.Index(fields=['model', 'status', 'completed_at']),  # For Statistics aggregation queries
        ]

    def __str__(self):
        return f"Task {str(self.id)[:8]}... - {self.status}"

    @property
    def processing_duration(self):
        """Calculate processing duration in seconds if available"""
        if self.started_processing_at and self.completed_at:
            delta = self.completed_at - self.started_processing_at
            return delta.total_seconds()
        return None

    @property
    def total_duration(self):
        """Calculate total duration from creation to completion"""
        if self.completed_at:
            delta = self.completed_at - self.created_at
            return delta.total_seconds()
        return None

    @property
    def is_terminal(self):
        """Check if task is in a terminal state (won't change)"""
        return self.status in ['COMPLETED', 'FAILED', 'TIMEOUT', 'CANCELLED']

    @property
    def can_retry(self):
        """Check if task can be retried"""
        if not self.model:
            return False
        return (
            self.status in ['FAILED', 'TIMEOUT'] and
            self.retry_count < self.model.max_retries
        )

    def clean(self):
        """Validate task before saving"""
        # Ensure input image belongs to the user creating the task
        if (self.input_image_id and self.created_by_id and
                self.input_image.series.study.uploaded_by_id != self.created_by_id):
            raise ValidationError({
                'input_image': 'You can only create tasks for your own images'
            })

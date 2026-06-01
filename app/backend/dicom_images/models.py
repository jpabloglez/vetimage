"""
DICOM Images Models

Database models for storing DICOM medical images with metadata.
Follows DICOMweb standard for compatibility with OHIF Viewer.
"""

import uuid
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
import os


class MedicalStudy(models.Model):
    """
    DICOM Study - top level container for medical images
    """
    # DICOM UIDs
    study_instance_uid = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Unique identifier for the study (StudyInstanceUID) - scoped per user"
    )

    # Patient information
    patient_id = models.CharField(max_length=100, db_index=True)
    patient_name = models.CharField(max_length=255, blank=True)
    patient_birth_date = models.DateField(null=True, blank=True)
    patient_sex = models.CharField(
        max_length=1,
        choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')],
        blank=True
    )

    # Study metadata
    study_date = models.DateField(null=True, blank=True, db_index=True)
    study_time = models.TimeField(null=True, blank=True)
    study_description = models.TextField(blank=True)
    accession_number = models.CharField(max_length=100, blank=True, db_index=True)

    # Ownership and tracking
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='studies'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Storage tracking
    total_size_bytes = models.BigIntegerField(default=0)

    # DICOM tag storage (comprehensive)
    dicom_tags = models.JSONField(
        default=dict,
        blank=True,
        help_text="Complete DICOM tag dump for extensibility"
    )

    # Search optimization fields
    patient_name_normalized = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Normalized patient name for search"
    )
    study_description_normalized = models.TextField(
        blank=True,
        db_index=True,
        help_text="Normalized description for full-text search"
    )

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Medical Study'
        verbose_name_plural = 'Medical Studies'
        indexes = [
            models.Index(fields=['uploaded_by', '-uploaded_at']),
            models.Index(fields=['patient_id', 'study_date']),
            # Index for identifying same study uploaded multiple times by same user
            models.Index(fields=['study_instance_uid', 'uploaded_by', '-uploaded_at']),
        ]

    def __str__(self):
        return f"Study {self.study_instance_uid[:20]}... - {self.patient_name or self.patient_id}"

    @property
    def number_of_series(self):
        """Count of series in this study"""
        return self.series.count()

    @property
    def number_of_instances(self):
        """Total count of images across all series"""
        return MedicalImage.objects.filter(series__study=self).count()


class MedicalSeries(models.Model):
    """
    DICOM Series - collection of related images within a study
    """
    # Relationship
    study = models.ForeignKey(
        MedicalStudy,
        on_delete=models.CASCADE,
        related_name='series'
    )

    # DICOM UIDs
    series_instance_uid = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Unique identifier for the series (SeriesInstanceUID) - scoped per study"
    )

    # Series metadata
    series_number = models.IntegerField(null=True, blank=True)
    series_description = models.TextField(blank=True)
    modality = models.CharField(
        max_length=10,
        db_index=True,
        help_text="Imaging modality (CT, MR, CR, DX, etc.)"
    )

    # Technical parameters
    body_part_examined = models.CharField(max_length=100, blank=True)
    protocol_name = models.CharField(max_length=255, blank=True)

    # Timestamps
    series_date = models.DateField(null=True, blank=True)
    series_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # DICOM tag storage
    dicom_tags = models.JSONField(
        default=dict,
        blank=True,
        help_text="Complete DICOM tag dump"
    )

    # Search optimization
    series_description_normalized = models.TextField(
        blank=True,
        db_index=True,
        help_text="Normalized description for search"
    )

    # Thumbnail storage
    thumbnail_small = models.ImageField(
        upload_to='thumbnails/series/%Y/%m/%d/small/',
        null=True,
        blank=True,
        help_text="150x150 thumbnail"
    )
    thumbnail_medium = models.ImageField(
        upload_to='thumbnails/series/%Y/%m/%d/medium/',
        null=True,
        blank=True,
        help_text="300x300 thumbnail"
    )
    thumbnail_large = models.ImageField(
        upload_to='thumbnails/series/%Y/%m/%d/large/',
        null=True,
        blank=True,
        help_text="512x512 thumbnail"
    )

    # Thumbnail metadata
    thumbnail_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When thumbnails were generated"
    )
    thumbnail_generation_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed')
        ],
        default='pending',
        help_text="Status of thumbnail generation"
    )

    class Meta:
        ordering = ['series_number']
        verbose_name = 'Medical Series'
        verbose_name_plural = 'Medical Series'
        indexes = [
            models.Index(fields=['study', 'series_number']),
            models.Index(fields=['modality']),
            # Index for series within study (allows duplicates)
            models.Index(fields=['series_instance_uid', 'study', '-created_at']),
        ]

    def __str__(self):
        return f"Series {self.series_number} - {self.modality} ({self.series_description})"

    @property
    def number_of_instances(self):
        """Count of images in this series"""
        return self.images.count()


class MedicalImage(models.Model):
    """
    DICOM Instance - individual medical image file
    """
    # Relationship
    series = models.ForeignKey(
        MedicalSeries,
        on_delete=models.CASCADE,
        related_name='images'
    )

    # DICOM UIDs
    sop_instance_uid = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Unique identifier for the instance (SOPInstanceUID) - scoped per series"
    )
    sop_class_uid = models.CharField(
        max_length=255,
        help_text="SOP Class UID defining the image type"
    )

    # Instance metadata
    instance_number = models.IntegerField(null=True, blank=True)

    # File storage
    file = models.FileField(
        upload_to='dicom/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['dcm', 'dicom'])],
        help_text="DICOM file"
    )
    file_size_bytes = models.BigIntegerField(default=0)
    original_filename = models.CharField(max_length=255)

    # Image technical details
    rows = models.IntegerField(null=True, blank=True, help_text="Image height")
    columns = models.IntegerField(null=True, blank=True, help_text="Image width")
    number_of_frames = models.IntegerField(default=1, help_text="Number of frames in multi-frame image")

    # Timestamps
    acquisition_datetime = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # DICOM tag storage
    dicom_tags = models.JSONField(
        default=dict,
        blank=True,
        help_text="Complete DICOM tag dump"
    )

    # Technical parameters for advanced queries
    pixel_spacing_row = models.FloatField(
        null=True,
        blank=True,
        help_text="Pixel spacing in row direction (mm)"
    )
    pixel_spacing_column = models.FloatField(
        null=True,
        blank=True,
        help_text="Pixel spacing in column direction (mm)"
    )
    slice_thickness = models.FloatField(
        null=True,
        blank=True,
        help_text="Slice thickness (mm)"
    )
    slice_location = models.FloatField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Slice location for 3D reconstruction"
    )

    # Window/Level defaults
    window_center = models.FloatField(
        null=True,
        blank=True,
        help_text="Default window center for display"
    )
    window_width = models.FloatField(
        null=True,
        blank=True,
        help_text="Default window width for display"
    )

    # Hounsfield units range (for CT)
    min_pixel_value = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minimum pixel value in image"
    )
    max_pixel_value = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum pixel value in image"
    )

    class Meta:
        ordering = ['instance_number']
        verbose_name = 'Medical Image'
        verbose_name_plural = 'Medical Images'
        indexes = [
            models.Index(fields=['series', 'instance_number']),
            # Index for instances within series (allows duplicates by upload date)
            models.Index(fields=['sop_instance_uid', 'series', '-uploaded_at']),
        ]

    def __str__(self):
        return f"Instance {self.instance_number} - {self.original_filename}"

    def save(self, *args, **kwargs):
        """Override save to update file size"""
        if self.file and not self.file_size_bytes:
            self.file_size_bytes = self.file.size
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Override delete to remove file from storage"""
        # Delete the file from storage
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)


class UserStorageQuota(models.Model):
    """
    Track storage usage per user
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='storage_quota'
    )

    used_bytes = models.BigIntegerField(default=0)
    quota_bytes = models.BigIntegerField(default=5 * 1024 * 1024 * 1024)  # 5 GB default
    thumbnail_size_bytes = models.BigIntegerField(
        default=0,
        help_text="Storage used by thumbnails"
    )

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Storage Quota'
        verbose_name_plural = 'User Storage Quotas'

    def __str__(self):
        return f"{self.user.email} - {self.used_bytes}/{self.quota_bytes} bytes"

    @property
    def remaining_bytes(self):
        """Calculate remaining storage"""
        return max(0, self.quota_bytes - self.used_bytes)

    @property
    def usage_percentage(self):
        """Calculate usage as percentage"""
        if self.quota_bytes == 0:
            return 100
        return (self.used_bytes / self.quota_bytes) * 100

    @property
    def is_over_quota(self):
        """Check if user has exceeded quota"""
        return self.used_bytes >= self.quota_bytes

    def update_usage(self):
        """Recalculate storage usage from all studies"""
        from django.db.models import Sum
        total = MedicalStudy.objects.filter(
            uploaded_by=self.user
        ).aggregate(Sum('total_size_bytes'))['total_size_bytes__sum'] or 0

        self.used_bytes = total
        self.save()
        return self.used_bytes


class SavedSearch(models.Model):
    """
    Saved search queries for quick access to frequently used filters
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_searches'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # JSON structure: {
    #   "patient_name": "John",
    #   "modality": ["CT", "MR"],
    #   "date_range": {"from": "2024-01-01", "to": "2024-12-31"},
    #   "tags": {"00100020": "12345"}
    # }
    search_filters = models.JSONField(
        help_text="JSON object containing search parameters"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    use_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-last_used_at']
        verbose_name = 'Saved Search'
        verbose_name_plural = 'Saved Searches'
        indexes = [
            models.Index(fields=['user', '-last_used_at']),
        ]

    def __str__(self):
        return f"{self.name} - {self.user.email}"


class ImageAnnotation(models.Model):
    """
    User annotations on medical images with measurement support
    """
    image = models.ForeignKey(
        'MedicalImage',
        on_delete=models.CASCADE,
        related_name='annotations'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='annotations'
    )

    ANNOTATION_TYPES = [
        ('text', 'Text Label'),
        ('arrow', 'Arrow'),
        ('rectangle', 'Rectangle'),
        ('ellipse', 'Ellipse'),
        ('polygon', 'Polygon'),
        ('line', 'Line'),
        ('angle', 'Angle Measurement'),
        ('distance', 'Distance Measurement'),
        ('area', 'Area Measurement'),
        ('roi', 'Region of Interest'),
    ]
    annotation_type = models.CharField(
        max_length=20,
        choices=ANNOTATION_TYPES
    )
    frame_number = models.IntegerField(
        default=0,
        help_text="Frame number for multi-frame images"
    )

    # Spatial data in image coordinates
    # Example structures:
    # - Point: {"x": 100, "y": 200}
    # - Line: {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 100}]}
    # - Polygon: {"points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 50, "y": 100}]}
    # - Text: {"position": {"x": 100, "y": 200}, "text": "Finding here", "fontSize": 14}
    geometry_data = models.JSONField(
        help_text="Coordinates and properties in JSON format"
    )

    # Measurement results (auto-calculated)
    measurement_value = models.FloatField(
        null=True,
        blank=True,
        help_text="Calculated measurement value"
    )
    measurement_unit = models.CharField(
        max_length=20,
        blank=True,
        help_text="Unit of measurement (mm, mm², degrees, etc.)"
    )

    # Annotation metadata
    label = models.CharField(
        max_length=255,
        blank=True,
        help_text="User-defined label or title"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description or clinical notes"
    )

    VISIBILITY_CHOICES = [
        ('private', 'Private'),
        ('shared', 'Shared'),
        ('public', 'Public')
    ]
    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY_CHOICES,
        default='private'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Image Annotation'
        verbose_name_plural = 'Image Annotations'
        indexes = [
            models.Index(fields=['image', 'frame_number']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['annotation_type']),
        ]

    def __str__(self):
        return f"{self.annotation_type} on {self.image.original_filename} by {self.created_by.email}"


class AnnotationTemplate(models.Model):
    """
    Reusable annotation templates for common measurements
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='annotation_templates'
    )
    name = models.CharField(
        max_length=255,
        help_text="Template name (e.g., 'Lung Nodule ROI')"
    )
    annotation_type = models.CharField(
        max_length=20,
        help_text="Type of annotation this template creates"
    )

    # Default properties like colors, line thickness, default text, etc.
    # Example: {"color": "#FF0000", "lineWidth": 2, "fillOpacity": 0.3}
    default_properties = models.JSONField(
        help_text="Default geometry and style properties"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Annotation Template'
        verbose_name_plural = 'Annotation Templates'

    def __str__(self):
        return f"{self.name} ({self.annotation_type})"


class AnonymizationJob(models.Model):
    """
    Tracks a DICOM anonymization job (background Celery task).
    """

    PROFILE_CHOICES = [
        ('basic', 'Basic'),
        ('full', 'Full'),
        ('research', 'Research'),
    ]

    OUTPUT_FORMAT_CHOICES = [
        ('dicom_zip', 'DICOM ZIP'),
        ('nifti_bids', 'NIfTI + BIDS JSON'),
        ('png_bids', 'PNG + BIDS JSON'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    study = models.ForeignKey(
        MedicalStudy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anonymization_jobs',
    )
    image_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of MedicalImage IDs to anonymize (used when no study is specified)",
    )
    profile = models.CharField(
        max_length=20,
        choices=PROFILE_CHOICES,
        default='basic',
    )
    output_format = models.CharField(
        max_length=20,
        choices=OUTPUT_FORMAT_CHOICES,
        default='dicom_zip',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True,
    )
    result_file_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Relative path to the output ZIP file",
    )
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='anonymization_jobs',
    )
    celery_task_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Anonymization Job'
        verbose_name_plural = 'Anonymization Jobs'
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"AnonymizationJob {str(self.id)[:8]}... - {self.status}"


class ConversionJob(models.Model):
    """
    Tracks a format conversion job (background Celery task).
    """

    FORMAT_CHOICES = [
        ('jpeg', 'JPEG'),
        ('png', 'PNG'),
        ('nifti', 'NIfTI'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    study = models.ForeignKey(
        MedicalStudy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversion_jobs',
    )
    series_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of MedicalSeries IDs (for NIfTI conversion)",
    )
    target_format = models.CharField(
        max_length=10,
        choices=FORMAT_CHOICES,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True,
    )
    result_file_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Relative path to the output file or ZIP",
    )
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversion_jobs',
    )
    celery_task_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Conversion Job'
        verbose_name_plural = 'Conversion Jobs'
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"ConversionJob {str(self.id)[:8]}... - {self.target_format} - {self.status}"


class BatchJob(models.Model):
    """
    Tracks a batch operation job (export, delete, analyze).
    """

    OPERATION_CHOICES = [
        ('export', 'Export'),
        ('delete', 'Delete'),
        ('analyze', 'Analyze'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    operation = models.CharField(
        max_length=20,
        choices=OPERATION_CHOICES,
    )
    study_ids = models.JSONField(
        default=list,
        help_text="List of MedicalStudy IDs to process",
    )
    model_key = models.CharField(
        max_length=255,
        blank=True,
        help_text="AI model key (for analyze operation)",
    )
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional parameters for the operation",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True,
    )
    result_file_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Relative path to the output file (for export)",
    )
    result_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Summary of the operation result",
    )
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='batch_jobs',
    )
    celery_task_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Batch Job'
        verbose_name_plural = 'Batch Jobs'
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"BatchJob {str(self.id)[:8]}... - {self.operation} - {self.status}"

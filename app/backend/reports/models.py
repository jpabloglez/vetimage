"""
Reports Models

Structured medical reports generated from AI analysis results.
"""

import uuid
from django.db import models
from django.conf import settings


class Report(models.Model):
    """
    A structured medical report built from AI analysis task results.
    """

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('FINAL', 'Final'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    analysis_task = models.ForeignKey(
        'ai_analysis.AnalysisTask',
        on_delete=models.CASCADE,
        related_name='reports',
        help_text="Source analysis task",
    )
    study = models.ForeignKey(
        'dicom_images.MedicalStudy',
        on_delete=models.CASCADE,
        related_name='reports',
        help_text="Associated medical study",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports',
    )

    template = models.ForeignKey(
        'ReportTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
        help_text="Template used to generate this report",
    )
    title = models.CharField(max_length=255)
    content = models.JSONField(
        default=dict,
        help_text="Structured report content (sections, findings, scores)",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='DRAFT',
    )

    # Veterinarian sign-off (human-in-the-loop). A report is only clinically
    # valid once a qualified veterinarian has reviewed and approved it.
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_reports',
        help_text="Veterinarian who reviewed and approved the report",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Owner sharing: an unguessable token grants read-only access to a plain-language
    # view of the report. Only APPROVED reports can be shared (human-in-the-loop).
    share_token = models.UUIDField(null=True, blank=True, unique=True, db_index=True)
    shared_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_approved(self):
        return self.approved_at is not None

    @property
    def is_shared(self):
        return self.share_token is not None

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['analysis_task']),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"


class ReportTemplate(models.Model):
    """
    A reusable template that controls how report content is structured.
    """

    TEMPLATE_TYPE_CHOICES = [
        ('radiology', 'Radiology'),
        ('pathology', 'Pathology'),
        ('general', 'General'),
        ('custom', 'Custom'),
        # Veterinary-specific templates
        ('thoracic_canine', 'Thoracic Radiograph — Canine'),
        ('thoracic_feline', 'Thoracic Radiograph — Feline'),
        ('thoracic_equine', 'Thoracic Radiograph — Equine'),
        ('abdominal_us', 'Abdominal Ultrasound'),
        ('orthopedic', 'Orthopedic Assessment'),
        ('dental', 'Dental Radiograph'),
        ('cardiac_vhs', 'Cardiac / VHS Report'),
        ('discharge_summary', 'Discharge Summary'),
        ('vaccination_certificate', 'Vaccination Certificate'),
        ('referral_letter', 'Specialist Referral'),
        ('soap_note', 'SOAP Clinical Note'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=255)
    template_type = models.CharField(
        max_length=30,
        choices=TEMPLATE_TYPE_CHOICES,
        default='custom',
    )
    layout = models.JSONField(
        default=dict,
        help_text="Template layout with sections, disclaimer, header_fields",
    )
    species_filter = models.JSONField(
        default=list,
        blank=True,
        help_text="Empty list = all species. Example: ['canine', 'feline']",
    )
    modality_filter = models.JSONField(
        default=list,
        blank=True,
        help_text="DICOM modality codes this template applies to. Example: ['CR', 'DX', 'US']",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="System-provided default templates cannot be deleted",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='report_templates',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'name']
        verbose_name = 'Report Template'
        verbose_name_plural = 'Report Templates'

    def __str__(self):
        return f"{self.name} ({self.template_type})"

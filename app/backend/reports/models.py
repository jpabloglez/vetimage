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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=255)
    template_type = models.CharField(
        max_length=20,
        choices=TEMPLATE_TYPE_CHOICES,
        default='custom',
    )
    layout = models.JSONField(
        default=dict,
        help_text="Template layout with sections, disclaimer, header_fields",
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

"""
Root conftest.py — Shared fixtures for all backend tests.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

User = get_user_model()


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='testuser@example.com',
        password='TestPass123!',
        role=1,
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email='otheruser@example.com',
        password='OtherPass123!',
        role=1,
    )


# ---------------------------------------------------------------------------
# API client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---------------------------------------------------------------------------
# DICOM fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def study(user):
    from dicom_images.models import MedicalStudy

    return MedicalStudy.objects.create(
        study_instance_uid='1.2.840.113619.2.55.12345',
        patient_id='PAT001',
        patient_name='DOE^JOHN',
        study_description='CT Chest',
        uploaded_by=user,
        total_size_bytes=1024,
    )


@pytest.fixture
def series(study):
    from dicom_images.models import MedicalSeries

    return MedicalSeries.objects.create(
        study=study,
        series_instance_uid='1.2.840.113619.2.55.12345.1',
        series_number=1,
        series_description='Axial',
        modality='CT',
    )


@pytest.fixture
def image(series):
    from dicom_images.models import MedicalImage

    dummy_dcm = SimpleUploadedFile(
        'test.dcm',
        b'\x00' * 256,
        content_type='application/dicom',
    )
    return MedicalImage.objects.create(
        series=series,
        sop_instance_uid='1.2.840.113619.2.55.12345.1.1',
        sop_class_uid='1.2.840.10008.5.1.4.1.1.2',
        instance_number=1,
        file=dummy_dcm,
        original_filename='test.dcm',
        file_size_bytes=256,
    )


# ---------------------------------------------------------------------------
# AI Analysis fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ai_model(db):
    from ai_analysis.models import AIModel

    return AIModel.objects.create(
        name='Test Model',
        key='test-model-v1',
        description='A test AI model',
        version='1.0',
        endpoint_url='http://test-service:8000',
        connector_class='ai_analysis.connectors.test.TestConnector',
        model_type='segmentation',
        supported_modalities=['CT', 'MR'],
        is_active=True,
        timeout_seconds=300,
        max_retries=3,
    )


@pytest.fixture
def analysis_task(user, image, ai_model):
    from ai_analysis.models import AnalysisTask

    return AnalysisTask.objects.create(
        input_image=image,
        model=ai_model,
        created_by=user,
        status='PENDING',
        parameters={'modality': 't1'},
    )


@pytest.fixture
def completed_task(user, image, ai_model):
    from ai_analysis.models import AnalysisTask
    from django.utils import timezone

    return AnalysisTask.objects.create(
        input_image=image,
        model=ai_model,
        created_by=user,
        status='COMPLETED',
        parameters={'modality': 't1'},
        result_metadata={
            'findings': [
                {'description': 'No abnormalities detected', 'confidence': 0.95},
            ],
            'confidence': {'overall': 0.95},
            'processing_time': 12.5,
        },
        completed_at=timezone.now(),
    )


@pytest.fixture
def report(completed_task, user):
    from reports.models import Report

    study = completed_task.input_image.series.study
    return Report.objects.create(
        analysis_task=completed_task,
        study=study,
        created_by=user,
        title='Test Report',
        content={
            'report_type': 'AI Analysis Report',
            'generated_at': '2026-01-01T00:00:00',
            'model_info': {'name': 'Test Model', 'version': '1.0', 'type': 'Segmentation'},
            'patient_info': {'patient_id': 'PAT001', 'patient_name': 'DOE^JOHN'},
            'sections': [
                {
                    'title': 'Findings',
                    'type': 'findings',
                    'items': [{'description': 'No abnormalities', 'confidence': 0.95}],
                }
            ],
            'summary': 'Analysis performed by Test Model.',
            'disclaimer': 'For research purposes only.',
        },
        status='DRAFT',
    )

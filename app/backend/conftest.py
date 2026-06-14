"""
Root conftest.py — Shared fixtures for all backend tests.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """
    Reset the cache before each test so DRF scoped-rate throttles (login,
    register, password_reset…) don't leak counters across tests in the same
    minute window and cause spurious 429s.
    """
    from django.core.cache import cache
    cache.clear()
    yield


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
# Veterinary patient fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def organization(db):
    from users.models import Organization, User as UserModel
    admin_user = UserModel.objects.create_user(email='org-admin@example.com', password='pass')
    return Organization.objects.create(
        user=admin_user,
        centre='Test Clinic',
        address='1 Vet Street',
        city='Testville',
        billing_address='1 Vet Street',
        billing_code='TC001',
    )


@pytest.fixture
def owner(db, organization):
    from patients.models import Owner
    return Owner.objects.create(
        organization=organization,
        first_name='Jane',
        last_name='Smith',
        email='jane.smith@example.com',
        phone='555-0100',
    )


@pytest.fixture
def animal_patient(owner):
    from patients.models import AnimalPatient
    return AnimalPatient.objects.create(
        owner=owner,
        name='Rex',
        species='canine',
        breed='Labrador Retriever',
        sex='M',
        weight_kg='30.00',
    )


@pytest.fixture
def clinical_visit(animal_patient, user):
    from patients.models import ClinicalVisit
    return ClinicalVisit.objects.create(
        animal_patient=animal_patient,
        visit_date='2026-01-15 10:00:00+00:00',
        visit_type='consultation',
        attending_vet=user,
        chief_complaint='Annual checkup',
        created_by=user,
    )


@pytest.fixture
def vaccination_record(animal_patient, user):
    from patients.models import VaccinationRecord
    return VaccinationRecord.objects.create(
        animal_patient=animal_patient,
        vaccine_name='Rabies',
        administered_on='2026-01-15',
        next_due_on='2027-01-15',
        administered_by=user,
    )


@pytest.fixture
def weight_record(animal_patient, user):
    from patients.models import WeightRecord
    return WeightRecord.objects.create(
        animal_patient=animal_patient,
        measured_on='2026-01-15',
        weight_kg='30.50',
        bcs=5,
        recorded_by=user,
    )


@pytest.fixture
def appointment(animal_patient, user):
    from patients.models import Appointment
    from django.utils import timezone
    return Appointment.objects.create(
        animal_patient=animal_patient,
        attending_vet=user,
        appointment_type='consultation',
        scheduled_at=timezone.now() + timezone.timedelta(days=3),
        created_by=user,
    )


@pytest.fixture
def prescription(animal_patient, user):
    from patients.models import Prescription
    return Prescription.objects.create(
        animal_patient=animal_patient,
        prescribed_by=user,
        prescribed_on='2026-01-15',
        medication_name='Amoxicillin',
        dose='10 mg/kg',
        route='oral',
        frequency='BID',
        duration_days=7,
    )


@pytest.fixture
def allergy_record(animal_patient, user):
    from patients.models import AllergyRecord
    return AllergyRecord.objects.create(
        animal_patient=animal_patient,
        allergen='Penicillin',
        allergen_type='drug',
        severity='severe',
        reaction='Anaphylaxis',
        recorded_by=user,
    )


@pytest.fixture
def lab_result(animal_patient, user):
    from patients.models import LabResult
    return LabResult.objects.create(
        animal_patient=animal_patient,
        requested_by=user,
        result_type='hematology',
        panel_name='CBC',
        result_date='2026-01-15',
        result_data={
            'RBC': {'value': 6.5, 'unit': 'x10⁶/µL', 'ref_low': 5.5, 'ref_high': 8.5, 'flag': 'N'},
            'WBC': {'value': 12.0, 'unit': 'x10³/µL', 'ref_low': 5.5, 'ref_high': 16.9, 'flag': 'N'},
        },
        lab_name='VetLab Inc.',
    )


@pytest.fixture
def reproductive_event(animal_patient, user):
    from patients.models import ReproductiveEvent
    return ReproductiveEvent.objects.create(
        animal_patient=animal_patient,
        event_type='heat',
        event_date='2026-01-15',
        recorded_by=user,
    )


@pytest.fixture
def breed_reference(db):
    from patients.models import BreedReference
    return BreedReference.objects.create(
        species='canine',
        breed_pattern='Boxer',
        metric='vhs',
        low='9.80',
        high='11.60',
        source='Lamb et al. 2001',
    )


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
            'patient_info': {
                'patient_name': 'Rex', 'species': 'Canine',
                'breed': 'Labrador Retriever', 'sex': 'Male', 'owner': 'Jane Smith',
            },
            'sections': [
                {
                    'title': 'Findings',
                    'type': 'findings',
                    'items': [{'description': 'No abnormalities', 'confidence': 0.95}],
                }
            ],
            'summary': 'Analysis performed by Test Model.',
            'disclaimer': 'Veterinary decision support — not a diagnosis. Vet review required.',
        },
        status='DRAFT',
    )

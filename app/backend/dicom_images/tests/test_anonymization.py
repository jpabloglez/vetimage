"""
Tests for DICOM Anonymization service and API views.
"""

import pytest
import pydicom
from pydicom.dataset import Dataset
from rest_framework.test import APIClient

from dicom_images.services.anonymization import AnonymizationService, AnonymizationProfile
from dicom_images.models import AnonymizationJob


def _make_dataset():
    """Create a minimal pydicom Dataset with PHI tags for testing."""
    ds = Dataset()
    ds.PatientName = 'DOE^JOHN'
    ds.PatientID = 'PAT001'
    ds.PatientBirthDate = '19800101'
    ds.ReferringPhysicianName = 'DR SMITH'
    ds.InstitutionName = 'Test Hospital'
    ds.PerformingPhysicianName = 'DR JONES'
    ds.OtherPatientNames = 'JOHNNY'
    # Full-profile tags
    ds.PatientSex = 'M'
    ds.PatientAge = '044Y'
    ds.AccessionNumber = 'ACC123'
    ds.OperatorsName = 'TECH1'
    # Research-profile tags
    ds.StudyInstanceUID = '1.2.3.4.5'
    ds.SeriesInstanceUID = '1.2.3.4.6'
    ds.SOPInstanceUID = '1.2.3.4.7'
    ds.StudyDate = '20240101'
    ds.is_little_endian = True
    ds.is_implicit_VR = True
    return ds


class TestAnonymizationProfiles:
    """Tests for anonymization at the dataset level."""

    def setup_method(self):
        self.service = AnonymizationService()

    def test_anonymize_dataset_basic_profile(self):
        """Basic profile removes critical direct identifiers."""
        ds = _make_dataset()
        self.service.anonymize_dataset(ds, profile='basic')

        # Direct identifiers replaced
        assert 'DOE' not in str(ds.PatientName)
        assert 'PAT001' != ds.PatientID
        assert ds.PatientName == 'ANON_PATIENT'

        # Non-basic tags should still be present
        assert hasattr(ds, 'PatientSex')
        assert hasattr(ds, 'AccessionNumber')

    def test_anonymize_dataset_full_profile(self):
        """Full profile removes all PS3.15 PHI tags."""
        ds = _make_dataset()
        self.service.anonymize_dataset(ds, profile='full')

        assert ds.PatientName == 'ANON_PATIENT'
        # Full-profile tags removed
        assert (0x0010, 0x0040) not in ds  # PatientSex
        assert (0x0008, 0x0050) not in ds  # AccessionNumber
        assert (0x0008, 0x1070) not in ds  # OperatorsName

    def test_anonymize_dataset_research_profile(self):
        """Research profile replaces UIDs and shifts dates."""
        ds = _make_dataset()
        original_study_uid = ds.StudyInstanceUID
        original_date = ds.StudyDate

        self.service.anonymize_dataset(ds, profile='research')

        # UIDs replaced
        assert ds.StudyInstanceUID != original_study_uid
        assert ds.StudyInstanceUID.startswith('2.25.')
        # Dates shifted
        assert ds.StudyDate != original_date


@pytest.mark.django_db
class TestAnonymizeStudyAndImages:
    """Tests for study-level and image-level anonymization."""

    def setup_method(self):
        self.service = AnonymizationService()

    def test_anonymize_study_creates_zip(self, study, image, user):
        """anonymize_study returns a zip path for a valid study."""
        # The image fixture uses a dummy file that isn't valid DICOM,
        # so the zip will be empty but should still be created.
        path = self.service.anonymize_study(
            study_id=study.id, profile='basic', user=user,
        )
        assert path.startswith('anonymized/')
        assert path.endswith('.zip')

    def test_anonymize_images_creates_zip(self, image, user):
        """anonymize_images returns a zip path for valid image IDs."""
        path = self.service.anonymize_images(
            image_ids=[image.id], profile='full', user=user,
        )
        assert path.startswith('anonymized/')
        assert path.endswith('.zip')


@pytest.mark.django_db
class TestAnonymizationJobAPI:
    """Tests for the anonymization job API endpoints."""

    def test_create_anonymization_job_api(self, auth_client, study):
        """Can create an anonymization job via API."""
        response = auth_client.post('/api/dicom/anonymize/', {
            'study_id': study.id,
            'profile': 'basic',
        }, format='json')
        assert response.status_code == 201
        assert response.data['status'] == 'PENDING'
        assert response.data['profile'] == 'basic'

    def test_create_anonymization_job_invalid_profile(self, auth_client, study):
        """Rejects invalid profile names."""
        response = auth_client.post('/api/dicom/anonymize/', {
            'study_id': study.id,
            'profile': 'nonexistent',
        }, format='json')
        assert response.status_code == 400

    def test_download_completed_job(self, auth_client, study, user, tmp_path):
        """Can download ZIP from a completed job."""
        import os
        from django.conf import settings
        from pathlib import Path

        # Create output directory and fake zip
        output_dir = Path(settings.MEDIA_ROOT) / 'anonymized'
        output_dir.mkdir(parents=True, exist_ok=True)
        zip_path = output_dir / 'test_download.zip'
        zip_path.write_bytes(b'PK\x03\x04fake')

        job = AnonymizationJob.objects.create(
            study=study,
            profile='basic',
            status='COMPLETED',
            result_file_path='anonymized/test_download.zip',
            created_by=user,
        )

        response = auth_client.get(f'/api/dicom/anonymize/{job.id}/download/')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/zip'

        # Cleanup
        zip_path.unlink(missing_ok=True)

    def test_download_pending_job(self, auth_client, study, user):
        """Cannot download from a pending job."""
        job = AnonymizationJob.objects.create(
            study=study,
            profile='basic',
            status='PENDING',
            created_by=user,
        )
        response = auth_client.get(f'/api/dicom/anonymize/{job.id}/download/')
        assert response.status_code == 400

    def test_anonymization_respects_ownership(self, study, other_user):
        """Cannot create a job for another user's study."""
        client = APIClient()
        client.force_authenticate(user=other_user)
        response = client.post('/api/dicom/anonymize/', {
            'study_id': study.id,
            'profile': 'basic',
        }, format='json')
        assert response.status_code == 400

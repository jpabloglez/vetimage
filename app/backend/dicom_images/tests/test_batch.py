"""
Tests for the Batch Operations service and API views.
"""

import pytest
from pathlib import Path
from rest_framework.test import APIClient

from dicom_images.models import BatchJob, MedicalStudy
from dicom_images.services.batch_operations import BatchOperationService


@pytest.mark.django_db
class TestBatchOperationService:

    def test_delete_single(self, study, user):
        """batch_delete removes a single study."""
        service = BatchOperationService()
        count = service.batch_delete([study.id], user)
        assert count == 1
        assert not MedicalStudy.objects.filter(id=study.id).exists()

    def test_delete_multiple(self, user):
        """batch_delete removes multiple studies."""
        s1 = MedicalStudy.objects.create(
            study_instance_uid='1.2.3.100', patient_id='P1', uploaded_by=user,
        )
        s2 = MedicalStudy.objects.create(
            study_instance_uid='1.2.3.200', patient_id='P2', uploaded_by=user,
        )
        service = BatchOperationService()
        count = service.batch_delete([s1.id, s2.id], user)
        assert count == 2

    def test_delete_ownership(self, study, other_user):
        """batch_delete ignores studies not owned by user."""
        service = BatchOperationService()
        count = service.batch_delete([study.id], other_user)
        assert count == 0
        assert MedicalStudy.objects.filter(id=study.id).exists()

    def test_export_zip(self, study, image, user):
        """batch_export creates a ZIP file."""
        service = BatchOperationService()
        path = service.batch_export([study.id], user)
        assert path.startswith('exports/')
        assert path.endswith('.zip')

    def test_empty_list(self, user):
        """batch_delete with empty list deletes nothing."""
        service = BatchOperationService()
        count = service.batch_delete([], user)
        assert count == 0


@pytest.mark.django_db
class TestBatchJobAPI:

    def test_create_export_job(self, auth_client, study):
        """Can create an export batch job via API."""
        response = auth_client.post('/api/dicom/batch/', {
            'study_ids': [study.id],
            'operation': 'export',
        }, format='json')
        assert response.status_code == 201
        assert response.data['status'] == 'PENDING'
        assert response.data['operation'] == 'export'

    def test_create_analyze_requires_model_key(self, auth_client, study):
        """Analyze operation requires model_key."""
        response = auth_client.post('/api/dicom/batch/', {
            'study_ids': [study.id],
            'operation': 'analyze',
        }, format='json')
        assert response.status_code == 400

    def test_download_export(self, auth_client, study, user):
        """Can download ZIP from a completed export job."""
        from django.conf import settings

        output_dir = Path(settings.MEDIA_ROOT) / 'exports'
        output_dir.mkdir(parents=True, exist_ok=True)
        zip_path = output_dir / 'test_export.zip'
        zip_path.write_bytes(b'PK\x03\x04fake')

        job = BatchJob.objects.create(
            operation='export',
            study_ids=[study.id],
            status='COMPLETED',
            result_file_path='exports/test_export.zip',
            created_by=user,
        )

        response = auth_client.get(f'/api/dicom/batch/{job.id}/download/')
        assert response.status_code == 200

        zip_path.unlink(missing_ok=True)

    def test_status_transitions(self, auth_client, study, user):
        """Job starts as PENDING."""
        job = BatchJob.objects.create(
            operation='export',
            study_ids=[study.id],
            status='PENDING',
            created_by=user,
        )
        response = auth_client.get(f'/api/dicom/batch/{job.id}/')
        assert response.status_code == 200
        assert response.data['status'] == 'PENDING'

    def test_ownership(self, study, other_user):
        """Cannot create batch job for another user's study."""
        client = APIClient()
        client.force_authenticate(user=other_user)
        response = client.post('/api/dicom/batch/', {
            'study_ids': [study.id],
            'operation': 'export',
        }, format='json')
        assert response.status_code == 400

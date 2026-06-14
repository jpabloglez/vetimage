"""
Tests for the Format Conversion service and API views.
"""

import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from pathlib import Path
from rest_framework.test import APIClient

from dicom_images.models import ConversionJob
from dicom_images.services.format_conversion import FormatConversionService


@pytest.mark.django_db
class TestFormatConversionService:

    def test_invalid_format_rejected(self, image, user):
        """convert_dicom_to_image rejects unsupported formats."""
        service = FormatConversionService()
        with pytest.raises(ValueError, match='Unsupported'):
            service.convert_dicom_to_image(image.id, 'bmp', user)

    @patch('dicom_images.services.format_conversion.pydicom.dcmread')
    @patch('dicom_images.services.format_conversion.dicom_to_image')
    def test_dicom_to_jpeg(self, mock_convert, mock_dcmread, image, user):
        """convert_dicom_to_image returns a BytesIO for JPEG."""
        mock_dcmread.return_value = MagicMock()
        mock_convert.return_value = BytesIO(b'\xff\xd8\xff')

        service = FormatConversionService()
        result = service.convert_dicom_to_image(image.id, 'jpeg', user)
        assert isinstance(result, BytesIO)

    @patch('dicom_images.services.format_conversion.pydicom.dcmread')
    @patch('dicom_images.services.format_conversion.dicom_to_image')
    def test_dicom_to_png(self, mock_convert, mock_dcmread, image, user):
        """convert_dicom_to_image returns a BytesIO for PNG."""
        mock_dcmread.return_value = MagicMock()
        mock_convert.return_value = BytesIO(b'\x89PNG')

        service = FormatConversionService()
        result = service.convert_dicom_to_image(image.id, 'png', user)
        assert isinstance(result, BytesIO)

    def test_ownership_check(self, image, other_user):
        """Cannot convert images owned by another user."""
        from dicom_images.models import MedicalImage
        service = FormatConversionService()
        with pytest.raises(MedicalImage.DoesNotExist):
            service.convert_dicom_to_image(image.id, 'jpeg', other_user)


@pytest.mark.django_db
class TestConversionJobAPI:

    def test_create_conversion_job_api(self, auth_client, study):
        """Can create a conversion job via API."""
        response = auth_client.post('/api/dicom/convert/', {
            'study_id': study.id,
            'target_format': 'jpeg',
        }, format='json')
        assert response.status_code == 201
        assert response.data['status'] == 'PENDING'
        assert response.data['target_format'] == 'jpeg'

    def test_create_conversion_job_invalid_format(self, auth_client, study):
        """Rejects invalid target format."""
        response = auth_client.post('/api/dicom/convert/', {
            'study_id': study.id,
            'target_format': 'bmp',
        }, format='json')
        assert response.status_code == 400

    def test_download_completed_job(self, auth_client, study, user):
        """Can download output from a completed job."""
        from django.conf import settings

        output_dir = Path(settings.MEDIA_ROOT) / 'converted'
        output_dir.mkdir(parents=True, exist_ok=True)
        zip_path = output_dir / 'test_convert.zip'
        zip_path.write_bytes(b'PK\x03\x04fake')

        job = ConversionJob.objects.create(
            study=study,
            target_format='jpeg',
            status='COMPLETED',
            result_file_path='converted/test_convert.zip',
            created_by=user,
        )

        response = auth_client.get(f'/api/dicom/convert/{job.id}/download/')
        assert response.status_code == 200

        zip_path.unlink(missing_ok=True)

    def test_download_pending_fails(self, auth_client, study, user):
        """Cannot download from a pending job."""
        job = ConversionJob.objects.create(
            study=study,
            target_format='jpeg',
            status='PENDING',
            created_by=user,
        )
        response = auth_client.get(f'/api/dicom/convert/{job.id}/download/')
        assert response.status_code == 400

    def test_ownership(self, study, other_user):
        """Cannot create job for another user's study."""
        client = APIClient()
        client.force_authenticate(user=other_user)
        response = client.post('/api/dicom/convert/', {
            'study_id': study.id,
            'target_format': 'jpeg',
        }, format='json')
        assert response.status_code == 400

    def test_list_jobs(self, auth_client, study, user):
        """Can list user's conversion jobs."""
        ConversionJob.objects.create(
            study=study, target_format='jpeg',
            status='PENDING', created_by=user,
        )
        response = auth_client.get('/api/dicom/convert/')
        assert response.status_code == 200
        assert len(response.data['results']) >= 1

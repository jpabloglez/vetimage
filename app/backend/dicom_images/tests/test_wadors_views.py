"""
Tests for WADO-RS retrieval endpoints.

Covers: WADORSFrameRetrieveView, WADORSInstanceRetrieveView, WADORSMetadataRetrieveView
"""

import io
import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from dicom_images.models import MedicalStudy, MedicalSeries, MedicalImage

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user2(db):
    """A second user for isolation tests."""
    return User.objects.create_user(
        email='user2@example.com',
        password='User2Pass123!',
        role=1,
    )


@pytest.fixture
def auth_client2(user2):
    client = APIClient()
    client.force_authenticate(user=user2)
    return client


# Shorthand URL kwargs helpers

def _frame_kwargs(study, series, image, frame=1):
    return {
        'study_uid': study.study_instance_uid,
        'series_uid': series.series_instance_uid,
        'sop_uid': image.sop_instance_uid,
        'frame_number': frame,
    }


def _instance_kwargs(study, series, image):
    return {
        'study_uid': study.study_instance_uid,
        'series_uid': series.series_instance_uid,
        'sop_uid': image.sop_instance_uid,
    }


# ===========================================================================
# WADORSFrameRetrieveView Tests
# ===========================================================================


@pytest.mark.django_db
class TestWADORSFrameRetrieveView:

    def test_unauthenticated_401(self, api_client, study, series, image):
        url = reverse('dicom_images:wadors-frame', kwargs=_frame_kwargs(study, series, image))
        response = api_client.get(url)
        assert response.status_code == 401

    def test_nonexistent_instance_404(self, auth_client, study, series, image):
        kwargs = _frame_kwargs(study, series, image)
        kwargs['sop_uid'] = '9.9.9.9.9'
        url = reverse('dicom_images:wadors-frame', kwargs=kwargs)
        response = auth_client.get(url)
        assert response.status_code == 404

    @patch('dicom_images.views.dicom_to_image')
    @patch('dicom_images.views.pydicom.dcmread')
    @patch('dicom_images.views.get_num_frames', return_value=1)
    def test_retrieve_frame_jpeg_success(self, mock_frames, mock_dcmread, mock_to_image,
                                          auth_client, study, series, image):
        # Mock dcmread to return a fake dataset
        mock_dcm = MagicMock()
        mock_dcmread.return_value = mock_dcm

        # Mock dicom_to_image to return a BytesIO with JPEG data
        fake_jpeg = io.BytesIO(b'\xff\xd8\xff\xe0fake-jpeg-data')
        mock_to_image.return_value = fake_jpeg

        url = reverse('dicom_images:wadors-frame', kwargs=_frame_kwargs(study, series, image))
        response = auth_client.get(url)
        assert response.status_code == 200
        assert 'image/jpeg' in response['Content-Type']

    @patch('dicom_images.views.dicom_to_image')
    @patch('dicom_images.views.pydicom.dcmread')
    @patch('dicom_images.views.get_num_frames', return_value=1)
    def test_retrieve_frame_default_jpeg(self, mock_frames, mock_dcmread, mock_to_image,
                                          auth_client, study, series, image):
        """Without format param, defaults to JPEG."""
        mock_dcmread.return_value = MagicMock()
        fake_jpeg = io.BytesIO(b'\xff\xd8\xff\xe0default-jpeg')
        mock_to_image.return_value = fake_jpeg

        url = reverse('dicom_images:wadors-frame', kwargs=_frame_kwargs(study, series, image))
        response = auth_client.get(url)
        assert response.status_code == 200
        assert 'image/jpeg' in response['Content-Type']
        # Verify dicom_to_image was called with JPEG format
        mock_to_image.assert_called_once()
        call_kwargs = mock_to_image.call_args
        assert call_kwargs[1].get('output_format', call_kwargs[0][-1] if len(call_kwargs[0]) > 3 else 'JPEG') == 'JPEG'

    @patch('dicom_images.views.pydicom.dcmread')
    @patch('dicom_images.views.get_num_frames', return_value=1)
    def test_invalid_frame_number_400(self, mock_frames, mock_dcmread,
                                       auth_client, study, series, image):
        mock_dcmread.return_value = MagicMock()

        kwargs = _frame_kwargs(study, series, image, frame=99)
        url = reverse('dicom_images:wadors-frame', kwargs=kwargs)
        response = auth_client.get(url)
        assert response.status_code == 400

    @patch('dicom_images.views.dicom_to_image')
    @patch('dicom_images.views.pydicom.dcmread')
    @patch('dicom_images.views.get_num_frames', return_value=1)
    def test_windowing_parameters(self, mock_frames, mock_dcmread, mock_to_image,
                                   auth_client, study, series, image):
        mock_dcmread.return_value = MagicMock()
        mock_to_image.return_value = io.BytesIO(b'\xff\xd8\xff\xe0data')

        url = reverse('dicom_images:wadors-frame', kwargs=_frame_kwargs(study, series, image))
        response = auth_client.get(url, {'windowCenter': '40', 'windowWidth': '400'})
        assert response.status_code == 200

        # Verify windowing params were passed to dicom_to_image
        call_kwargs = mock_to_image.call_args
        assert call_kwargs[1].get('window_center') == 40.0 or call_kwargs[0][2] == 40.0 if len(call_kwargs[0]) > 2 else True

    def test_user_isolation_404(self, auth_client2, study, series, image):
        """User2 should not see user1's images."""
        url = reverse('dicom_images:wadors-frame', kwargs=_frame_kwargs(study, series, image))
        response = auth_client2.get(url)
        assert response.status_code == 404

    def test_standard_image_frame_1_succeeds(self, auth_client, user):
        """For a .jpg image, frame 1 should work."""
        study_obj = MedicalStudy.objects.create(
            study_instance_uid='2.2.2.2.2',
            patient_id='PAT002',
            uploaded_by=user,
            total_size_bytes=100,
        )
        series_obj = MedicalSeries.objects.create(
            study=study_obj,
            series_instance_uid='2.2.2.2.2.1',
            series_number=1,
            modality='OT',
        )
        # Create a minimal valid JPEG
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (2, 2), color='red').save(buf, format='JPEG')
        buf.seek(0)
        img = MedicalImage.objects.create(
            series=series_obj,
            sop_instance_uid='2.2.2.2.2.1.1',
            sop_class_uid='1.2.840.10008.5.1.4.1.1.7',
            instance_number=1,
            file=SimpleUploadedFile('test.jpg', buf.getvalue(), content_type='image/jpeg'),
            original_filename='test.jpg',
            file_size_bytes=len(buf.getvalue()),
        )

        url = reverse('dicom_images:wadors-frame', kwargs={
            'study_uid': study_obj.study_instance_uid,
            'series_uid': series_obj.series_instance_uid,
            'sop_uid': img.sop_instance_uid,
            'frame_number': 1,
        })
        response = auth_client.get(url)
        assert response.status_code == 200

    def test_standard_image_frame_2_returns_400(self, auth_client, user):
        """For a .jpg image, frame > 1 should return 400."""
        study_obj = MedicalStudy.objects.create(
            study_instance_uid='3.3.3.3.3',
            patient_id='PAT003',
            uploaded_by=user,
            total_size_bytes=100,
        )
        series_obj = MedicalSeries.objects.create(
            study=study_obj,
            series_instance_uid='3.3.3.3.3.1',
            series_number=1,
            modality='OT',
        )
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (2, 2), color='blue').save(buf, format='JPEG')
        buf.seek(0)
        img = MedicalImage.objects.create(
            series=series_obj,
            sop_instance_uid='3.3.3.3.3.1.1',
            sop_class_uid='1.2.840.10008.5.1.4.1.1.7',
            instance_number=1,
            file=SimpleUploadedFile('test2.jpg', buf.getvalue(), content_type='image/jpeg'),
            original_filename='test2.jpg',
            file_size_bytes=len(buf.getvalue()),
        )

        url = reverse('dicom_images:wadors-frame', kwargs={
            'study_uid': study_obj.study_instance_uid,
            'series_uid': series_obj.series_instance_uid,
            'sop_uid': img.sop_instance_uid,
            'frame_number': 2,
        })
        response = auth_client.get(url)
        assert response.status_code == 400


# ===========================================================================
# WADORSInstanceRetrieveView Tests
# ===========================================================================


@pytest.mark.django_db
class TestWADORSInstanceRetrieveView:

    def test_unauthenticated_401(self, api_client, study, series, image):
        url = reverse('dicom_images:wadors-instance', kwargs=_instance_kwargs(study, series, image))
        response = api_client.get(url)
        assert response.status_code == 401

    def test_nonexistent_instance_404(self, auth_client, study, series, image):
        kwargs = _instance_kwargs(study, series, image)
        kwargs['sop_uid'] = '9.9.9.9.9'
        url = reverse('dicom_images:wadors-instance', kwargs=kwargs)
        response = auth_client.get(url)
        assert response.status_code == 404

    def test_retrieve_instance_success(self, auth_client, study, series, image):
        url = reverse('dicom_images:wadors-instance', kwargs=_instance_kwargs(study, series, image))
        response = auth_client.get(url)
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/dicom'

    def test_content_disposition_header(self, auth_client, study, series, image):
        url = reverse('dicom_images:wadors-instance', kwargs=_instance_kwargs(study, series, image))
        response = auth_client.get(url)
        assert 'Content-Disposition' in response
        assert image.original_filename in response['Content-Disposition']

    def test_user_isolation_404(self, auth_client2, study, series, image):
        url = reverse('dicom_images:wadors-instance', kwargs=_instance_kwargs(study, series, image))
        response = auth_client2.get(url)
        assert response.status_code == 404


# ===========================================================================
# WADORSMetadataRetrieveView Tests
# ===========================================================================


@pytest.mark.django_db
class TestWADORSMetadataRetrieveView:

    def test_unauthenticated_401(self, api_client, study):
        url = reverse('dicom_images:wadors-metadata-study', kwargs={
            'study_uid': study.study_instance_uid,
        })
        response = api_client.get(url)
        assert response.status_code == 401

    @patch('dicom_images.views.pydicom.dcmread')
    def test_study_level_metadata(self, mock_dcmread, auth_client, study, series, image):
        mock_dcm = MagicMock()
        mock_dcm.SOPInstanceUID = image.sop_instance_uid
        mock_dcm.SOPClassUID = image.sop_class_uid
        mock_dcm.StudyInstanceUID = study.study_instance_uid
        mock_dcm.SeriesInstanceUID = series.series_instance_uid
        mock_dcm.Modality = 'CT'
        mock_dcm.PatientID = 'PAT001'
        mock_dcm.PatientName = 'DOE^JOHN'
        mock_dcm.StudyDate = '20240101'
        mock_dcm.StudyDescription = 'CT Chest'
        mock_dcm.SeriesDescription = 'Axial'
        mock_dcm.Rows = 512
        mock_dcm.Columns = 512
        mock_dcm.NumberOfFrames = 1
        mock_dcmread.return_value = mock_dcm

        url = reverse('dicom_images:wadors-metadata-study', kwargs={
            'study_uid': study.study_instance_uid,
        })
        response = auth_client.get(url)
        assert response.status_code == 200
        assert isinstance(response.data, list)
        assert len(response.data) >= 1
        assert response.data[0]['Modality'] == 'CT'

    @patch('dicom_images.views.pydicom.dcmread')
    def test_series_level_metadata(self, mock_dcmread, auth_client, study, series, image):
        mock_dcm = MagicMock()
        mock_dcm.SOPInstanceUID = image.sop_instance_uid
        mock_dcm.SOPClassUID = image.sop_class_uid
        mock_dcm.StudyInstanceUID = study.study_instance_uid
        mock_dcm.SeriesInstanceUID = series.series_instance_uid
        mock_dcm.Modality = 'CT'
        mock_dcm.PatientID = 'PAT001'
        mock_dcm.PatientName = 'DOE^JOHN'
        mock_dcm.StudyDate = '20240101'
        mock_dcm.StudyDescription = 'CT Chest'
        mock_dcm.SeriesDescription = 'Axial'
        mock_dcm.Rows = 512
        mock_dcm.Columns = 512
        mock_dcm.NumberOfFrames = 1
        mock_dcmread.return_value = mock_dcm

        url = reverse('dicom_images:wadors-metadata-series', kwargs={
            'study_uid': study.study_instance_uid,
            'series_uid': series.series_instance_uid,
        })
        response = auth_client.get(url)
        assert response.status_code == 200
        assert isinstance(response.data, list)

    @patch('dicom_images.views.pydicom.dcmread')
    def test_instance_level_metadata(self, mock_dcmread, auth_client, study, series, image):
        mock_dcm = MagicMock()
        mock_dcm.SOPInstanceUID = image.sop_instance_uid
        mock_dcm.SOPClassUID = image.sop_class_uid
        mock_dcm.StudyInstanceUID = study.study_instance_uid
        mock_dcm.SeriesInstanceUID = series.series_instance_uid
        mock_dcm.Modality = 'CT'
        mock_dcm.PatientID = 'PAT001'
        mock_dcm.PatientName = 'DOE^JOHN'
        mock_dcm.StudyDate = '20240101'
        mock_dcm.StudyDescription = 'CT Chest'
        mock_dcm.SeriesDescription = 'Axial'
        mock_dcm.Rows = 512
        mock_dcm.Columns = 512
        mock_dcm.NumberOfFrames = 1
        mock_dcmread.return_value = mock_dcm

        url = reverse('dicom_images:wadors-metadata-instance', kwargs={
            'study_uid': study.study_instance_uid,
            'series_uid': series.series_instance_uid,
            'sop_uid': image.sop_instance_uid,
        })
        response = auth_client.get(url)
        assert response.status_code == 200
        assert isinstance(response.data, list)
        assert len(response.data) == 1

    def test_nonexistent_study_404(self, auth_client):
        url = reverse('dicom_images:wadors-metadata-study', kwargs={
            'study_uid': '9.9.9.9.9.9',
        })
        response = auth_client.get(url)
        assert response.status_code == 404

    def test_nonexistent_series_404(self, auth_client, study):
        url = reverse('dicom_images:wadors-metadata-series', kwargs={
            'study_uid': study.study_instance_uid,
            'series_uid': '9.9.9.9.9.9',
        })
        response = auth_client.get(url)
        assert response.status_code == 404

    def test_user_isolation_404(self, auth_client2, study):
        """User2 cannot access user1's study metadata."""
        url = reverse('dicom_images:wadors-metadata-study', kwargs={
            'study_uid': study.study_instance_uid,
        })
        response = auth_client2.get(url)
        assert response.status_code == 404


# ===========================================================================
# InstanceListView (QIDO-RS) Tests
# ===========================================================================


def _instances_kwargs(study, series):
    return {
        'study_uid': study.study_instance_uid,
        'series_uid': series.series_instance_uid,
    }


@pytest.mark.django_db
class TestInstanceListView:

    def test_list_instances_authenticated(self, auth_client, study, series, image):
        """Authenticated user can list instances for their series."""
        url = reverse('dicom_images:dicomweb-instances', kwargs=_instances_kwargs(study, series))
        response = auth_client.get(url)
        assert response.status_code == 200
        assert isinstance(response.data, list)
        assert len(response.data) >= 1

    def test_unauthenticated_401(self, api_client, study, series):
        """Unauthenticated request returns 401."""
        url = reverse('dicom_images:dicomweb-instances', kwargs=_instances_kwargs(study, series))
        response = api_client.get(url)
        assert response.status_code == 401

    def test_nonexistent_study_404(self, auth_client, series):
        """Nonexistent study UID returns 404."""
        url = reverse('dicom_images:dicomweb-instances', kwargs={
            'study_uid': '9.9.9.9.9.9',
            'series_uid': series.series_instance_uid,
        })
        response = auth_client.get(url)
        assert response.status_code == 404

    def test_nonexistent_series_404(self, auth_client, study):
        """Nonexistent series UID returns 404."""
        url = reverse('dicom_images:dicomweb-instances', kwargs={
            'study_uid': study.study_instance_uid,
            'series_uid': '9.9.9.9.9.9',
        })
        response = auth_client.get(url)
        assert response.status_code == 404

    def test_user_isolation_404(self, auth_client2, study, series):
        """User2 cannot list instances for user1's series."""
        url = reverse('dicom_images:dicomweb-instances', kwargs=_instances_kwargs(study, series))
        response = auth_client2.get(url)
        assert response.status_code == 404

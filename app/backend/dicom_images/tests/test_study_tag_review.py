"""
Tests for the study-level DICOM tag review step (confirm/correct
PatientName/PatientID/AccessionNumber across a whole study after upload).
"""

import pytest
from unittest.mock import patch, MagicMock

from dicom_images.services.study_tag_review import StudyTagReviewService


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStudyTagReviewService:

    def test_get_review_fields(self, study):
        service = StudyTagReviewService()
        fields = service.get_review_fields(study)
        assert fields == {
            'patient_name': 'DOE^JOHN',
            'patient_id': 'PAT001',
            'accession_number': '',
        }

    @patch('dicom_images.services.study_tag_review.pydicom.dcmread')
    def test_update_writes_db_and_files(self, mock_dcmread, study, image):
        mock_dcm = MagicMock()
        mock_dcm.__contains__ = MagicMock(return_value=True)
        mock_dcmread.return_value = mock_dcm

        with patch('dicom_images.services.study_tag_review.extract_all_dicom_tags') as mock_extract:
            mock_extract.return_value = {'00100020': {'value': 'REX-001'}}
            service = StudyTagReviewService()
            files_updated, files_total = service.update_review_fields(
                study, {'patient_name': 'Rex', 'patient_id': 'REX-001'},
            )

        assert files_updated == 1
        assert files_total == 1
        mock_dcm.save_as.assert_called_once()

        study.refresh_from_db()
        assert study.patient_name == 'Rex'
        assert study.patient_id == 'REX-001'
        assert study.patient_name_normalized == 'rex'

        image.refresh_from_db()
        assert image.dicom_tags == {'00100020': {'value': 'REX-001'}}

    def test_update_partial_leaves_other_fields_untouched(self, study):
        service = StudyTagReviewService()
        service.update_review_fields(study, {'accession_number': 'ACC-42'})

        study.refresh_from_db()
        assert study.accession_number == 'ACC-42'
        assert study.patient_name == 'DOE^JOHN'  # unchanged
        assert study.patient_id == 'PAT001'  # unchanged

    def test_update_survives_unreadable_file(self, study, image):
        """A file that can't be parsed shouldn't block the DB-level update."""
        service = StudyTagReviewService()
        files_updated, files_total = service.update_review_fields(
            study, {'patient_id': 'REX-001'},
        )

        # `image` fixture's file is dummy zero bytes — not valid DICOM.
        assert files_total == 1
        assert files_updated == 0

        study.refresh_from_db()
        assert study.patient_id == 'REX-001'


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestStudyTagReviewAPI:

    def _url(self, study):
        return f'/api/dicom/studies/{study.study_instance_uid}/tags/'

    def test_get_returns_current_fields(self, auth_client, study):
        resp = auth_client.get(self._url(study))
        assert resp.status_code == 200
        assert resp.data == {
            'patient_name': 'DOE^JOHN',
            'patient_id': 'PAT001',
            'accession_number': '',
        }

    def test_patch_updates_study(self, auth_client, study):
        resp = auth_client.patch(
            self._url(study), {'patient_name': 'Rex', 'patient_id': 'REX-001'}, format='json',
        )
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['patient_name'] == 'Rex'

        study.refresh_from_db()
        assert study.patient_name == 'Rex'
        assert study.patient_id == 'REX-001'

    def test_patch_rejects_empty_body(self, auth_client, study):
        resp = auth_client.patch(self._url(study), {}, format='json')
        assert resp.status_code == 400

    def test_get_rejects_other_users_study(self, auth_client, other_user):
        from dicom_images.models import MedicalStudy

        other_study = MedicalStudy.objects.create(
            study_instance_uid='1.2.840.113619.2.55.99999',
            patient_id='OTHER',
            patient_name='NOBODY',
            uploaded_by=other_user,
        )
        resp = auth_client.get(self._url(other_study))
        assert resp.status_code == 404

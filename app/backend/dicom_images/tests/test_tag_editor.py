"""
Tests for the DICOM Tag Editor service and API views.
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient

from dicom_images.services.tag_editor import DicomTagEditorService, RESTRICTED_TAGS


# ---------------------------------------------------------------------------
# Service-level tests (no file I/O needed)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDicomTagEditorService:

    def test_get_tags_returns_json(self, image, user):
        """get_tags returns the dicom_tags field content."""
        image.dicom_tags = {
            '00100020': {'vr': 'LO', 'name': 'PatientID', 'value': 'PAT001'},
            '00100010': {'vr': 'PN', 'name': 'PatientName', 'value': 'DOE^JOHN'},
        }
        image.save(update_fields=['dicom_tags'])

        service = DicomTagEditorService()
        tags = service.get_tags(image.id, user)

        assert '00100020' in tags
        assert tags['00100020']['value'] == 'PAT001'

    def test_search_filter(self, image, user):
        """get_tags with search param filters tags by name/key."""
        image.dicom_tags = {
            '00100020': {'vr': 'LO', 'name': 'PatientID', 'value': 'PAT001'},
            '00100010': {'vr': 'PN', 'name': 'PatientName', 'value': 'DOE^JOHN'},
            '00080060': {'vr': 'CS', 'name': 'Modality', 'value': 'CT'},
        }
        image.save(update_fields=['dicom_tags'])

        service = DicomTagEditorService()
        tags = service.get_tags(image.id, user, search='Patient')

        assert '00100020' in tags
        assert '00100010' in tags
        assert '00080060' not in tags

    def test_ownership_check(self, image, other_user):
        """get_tags raises DoesNotExist for non-owner."""
        from dicom_images.models import MedicalImage

        service = DicomTagEditorService()
        with pytest.raises(MedicalImage.DoesNotExist):
            service.get_tags(image.id, other_user)

    @patch('dicom_images.services.tag_editor.pydicom.dcmread')
    def test_update_valid(self, mock_dcmread, image, user):
        """update_tags writes to file and refreshes JSONField."""
        mock_dcm = MagicMock()
        mock_tag = MagicMock()
        mock_dcm.__contains__ = MagicMock(return_value=True)
        mock_dcm.__getitem__ = MagicMock(return_value=mock_tag)
        mock_dcmread.return_value = mock_dcm

        with patch('dicom_images.services.tag_editor.extract_all_dicom_tags') as mock_extract:
            mock_extract.return_value = {'00100020': {'vr': 'LO', 'name': 'PatientID', 'value': 'NEW'}}
            service = DicomTagEditorService()
            tags = service.update_tags(image.id, [{'tag': '00100020', 'value': 'NEW'}], user)

        assert tags['00100020']['value'] == 'NEW'
        mock_dcm.save_as.assert_called_once()

    def test_invalid_hex_rejected(self, image, user):
        """update_tags rejects non-hex tag strings."""
        service = DicomTagEditorService()
        with pytest.raises(ValueError, match='not a valid'):
            service.update_tags(image.id, [{'tag': 'ZZZZZZZZ', 'value': 'x'}], user)

    def test_readonly_pixel_data(self, image, user):
        """update_tags rejects changes to pixel data tag."""
        service = DicomTagEditorService()
        with pytest.raises(ValueError, match='restricted'):
            service.update_tags(image.id, [{'tag': '7FE00010', 'value': 'x'}], user)


# ---------------------------------------------------------------------------
# API-level tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDicomTagEditorAPI:

    def test_get_tags_api(self, auth_client, image):
        """GET returns tags JSON."""
        image.dicom_tags = {
            '00100020': {'vr': 'LO', 'name': 'PatientID', 'value': 'PAT001'},
        }
        image.save(update_fields=['dicom_tags'])

        response = auth_client.get(f'/api/dicom/images/{image.id}/tags/')
        assert response.status_code == 200
        assert '00100020' in response.data['tags']

    def test_update_tags_api_invalid_hex(self, auth_client, image):
        """PATCH rejects invalid hex tags."""
        response = auth_client.patch(
            f'/api/dicom/images/{image.id}/tags/update/',
            {'tags': [{'tag': 'BADTAG', 'value': 'x'}]},
            format='json',
        )
        assert response.status_code == 400

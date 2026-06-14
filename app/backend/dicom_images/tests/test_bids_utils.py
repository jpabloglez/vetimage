"""
Unit tests for dicom_images/services/bids_utils.py

Covers: sanitize_bids_json, infer_bids_datatype, bids_filename_stem,
run_dcm2niix (mocked), and the output_format API field.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dicom_images.services.bids_utils import (
    BIDS_JSON_PHI_KEYS,
    bids_filename_stem,
    infer_bids_datatype,
    sanitize_bids_json,
)


# ---------------------------------------------------------------------------
# sanitize_bids_json
# ---------------------------------------------------------------------------

class TestSanitizeBidsJson:

    def test_removes_all_phi_keys(self, tmp_path):
        """All keys listed in BIDS_JSON_PHI_KEYS are stripped."""
        data = {key: f"sensitive_{key}" for key in BIDS_JSON_PHI_KEYS}
        data['Manufacturer'] = 'Siemens'
        data['MagneticFieldStrength'] = 3.0

        json_file = tmp_path / 'sidecar.json'
        json_file.write_text(json.dumps(data))

        cleaned = sanitize_bids_json(json_file)

        for phi_key in BIDS_JSON_PHI_KEYS:
            assert phi_key not in cleaned, f"{phi_key} was not removed"

    def test_preserves_non_phi_keys(self, tmp_path):
        """Technical parameters are kept."""
        data = {
            'PatientName': 'DOE^JOHN',  # PHI
            'Manufacturer': 'Siemens',  # safe
            'MagneticFieldStrength': 3.0,  # safe
            'RepetitionTime': 2500,  # safe
        }
        json_file = tmp_path / 'sidecar.json'
        json_file.write_text(json.dumps(data))

        cleaned = sanitize_bids_json(json_file)

        assert cleaned['Manufacturer'] == 'Siemens'
        assert cleaned['MagneticFieldStrength'] == 3.0
        assert cleaned['RepetitionTime'] == 2500

    def test_empty_json_stays_empty(self, tmp_path):
        json_file = tmp_path / 'empty.json'
        json_file.write_text('{}')
        assert sanitize_bids_json(json_file) == {}

    def test_returns_dict(self, tmp_path):
        json_file = tmp_path / 'sidecar.json'
        json_file.write_text(json.dumps({'Modality': 'MR'}))
        result = sanitize_bids_json(json_file)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# infer_bids_datatype
# ---------------------------------------------------------------------------

class TestInferBidsDatatype:

    @pytest.mark.parametrize("modality,expected", [
        ('MR', 'anat'),
        ('CT', 'anat'),
        ('PT', 'anat'),
        ('cr', 'anat'),   # lowercase
        ('DX', 'anat'),
        ('NM', 'pet'),
        ('',   'anat'),   # unknown defaults to anat
        ('XYZ', 'anat'),  # unknown defaults to anat
    ])
    def test_modality_mapping(self, modality, expected):
        assert infer_bids_datatype(modality) == expected


# ---------------------------------------------------------------------------
# bids_filename_stem
# ---------------------------------------------------------------------------

class TestBidsFilenameStem:

    def test_basic_structure(self):
        stem = bids_filename_stem('STUDY001', 'T1w Axial', 'MR', 1)
        assert stem.startswith('sub-STUDY001_run-01_')

    def test_run_index_zero_padded(self):
        stem = bids_filename_stem('P001', 'FLAIR', 'MR', 5)
        assert '_run-05_' in stem

    def test_strips_special_chars_from_description(self):
        stem = bids_filename_stem('P001', 'T1w: Axial (3mm)', 'MR', 1)
        # Colons, spaces, parentheses must not appear in stem
        for illegal in [':', ' ', '(', ')']:
            assert illegal not in stem

    def test_empty_description_uses_modality(self):
        stem = bids_filename_stem('P001', '', 'CT', 1)
        assert stem.endswith('CT')

    def test_none_description_uses_modality(self):
        stem = bids_filename_stem('P001', None, 'MR', 2)
        assert stem.endswith('MR')

    def test_prefix_embedded(self):
        stem = bids_filename_stem('TESTPFX', 'T2', 'MR', 1)
        assert 'TESTPFX' in stem


# ---------------------------------------------------------------------------
# run_dcm2niix (mocked)
# ---------------------------------------------------------------------------

class TestRunDcm2niix:

    def test_returns_nii_files_on_success(self, tmp_path):
        from dicom_images.services.bids_utils import run_dcm2niix

        dicom_dir = tmp_path / 'dicoms'
        dicom_dir.mkdir()
        out_dir = tmp_path / 'output'
        out_dir.mkdir()

        # Create a fake .nii.gz to simulate dcm2niix output
        fake_nii = out_dir / 'sub-P001_run-01_T1w.nii.gz'
        fake_nii.write_bytes(b'fake_nifti')

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = b''

        with patch('subprocess.run', return_value=mock_result):
            result = run_dcm2niix(dicom_dir, out_dir, 'sub-P001_run-01_T1w')

        assert len(result) == 1
        assert result[0].name == 'sub-P001_run-01_T1w.nii.gz'

    def test_raises_when_no_nii_produced(self, tmp_path):
        from dicom_images.services.bids_utils import run_dcm2niix

        dicom_dir = tmp_path / 'dicoms'
        dicom_dir.mkdir()
        out_dir = tmp_path / 'output'
        out_dir.mkdir()

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = b'dcm2niix: no DICOM files found'

        with patch('subprocess.run', return_value=mock_result):
            with pytest.raises(RuntimeError, match='no NIfTI output'):
                run_dcm2niix(dicom_dir, out_dir, 'stem')

    def test_still_returns_nii_even_on_nonzero_exit(self, tmp_path):
        """dcm2niix sometimes exits non-zero but still produces output."""
        from dicom_images.services.bids_utils import run_dcm2niix

        dicom_dir = tmp_path / 'dicoms'
        dicom_dir.mkdir()
        out_dir = tmp_path / 'output'
        out_dir.mkdir()

        fake_nii = out_dir / 'stem.nii.gz'
        fake_nii.write_bytes(b'data')

        mock_result = MagicMock()
        mock_result.returncode = 1  # non-zero but output exists
        mock_result.stderr = b'warning: some slices missing'

        with patch('subprocess.run', return_value=mock_result):
            result = run_dcm2niix(dicom_dir, out_dir, 'stem')

        assert len(result) == 1


# ---------------------------------------------------------------------------
# AnonymizationJob output_format — API tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAnonymizationJobOutputFormat:

    def test_default_output_format_is_dicom_zip(self, auth_client, study):
        """output_format defaults to dicom_zip when not provided."""
        response = auth_client.post('/api/dicom/anonymize/', {
            'study_id': study.id,
            'profile': 'basic',
        }, format='json')

        assert response.status_code == 201
        assert response.data['output_format'] == 'dicom_zip'

    def test_can_create_nifti_bids_job(self, auth_client, study):
        """Can request nifti_bids output format."""
        response = auth_client.post('/api/dicom/anonymize/', {
            'study_id': study.id,
            'profile': 'full',
            'output_format': 'nifti_bids',
        }, format='json')

        assert response.status_code == 201
        assert response.data['output_format'] == 'nifti_bids'

    def test_can_create_png_bids_job(self, auth_client, study):
        """Can request png_bids output format."""
        response = auth_client.post('/api/dicom/anonymize/', {
            'study_id': study.id,
            'profile': 'basic',
            'output_format': 'png_bids',
        }, format='json')

        assert response.status_code == 201
        assert response.data['output_format'] == 'png_bids'

    def test_bids_format_with_image_ids_rejected(self, auth_client, image):
        """BIDS output formats reject image_ids (require full study)."""
        response = auth_client.post('/api/dicom/anonymize/', {
            'image_ids': [image.id],
            'profile': 'basic',
            'output_format': 'nifti_bids',
        }, format='json')

        assert response.status_code == 400

    def test_invalid_output_format_rejected(self, auth_client, study):
        """Unknown output_format values are rejected."""
        response = auth_client.post('/api/dicom/anonymize/', {
            'study_id': study.id,
            'profile': 'basic',
            'output_format': 'not_a_format',
        }, format='json')

        assert response.status_code == 400

    def test_output_format_included_in_list_response(self, auth_client, study, user):
        """output_format appears in job list responses."""
        from dicom_images.models import AnonymizationJob

        AnonymizationJob.objects.create(
            study=study,
            profile='basic',
            output_format='png_bids',
            status='PENDING',
            created_by=user,
        )

        response = auth_client.get('/api/dicom/anonymize/')
        assert response.status_code == 200
        jobs = response.data['results']
        assert any(j['output_format'] == 'png_bids' for j in jobs)

    def test_task_routes_bids_formats(self, study, user):
        """anonymize_study_task routes nifti_bids to build_nifti_bids_zip."""
        from dicom_images.models import AnonymizationJob
        from dicom_images.tasks import anonymize_study_task

        job = AnonymizationJob.objects.create(
            study=study,
            profile='basic',
            output_format='nifti_bids',
            status='PENDING',
            created_by=user,
        )

        with patch(
            'dicom_images.services.bids_utils.build_nifti_bids_zip',
            return_value='anonymized/bids_test.zip',
        ) as mock_fn:
            anonymize_study_task(str(job.id))

        mock_fn.assert_called_once()
        job.refresh_from_db()
        assert job.status == 'COMPLETED'
        assert job.result_file_path == 'anonymized/bids_test.zip'

    def test_task_fails_bids_without_study(self, user):
        """Task marks job FAILED when BIDS format used without study_id."""
        from dicom_images.models import AnonymizationJob
        from dicom_images.tasks import anonymize_study_task

        job = AnonymizationJob.objects.create(
            image_ids=[999],
            profile='basic',
            output_format='nifti_bids',
            status='PENDING',
            created_by=user,
        )

        anonymize_study_task(str(job.id))

        job.refresh_from_db()
        assert job.status == 'FAILED'
        assert 'study_id' in job.error_message.lower() or 'study' in job.error_message.lower()

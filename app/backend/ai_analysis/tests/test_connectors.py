"""
Tests for AI analysis connectors (PICAI, CheXNet).
"""

from unittest.mock import patch, MagicMock, Mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from ai_analysis.connectors.picai import PICAIConnector
from ai_analysis.connectors.chexnet import CheXNetConnector, CHEXNET_PATHOLOGIES
from ai_analysis.models import AIModel


# ===========================================================================
# Helper to build a mock AIModel for connectors
# ===========================================================================

def _make_ai_model(**overrides):
    """Create a mock AIModel for connector instantiation."""
    defaults = {
        'endpoint_url': 'http://test-service:8000',
        'timeout_seconds': 300,
        'required_parameters': {},
    }
    defaults.update(overrides)
    model = MagicMock(spec=AIModel)
    for k, v in defaults.items():
        setattr(model, k, v)
    return model


def _make_task(parameters=None, modality='MR'):
    """Create a mock AnalysisTask with associated image/series."""
    task = MagicMock()
    task.id = 'test-task-001'
    task.parameters = parameters or {}
    task.webhook_secret = 'secret123'

    # Mock input_image -> series -> modality chain
    task.input_image.series.modality = modality
    task.input_image.file = MagicMock()
    task.input_image.file.name = 'dicom/test/image.dcm'
    return task


# ===========================================================================
# PICAI Connector Tests
# ===========================================================================

class TestPICAIConnectorValidateModalities:

    def test_validate_modalities_missing_adc(self):
        connector = PICAIConnector(_make_ai_model())
        task = _make_task(parameters={}, modality='MR')

        with pytest.raises(ValueError, match="ADC image"):
            connector._validate_modalities(task)

    @pytest.mark.django_db
    def test_validate_modalities_success(self, image):
        """Passes when primary is MR and ADC image exists."""
        connector = PICAIConnector(_make_ai_model())
        task = _make_task(parameters={'adc_image_id': image.pk}, modality='MR')

        mock_adc = MagicMock()
        mock_adc.series.modality = 'MR'

        with patch('dicom_images.models.MedicalImage.objects') as mock_objects:
            mock_objects.select_related.return_value.get.return_value = mock_adc
            # Should not raise
            connector._validate_modalities(task)

    def test_validate_modalities_wrong_primary_modality(self):
        connector = PICAIConnector(_make_ai_model())
        task = _make_task(parameters={'adc_image_id': 99}, modality='CT')

        with pytest.raises(ValueError, match="PICAI requires MR images"):
            connector._validate_modalities(task)

    @pytest.mark.django_db
    def test_build_grpc_request(self, image):
        """Correct payload structure with t2w + adc images."""
        connector = PICAIConnector(_make_ai_model())
        task = _make_task(parameters={'adc_image_id': image.pk}, modality='MR')

        mock_img = MagicMock()
        mock_img.file = MagicMock()
        mock_img.file.name = 'dicom/adc/image.dcm'

        with patch('dicom_images.models.MedicalImage.objects') as mock_objects:
            mock_objects.get.return_value = mock_img
            payload = connector._build_grpc_request(task)

        assert 'job_id' in payload
        assert 'images' in payload
        assert len(payload['images']) >= 2
        modalities = [img['modality'] for img in payload['images']]
        assert 't2w' in modalities
        assert 'adc' in modalities
        assert payload['task_type'] == 'segmentation'


class TestPICAIConnectorValidateParameters:

    def test_validate_parameters_valid(self):
        connector = PICAIConnector(_make_ai_model())
        assert connector.validate_parameters({'output_format': 'mha', 'ensemble_folds': 3})

    def test_validate_parameters_invalid_format(self):
        connector = PICAIConnector(_make_ai_model())
        with pytest.raises(ValueError, match="Invalid output_format"):
            connector.validate_parameters({'output_format': 'jpeg'})

    def test_validate_parameters_invalid_folds(self):
        connector = PICAIConnector(_make_ai_model())
        with pytest.raises(ValueError, match="Invalid ensemble_folds"):
            connector.validate_parameters({'ensemble_folds': 10})

    @pytest.mark.django_db
    def test_dispatch_raises_without_orchestrator(self, image):
        """dispatch_job should raise NotImplementedError — PICAI requires gRPC/Orchestrator mode."""
        connector = PICAIConnector(_make_ai_model())
        task = _make_task(parameters={'adc_image_id': image.pk}, modality='MR')

        mock_adc = MagicMock()
        mock_adc.series.modality = 'MR'
        mock_adc.file = MagicMock()
        mock_adc.file.name = 'dicom/adc/image.dcm'

        with patch('dicom_images.models.MedicalImage.objects') as mock_objects:
            mock_objects.select_related.return_value.get.return_value = mock_adc
            mock_objects.get.return_value = mock_adc
            with pytest.raises(NotImplementedError, match="PICAI requires Orchestrator mode"):
                connector.dispatch_job(task)


# ===========================================================================
# CheXNet Connector Tests
# ===========================================================================

class TestCheXNetConnectorValidateParameters:

    def test_validate_parameters_valid(self):
        connector = CheXNetConnector(_make_ai_model())
        assert connector.validate_parameters({'threshold': 0.5})

    def test_validate_parameters_invalid_threshold(self):
        connector = CheXNetConnector(_make_ai_model())
        with pytest.raises(ValueError, match="Invalid threshold"):
            connector.validate_parameters({'threshold': 1.5})

    def test_validate_parameters_negative_threshold(self):
        connector = CheXNetConnector(_make_ai_model())
        with pytest.raises(ValueError, match="Invalid threshold"):
            connector.validate_parameters({'threshold': -0.1})


class TestCheXNetConnectorDispatch:

    @patch('ai_analysis.connectors.chexnet.requests.post')
    def test_dispatch_job_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'job_id': 'chexnet-job-123',
            'status': 'queued',
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        connector = CheXNetConnector(_make_ai_model())
        task = _make_task(parameters={'threshold': 0.5}, modality='CR')

        result = connector.dispatch_job(task)

        assert result['service_job_id'] == 'chexnet-job-123'
        assert result['status'] == 'queued'
        mock_post.assert_called_once()

    @patch('ai_analysis.connectors.chexnet.requests.post')
    def test_dispatch_job_timeout(self, mock_post):
        import requests as req
        mock_post.side_effect = req.exceptions.Timeout("timed out")

        connector = CheXNetConnector(_make_ai_model())
        task = _make_task(parameters={}, modality='CR')

        with pytest.raises(TimeoutError, match="timed out"):
            connector.dispatch_job(task)


class TestCheXNetConnectorProcessResults:

    def test_process_results(self):
        connector = CheXNetConnector(_make_ai_model())
        raw = {
            'threshold': 0.5,
            'predictions': {
                'Pneumonia': 0.85,
                'Atelectasis': 0.30,
                'Cardiomegaly': 0.72,
                'Effusion': 0.10,
            },
        }
        processed = connector.process_results(raw)

        assert processed['findings_count'] == 2
        assert processed['total_pathologies_checked'] == len(CHEXNET_PATHOLOGIES)
        pathologies = [f['pathology'] for f in processed['findings']]
        assert 'Pneumonia' in pathologies
        assert 'Cardiomegaly' in pathologies
        assert 'Atelectasis' not in pathologies  # Below threshold

    def test_process_results_with_heatmap(self):
        connector = CheXNetConnector(_make_ai_model())
        raw = {
            'threshold': 0.5,
            'predictions': {'Pneumonia': 0.9},
            'heatmap_path': '/results/heatmap.png',
        }
        processed = connector.process_results(raw)
        assert processed['heatmap_path'] == '/results/heatmap.png'


# ===========================================================================
# Vet connector payload tests (#42 — dispatch must carry webhook callback)
# ===========================================================================

from ai_analysis.connectors.vet_thorax import VetThoraxConnector  # noqa: E402
from ai_analysis.connectors.vet_hip import HipDysplasiaConnector  # noqa: E402
from ai_analysis.connectors.vet_dental import VetDentalConnector  # noqa: E402


class TestVetConnectorPayloads:
    """The vet connectors must include webhook_url + webhook_secret + callback_url
    so the model service can post results back (regression: they previously read
    a non-existent task.webhook_url and omitted the secret)."""

    def _payload(self, connector_cls, modality='CR', params=None):
        connector = connector_cls(_make_ai_model())
        task = _make_task(parameters=params or {'species': 'canine'}, modality=modality)
        return connector._build_payload(task)

    def test_thorax_payload_has_webhook_and_secret(self):
        p = self._payload(VetThoraxConnector)
        assert p['webhook_secret'] == 'secret123'
        assert p['callback_url'] == p['webhook_url']
        assert '/api/ai-analysis/webhook/' in p['webhook_url']
        assert p['species'] == 'canine'
        assert p['study_instance_uid'] is not None

    def test_hip_payload_includes_scheme_and_secret(self):
        p = self._payload(HipDysplasiaConnector, params={'species': 'canine', 'scheme': 'BVA'})
        assert p['webhook_secret'] == 'secret123'
        assert p['callback_url'] == p['webhook_url']
        assert p['scheme'] == 'BVA'

    def test_dental_payload_has_secret(self):
        p = self._payload(VetDentalConnector, modality='IO')
        assert p['webhook_secret'] == 'secret123'
        assert p['callback_url'] == p['webhook_url']
        assert 'species' in p

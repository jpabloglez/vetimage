"""
Tests for ai_analysis views.
"""

import uuid
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from ai_analysis.models import AIModel, AnalysisTask


# ===========================================================================
# AIModelViewSet
# ===========================================================================


@pytest.mark.django_db
class TestAIModelViewSet:

    def test_list_public(self, api_client, ai_model):
        url = reverse('aimodel-list')
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        keys = [m['key'] for m in resp.data['results']]
        assert ai_model.key in keys

    def test_detail_by_key(self, api_client, ai_model):
        url = reverse('aimodel-detail', kwargs={'key': ai_model.key})
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['key'] == ai_model.key

    def test_inactive_hidden(self, api_client, ai_model):
        ai_model.is_active = False
        ai_model.save()
        url = reverse('aimodel-list')
        resp = api_client.get(url)
        keys = [m['key'] for m in resp.data['results']]
        assert ai_model.key not in keys


# ===========================================================================
# AnalysisTaskViewSet
# ===========================================================================


@pytest.mark.django_db
class TestAnalysisTaskViewSet:

    def test_list_requires_auth(self, api_client):
        url = reverse('task-list')
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_own_tasks(self, auth_client, analysis_task):
        url = reverse('task-list')
        resp = auth_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        task_ids = [str(t['id']) for t in resp.data['results']]
        assert str(analysis_task.pk) in task_ids

    @override_settings(USE_ORCHESTRATOR=False)
    @patch('ai_analysis.tasks.dispatch_ai_job.delay')
    def test_create_task(self, mock_dispatch, auth_client, ai_model, image):
        url = reverse('task-list')
        data = {
            'model_key': ai_model.key,
            'input_image_id': image.pk,
            'parameters': {'modality': 't1'},
        }
        resp = auth_client.post(url, data, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['status'] == 'PENDING'
        mock_dispatch.assert_called_once()

    @patch('ai_analysis.tasks.dispatch_ai_job.delay')
    def test_create_task_with_priority(self, mock_dispatch, auth_client, ai_model, image):
        """A STAT triage priority is stored and returned on the task."""
        url = reverse('task-list')
        resp = auth_client.post(url, {
            'model_key': ai_model.key,
            'input_image_id': image.pk,
            'parameters': {'modality': 't1'},
            'priority': 'stat',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['priority'] == 'stat'

    @patch('ai_analysis.tasks.dispatch_ai_job.delay')
    def test_priority_defaults_routine(self, mock_dispatch, auth_client, ai_model, image):
        url = reverse('task-list')
        resp = auth_client.post(url, {
            'model_key': ai_model.key,
            'input_image_id': image.pk,
            'parameters': {'modality': 't1'},
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['priority'] == 'routine'

    def test_cancel_pending(self, auth_client, analysis_task):
        url = reverse('task-detail', kwargs={'pk': str(analysis_task.pk)})
        resp = auth_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        analysis_task.refresh_from_db()
        assert analysis_task.status == 'CANCELLED'

    def test_cancel_completed_fails(self, auth_client, analysis_task):
        analysis_task.status = 'COMPLETED'
        analysis_task.save()
        url = reverse('task-detail', kwargs={'pk': str(analysis_task.pk)})
        resp = auth_client.delete(url)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @override_settings(USE_ORCHESTRATOR=False)
    @patch('ai_analysis.tasks.dispatch_ai_job.delay')
    def test_retry_failed(self, mock_dispatch, auth_client, analysis_task):
        analysis_task.status = 'FAILED'
        analysis_task.retry_count = 0
        analysis_task.save()
        url = reverse('task-retry', kwargs={'pk': str(analysis_task.pk)})
        resp = auth_client.post(url)
        assert resp.status_code == status.HTTP_200_OK
        analysis_task.refresh_from_db()
        assert analysis_task.status == 'PENDING'
        assert analysis_task.retry_count == 1
        mock_dispatch.assert_called_once()

    def test_retry_pending_fails(self, auth_client, analysis_task):
        url = reverse('task-retry', kwargs={'pk': str(analysis_task.pk)})
        resp = auth_client.post(url)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_stats_endpoint(self, auth_client, analysis_task):
        url = reverse('task-stats')
        resp = auth_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert 'total_jobs' in resp.data
        assert 'by_status' in resp.data
        assert 'success_rate' in resp.data

    def test_monitor_endpoint(self, auth_client, analysis_task):
        url = reverse('task-monitor')
        resp = auth_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert 'results' in resp.data

    @patch('ai_analysis.tasks.dispatch_ai_job.delay')
    def test_create_task_incompatible_modality_warns(self, mock_dispatch, auth_client, user, ai_model):
        """Incompatible modality is a soft warning (task still created), not a hard 400.

        The platform intentionally flags a possible modality mismatch rather than
        blocking — the veterinarian decides. The response carries a 'warning'.
        """
        from dicom_images.models import MedicalStudy, MedicalSeries, MedicalImage
        from django.core.files.uploadedfile import SimpleUploadedFile

        # Create a US (ultrasound) image — incompatible with ai_model which supports CT/MR
        study = MedicalStudy.objects.create(
            study_instance_uid='1.2.840.999.1',
            patient_id='PAT-US',
            uploaded_by=user,
            total_size_bytes=256,
        )
        series = MedicalSeries.objects.create(
            study=study,
            series_instance_uid='1.2.840.999.1.1',
            series_number=1,
            modality='US',
        )
        us_image = MedicalImage.objects.create(
            series=series,
            sop_instance_uid='1.2.840.999.1.1.1',
            sop_class_uid='1.2.840.10008.5.1.4.1.1.6.1',
            instance_number=1,
            file=SimpleUploadedFile('us.dcm', b'\x00' * 256),
            original_filename='us.dcm',
            file_size_bytes=256,
        )

        url = reverse('task-list')
        resp = auth_client.post(url, {
            'model_key': ai_model.key,
            'input_image_id': us_image.pk,
            'parameters': {},
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        # A modality-mismatch warning is surfaced to the caller.
        assert 'warning' in resp.data
        assert 'US' in resp.data['warning']

    @override_settings(USE_ORCHESTRATOR=False)
    @patch('ai_analysis.tasks.dispatch_ai_job.delay')
    def test_create_task_compatible_modality(self, mock_dispatch, auth_client, ai_model, image):
        """Should return 201 when image modality matches (CT image, model supports CT/MR)."""
        url = reverse('task-list')
        resp = auth_client.post(url, {
            'model_key': ai_model.key,
            'input_image_id': image.pk,
            'parameters': {},
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        mock_dispatch.assert_called_once()

    @patch('ai_analysis.tasks.dispatch_ai_job.delay')
    def test_create_picai_task_without_adc_fails(self, mock_dispatch, auth_client, user, image):
        """Should return 400 when PICAI model requires adc_image_id but it's missing."""
        from ai_analysis.models import AIModel

        picai_model = AIModel.objects.create(
            name='PICAI Test',
            key='picai-test-v1',
            version='1.0',
            endpoint_url='http://picai-test:50051',
            connector_class='ai_analysis.connectors.picai.PICAIConnector',
            model_type='segmentation',
            supported_modalities=['MR', 'T2W', 'ADC', 'HBV'],
            required_parameters={
                'adc_image_id': {
                    'type': 'integer',
                    'description': 'ADC image ID',
                    'required': True,
                }
            },
            is_active=True,
        )

        # image fixture has CT modality — create an MR image instead
        from dicom_images.models import MedicalStudy, MedicalSeries, MedicalImage
        from django.core.files.uploadedfile import SimpleUploadedFile

        study = MedicalStudy.objects.create(
            study_instance_uid='1.2.840.999.2',
            patient_id='PAT-MR',
            uploaded_by=user,
            total_size_bytes=256,
        )
        mr_series = MedicalSeries.objects.create(
            study=study,
            series_instance_uid='1.2.840.999.2.1',
            series_number=1,
            modality='MR',
        )
        mr_image = MedicalImage.objects.create(
            series=mr_series,
            sop_instance_uid='1.2.840.999.2.1.1',
            sop_class_uid='1.2.840.10008.5.1.4.1.1.4',
            instance_number=1,
            file=SimpleUploadedFile('mr.dcm', b'\x00' * 256),
            original_filename='mr.dcm',
            file_size_bytes=256,
        )

        url = reverse('task-list')
        resp = auth_client.post(url, {
            'model_key': picai_model.key,
            'input_image_id': mr_image.pk,
            'parameters': {},
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        mock_dispatch.assert_not_called()

    def test_user_isolation(self, auth_client, other_user, image, ai_model):
        """User should not see another user's tasks."""
        AnalysisTask.objects.create(
            input_image=image,
            model=ai_model,
            created_by=other_user,
            status='PENDING',
        )
        url = reverse('task-list')
        resp = auth_client.get(url)
        # auth_client is authenticated as `user`, not `other_user`
        for task in resp.data['results']:
            assert task.get('created_by') != other_user.pk


# ===========================================================================
# WebhookReceiverView
# ===========================================================================


@pytest.mark.django_db
class TestWebhookReceiverView:

    def test_valid_webhook(self, api_client, analysis_task):
        # Move task to DISPATCHED so the transition is valid
        analysis_task.status = 'DISPATCHED'
        analysis_task.save()

        url = reverse('webhook-receiver', kwargs={'task_id': str(analysis_task.pk)})
        data = {
            'status': 'PROCESSING',
            'webhook_secret': analysis_task.webhook_secret,
        }
        resp = api_client.post(url, data, format='json')
        assert resp.status_code == status.HTTP_200_OK

    def test_invalid_secret(self, api_client, analysis_task):
        analysis_task.status = 'DISPATCHED'
        analysis_task.save()

        url = reverse('webhook-receiver', kwargs={'task_id': str(analysis_task.pk)})
        data = {
            'status': 'PROCESSING',
            'webhook_secret': 'wrong-secret',
        }
        resp = api_client.post(url, data, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_task(self, api_client):
        fake_id = uuid.uuid4()
        url = reverse('webhook-receiver', kwargs={'task_id': str(fake_id)})
        data = {
            'status': 'PROCESSING',
            'webhook_secret': 'irrelevant',
        }
        resp = api_client.post(url, data, format='json')
        # The webhook handler raises ValueError for missing task
        assert resp.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        )


# ===========================================================================
# Anonymization Gate
# ===========================================================================


@pytest.mark.django_db
class TestAnonymizationGate:
    """
    Tests for the requires_anonymization gate on AnalysisTask creation.
    """

    def _create_url(self):
        return reverse('task-list')

    @override_settings(USE_ORCHESTRATOR=False)
    @patch('ai_analysis.tasks.dispatch_ai_job.delay')
    def test_gate_blocks_when_no_anon_job(self, mock_dispatch, auth_client, ai_model, image):
        """Task creation is rejected (422) when model requires anon but no job exists."""
        ai_model.requires_anonymization = True
        ai_model.save()

        resp = auth_client.post(self._create_url(), {
            'model_key': ai_model.key,
            'input_image_id': image.pk,
            'parameters': {},
        }, format='json')

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert 'anonymized' in resp.data['error'].lower()
        mock_dispatch.assert_not_called()

    @override_settings(USE_ORCHESTRATOR=False)
    @patch('ai_analysis.tasks.dispatch_ai_job.delay')
    def test_gate_blocks_when_only_basic_anon_job(self, mock_dispatch, auth_client, ai_model, image, user):
        """Task creation is rejected when only a 'basic' profile job exists."""
        from dicom_images.models import AnonymizationJob
        ai_model.requires_anonymization = True
        ai_model.save()

        AnonymizationJob.objects.create(
            study=image.series.study,
            profile='basic',
            status='COMPLETED',
            created_by=user,
        )

        resp = auth_client.post(self._create_url(), {
            'model_key': ai_model.key,
            'input_image_id': image.pk,
            'parameters': {},
        }, format='json')

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_dispatch.assert_not_called()

    @override_settings(USE_ORCHESTRATOR=False)
    @patch('ai_analysis.tasks.dispatch_ai_job.delay')
    def test_gate_passes_with_full_anon_job(self, mock_dispatch, auth_client, ai_model, image, user):
        """Task creation succeeds when a 'full' profile completed job exists."""
        from dicom_images.models import AnonymizationJob
        ai_model.requires_anonymization = True
        ai_model.save()

        AnonymizationJob.objects.create(
            study=image.series.study,
            profile='full',
            status='COMPLETED',
            created_by=user,
        )

        resp = auth_client.post(self._create_url(), {
            'model_key': ai_model.key,
            'input_image_id': image.pk,
            'parameters': {'modality': 't1'},
        }, format='json')

        assert resp.status_code == status.HTTP_201_CREATED
        mock_dispatch.assert_called_once()

    @override_settings(USE_ORCHESTRATOR=False)
    @patch('ai_analysis.tasks.dispatch_ai_job.delay')
    def test_gate_passes_with_research_anon_job(self, mock_dispatch, auth_client, ai_model, image, user):
        """Task creation succeeds when a 'research' profile completed job exists."""
        from dicom_images.models import AnonymizationJob
        ai_model.requires_anonymization = True
        ai_model.save()

        AnonymizationJob.objects.create(
            study=image.series.study,
            profile='research',
            status='COMPLETED',
            created_by=user,
        )

        resp = auth_client.post(self._create_url(), {
            'model_key': ai_model.key,
            'input_image_id': image.pk,
            'parameters': {'modality': 't1'},
        }, format='json')

        assert resp.status_code == status.HTTP_201_CREATED
        mock_dispatch.assert_called_once()

    @override_settings(USE_ORCHESTRATOR=False)
    @patch('ai_analysis.tasks.dispatch_ai_job.delay')
    def test_gate_blocks_pending_anon_job(self, mock_dispatch, auth_client, ai_model, image, user):
        """A PENDING anonymization job does not satisfy the gate."""
        from dicom_images.models import AnonymizationJob
        ai_model.requires_anonymization = True
        ai_model.save()

        AnonymizationJob.objects.create(
            study=image.series.study,
            profile='full',
            status='PENDING',
            created_by=user,
        )

        resp = auth_client.post(self._create_url(), {
            'model_key': ai_model.key,
            'input_image_id': image.pk,
            'parameters': {},
        }, format='json')

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        mock_dispatch.assert_not_called()

    @override_settings(USE_ORCHESTRATOR=False)
    @patch('ai_analysis.tasks.dispatch_ai_job.delay')
    def test_gate_not_applied_when_flag_false(self, mock_dispatch, auth_client, ai_model, image):
        """When requires_anonymization=False the gate is not checked at all."""
        # ai_model has requires_anonymization=False by default (no anon job needed)
        resp = auth_client.post(self._create_url(), {
            'model_key': ai_model.key,
            'input_image_id': image.pk,
            'parameters': {'modality': 't1'},
        }, format='json')

        assert resp.status_code == status.HTTP_201_CREATED
        mock_dispatch.assert_called_once()

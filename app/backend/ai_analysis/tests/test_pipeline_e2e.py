"""
End-to-end webhook lifecycle test for the vet AI pipeline (#44).

Drives an AnalysisTask through the same webhook contract the reference
VetThorax service uses: DISPATCHED -> PROCESSING -> COMPLETED, with findings
delivered in metadata.findings and persisted to result_metadata. This locks in
the integration contract without needing the model container running.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from ai_analysis.models import AnalysisTask


@pytest.fixture
def dispatched_task(user, image, ai_model):
    """A task already dispatched to a model service, awaiting webhooks."""
    return AnalysisTask.objects.create(
        input_image=image,
        model=ai_model,
        created_by=user,
        status='DISPATCHED',
        parameters={'species': 'canine'},
        service_job_id='vetthorax-job-1',
    )


FINDINGS = [
    {'label': 'cardiomegaly', 'region': 'cardiac', 'confidence': 0.78},
    {'label': 'pleural_effusion', 'region': 'pleural_space', 'confidence': 0.61},
]


@pytest.mark.django_db
class TestWebhookLifecycle:
    def _url(self, task):
        return reverse('webhook-receiver', kwargs={'task_id': task.id})

    def test_full_lifecycle_processing_then_completed(self, dispatched_task):
        client = APIClient()  # webhook is unauthenticated (secret-gated)
        url = self._url(dispatched_task)
        secret = dispatched_task.webhook_secret

        # 1) PROCESSING
        r1 = client.post(url, {'status': 'PROCESSING', 'webhook_secret': secret}, format='json')
        assert r1.status_code == 200, r1.content
        dispatched_task.refresh_from_db()
        assert dispatched_task.status == 'PROCESSING'
        assert dispatched_task.started_processing_at is not None

        # 2) COMPLETED with findings in metadata
        r2 = client.post(url, {
            'status': 'COMPLETED',
            'webhook_secret': secret,
            'metadata': {'findings': FINDINGS, 'model_version': 'vet-thorax-fixture-0.1.0'},
        }, format='json')
        assert r2.status_code == 200, r2.content
        dispatched_task.refresh_from_db()
        assert dispatched_task.status == 'COMPLETED'
        assert dispatched_task.completed_at is not None
        assert dispatched_task.result_metadata['findings'] == FINDINGS
        assert dispatched_task.result_metadata['model_version'] == 'vet-thorax-fixture-0.1.0'

    def test_invalid_secret_rejected(self, dispatched_task):
        client = APIClient()
        r = client.post(self._url(dispatched_task),
                        {'status': 'PROCESSING', 'webhook_secret': 'wrong'}, format='json')
        assert r.status_code == 400

    def test_invalid_transition_rejected(self, dispatched_task):
        # DISPATCHED -> COMPLETED is not allowed (must go through PROCESSING).
        client = APIClient()
        r = client.post(self._url(dispatched_task), {
            'status': 'COMPLETED', 'webhook_secret': dispatched_task.webhook_secret,
            'metadata': {'findings': FINDINGS},
        }, format='json')
        assert r.status_code == 400
        dispatched_task.refresh_from_db()
        assert dispatched_task.status == 'DISPATCHED'

    def test_terminal_state_is_idempotent(self, dispatched_task):
        client = APIClient()
        url = self._url(dispatched_task)
        secret = dispatched_task.webhook_secret
        client.post(url, {'status': 'PROCESSING', 'webhook_secret': secret}, format='json')
        client.post(url, {'status': 'COMPLETED', 'webhook_secret': secret,
                          'metadata': {'findings': FINDINGS}}, format='json')
        # A duplicate COMPLETED delivery must not error or corrupt state.
        r = client.post(url, {'status': 'COMPLETED', 'webhook_secret': secret,
                              'metadata': {'findings': []}}, format='json')
        assert r.status_code == 200
        dispatched_task.refresh_from_db()
        assert dispatched_task.result_metadata['findings'] == FINDINGS  # unchanged


@pytest.mark.django_db
class TestStudyFindingsEndpoint:
    """GET /api/ai-analysis/tasks/study-findings/?study=<uid> — for viewer overlay."""

    def test_returns_findings_for_completed_task(self, auth_client, image, ai_model, user):
        study_uid = image.series.study.study_instance_uid
        AnalysisTask.objects.create(
            input_image=image, model=ai_model, created_by=user, status='COMPLETED',
            result_metadata={'findings': [
                {'label': 'cardiomegaly', 'region': 'cardiac', 'confidence': 0.8,
                 'bbox': [0.38, 0.45, 0.30, 0.35]},
            ]},
        )
        resp = auth_client.get(f'/api/ai-analysis/tasks/study-findings/?study={study_uid}')
        assert resp.status_code == 200, resp.content
        assert resp.data['study_instance_uid'] == study_uid
        assert len(resp.data['findings']) == 1
        f = resp.data['findings'][0]
        assert f['label'] == 'cardiomegaly'
        assert f['bbox'] == [0.38, 0.45, 0.30, 0.35]
        assert 'task_id' in f and 'model' in f

    def test_missing_study_param_400(self, auth_client):
        resp = auth_client.get('/api/ai-analysis/tasks/study-findings/')
        assert resp.status_code == 400

    def test_excludes_incomplete_tasks(self, auth_client, image, ai_model, user):
        study_uid = image.series.study.study_instance_uid
        AnalysisTask.objects.create(
            input_image=image, model=ai_model, created_by=user, status='PROCESSING',
            result_metadata={'findings': [{'label': 'x'}]},
        )
        resp = auth_client.get(f'/api/ai-analysis/tasks/study-findings/?study={study_uid}')
        assert resp.data['findings'] == []

    def test_requires_auth(self, image):
        study_uid = image.series.study.study_instance_uid
        resp = APIClient().get(f'/api/ai-analysis/tasks/study-findings/?study={study_uid}')
        assert resp.status_code in (401, 403)

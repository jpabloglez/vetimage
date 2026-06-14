"""
HipDysplasiaConnector — REST + webhook connector for canine/equine hip
dysplasia scoring from a ventrodorsal hip-extended radiograph.

Follows the VetThoraxConnector / MirageConnector pattern: dispatch → webhook
callback, with a polling fallback. Output is a hip score (OFA / BVA / FCI
schemes) plus subluxation index and femoral-head congruence per side.

DECISION-SUPPORT only — a veterinarian must review and confirm every result
(human-in-the-loop). Supported species: canine, equine.
"""
import logging

import requests

from .base import BaseAIConnector

logger = logging.getLogger(__name__)


class HipDysplasiaConnector(BaseAIConnector):
    """Connector for the vet-hip-v1 model service."""

    def dispatch_job(self, task):
        payload = self._build_payload(task)
        try:
            response = requests.post(f'{self.endpoint_url}/analyze', json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            service_job_id = data.get('job_id') or data.get('id')
            logger.info('VetHip task %s dispatched; service_job_id=%s', task.id, service_job_id)
            return {'service_job_id': service_job_id, 'status': 'dispatched'}
        except requests.Timeout:
            raise RuntimeError(f'Connection to {self.endpoint_url} timed out after 30 seconds')
        except requests.ConnectionError as exc:
            raise RuntimeError(f'Could not connect to {self.endpoint_url}: {exc}')
        except requests.HTTPError as exc:
            raise RuntimeError(
                f'Model service returned HTTP {exc.response.status_code}: {exc.response.text}'
            )

    def poll_job_status(self, task, service_job_id: str) -> dict:
        try:
            resp = requests.get(f'{self.endpoint_url}/jobs/{service_job_id}', timeout=15)
            resp.raise_for_status()
            data = resp.json()
            service_status = data.get('status', '').lower()
            if service_status in ('completed', 'done', 'success'):
                return {
                    'status': 'completed',
                    'result_data': {
                        'scheme': data.get('scheme'),               # OFA / BVA / FCI
                        'hip_score': data.get('hip_score'),
                        'subluxation_index': data.get('subluxation_index'),
                        'findings': data.get('findings', []),
                        'model_version': data.get('model_version'),
                    },
                }
            if service_status in ('failed', 'error'):
                return {'status': 'failed', 'error': data.get('error', 'Unknown error')}
            return {'status': 'processing'}
        except Exception as exc:
            logger.warning('VetHip poll_job_status failed: %s', exc)
            return {'status': 'processing'}

    def health_check(self) -> dict:
        try:
            resp = requests.get(f'{self.endpoint_url}/health', timeout=10)
            resp.raise_for_status()
            return {'status': 'healthy', 'details': resp.json()}
        except Exception as exc:
            return {'status': 'unhealthy', 'error': str(exc)}

    def _build_payload(self, task) -> dict:
        payload = self.build_base_payload(task)
        payload['callback_url'] = payload['webhook_url']
        payload['modality'] = getattr(task.input_image, 'modality', 'CR')
        payload['species'] = (task.parameters or {}).get('species', 'canine')
        payload['scheme'] = (task.parameters or {}).get('scheme', 'OFA')
        if hasattr(task.input_image, 'series'):
            series = task.input_image.series
            payload['study_instance_uid'] = series.study.study_instance_uid
            payload['series_instance_uid'] = series.series_instance_uid
        return payload

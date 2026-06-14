"""
VetDentalConnector — REST + webhook connector for canine/feline dental
(intraoral) radiograph analysis.

Follows the VetThoraxConnector / MirageConnector pattern. Output is a list of
per-tooth findings (tooth resorption, periapical lesion, crown fracture,
retained roots, bone loss) with confidence and tooth identifier (modified
Triadan numbering).

DECISION-SUPPORT only — a veterinarian must review and confirm every result
(human-in-the-loop). Supported species: canine, feline.
"""
import logging

import requests

from .base import BaseAIConnector

logger = logging.getLogger(__name__)


class VetDentalConnector(BaseAIConnector):
    """Connector for the vet-dental-v1 model service."""

    def dispatch_job(self, task):
        payload = self._build_payload(task)
        try:
            response = requests.post(f'{self.endpoint_url}/analyze', json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            service_job_id = data.get('job_id') or data.get('id')
            logger.info('VetDental task %s dispatched; service_job_id=%s', task.id, service_job_id)
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
                        'findings': data.get('findings', []),   # [{tooth, label, confidence}]
                        'model_version': data.get('model_version'),
                    },
                }
            if service_status in ('failed', 'error'):
                return {'status': 'failed', 'error': data.get('error', 'Unknown error')}
            return {'status': 'processing'}
        except Exception as exc:
            logger.warning('VetDental poll_job_status failed: %s', exc)
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
        payload['modality'] = getattr(task.input_image, 'modality', 'IO')
        payload['species'] = (task.parameters or {}).get('species', 'canine')
        if hasattr(task.input_image, 'series'):
            series = task.input_image.series
            payload['study_instance_uid'] = series.study.study_instance_uid
            payload['series_instance_uid'] = series.series_instance_uid
        return payload

"""
VetThoraxConnector — REST + webhook connector for canine/feline thoracic
radiograph screening.

Follows the MirageConnector pattern exactly:
  1. dispatch_job() POSTs the DICOM series + callback URL to the model service.
  2. The service calls back to /api/ai-analysis/webhook/ when done.
  3. poll_job_status() provides a polling fallback.

Input:  lateral ± VD thoracic radiograph DICOM series (modalities: CR, DX)
Output: JSON list of findings with confidence and bounding-box regions.
        Example: [{"label": "cardiomegaly", "confidence": 0.87, "region": "cardiac"}]

This is a DECISION-SUPPORT tool. All results must be reviewed and confirmed by
a veterinarian before any clinical action — human-in-the-loop is mandatory.

Supported species: canine, feline
"""
import logging
from typing import Optional

import requests

from .base import BaseAIConnector

logger = logging.getLogger(__name__)


class VetThoraxConnector(BaseAIConnector):
    """
    Connector for the vet-thorax-cr-v1 model service.

    The service exposes a REST API compatible with the MIRAGE webhook protocol,
    so this connector re-uses that dispatch/poll/health surface.
    """

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch_job(self, task):
        """POST job to the model service and return service_job_id."""
        payload = self._build_payload(task)

        try:
            response = requests.post(
                f'{self.endpoint_url}/analyze',
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            service_job_id = data.get('job_id') or data.get('id')
            logger.info(
                'VetThorax task %s dispatched; service_job_id=%s',
                task.id, service_job_id,
            )
            return {'service_job_id': service_job_id, 'status': 'dispatched'}

        except requests.Timeout:
            raise RuntimeError(
                f'Connection to {self.endpoint_url} timed out after 30 seconds'
            )
        except requests.ConnectionError as exc:
            raise RuntimeError(
                f'Could not connect to {self.endpoint_url}: {exc}'
            )
        except requests.HTTPError as exc:
            raise RuntimeError(
                f'Model service returned HTTP {exc.response.status_code}: {exc.response.text}'
            )

    # ------------------------------------------------------------------
    # Polling (fallback when webhook doesn't fire)
    # ------------------------------------------------------------------

    def poll_job_status(self, task, service_job_id: str) -> dict:
        """Poll /jobs/{id} for completion. Returns {status, result_data}."""
        try:
            resp = requests.get(
                f'{self.endpoint_url}/jobs/{service_job_id}',
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            service_status = data.get('status', '').lower()
            if service_status in ('completed', 'done', 'success'):
                return {
                    'status': 'completed',
                    'result_data': {
                        'findings': data.get('findings', []),
                        'model_version': data.get('model_version'),
                        'processing_time_s': data.get('processing_time_s'),
                    },
                }
            if service_status in ('failed', 'error'):
                return {'status': 'failed', 'error': data.get('error', 'Unknown error')}
            return {'status': 'processing'}

        except Exception as exc:
            logger.warning('VetThorax poll_job_status failed: %s', exc)
            return {'status': 'processing'}

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health_check(self) -> dict:
        try:
            resp = requests.get(f'{self.endpoint_url}/health', timeout=10)
            resp.raise_for_status()
            return {'status': 'healthy', 'details': resp.json()}
        except Exception as exc:
            return {'status': 'unhealthy', 'error': str(exc)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_payload(self, task) -> dict:
        """Assemble the JSON payload for the /analyze endpoint.

        Starts from the base payload so the service receives the correct
        ``webhook_url`` + ``webhook_secret`` needed to post results back, then
        adds the thoracic-specific fields.
        """
        payload = self.build_base_payload(task)
        # The vet model services read the callback URL as `callback_url`.
        payload['callback_url'] = payload['webhook_url']
        payload['modality'] = getattr(task.input_image, 'modality', 'CR')
        payload['species'] = (task.parameters or {}).get('species', 'canine')

        # Include DICOM study reference if available
        if hasattr(task.input_image, 'series'):
            series = task.input_image.series
            payload['study_instance_uid'] = series.study.study_instance_uid
            payload['series_instance_uid'] = series.series_instance_uid

        return payload

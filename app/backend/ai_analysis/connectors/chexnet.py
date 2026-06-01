"""
CheXNet Connector - Interface for CheXNet chest X-ray classification service

This connector communicates with the CheXNet REST API for 14-class chest X-ray
pathology classification based on the Stanford ML Group model.
"""

import requests
import logging
from typing import Dict, Any
from .base import BaseAIConnector

logger = logging.getLogger(__name__)

# CheXNet's 14 pathology labels from CheXpert/ChestX-ray14
CHEXNET_PATHOLOGIES = [
    'Atelectasis',
    'Cardiomegaly',
    'Consolidation',
    'Edema',
    'Effusion',
    'Emphysema',
    'Fibrosis',
    'Hernia',
    'Infiltration',
    'Mass',
    'Nodule',
    'Pleural_Thickening',
    'Pneumonia',
    'Pneumothorax',
]


class CheXNetConnector(BaseAIConnector):
    """
    Connector for CheXNet chest X-ray classification model.

    CheXNet is a 121-layer DenseNet trained on ChestX-ray14 dataset that classifies
    14 thoracic pathologies from frontal chest X-rays (CR/DX modality).
    """

    def dispatch_job(self, task) -> Dict[str, Any]:
        """
        Dispatch classification job to CheXNet REST service.

        Args:
            task: AnalysisTask instance

        Returns:
            Dict with service_job_id and status

        Raises:
            TimeoutError: Connection timeout
            ConnectionError: Cannot reach service
            ValueError: HTTP error or invalid response
        """
        parameters = task.parameters or {}
        threshold = parameters.get('threshold', 0.5)
        return_heatmap = parameters.get('return_heatmap', False)

        image_source = self.build_file_path(task.input_image.file)

        payload = {
            'image_path': image_source,
            'threshold': threshold,
            'return_heatmap': return_heatmap,
            'callback_url': self.get_webhook_url(task),
            'webhook_secret': task.webhook_secret,
        }

        logger.info(
            f"Dispatching CheXNet task {task.id} to {self.endpoint_url}/classify "
            f"(threshold={threshold}, heatmap={return_heatmap})"
        )

        try:
            response = requests.post(
                f"{self.endpoint_url}/classify",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            logger.info(
                f"CheXNet task {task.id} dispatched. "
                f"Job ID: {result.get('job_id')}, Status: {result.get('status')}"
            )

            return {
                'service_job_id': result.get('job_id'),
                'status': result.get('status', 'queued'),
                'message': result.get('message', ''),
            }

        except requests.exceptions.Timeout:
            error_msg = f"Connection to {self.endpoint_url} timed out after 30 seconds"
            logger.error(f"Task {task.id}: {error_msg}")
            raise TimeoutError(error_msg)

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Could not connect to {self.endpoint_url}: {str(e)}"
            logger.error(f"Task {task.id}: {error_msg}")
            raise ConnectionError(error_msg)

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"Task {task.id}: {error_msg}")
            raise ValueError(error_msg)

    def validate_parameters(self, parameters: Dict) -> bool:
        """
        Validate CheXNet-specific parameters.

        Args:
            parameters: Dict of task parameters

        Returns:
            True if validation passes

        Raises:
            ValueError: If validation fails
        """
        threshold = parameters.get('threshold', 0.5)
        if not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 1:
            raise ValueError(
                f"Invalid threshold '{threshold}'. Must be a float between 0 and 1"
            )

        return_heatmap = parameters.get('return_heatmap', False)
        if not isinstance(return_heatmap, bool):
            raise ValueError(
                f"Invalid return_heatmap '{return_heatmap}'. Must be a boolean"
            )

        return True

    def process_results(self, results: Dict) -> Dict[str, Any]:
        """
        Process CheXNet classification results, filtering findings by threshold.

        Args:
            results: Raw results from CheXNet service with per-pathology scores

        Returns:
            Processed results with findings filtered by threshold
        """
        threshold = results.get('threshold', 0.5)
        predictions = results.get('predictions', {})

        findings = []
        for pathology in CHEXNET_PATHOLOGIES:
            score = predictions.get(pathology, 0.0)
            if score >= threshold:
                findings.append({
                    'pathology': pathology,
                    'confidence': round(score, 4),
                })

        findings.sort(key=lambda x: x['confidence'], reverse=True)

        processed = {
            'findings': findings,
            'total_pathologies_checked': len(CHEXNET_PATHOLOGIES),
            'threshold': threshold,
            'findings_count': len(findings),
        }

        if 'heatmap_path' in results:
            processed['heatmap_path'] = results['heatmap_path']

        return processed

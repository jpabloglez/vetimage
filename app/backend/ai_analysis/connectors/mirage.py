"""
MIRAGE Connector - Communication layer for MIRAGE OCT analysis service

This module implements the connector for the MIRAGE (Medical Image Representation via
Adversarial Gradient Estimation) model, which performs OCT image analysis including:
- Feature extraction
- Segmentation
- Classification

API Endpoints:
- POST /analyze - Submit analysis job
- GET /jobs/{job_id} - Check job status
- POST /models/{model_size}/load - Load model
- POST /models/{model_size}/unload - Unload model
- GET /health - Service health check
"""

import requests
import logging
import time
from typing import Dict, Optional
from .base import BaseAIConnector

logger = logging.getLogger(__name__)


class MirageConnector(BaseAIConnector):
    """
    Connector for MIRAGE OCT analysis model.

    MIRAGE is a foundation model for retinal OCT images supporting multiple modalities:
    - bscan: B-scan images (512x512)
    - slo: Scanning Laser Ophthalmoscopy images
    - bscanlayermap: Layer segmentation maps (128x128)

    Supported tasks:
    - feature_extraction: Extract embedding vectors
    - segmentation: Segment anatomical structures
    - classification: Classify pathological conditions
    """

    def dispatch_job(self, task):
        """
        Dispatch analysis job to MIRAGE FastAPI service.

        MIRAGE expects:
        - images: List of {modality, source} dicts
        - task_type: feature_extraction, segmentation, or classification
        - model_size: base or large
        - output_destination: S3 URI or local path for results

        Args:
            task: AnalysisTask instance

        Returns:
            Dict with 'service_job_id' and 'status'

        Raises:
            TimeoutError: Connection timeout
            ConnectionError: Cannot reach service
            ValueError: HTTP error or invalid response
        """
        # Extract parameters
        task_type = task.parameters.get('task_type', 'feature_extraction')
        model_size = task.parameters.get('model_size', 'base')
        modality = task.parameters.get('modality', 'bscan')
        output_destination = task.parameters.get(
            'output_destination',
            f's3://openmedlab-results/mirage/{task.id}'
        )

        # Get image file path (from container perspective)
        image_source = self.build_file_path(task.input_image.file)

        # Build payload matching MIRAGE API structure
        payload = {
            "images": [
                {
                    "modality": modality,
                    "source": image_source
                }
            ],
            "task_type": task_type,
            "model_size": model_size,
            "output_destination": output_destination
        }

        # Add optional callback URL for async notifications
        if hasattr(task, 'webhook_url') and task.webhook_url:
            payload['callback_url'] = task.webhook_url

        # Log the dispatch attempt
        logger.info(
            f"Dispatching MIRAGE task {task.id} to {self.endpoint_url}/analyze "
            f"(task_type={task_type}, model={model_size}, modality={modality})"
        )

        # Ensure model is loaded before submitting job
        self._ensure_model_loaded(model_size)

        # Send HTTP POST request to MIRAGE service
        try:
            response = requests.post(
                f"{self.endpoint_url}/analyze",
                json=payload,
                timeout=30  # Connection timeout (not processing timeout)
            )

            # Raise exception for 4xx/5xx status codes
            response.raise_for_status()

            # Parse JSON response
            result = response.json()

            logger.info(
                f"MIRAGE task {task.id} dispatched successfully. "
                f"Service job ID: {result.get('job_id')}, Status: {result.get('status')}"
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

        except ValueError as e:
            # JSON decode error or other value errors
            error_msg = f"Invalid response from MIRAGE service: {str(e)}"
            logger.error(f"Task {task.id}: {error_msg}")
            raise ValueError(error_msg)

    def poll_job_status(self, task) -> Dict:
        """
        Poll MIRAGE service for job status.

        Args:
            task: AnalysisTask instance with service_job_id

        Returns:
            Dict with current status and results (if completed)

        Raises:
            ConnectionError: Cannot reach service
            ValueError: Invalid response
        """
        service_job_id = task.service_job_id

        if not service_job_id:
            raise ValueError("Task has no service_job_id - cannot poll status")

        try:
            response = requests.get(
                f"{self.endpoint_url}/jobs/{service_job_id}",
                timeout=10
            )

            response.raise_for_status()
            result = response.json()

            # MIRAGE API returns: {job_id, status, output_uri, output_keys, result, error}
            status = result.get('status', 'unknown')

            logger.debug(
                f"Task {task.id} (service job {service_job_id}): status={status}"
            )

            return {
                'status': status,
                'result': result.get('result', {}),
                'output_uri': result.get('output_uri'),
                'output_keys': result.get('output_keys', []),
                'error': result.get('error'),
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to poll status for job {service_job_id}: {str(e)}"
            logger.error(f"Task {task.id}: {error_msg}")
            raise ConnectionError(error_msg)

    def _ensure_model_loaded(self, model_size: str = 'base') -> bool:
        """
        Ensure MIRAGE model is loaded before submitting job.

        Args:
            model_size: 'base' or 'large'

        Returns:
            True if model is loaded

        Raises:
            ConnectionError: Cannot load model
        """
        try:
            # Check if model is already loaded via health endpoint
            health_response = requests.get(
                f"{self.endpoint_url}/health",
                timeout=10
            )

            if health_response.status_code == 200:
                health_data = health_response.json()
                models_loaded = health_data.get('models_loaded', {})

                if models_loaded.get(model_size):
                    logger.debug(f"MIRAGE {model_size} model already loaded")
                    return True

            # Load the model
            logger.info(f"Loading MIRAGE {model_size} model...")
            load_response = requests.post(
                f"{self.endpoint_url}/models/{model_size}/load",
                timeout=60  # Model loading can take time
            )

            if load_response.status_code == 200:
                logger.info(f"MIRAGE {model_size} model loaded successfully")
                return True
            else:
                logger.warning(
                    f"Failed to load MIRAGE {model_size} model: "
                    f"HTTP {load_response.status_code}"
                )
                return False

        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not ensure model loaded: {str(e)}")
            # Don't fail the job - let the service handle missing models
            return False

    def validate_parameters(self, parameters: Dict) -> bool:
        """
        Validate MIRAGE-specific parameters.

        Required parameters:
        - task_type: feature_extraction, segmentation, or classification
        - modality: bscan, slo, or bscanlayermap

        Optional parameters:
        - model_size: base or large (default: base)
        - output_destination: S3 URI or local path (auto-generated if missing)

        Args:
            parameters: Dict of task parameters

        Returns:
            True if validation passes

        Raises:
            ValueError: If validation fails
        """
        # Call parent validation for required_parameters from DB
        super().validate_parameters(parameters)

        # Validate task_type
        valid_task_types = ['feature_extraction', 'segmentation', 'classification']
        task_type = parameters.get('task_type', 'feature_extraction')
        if task_type not in valid_task_types:
            raise ValueError(
                f"Invalid task_type '{task_type}'. "
                f"Must be one of: {', '.join(valid_task_types)}"
            )

        # Validate modality
        valid_modalities = ['bscan', 'slo', 'bscanlayermap']
        modality = parameters.get('modality', 'bscan')
        if modality not in valid_modalities:
            raise ValueError(
                f"Invalid modality '{modality}'. "
                f"Must be one of: {', '.join(valid_modalities)}"
            )

        # Validate model_size
        valid_model_sizes = ['base', 'large']
        model_size = parameters.get('model_size', 'base')
        if model_size not in valid_model_sizes:
            raise ValueError(
                f"Invalid model_size '{model_size}'. "
                f"Must be one of: {', '.join(valid_model_sizes)}"
            )

        # Validate output_destination format if provided
        output_dest = parameters.get('output_destination')
        if output_dest:
            # Must be S3 URI or absolute path
            if not (output_dest.startswith('s3://') or output_dest.startswith('/')):
                raise ValueError(
                    f"Invalid output_destination '{output_dest}'. "
                    "Must be S3 URI (s3://...) or absolute path (/...)"
                )

        return True

    def check_health(self) -> Dict:
        """
        Check MIRAGE service health and availability.

        Returns:
            Dict with health status, GPU info, and loaded models

        Raises:
            ConnectionError: Cannot reach service
        """
        try:
            response = requests.get(
                f"{self.endpoint_url}/health",
                timeout=10
            )

            response.raise_for_status()
            health_data = response.json()

            return {
                'status': health_data.get('status', 'unknown'),
                'gpu_available': health_data.get('gpu_available', False),
                'gpu_name': health_data.get('gpu_name'),
                'device': health_data.get('device', 'cpu'),
                'models_loaded': health_data.get('models_loaded', {}),
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(error_msg)

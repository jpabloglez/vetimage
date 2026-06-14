"""
PICAI Connector - Interface for PICAI prostate cancer detection service

This connector communicates with the PICAI service via the orchestrator's gRPC interface.
PICAI requires T2W, ADC, and HBV MRI modalities to detect clinically significant prostate cancer.
"""

import logging
from typing import Dict, Any
from .base import BaseAIConnector

logger = logging.getLogger(__name__)


class PICAIConnector(BaseAIConnector):
    """
    Connector for PICAI (Prostate Imaging - Cancer AI) model service.

    PICAI analyzes biparametric MRI scans to detect clinically significant prostate cancer.
    Requires three modalities:
    - T2W: T2-weighted MRI
    - ADC: Apparent Diffusion Coefficient map
    - HBV: High b-value Diffusion-Weighted Imaging

    The orchestrator routes requests to the PICAI gRPC service running on separate infrastructure.
    """

    def dispatch_job(self, task) -> Dict[str, Any]:
        """
        Dispatch analysis job to PICAI service via orchestrator.

        Args:
            task: AnalysisTask instance with input images and parameters

        Returns:
            Dict with:
                - service_job_id: Job ID from orchestrator
                - status: 'queued' or 'processing'

        Raises:
            ValueError: If required modalities are missing
            ConnectionError: If orchestrator is unavailable
            TimeoutError: If request times out
        """
        logger.info(f"Dispatching PICAI job for task {task.id}")

        # Validate required modalities are present
        self._validate_modalities(task)

        # Build gRPC request payload
        payload = self._build_grpc_request(task)

        logger.info(f"PICAI payload built for task {task.id}: {list(payload.keys())}")

        raise NotImplementedError(
            "PICAI requires Orchestrator mode (gRPC). "
            "Ensure use_orchestrator=True is set on the AIModel record and "
            "the orchestrator-vetimage service is running."
        )

    def _validate_modalities(self, task):
        """
        Validate that all required MRI modalities are present.

        Args:
            task: AnalysisTask instance

        Raises:
            ValueError: If any required modality is missing
        """
        # Primary image must be MR modality
        primary_modality = task.input_image.series.modality
        if primary_modality and primary_modality.upper() not in ('MR', 'MRI', 'T2W'):
            raise ValueError(
                f"PICAI requires MR images. Primary image modality is '{primary_modality}'"
            )

        # ADC image is required
        parameters = task.parameters or {}
        adc_image_id = parameters.get('adc_image_id')
        if not adc_image_id:
            raise ValueError(
                "PICAI requires an ADC image. Provide 'adc_image_id' in parameters"
            )

        # Validate ADC image is MR modality
        from dicom_images.models import MedicalImage
        try:
            adc_image = MedicalImage.objects.select_related('series').get(id=adc_image_id)
            adc_modality = adc_image.series.modality
            if adc_modality and adc_modality.upper() not in ('MR', 'MRI', 'ADC'):
                raise ValueError(
                    f"ADC image must be MR modality. Got '{adc_modality}'"
                )
        except MedicalImage.DoesNotExist:
            raise ValueError(f"ADC image with ID {adc_image_id} not found")

        # HBV image is optional but validated if present
        hbv_image_id = parameters.get('hbv_image_id')
        if hbv_image_id:
            try:
                hbv_image = MedicalImage.objects.select_related('series').get(id=hbv_image_id)
                hbv_modality = hbv_image.series.modality
                if hbv_modality and hbv_modality.upper() not in ('MR', 'MRI', 'HBV', 'DWI'):
                    raise ValueError(
                        f"HBV image must be MR modality. Got '{hbv_modality}'"
                    )
            except MedicalImage.DoesNotExist:
                raise ValueError(f"HBV image with ID {hbv_image_id} not found")

        logger.debug(f"Validated PICAI modalities for task {task.id}")

    def _build_grpc_request(self, task) -> Dict[str, Any]:
        """
        Build gRPC request payload for orchestrator.

        Args:
            task: AnalysisTask instance

        Returns:
            Dict formatted for orchestrator gRPC InferenceRequest
        """
        parameters = task.parameters or {}

        # Build images array
        images = [
            {
                'modality': 't2w',
                'source': self.build_file_path(task.input_image.file),
            }
        ]

        # Add ADC image
        from dicom_images.models import MedicalImage
        adc_image_id = parameters.get('adc_image_id')
        if adc_image_id:
            adc_image = MedicalImage.objects.get(id=adc_image_id)
            images.append({
                'modality': 'adc',
                'source': self.build_file_path(adc_image.file),
            })

        # Add optional HBV image
        hbv_image_id = parameters.get('hbv_image_id')
        if hbv_image_id:
            hbv_image = MedicalImage.objects.get(id=hbv_image_id)
            images.append({
                'modality': 'hbv',
                'source': self.build_file_path(hbv_image.file),
            })

        output_format = parameters.get('output_format', 'mha')
        output_destination = parameters.get(
            'output_destination',
            f's3://vetimage-results/picai/{task.id}'
        )

        return {
            'job_id': str(task.id),
            'images': images,
            'task_type': 'segmentation',
            'output_destination': output_destination,
            'output_format': output_format,
            'timeout_seconds': self.timeout,
            'callback_url': self.get_webhook_url(task),
        }

    def validate_parameters(self, parameters: Dict) -> bool:
        """
        Validate PICAI-specific parameters.

        Args:
            parameters: Dict of task parameters

        Returns:
            True if validation passes

        Raises:
            ValueError: If validation fails
        """
        # Validate output_format
        valid_formats = ['mha', 'nifti', 'nii.gz']
        output_format = parameters.get('output_format', 'mha')
        if output_format not in valid_formats:
            raise ValueError(
                f"Invalid output_format '{output_format}'. "
                f"Must be one of: {', '.join(valid_formats)}"
            )

        # Validate ensemble_folds
        ensemble_folds = parameters.get('ensemble_folds', 5)
        if not isinstance(ensemble_folds, int) or ensemble_folds < 1 or ensemble_folds > 5:
            raise ValueError(
                f"Invalid ensemble_folds '{ensemble_folds}'. Must be an integer between 1 and 5"
            )

        return True

    def process_results(self, results: Dict) -> Dict[str, Any]:
        """
        Process results from PICAI service.

        Args:
            results: Response from orchestrator containing detection map and score

        Returns:
            Processed results for frontend display
        """
        return results

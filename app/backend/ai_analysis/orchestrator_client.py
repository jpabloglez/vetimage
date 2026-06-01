"""
Orchestrator gRPC Client

Handles communication with the orchestrator service for AI model job submission
and status tracking.
"""

import grpc
import logging
from django.conf import settings
from protos import orchestrator_pb2, orchestrator_pb2_grpc

logger = logging.getLogger(__name__)


class OrchestratorClient:
    """gRPC client for orchestrator service communication."""

    def __init__(self):
        host = settings.ORCHESTRATOR_HOST
        port = settings.ORCHESTRATOR_PORT
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = orchestrator_pb2_grpc.OrchestratorServiceStub(self.channel)

    def submit_job(self, task):
        """
        Submit analysis job to orchestrator via gRPC.

        Handles both single-image models (MIRAGE) and multi-image models (PICAI).

        Args:
            task: AnalysisTask instance

        Returns:
            dict with job_id, status, and message

        Raises:
            ConnectionError: If submission fails
        """
        # Build images list - primary image plus any additional images from parameters
        images = []

        # NIfTI-native models (e.g. FastSurfer): connector sets nifti_path in parameters
        nifti_path = task.parameters.get('nifti_path')
        if nifti_path:
            images.append(orchestrator_pb2.ImageInput(
                modality='t1w',
                source=nifti_path
            ))
        else:
            # For PICAI-like models: check if we have T2, ADC, HBV image IDs in parameters
            from dicom_images.models import MedicalImage

            # Handle T2 image (or primary image for single-image models)
            t2_image_id = task.parameters.get('t2_image_id')
            if t2_image_id:
                t2_image = MedicalImage.objects.get(id=t2_image_id)
                images.append(orchestrator_pb2.ImageInput(
                    modality='t2w',
                    source=self._build_file_path(t2_image.file)
                ))
            else:
                # Use primary input_image; derive modality from model's first supported modality
                # (falls back to 't2w' for PICAI-style models without explicit parameter)
                supported = getattr(task.model, 'supported_modalities', None)
                default_modality = (supported[0].lower() if supported else 't2w')
                images.append(orchestrator_pb2.ImageInput(
                    modality=task.parameters.get('modality', default_modality),
                    source=self._build_file_path(task.input_image.file)
                ))

            # Handle ADC image
            adc_image_id = task.parameters.get('adc_image_id')
            if adc_image_id:
                adc_image = MedicalImage.objects.get(id=adc_image_id)
                images.append(orchestrator_pb2.ImageInput(
                    modality='adc',
                    source=self._build_file_path(adc_image.file)
                ))

            # Handle HBV image (optional for PICAI)
            hbv_image_id = task.parameters.get('hbv_image_id')
            if hbv_image_id:
                hbv_image = MedicalImage.objects.get(id=hbv_image_id)
                images.append(orchestrator_pb2.ImageInput(
                    modality='hbv',
                    source=self._build_file_path(hbv_image.file)
                ))

        # Build metadata: always include task/user IDs; forward connector-specific
        # runtime params so the gRPC adapter can pass them to the service.
        metadata = {
            'openmedlab_task_id': str(task.id),
            'user_id': str(task.created_by_id),
        }
        # Forward any model-specific runtime parameters as string metadata
        for param_key in ('device', 'threads', 'use_3T'):
            val = task.parameters.get(param_key)
            if val is not None:
                metadata[param_key] = str(val)

        request = orchestrator_pb2.SubmitJobRequest(
            images=images,
            task_type=task.parameters.get('task_type', 'segmentation'),
            model_name=task.model.key.split('-')[0],
            model_size=task.parameters.get('model_size', 'standard'),
            output_destination=f'/var/www/app/backend/media/ai_results/{task.id}',
            output_format=task.parameters.get('output_format', 'npy'),
            metadata=metadata,
        )

        try:
            response = self.stub.SubmitJob(request, timeout=10)
            return {
                'job_id': response.job_id,
                'status': self._map_status_from_proto(response.status),
                'message': response.message
            }
        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e.code()} - {e.details()}")
            raise ConnectionError(f"Orchestrator submission failed: {e.details()}")

    def get_job_status(self, job_id):
        """
        Get current status of orchestrator job.

        Args:
            job_id: Orchestrator job ID

        Returns:
            dict with status information

        Raises:
            ConnectionError: If status check fails
        """
        request = orchestrator_pb2.GetJobStatusRequest(job_id=job_id)

        try:
            response = self.stub.GetJobStatus(request, timeout=5)
            return {
                'job_id': response.job_id,
                'status': self._map_status_from_proto(response.status),
                'output_uri': response.output_uri,
                'output_keys': list(response.output_keys),
                'error_message': response.error_message,
                'progress_percent': response.progress_percent,
                'result_metadata': dict(response.result_metadata)
            }
        except grpc.RpcError as e:
            logger.error(f"Status check error: {e.code()}")
            raise ConnectionError(f"Failed to get job status: {e.details()}")

    def _map_status_from_proto(self, proto_status):
        """Map orchestrator JobStatus to OpenMedLab status."""
        mapping = {
            orchestrator_pb2.JOB_STATUS_QUEUED: 'QUEUED',
            orchestrator_pb2.JOB_STATUS_PROCESSING: 'PROCESSING',
            orchestrator_pb2.JOB_STATUS_COMPLETED: 'COMPLETED',
            orchestrator_pb2.JOB_STATUS_FAILED: 'FAILED',
            orchestrator_pb2.JOB_STATUS_CANCELLED: 'CANCELLED'
        }
        return mapping.get(proto_status, 'PENDING')

    def _build_file_path(self, file_field):
        """Convert Django FileField to container path."""
        if not file_field:
            return None
        return f'/var/www/app/backend/media/{file_field.name}'

    def close(self):
        """Close gRPC channel."""
        if self.channel:
            self.channel.close()

"""
Orchestrator gRPC Server

Implements the OrchestratorService gRPC interface.
"""

import logging
import time

import grpc

# Import generated proto stubs
try:
    from orchestrator_pb2 import (
        SubmitJobResponse, JobStatusResponse, ListModelsResponse,
        HealthCheckResponse, ModelInfo, ModelHealth, JobStatus, ErrorCode
    )
    from orchestrator_pb2_grpc import OrchestratorServiceServicer
except ImportError:
    logging.warning("Proto stubs not yet generated. Run 'make proto' in protos/ directory.")
    SubmitJobResponse = None
    JobStatusResponse = None
    ListModelsResponse = None
    HealthCheckResponse = None
    ModelInfo = None
    ModelHealth = None
    JobStatus = None
    ErrorCode = None
    OrchestratorServiceServicer = object

from orchestrator.job_queue import JobQueueManager
from orchestrator.model_registry import ModelRegistry
from orchestrator.file_handler import FilePathHandler


logger = logging.getLogger(__name__)


class OrchestratorServiceImpl(OrchestratorServiceServicer):
    """Implementation of OrchestratorService gRPC interface"""

    def __init__(self, job_queue: JobQueueManager, model_registry: ModelRegistry):
        """
        Initialize gRPC service

        Args:
            job_queue: Job queue manager
            model_registry: Model registry
        """
        self.job_queue = job_queue
        self.model_registry = model_registry
        logger.info("OrchestratorServiceImpl initialized")

    def SubmitJob(self, request, context):
        """
        Handle job submission

        Args:
            request: SubmitJobRequest
            context: gRPC context

        Returns:
            SubmitJobResponse
        """
        if SubmitJobResponse is None:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Proto stubs not generated")
            return

        try:
            logger.info(f"Received job submission: task={request.task_type}, model={request.model_name}")

            # Validate request
            validation_error = self._validate_submit_request(request)
            if validation_error:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(validation_error)
                return SubmitJobResponse(
                    job_id="",
                    status=JobStatus.JOB_STATUS_FAILED,
                    message=validation_error
                )

            # Extract modalities from images
            modalities = [img.modality for img in request.images]

            # Select model
            model_name = self.model_registry.select_model(
                task_type=request.task_type,
                modalities=modalities,
                model_name=request.model_name if request.model_name else None
            )

            if not model_name:
                error_msg = f"No healthy model available for task={request.task_type}, modalities={modalities}"
                logger.error(error_msg)
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                context.set_details(error_msg)
                return SubmitJobResponse(
                    job_id="",
                    status=JobStatus.JOB_STATUS_FAILED,
                    message=error_msg
                )

            # Prepare job data
            job_data = {
                "model_service": model_name,
                "task_type": request.task_type,
                "model_size": request.model_size or "base",
                "input_images": [
                    {"modality": img.modality, "source": img.source}
                    for img in request.images
                ],
                "output_destination": request.output_destination,
                "output_format": request.output_format or "",
                "num_classes": request.num_classes,
                "class_names": list(request.class_names) if request.class_names else [],
                "metadata": dict(request.metadata) if request.metadata else {}
            }

            # Enqueue job
            job_id = self.job_queue.enqueue_job(job_data)

            logger.info(f"Job {job_id} enqueued successfully for model {model_name}")

            return SubmitJobResponse(
                job_id=job_id,
                status=JobStatus.JOB_STATUS_QUEUED,
                message=f"Job submitted successfully to model '{model_name}'"
            )

        except Exception as e:
            logger.error(f"Error submitting job: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return SubmitJobResponse(
                job_id="",
                status=JobStatus.JOB_STATUS_FAILED,
                message=f"Internal error: {str(e)}"
            )

    def GetJobStatus(self, request, context):
        """
        Get job status

        Args:
            request: GetJobStatusRequest
            context: gRPC context

        Returns:
            JobStatusResponse
        """
        if JobStatusResponse is None:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Proto stubs not generated")
            return

        try:
            job_id = request.job_id
            logger.debug(f"Getting status for job {job_id}")

            # Get job from queue
            job_data = self.job_queue.get_job(job_id)

            if not job_data:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Job {job_id} not found")
                return JobStatusResponse(
                    job_id=job_id,
                    status=JobStatus.JOB_STATUS_UNSPECIFIED,
                    error_message="Job not found",
                    error_code=ErrorCode.ERROR_CODE_UNSPECIFIED
                )

            # Map status string to enum
            status_map = {
                "queued": JobStatus.JOB_STATUS_QUEUED,
                "processing": JobStatus.JOB_STATUS_PROCESSING,
                "completed": JobStatus.JOB_STATUS_COMPLETED,
                "failed": JobStatus.JOB_STATUS_FAILED,
                "cancelled": JobStatus.JOB_STATUS_CANCELLED
            }
            status = status_map.get(job_data.get('status', ''), JobStatus.JOB_STATUS_UNSPECIFIED)

            # Map error code string to enum
            error_code_map = {
                "ERROR_CODE_INVALID_INPUT": ErrorCode.ERROR_CODE_INVALID_INPUT,
                "ERROR_CODE_MODEL_UNAVAILABLE": ErrorCode.ERROR_CODE_MODEL_UNAVAILABLE,
                "ERROR_CODE_INFERENCE_FAILED": ErrorCode.ERROR_CODE_INFERENCE_FAILED,
                "ERROR_CODE_STORAGE_ERROR": ErrorCode.ERROR_CODE_STORAGE_ERROR,
                "ERROR_CODE_TIMEOUT": ErrorCode.ERROR_CODE_TIMEOUT,
                "ERROR_CODE_RESOURCE_EXHAUSTED": ErrorCode.ERROR_CODE_RESOURCE_EXHAUSTED,
            }
            error_code = error_code_map.get(
                job_data.get('error_code', ''),
                ErrorCode.ERROR_CODE_UNSPECIFIED
            )

            # Build response
            response = JobStatusResponse(
                job_id=job_id,
                status=status,
                model_service=job_data.get('model_service', ''),
                output_uri=job_data.get('output_uri', ''),
                output_keys=job_data.get('output_keys', []),
                error_message=job_data.get('error_message', ''),
                error_code=error_code,
                created_at=int(job_data.get('created_at', 0)),
                updated_at=int(job_data.get('updated_at', 0)),
                started_at=int(job_data.get('started_at', 0)),
                completed_at=int(job_data.get('completed_at', 0)),
                progress_percent=float(job_data.get('progress_percent', 0.0)),
                progress_message=job_data.get('progress_message', '')
            )

            return response

        except Exception as e:
            logger.error(f"Error getting job status: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return JobStatusResponse(
                job_id=request.job_id,
                status=JobStatus.JOB_STATUS_UNSPECIFIED,
                error_message=f"Internal error: {str(e)}",
                error_code=ErrorCode.ERROR_CODE_UNSPECIFIED
            )

    def StreamJobStatus(self, request, context):
        """
        Stream job status updates (future enhancement)

        Args:
            request: GetJobStatusRequest
            context: gRPC context

        Yields:
            JobStatusResponse
        """
        # TODO: Implement streaming job status
        # For now, just yield current status once
        status = self.GetJobStatus(request, context)
        yield status

    def ListModels(self, request, context):
        """
        List available models

        Args:
            request: ListModelsRequest
            context: gRPC context

        Returns:
            ListModelsResponse
        """
        if ListModelsResponse is None:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Proto stubs not generated")
            return

        try:
            logger.debug(f"Listing models (only_healthy={request.only_healthy})")

            models = self.model_registry.list_models(only_healthy=request.only_healthy)

            # Convert to proto messages
            model_infos = []
            for model in models:
                model_info = ModelInfo(
                    name=model['name'],
                    version=model['version'],
                    supported_tasks=model['supported_tasks'],
                    supported_modalities=model['supported_modalities'],
                    is_healthy=model['is_healthy'],
                    endpoint=model['endpoint']
                )
                model_infos.append(model_info)

            logger.info(f"Returning {len(model_infos)} models")

            return ListModelsResponse(models=model_infos)

        except Exception as e:
            logger.error(f"Error listing models: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ListModelsResponse(models=[])

    def HealthCheck(self, request, context):
        """
        Orchestrator health check

        Args:
            request: HealthCheckRequest
            context: gRPC context

        Returns:
            HealthCheckResponse
        """
        if HealthCheckResponse is None:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Proto stubs not generated")
            return

        try:
            logger.debug("Health check requested")

            # Check Redis connectivity
            redis_healthy = self._check_redis_health()

            # Get model health
            models = self.model_registry.list_models(only_healthy=False)
            model_health_list = []

            for model in models:
                model_health = ModelHealth(
                    model_name=model['name'],
                    is_healthy=model['is_healthy'],
                    last_check_time=int(time.time())
                )
                model_health_list.append(model_health)

            # Get queue stats
            queue_stats = self.job_queue.get_queue_stats()

            # Overall health
            overall_healthy = (
                redis_healthy and
                any(m.is_healthy for m in model_health_list)  # At least one model healthy
            )

            response = HealthCheckResponse(
                healthy=overall_healthy,
                version="1.0.0",
                active_jobs=queue_stats.get('processing', 0),
                queued_jobs=queue_stats.get('queued', 0),
                model_health=model_health_list
            )

            logger.info(f"Health check: healthy={overall_healthy}, queued={queue_stats.get('queued', 0)}, processing={queue_stats.get('processing', 0)}")

            return response

        except Exception as e:
            logger.error(f"Health check error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return HealthCheckResponse(
                healthy=False,
                version="1.0.0",
                active_jobs=0,
                queued_jobs=0,
                model_health=[]
            )

    def _validate_submit_request(self, request) -> str:
        """
        Validate SubmitJobRequest

        Args:
            request: SubmitJobRequest

        Returns:
            Error message string, or empty string if valid
        """
        # Check images
        if not request.images:
            return "At least one input image required"

        # Validate image sources
        for img in request.images:
            if not img.source:
                return f"Image source cannot be empty for modality '{img.modality}'"

            try:
                source_type = FilePathHandler.detect_source_type(img.source)
                if source_type == 's3':
                    FilePathHandler.validate_s3_uri(img.source)
                else:
                    FilePathHandler.validate_local_path(img.source, allow_relative=True)
            except ValueError as e:
                return f"Invalid image source: {str(e)}"

        # Check task type
        if not request.task_type:
            return "Task type is required"

        # Check output destination
        if not request.output_destination:
            return "Output destination is required"

        try:
            FilePathHandler.validate_output_destination(request.output_destination)
        except ValueError as e:
            return f"Invalid output destination: {str(e)}"

        # Validate classification-specific requirements
        if request.task_type == "classification":
            if request.num_classes <= 0:
                return "num_classes is required for classification tasks"
            if len(request.images) != 1:
                return "Classification requires exactly one input modality"

        return ""  # Valid

    def _check_redis_health(self) -> bool:
        """Check if Redis is healthy"""
        try:
            self.job_queue.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

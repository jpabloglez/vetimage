"""
Background Job Worker

Processes jobs from the Redis queue by calling model services via gRPC.
"""

import logging
import threading
import time
from typing import Optional

import grpc

# Import generated proto stubs
try:
    from model_service_pb2 import InferenceRequest, ImageInput
    from model_service_pb2_grpc import ModelServiceStub
except ImportError:
    logging.warning("Proto stubs not yet generated. Run 'make proto' in protos/ directory.")
    InferenceRequest = None
    ImageInput = None
    ModelServiceStub = None

from orchestrator.job_queue import JobQueueManager
from orchestrator.model_registry import ModelRegistry


logger = logging.getLogger(__name__)


class JobWorker:
    """Background worker to process jobs from queue"""

    def __init__(self, job_queue: JobQueueManager, model_registry: ModelRegistry, num_workers: int = 1):
        """
        Initialize job worker

        Args:
            job_queue: Job queue manager
            model_registry: Model registry
            num_workers: Number of worker threads
        """
        self.job_queue = job_queue
        self.model_registry = model_registry
        self.num_workers = num_workers
        self.threads = []
        self.running = False

        logger.info(f"JobWorker initialized with {num_workers} worker(s)")

    def start(self):
        """Start worker threads"""
        if self.running:
            logger.warning("JobWorker already running")
            return

        self.running = True

        for i in range(self.num_workers):
            thread = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
            thread.start()
            self.threads.append(thread)
            logger.info(f"Started worker thread {i}")

        logger.info(f"All {self.num_workers} worker threads started")

    def stop(self):
        """Stop worker threads"""
        logger.info("Stopping worker threads...")
        self.running = False

        # Wait for threads to finish
        for i, thread in enumerate(self.threads):
            thread.join(timeout=5)
            if thread.is_alive():
                logger.warning(f"Worker thread {i} did not stop gracefully")
            else:
                logger.info(f"Worker thread {i} stopped")

        self.threads = []
        logger.info("All worker threads stopped")

    def _worker_loop(self, worker_id: int):
        """
        Main worker loop

        Args:
            worker_id: Worker thread ID
        """
        logger.info(f"Worker {worker_id} started")

        while self.running:
            try:
                # Pop job from queue
                job_id = self.job_queue.dequeue_job()

                if not job_id:
                    # Queue empty, sleep and retry
                    time.sleep(1)
                    continue

                logger.info(f"Worker {worker_id} picked up job {job_id}")

                # Process job
                self._process_job(job_id, worker_id)

            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
                time.sleep(1)

        logger.info(f"Worker {worker_id} stopped")

    def _process_job(self, job_id: str, worker_id: int):
        """
        Process a single job

        Args:
            job_id: Job UUID
            worker_id: Worker thread ID
        """
        try:
            # Get job details
            job_data = self.job_queue.get_job(job_id)
            if not job_data:
                logger.error(f"Worker {worker_id}: Job {job_id} not found in queue")
                return

            model_name = job_data.get('model_service')
            if not model_name:
                self.job_queue.set_error(
                    job_id,
                    "No model service specified",
                    "ERROR_CODE_INVALID_INPUT"
                )
                return

            # Get model service stub
            stub = self.model_registry.get_model_stub(model_name)
            if not stub:
                self.job_queue.set_error(
                    job_id,
                    f"Model service '{model_name}' unavailable",
                    "ERROR_CODE_MODEL_UNAVAILABLE"
                )
                return

            # Build gRPC request
            request = self._build_grpc_request(job_data)
            if not request:
                self.job_queue.set_error(
                    job_id,
                    "Failed to build gRPC request",
                    "ERROR_CODE_INVALID_INPUT"
                )
                return

            # Call model service with retry
            logger.info(f"Worker {worker_id}: Calling model service '{model_name}' for job {job_id}")
            response, error = self._call_model_service_with_retry(stub, request, max_retries=3)

            if response:
                # Success
                self._handle_success(job_id, response)
                self.model_registry.record_success(model_name)
                logger.info(f"Worker {worker_id}: Job {job_id} completed successfully")

            else:
                # Failure
                self._handle_failure(job_id, error or "Unknown error")
                self.model_registry.record_failure(model_name)
                logger.error(f"Worker {worker_id}: Job {job_id} failed: {error}")

        except Exception as e:
            logger.error(f"Worker {worker_id}: Job {job_id} processing failed: {e}", exc_info=True)
            self.job_queue.set_error(
                job_id,
                f"Processing error: {str(e)}",
                "ERROR_CODE_INFERENCE_FAILED"
            )

    def _build_grpc_request(self, job_data: dict):
        """
        Build gRPC InferenceRequest from job data

        Args:
            job_data: Job metadata dictionary

        Returns:
            InferenceRequest or None
        """
        if InferenceRequest is None or ImageInput is None:
            logger.error("Cannot build gRPC request - proto stubs not generated")
            return None

        try:
            # Parse input images
            input_images_data = job_data.get('input_images', [])
            if isinstance(input_images_data, str):
                import json
                input_images_data = json.loads(input_images_data)

            # Build ImageInput messages
            image_inputs = []
            for img in input_images_data:
                image_inputs.append(ImageInput(
                    modality=img.get('modality', ''),
                    source=img.get('source', '')
                ))

            # Parse class names
            class_names_data = job_data.get('class_names', [])
            if isinstance(class_names_data, str):
                import json
                class_names_data = json.loads(class_names_data)

            # Build request
            request = InferenceRequest(
                job_id=job_data.get('job_id'),
                images=image_inputs,
                task_type=job_data.get('task_type', ''),
                model_size=job_data.get('model_size', 'base'),
                output_destination=job_data.get('output_destination', ''),
                output_format=job_data.get('output_format', ''),
                num_classes=int(job_data.get('num_classes', 0)),
                class_names=class_names_data,
                timeout_seconds=300  # 5 minutes default
            )

            logger.debug(f"Built gRPC request for job {job_data.get('job_id')}")
            return request

        except Exception as e:
            logger.error(f"Failed to build gRPC request: {e}", exc_info=True)
            return None

    def _call_model_service_with_retry(self, stub: ModelServiceStub, request,
                                        max_retries: int = 3) -> tuple:
        """
        Call model service with exponential backoff retry

        Args:
            stub: gRPC model service stub
            request: InferenceRequest
            max_retries: Maximum retry attempts

        Returns:
            Tuple of (response, error_message)
        """
        for attempt in range(max_retries):
            try:
                # Call with timeout
                response = stub.RunInference(request, timeout=request.timeout_seconds)

                # Check response status
                if response.status == 2:  # INFERENCE_STATUS_COMPLETED
                    return response, None
                elif response.status == 3:  # INFERENCE_STATUS_FAILED
                    return None, response.error_message or "Inference failed"
                else:
                    return None, f"Unexpected status: {response.status}"

            except grpc.RpcError as e:
                error_code = e.code()

                if error_code == grpc.StatusCode.UNAVAILABLE:
                    # Service down, retry with backoff
                    wait_time = min(2 ** attempt, 30)  # Cap at 30s
                    logger.warning(
                        f"Model service unavailable, retry {attempt + 1}/{max_retries} "
                        f"after {wait_time}s"
                    )
                    time.sleep(wait_time)
                    continue

                elif error_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    # Timeout, don't retry
                    logger.error("Model service timeout")
                    return None, "TIMEOUT"

                elif error_code == grpc.StatusCode.RESOURCE_EXHAUSTED:
                    # GPU OOM or quota exceeded
                    logger.error("Model service resource exhausted")
                    return None, "RESOURCE_EXHAUSTED"

                else:
                    # Other error, don't retry
                    logger.error(f"Model service error: {error_code} - {e.details()}")
                    return None, f"SERVICE_ERROR: {e.details()}"

            except Exception as e:
                logger.error(f"Unexpected error calling model service: {e}", exc_info=True)
                return None, f"UNEXPECTED_ERROR: {str(e)}"

        # All retries failed
        return None, "MAX_RETRIES_EXCEEDED"

    def _handle_success(self, job_id: str, response):
        """
        Handle successful inference

        Args:
            job_id: Job UUID
            response: InferenceResponse from model service
        """
        # Extract output URIs
        output_keys = [artifact.key for artifact in response.outputs]
        output_uri = response.outputs[0].uri if response.outputs else ""

        # Extract base URI (remove filename)
        if output_uri and '/' in output_uri:
            # For S3: s3://bucket/prefix/job_id/file.npy -> s3://bucket/prefix/job_id
            # For local: /path/to/job_id/file.npy -> /path/to/job_id
            parts = output_uri.rsplit('/', 1)
            base_uri = parts[0]
        else:
            base_uri = output_uri

        # Mark job as completed
        self.job_queue.set_result(job_id, base_uri, output_keys)

    def _handle_failure(self, job_id: str, error_message: str):
        """
        Handle failed inference

        Args:
            job_id: Job UUID
            error_message: Error description
        """
        # Map error message to error code
        if "TIMEOUT" in error_message:
            error_code = "ERROR_CODE_TIMEOUT"
        elif "RESOURCE_EXHAUSTED" in error_message:
            error_code = "ERROR_CODE_RESOURCE_EXHAUSTED"
        elif "MODEL_UNAVAILABLE" in error_message or "UNAVAILABLE" in error_message:
            error_code = "ERROR_CODE_MODEL_UNAVAILABLE"
        else:
            error_code = "ERROR_CODE_INFERENCE_FAILED"

        self.job_queue.set_error(job_id, error_message, error_code)

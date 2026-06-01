"""
Celery Tasks for AI Analysis Orchestration

This module defines asynchronous Celery tasks for:
- Dispatching AI analysis jobs to external services
- Monitoring task timeouts
- Cleaning up old completed tasks
"""

from celery import shared_task
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from .models import AnalysisTask
from .connectors.factory import ConnectorFactory
import logging

logger = logging.getLogger(__name__)


def _create_task_notification(task, notification_type, message, link=''):
    """Create a notification for the task owner."""
    try:
        from credentials.models import Notification
        if task.created_by_id:
            Notification.objects.create(
                user_id=task.created_by_id,
                message=message,
                notification_type=notification_type,
                link=link,
            )
    except Exception as e:
        logger.warning(f"Failed to create notification for task {task.id}: {e}")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 60 seconds
    retry_backoff=True,  # Exponential backoff: 60s, 120s, 240s
    retry_backoff_max=600,  # Max 10 minutes between retries
    retry_jitter=True  # Add random jitter to prevent thundering herd
)
def dispatch_ai_job(self, task_id):
    """
    Celery task to dispatch analysis job to AI service.

    This task:
    1. Retrieves the AnalysisTask from database
    2. Creates appropriate connector using ConnectorFactory
    3. Validates parameters
    4. Dispatches job to AI service via HTTP
    5. Updates task status and service_job_id

    Retry strategy:
    - Automatic retry on TimeoutError and ConnectionError
    - 3 attempts with exponential backoff (60s, 120s, 240s)
    - No retry on ValueError (configuration errors)

    Args:
        task_id: UUID of the AnalysisTask

    Returns:
        None (task status is updated in database)
    """
    try:
        # Fetch task from database
        task = AnalysisTask.objects.get(id=task_id)

        logger.info(f"Processing task {task_id} for model {task.model.key}")

        # Update status to QUEUED and store Celery task ID
        task.status = 'QUEUED'
        task.celery_task_id = self.request.id
        task.save(update_fields=['status', 'celery_task_id'])

        # Create connector for this AI model
        connector = ConnectorFactory.create(task.model)

        # Validate parameters before dispatch
        connector.validate_parameters(task.parameters)

        logger.debug(
            f"Task {task_id}: Dispatching to {task.model.name} "
            f"at {task.model.endpoint_url}"
        )

        # Dispatch job to AI service
        result = connector.dispatch_job(task)

        # Update task with service job ID and status
        task.status = 'DISPATCHED'
        task.service_job_id = result.get('service_job_id')
        task.dispatched_at = timezone.now()
        task.save(update_fields=['status', 'service_job_id', 'dispatched_at'])

        logger.info(
            f"Task {task_id} dispatched successfully. "
            f"Service job ID: {result.get('service_job_id')}"
        )

        # Start polling for MIRAGE jobs (which don't support webhooks)
        if task.model.key.startswith('mirage'):
            logger.info(f"Starting status polling for MIRAGE task {task_id}")
            poll_mirage_job_status.apply_async(
                args=[str(task_id)],
                countdown=5  # Start polling after 5 seconds
            )

    except AnalysisTask.DoesNotExist:
        logger.error(f"Task {task_id} does not exist. Cannot dispatch.")
        return

    except (TimeoutError, ConnectionError) as e:
        # Retryable errors - network issues, service temporarily down
        logger.warning(
            f"Retryable error for task {task_id} (attempt {self.request.retries + 1}/3): {e}"
        )

        # Update task status back to PENDING for retry
        task = AnalysisTask.objects.get(id=task_id)
        task.status = 'PENDING'
        task.retry_count += 1
        task.save(update_fields=['status', 'retry_count'])

        # Retry with exponential backoff
        raise self.retry(exc=e)

    except ValueError as e:
        # Non-retryable errors - configuration issues, invalid parameters
        logger.error(
            f"Task {task_id} failed with non-retryable error: {e}",
            exc_info=True
        )

        task = AnalysisTask.objects.get(id=task_id)
        task.status = 'FAILED'
        task.error_message = str(e)
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'error_message', 'completed_at'])
        _create_task_notification(
            task, 'error',
            f'Analysis "{task.model.name}" failed: {str(e)[:100]}',
            link='/monitor',
        )

    except Exception as e:
        # Unexpected errors - log and mark as failed
        logger.error(
            f"Task {task_id} failed with unexpected error: {e}",
            exc_info=True
        )

        task = AnalysisTask.objects.get(id=task_id)
        task.status = 'FAILED'
        task.error_message = f"Unexpected error: {str(e)}"
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'error_message', 'completed_at'])
        _create_task_notification(
            task, 'error',
            f'Analysis "{task.model.name}" failed unexpectedly.',
            link='/monitor',
        )


@shared_task
def check_task_timeouts():
    """
    Periodic task to mark stalled tasks as TIMEOUT.

    This task runs every 10 minutes (configured in celery.py) and:
    1. Finds tasks in DISPATCHED or PROCESSING status
    2. Checks if they've exceeded the model's timeout_seconds
    3. Marks timed-out tasks as TIMEOUT

    This is a safety mechanism in case:
    - AI service crashes without sending webhook
    - Webhook fails to deliver
    - Network issues prevent communication

    Returns:
        Number of tasks marked as TIMEOUT
    """
    logger.info("Checking for timed-out analysis tasks...")

    # Default timeout if not specified
    default_timeout = getattr(settings, 'AI_TASK_DEFAULT_TIMEOUT', 1800)

    # Find potentially stalled tasks
    stalled_tasks = AnalysisTask.objects.filter(
        status__in=['DISPATCHED', 'PROCESSING'],
        dispatched_at__isnull=False
    ).select_related('model')

    timeout_count = 0

    for task in stalled_tasks:
        # Get timeout from model or use default
        timeout_seconds = task.model.timeout_seconds if task.model else default_timeout

        # Calculate cutoff time
        cutoff_time = timezone.now() - timedelta(seconds=timeout_seconds)

        # Check if task has exceeded timeout
        if task.dispatched_at < cutoff_time:
            logger.warning(
                f"Task {task.id} exceeded timeout of {timeout_seconds}s. "
                f"Marking as TIMEOUT."
            )

            task.status = 'TIMEOUT'
            task.error_message = f'Task exceeded maximum processing time ({timeout_seconds}s)'
            task.completed_at = timezone.now()
            task.save(update_fields=['status', 'error_message', 'completed_at'])
            _create_task_notification(
                task, 'warning',
                f'Analysis "{task.model.name}" timed out after {timeout_seconds}s.',
                link='/monitor',
            )

            timeout_count += 1

    if timeout_count > 0:
        logger.info(f"Marked {timeout_count} tasks as TIMEOUT")
    else:
        logger.debug("No timed-out tasks found")

    return timeout_count


@shared_task
def cleanup_old_tasks():
    """
    Daily task to delete old completed/failed tasks.

    This task runs daily at 2 AM (configured in celery.py) and:
    1. Finds tasks in terminal states (COMPLETED, FAILED, TIMEOUT, CANCELLED)
    2. Older than AI_TASK_CLEANUP_DAYS (default: 30 days)
    3. Deletes them to prevent database bloat

    Note: This only deletes task records, not result files.
    Result file cleanup should be handled separately.

    Returns:
        Number of tasks deleted
    """
    cleanup_days = getattr(settings, 'AI_TASK_CLEANUP_DAYS', 30)

    logger.info(f"Cleaning up analysis tasks older than {cleanup_days} days...")

    # Calculate cutoff date
    cutoff_date = timezone.now() - timedelta(days=cleanup_days)

    # Find old terminal tasks
    old_tasks = AnalysisTask.objects.filter(
        status__in=['COMPLETED', 'FAILED', 'TIMEOUT', 'CANCELLED'],
        completed_at__lt=cutoff_date
    )

    count = old_tasks.count()

    if count > 0:
        # Delete tasks
        old_tasks.delete()
        logger.info(f"Deleted {count} old analysis tasks")
    else:
        logger.debug("No old tasks to clean up")

    return count


@shared_task
def retry_failed_task(task_id):
    """
    Manually retry a failed task.

    This can be called from the API or admin interface to retry a task
    that failed or timed out.

    Args:
        task_id: UUID of the AnalysisTask to retry

    Returns:
        New Celery task ID if retry initiated, None otherwise
    """
    try:
        task = AnalysisTask.objects.get(id=task_id)

        # Check if task can be retried
        if not task.can_retry:
            logger.warning(
                f"Task {task_id} cannot be retried. "
                f"Status: {task.status}, Retry count: {task.retry_count}/{task.model.max_retries}"
            )
            return None

        logger.info(f"Manually retrying task {task_id}")

        # Reset task state
        task.status = 'PENDING'
        task.error_message = ''
        task.retry_count += 1
        task.celery_task_id = None
        task.service_job_id = None
        task.dispatched_at = None
        task.started_processing_at = None
        task.completed_at = None
        task.save()

        # Dispatch new Celery task
        result = dispatch_ai_job.delay(str(task_id))

        logger.info(f"Task {task_id} retry initiated with Celery task ID: {result.id}")

        return result.id

    except AnalysisTask.DoesNotExist:
        logger.error(f"Cannot retry task {task_id}: Task does not exist")
        return None


@shared_task(
    bind=True,
    max_retries=60,  # Poll up to 60 times
    default_retry_delay=5,  # Poll every 5 seconds
    retry_backoff=False  # Don't increase delay
)
def poll_mirage_job_status(self, task_id):
    """
    Celery task to poll MIRAGE service for job status.

    This task is used for AI services that don't support webhooks.
    It polls the service periodically until the job completes or times out.

    Polling strategy:
    - Poll every 5 seconds
    - Up to 60 attempts (5 minutes total)
    - Updates task status based on service response

    Args:
        task_id: UUID of the AnalysisTask

    Returns:
        None (task status is updated in database)
    """
    try:
        # Fetch task from database
        task = AnalysisTask.objects.select_related('model').get(id=task_id)

        # Only poll if task is still in progress
        if task.status not in ['DISPATCHED', 'PROCESSING']:
            logger.info(f"Task {task_id} is in terminal state {task.status}, stopping poll")
            return

        # Create connector for this AI model
        connector = ConnectorFactory.create(task.model)

        # Poll job status
        logger.debug(f"Polling status for task {task_id}, service job {task.service_job_id}")
        result = connector.poll_job_status(task)

        service_status = result.get('status', '').lower()

        # Map service status to our status codes
        if service_status == 'completed':
            logger.info(f"Task {task_id} completed successfully")
            task.status = 'COMPLETED'
            task.result_data = result.get('result', {})
            task.result_uri = result.get('output_uri')
            task.completed_at = timezone.now()
            task.save(update_fields=['status', 'result_data', 'result_uri', 'completed_at'])
            _create_task_notification(
                task, 'success',
                f'Analysis "{task.model.name}" completed successfully.',
                link=f'/monitor',
            )

        elif service_status == 'failed':
            error_message = result.get('error', 'Unknown error')
            logger.error(f"Task {task_id} failed: {error_message}")
            task.status = 'FAILED'
            task.error_message = error_message
            task.completed_at = timezone.now()
            task.save(update_fields=['status', 'error_message', 'completed_at'])
            _create_task_notification(
                task, 'error',
                f'Analysis "{task.model.name}" failed: {error_message[:100]}',
                link=f'/monitor',
            )

        elif service_status == 'processing':
            # Update status to PROCESSING if not already
            if task.status != 'PROCESSING':
                logger.info(f"Task {task_id} is now processing")
                task.status = 'PROCESSING'
                task.started_processing_at = timezone.now()
                task.save(update_fields=['status', 'started_processing_at'])

            # Continue polling
            raise self.retry(countdown=5)

        elif service_status == 'queued':
            # Still queued, continue polling
            raise self.retry(countdown=5)

        else:
            # Unknown status, log and continue polling
            logger.warning(f"Task {task_id} has unknown status: {service_status}")
            raise self.retry(countdown=5)

    except AnalysisTask.DoesNotExist:
        logger.error(f"Task {task_id} does not exist. Cannot poll status.")
        return

    except ConnectionError as e:
        # Service unavailable, retry polling
        logger.warning(f"Could not poll task {task_id}: {e}")
        raise self.retry(countdown=10, exc=e)

    except self.MaxRetriesExceededError:
        # Polling timed out
        logger.error(f"Task {task_id} polling timed out after {self.max_retries} attempts")
        task = AnalysisTask.objects.get(id=task_id)
        task.status = 'TIMEOUT'
        task.error_message = 'Job polling timed out - service may be unresponsive'
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'error_message', 'completed_at'])

    except Exception as e:
        logger.error(f"Unexpected error polling task {task_id}: {e}", exc_info=True)
        # Don't fail the task yet, continue polling
        raise self.retry(countdown=5, exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    retry_backoff=True,
)
def create_dicom_seg_task(self, analysis_task_id: str):
    """
    Post-process a completed segmentation task by converting its NIfTI result
    to a DICOM SEG object and uploading it to Orthanc.

    Triggered automatically after a segmentation task reaches COMPLETED status
    when the model has a non-empty ``label_map``.

    Steps:
      1. Resolve the NIfTI mask path from ``task.result_file_path``.
      2. Build dcmqi metadata from ``task.model.label_map``.
      3. Run ``itkimage2segimage`` to produce a DICOM SEG (.dcm).
      4. Upload the SEG to Orthanc.
      5. Read ``SeriesInstanceUID`` from the generated file.
      6. Store ``dicom_seg_series_uid`` and ``dicom_seg_orthanc_id`` in
         ``task.result_metadata``.

    Args:
        analysis_task_id: UUID string of the ``AnalysisTask``.
    """
    from pathlib import Path

    import pydicom

    from .models import AnalysisTask
    from .services.dicom_seg import create_dicom_seg
    from .services.orthanc_client import upload_dicom_to_orthanc

    try:
        task = AnalysisTask.objects.select_related(
            "model", "input_image__series"
        ).get(id=analysis_task_id)
    except AnalysisTask.DoesNotExist:
        logger.error("create_dicom_seg_task: task %s not found", analysis_task_id)
        return

    # Guard: needs a result file
    if not task.result_file_path:
        logger.info(
            "create_dicom_seg_task: task %s has no result_file_path — skipping",
            analysis_task_id,
        )
        return

    # Guard: needs a label map
    label_map = (task.model.label_map or {}) if task.model else {}
    if not label_map:
        logger.info(
            "create_dicom_seg_task: model %s has no label_map — skipping",
            task.model.key if task.model else "None",
        )
        return

    # Resolve NIfTI absolute path (result_file_path may be relative to MEDIA_ROOT)
    from django.conf import settings as _settings

    raw_path = task.result_file_path
    nifti_path = Path(raw_path)
    if not nifti_path.is_absolute():
        nifti_path = Path(_settings.MEDIA_ROOT) / raw_path

    series = task.input_image.series
    model_name = task.model.name if task.model else "AI Model"

    try:
        # Convert NIfTI → DICOM SEG
        seg_dcm_path = create_dicom_seg(
            nifti_path=nifti_path,
            series=series,
            label_map=label_map,
            series_description=f"{model_name} Segmentation",
            algorithm_name=model_name,
        )

        # Extract SeriesInstanceUID before upload (cheap header-only read)
        ds = pydicom.dcmread(str(seg_dcm_path), stop_before_pixels=True)
        series_uid = str(ds.SeriesInstanceUID)

        # Upload to Orthanc
        orthanc_response = upload_dicom_to_orthanc(seg_dcm_path)

        # Persist metadata on the task
        metadata = task.result_metadata or {}
        metadata["dicom_seg_series_uid"] = series_uid
        metadata["dicom_seg_orthanc_id"] = orthanc_response.get("ID", "")
        task.result_metadata = metadata
        task.save(update_fields=["result_metadata"])

        logger.info(
            "create_dicom_seg_task: task %s — SEG series_uid=%s orthanc_id=%s",
            analysis_task_id,
            series_uid,
            orthanc_response.get("ID"),
        )

    except Exception as exc:
        logger.exception(
            "create_dicom_seg_task: failed for task %s: %s", analysis_task_id, exc
        )
        raise self.retry(exc=exc, countdown=60)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    queue="ai_jobs",
)
def run_nnunet_inference(self, task_id: str):
    """
    Run nnU-Net inference as a local subprocess for a queued AnalysisTask.

    This task is scheduled by ``NNUNetConnector.dispatch_job()`` and executes
    ``nnUNetv2_predict`` directly inside the Celery worker container (no
    separate AI service container is required — nnU-Net must be installed in
    the worker image and model weights accessible via ``nnUNet_results``).

    Steps:
      1. Resolve ``nnunet_input_dir`` from ``task.parameters`` (set by
         ``NNUNetConnector.prepare_input()`` and stored in create()).
      2. Create a per-task output directory under ``MEDIA_ROOT/nnunet_outputs/``.
      3. Run ``nnUNetv2_predict``.
      4. Locate the output NIfTI mask (``<case_id>.nii.gz``).
      5. Store relative path in ``task.result_file_path`` and metadata.
      6. Mark task COMPLETED (or FAILED on error).

    AIModel.metadata keys used:
        nnunet_dataset_id  (required) — e.g. ``"Dataset010_Liver"``
        nnunet_config      (optional) — e.g. ``"3d_fullres"`` (default)
        nnunet_folds       (optional) — e.g. ``"all"`` (default)
        nnunet_extra_args  (optional) — list of extra CLI flags
    """
    import os
    import subprocess
    from pathlib import Path

    try:
        task = AnalysisTask.objects.select_related("model").get(id=task_id)
    except AnalysisTask.DoesNotExist:
        logger.error("run_nnunet_inference: task %s not found", task_id)
        return

    task.status = "PROCESSING"
    task.save(update_fields=["status"])

    metadata = task.model.metadata or {}
    dataset_id = metadata.get("nnunet_dataset_id")
    config     = metadata.get("nnunet_config", "3d_fullres")
    folds      = metadata.get("nnunet_folds",  "all")
    extra_args = metadata.get("nnunet_extra_args", [])

    if not dataset_id:
        _fail_task(task, "nnunet_dataset_id not set in AIModel.metadata")
        return

    # Input directory was prepared by NNUNetConnector.prepare_input()
    input_dir_str = task.parameters.get("nnunet_input_dir")
    case_id       = task.parameters.get("nnunet_case_id", str(task.id)[:8])

    if not input_dir_str:
        _fail_task(task, "nnunet_input_dir not found in task.parameters — prepare_input() may not have run")
        return

    input_dir  = Path(input_dir_str)
    output_dir = Path(settings.MEDIA_ROOT) / "nnunet_outputs" / f"task_{task.id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    from .connectors.nnunet import NNUNetConnector
    cmd = NNUNetConnector.build_predict_command(
        input_dir  = input_dir,
        output_dir = output_dir,
        dataset_id = dataset_id,
        config     = config,
        folds      = folds,
        extra_args = extra_args if isinstance(extra_args, list) else [],
    )

    # Forward nnUNet_results env var if configured in settings
    env = os.environ.copy()
    nnunet_results = getattr(settings, "NNUNET_RESULTS", None)
    if nnunet_results:
        env[_NNUNET_RESULTS_ENV] = nnunet_results

    logger.info("Task %s: running %s", task_id, " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=task.model.timeout_seconds or 3600,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        _fail_task(task, f"nnUNetv2_predict timed out after {task.model.timeout_seconds}s")
        raise self.retry(exc=exc, countdown=60)

    if result.returncode != 0:
        err = f"nnUNetv2_predict failed (rc={result.returncode}). stderr: {result.stderr[-1000:]}"
        logger.error("Task %s: %s", task_id, err)
        _fail_task(task, err)
        return

    # Locate output mask — nnU-Net writes <case_id>.nii.gz
    mask_path = output_dir / f"{case_id}.nii.gz"
    if not mask_path.exists():
        # Fallback: first NIfTI in output dir
        candidates = sorted(output_dir.glob("*.nii.gz")) or sorted(output_dir.glob("*.nii"))
        if not candidates:
            _fail_task(task, f"nnUNetv2_predict produced no NIfTI in {output_dir}")
            return
        mask_path = candidates[0]

    # Store path relative to MEDIA_ROOT
    rel_path = str(mask_path.relative_to(Path(settings.MEDIA_ROOT)))

    task.status          = "COMPLETED"
    task.result_file_path = rel_path
    task.result_metadata  = {
        **(task.result_metadata or {}),
        "nnunet_dataset_id": dataset_id,
        "nnunet_config":     config,
        "output_keys":       [mask_path.name],
    }
    task.completed_at = timezone.now()
    task.save(update_fields=["status", "result_file_path", "result_metadata", "completed_at"])

    logger.info("Task %s: nnU-Net inference COMPLETED — mask at %s", task_id, rel_path)


# Module-level name used in run_nnunet_inference env setup
_NNUNET_RESULTS_ENV = "nnUNet_results"


def _fail_task(task, error_message: str):
    """Mark an AnalysisTask as FAILED with an error message."""
    task.status        = "FAILED"
    task.error_message = error_message
    task.completed_at  = timezone.now()
    task.save(update_fields=["status", "error_message", "completed_at"])
    logger.error("Task %s FAILED: %s", task.id, error_message)


@shared_task
def sync_orchestrator_status():
    """
    Periodic task to sync status from orchestrator.

    This task runs every 5 seconds (configured in celery.py) and:
    1. Finds all active orchestrator tasks (PENDING, QUEUED, DISPATCHED, PROCESSING)
    2. Polls orchestrator for current status via gRPC
    3. Updates task status in database
    4. Triggers WebSocket broadcasts via Django signals

    Returns:
        dict: Summary with total and updated counts
    """
    from .services.orchestrator_sync import OrchestratorStatusSync

    if not settings.USE_ORCHESTRATOR:
        # Still sync if any per-model orchestrator tasks are active
        from .models import AnalysisTask as _AT
        has_orchestrator_tasks = _AT.objects.filter(
            orchestrator_job_id__isnull=False,
            status__in=['PENDING', 'QUEUED', 'DISPATCHED', 'PROCESSING'],
        ).exists()
        if not has_orchestrator_tasks:
            return {'skipped': True}

    try:
        return OrchestratorStatusSync.sync_all_active_tasks()
    except Exception as e:
        logger.error(f"Orchestrator sync failed: {e}")
        return {'error': str(e)}

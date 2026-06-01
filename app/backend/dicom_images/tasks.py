"""
DICOM Images Celery Tasks

Background tasks for DICOM processing operations.
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def anonymize_study_task(self, job_id):
    """
    Background task to anonymize DICOM images.

    Reads the AnonymizationJob to determine study vs. image_ids mode,
    runs the anonymization, and updates the job status.
    """
    from dicom_images.models import AnonymizationJob
    from dicom_images.services.anonymization import AnonymizationService

    try:
        job = AnonymizationJob.objects.select_related('study', 'created_by').get(id=job_id)
    except AnonymizationJob.DoesNotExist:
        logger.error(f"AnonymizationJob {job_id} not found")
        return

    # Mark as processing
    job.status = 'PROCESSING'
    job.celery_task_id = self.request.id or ''
    job.save(update_fields=['status', 'celery_task_id'])

    service = AnonymizationService()

    try:
        output_format = job.output_format

        if output_format == 'dicom_zip':
            if job.study_id:
                zip_path = service.anonymize_study(
                    study_id=job.study_id,
                    profile=job.profile,
                    user=job.created_by,
                )
            elif job.image_ids:
                zip_path = service.anonymize_images(
                    image_ids=job.image_ids,
                    profile=job.profile,
                    user=job.created_by,
                )
            else:
                raise ValueError("Job has neither study_id nor image_ids")
        elif output_format in ('nifti_bids', 'png_bids'):
            from dicom_images.services.bids_utils import (
                build_nifti_bids_zip,
                build_png_bids_zip,
            )
            if not job.study_id:
                raise ValueError("BIDS output requires a full study (study_id)")
            anon_prefix = f"STUDY{str(job.study_id)[:6].zfill(6)}"
            fn = build_nifti_bids_zip if output_format == 'nifti_bids' else build_png_bids_zip
            zip_path = fn(study=job.study, profile=job.profile, anon_prefix=anon_prefix)
        else:
            raise ValueError(f"Unknown output_format: {output_format}")

        job.status = 'COMPLETED'
        job.result_file_path = zip_path
        job.save(update_fields=['status', 'result_file_path', 'updated_at'])
        logger.info(f"AnonymizationJob {job_id} completed: {zip_path}")

    except Exception as exc:
        job.status = 'FAILED'
        job.error_message = str(exc)
        job.save(update_fields=['status', 'error_message', 'updated_at'])
        logger.exception(f"AnonymizationJob {job_id} failed: {exc}")


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def convert_format_task(self, job_id):
    """
    Background task to convert DICOM images to another format.
    """
    from dicom_images.models import ConversionJob
    from dicom_images.services.format_conversion import FormatConversionService

    try:
        job = ConversionJob.objects.select_related('study', 'created_by').get(id=job_id)
    except ConversionJob.DoesNotExist:
        logger.error(f"ConversionJob {job_id} not found")
        return

    job.status = 'PROCESSING'
    job.celery_task_id = self.request.id or ''
    job.save(update_fields=['status', 'celery_task_id'])

    service = FormatConversionService()

    try:
        if job.target_format == 'nifti' and job.series_ids:
            # Convert each series to NIfTI — take the first one
            result_path = service.convert_series_to_nifti(
                series_id=job.series_ids[0],
                user=job.created_by,
            )
        elif job.study_id:
            result_path = service.batch_convert(
                study_id=job.study_id,
                target_format=job.target_format,
                user=job.created_by,
            )
        else:
            raise ValueError("Job has neither study nor series_ids")

        job.status = 'COMPLETED'
        job.result_file_path = result_path
        job.save(update_fields=['status', 'result_file_path', 'updated_at'])
        logger.info(f"ConversionJob {job_id} completed: {result_path}")

    except Exception as exc:
        job.status = 'FAILED'
        job.error_message = str(exc)
        job.save(update_fields=['status', 'error_message', 'updated_at'])
        logger.exception(f"ConversionJob {job_id} failed: {exc}")


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def batch_operation_task(self, job_id):
    """
    Background task for batch operations (export, delete, analyze).
    """
    from dicom_images.models import BatchJob
    from dicom_images.services.batch_operations import BatchOperationService

    try:
        job = BatchJob.objects.select_related('created_by').get(id=job_id)
    except BatchJob.DoesNotExist:
        logger.error(f"BatchJob {job_id} not found")
        return

    job.status = 'PROCESSING'
    job.celery_task_id = self.request.id or ''
    job.save(update_fields=['status', 'celery_task_id'])

    service = BatchOperationService()

    try:
        if job.operation == 'export':
            result_path = service.batch_export(
                study_ids=job.study_ids, user=job.created_by,
            )
            job.result_file_path = result_path
        elif job.operation == 'delete':
            count = service.batch_delete(
                study_ids=job.study_ids, user=job.created_by,
            )
            job.result_summary = {'deleted_count': count}
        elif job.operation == 'analyze':
            task_ids = service.batch_analyze(
                study_ids=job.study_ids,
                model_key=job.model_key,
                parameters=job.parameters,
                user=job.created_by,
            )
            job.result_summary = {'task_ids': task_ids}
        else:
            raise ValueError(f"Unknown operation: {job.operation}")

        job.status = 'COMPLETED'
        job.save(update_fields=[
            'status', 'result_file_path', 'result_summary', 'updated_at',
        ])
        logger.info(f"BatchJob {job_id} completed")

    except Exception as exc:
        job.status = 'FAILED'
        job.error_message = str(exc)
        job.save(update_fields=['status', 'error_message', 'updated_at'])
        logger.exception(f"BatchJob {job_id} failed: {exc}")

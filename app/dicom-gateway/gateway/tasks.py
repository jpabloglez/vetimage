"""
Celery Tasks for DICOM Processing

Async tasks for processing received DICOM files and forwarding to backend.
"""

import logging
import os
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import httpx
from celery import Celery
from pydicom import dcmread

from .config import settings

logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    'dicom_gateway',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max
    task_soft_time_limit=540,  # 9 minutes soft limit
    # Route all tasks to dicom_processing queue (matches worker --queues config)
    task_default_queue='dicom_processing',
    task_default_exchange='dicom_processing',
    task_default_routing_key='dicom_processing',
)


@celery_app.task(bind=True, max_retries=3)
def process_dicom_file(self, file_path: str, metadata: Dict[str, Any]):
    """
    Process received DICOM file and forward to backend

    Steps:
    1. Validate DICOM file
    2. Extract full metadata
    3. Anonymize if enabled
    4. Upload to backend API
    5. Clean up temporary file

    Args:
        file_path: Path to DICOM file
        metadata: Basic metadata from SCP handler

    Returns:
        dict: Processing result
    """
    logger.info(f"Processing DICOM file: {file_path}")
    start_time = datetime.now()

    try:
        # Step 1: Validate file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"DICOM file not found: {file_path}")

        # Step 2: Read and validate DICOM
        ds = dcmread(file_path)
        logger.info(f"DICOM file validated: {metadata.get('sop_instance_uid')}")

        # Step 3: Anonymize if enabled
        if settings.ENABLE_ANONYMIZATION:
            anonymize_dicom.delay(file_path)
            logger.info("Queued for anonymization")

        # Step 4: Lookup PACS user and API key, then get auth token
        source_ae = metadata.get('source_ae', 'UNKNOWN')
        pacs_credentials = get_pacs_api_key(source_ae)

        if pacs_credentials:
            user_email, api_key = pacs_credentials
            logger.info(f"Routing upload to user: {user_email} (PACS: {source_ae})")

            # Authenticate using API key
            token = get_auth_token_from_api_key(api_key)
        else:
            # No PACS mapping - use gateway service account
            logger.info(f"No PACS mapping for {source_ae}, using gateway service account")
            token = get_auth_token()  # Uses password-based auth for gateway user

        # Step 5: Upload to backend
        if settings.AUTO_FORWARD_TO_BACKEND:
            result = upload_to_backend(file_path, metadata, token)
            logger.info(f"Uploaded to backend: {result}")

        # Step 6: Calculate processing time
        duration = (datetime.now() - start_time).total_seconds()

        # Step 7: Log transaction with PACS config
        log_transaction(metadata, 'success', duration, pacs_ae_title=source_ae)

        return {
            'status': 'success',
            'file_path': file_path,
            'sop_instance_uid': metadata.get('sop_instance_uid'),
            'duration_seconds': duration,
        }

    except Exception as e:
        logger.error(f"Failed to process DICOM file: {str(e)}", exc_info=True)

        # Log failed transaction
        source_ae = metadata.get('source_ae', 'UNKNOWN')
        log_transaction(metadata, 'failure', error=str(e), pacs_ae_title=source_ae)

        # Retry the task
        try:
            raise self.retry(exc=e, countdown=60)  # Retry after 1 minute
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for {file_path}")
            return {
                'status': 'failed',
                'error': str(e),
                'file_path': file_path,
            }


@celery_app.task
def anonymize_dicom(file_path: str):
    """
    Anonymize DICOM file (remove PHI)

    Args:
        file_path: Path to DICOM file

    Returns:
        str: Path to anonymized file
    """
    logger.info(f"Anonymizing DICOM file: {file_path}")

    try:
        ds = dcmread(file_path)

        # Tags to remove (basic anonymization)
        phi_tags = [
            'PatientName',
            'PatientBirthDate',
            'PatientAddress',
            'PatientTelephoneNumbers',
            'InstitutionName',
            'InstitutionAddress',
            'ReferringPhysicianName',
            'PerformingPhysicianName',
            'OperatorsName',
        ]

        # Remove PHI tags
        for tag_name in phi_tags:
            if tag_name in ds:
                delattr(ds, tag_name)

        # Hash Patient ID
        if 'PatientID' in ds:
            original_id = str(ds.PatientID)
            hashed_id = hashlib.sha256(original_id.encode()).hexdigest()[:16]
            ds.PatientID = hashed_id

        # Set anonymization flag
        ds.PatientIdentityRemoved = 'YES'
        ds.DeidentificationMethod = 'VetImage Gateway Auto-Anonymization'

        # Save anonymized file
        ds.save_as(file_path)
        logger.info(f"DICOM file anonymized: {file_path}")

        return file_path

    except Exception as e:
        logger.error(f"Failed to anonymize DICOM: {str(e)}", exc_info=True)
        raise


def get_pacs_user_credentials(source_ae: str) -> Optional[Tuple[str, str]]:
    """
    DEPRECATED: Password-based PACS authentication (replaced by API keys).

    This function is kept for backward compatibility but should not be used.
    Use get_pacs_api_key() instead for secure API key-based authentication.

    Migration Path:
    1. Generate API key via Django admin (/admin/users/userapikey/)
    2. Add API key to gateway PACS_USER_API_KEYS environment variable
    3. Gateway will automatically use get_pacs_api_key() in process_dicom_file()

    Args:
        source_ae: Source Application Entity Title from DICOM transfer

    Returns:
        Tuple of (email, password) for the receiving user, or None if not configured

    Security Warning:
        This function returns passwords in plaintext. Do not use for new implementations.
    """
    try:
        url = f"{settings.BACKEND_API_URL}/api/dicom-gateway/pacs/lookup/"
        params = {'ae_title': source_ae}

        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                return (data.get('user_email'), data.get('user_password'))
            elif response.status_code == 404:
                # No PACS config found for this AE Title
                logger.info(f"No PACS configuration found for AE Title: {source_ae}")
                return None
            else:
                logger.error(f"PACS lookup failed: {response.status_code}")
                return None

    except Exception as e:
        logger.error(f"Error looking up PACS config for {source_ae}: {e}")
        return None


def get_pacs_api_key(source_ae: str) -> Optional[Tuple[str, str]]:
    """
    Lookup PACS user and retrieve their API key from config.

    Args:
        source_ae: Source Application Entity Title from DICOM transfer

    Returns:
        Tuple of (user_email, api_key) or None if not configured
    """
    try:
        url = f"{settings.BACKEND_API_URL}/api/dicom-gateway/pacs/lookup/"
        params = {'ae_title': source_ae}

        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                user_email = data.get('user_email')

                # Get API key from config
                api_key = settings.pacs_user_api_keys_dict.get(user_email)

                if not api_key:
                    logger.warning(
                        f"PACS user {user_email} found but no API key in config. "
                        f"Add key to PACS_USER_API_KEYS env var."
                    )
                    return None

                # Verify key prefix matches (sanity check)
                if data.get('api_key_prefix') and not api_key.startswith(data['api_key_prefix']):
                    logger.error(
                        f"API key prefix mismatch for {user_email}. "
                        f"Expected: {data['api_key_prefix']}..., Got: {api_key[:8]}..."
                    )
                    return None

                return (user_email, api_key)

            elif response.status_code == 404:
                logger.info(f"No PACS configuration found for AE Title: {source_ae}")
                return None
            else:
                logger.error(f"PACS lookup failed: {response.status_code}")
                return None

    except Exception as e:
        logger.error(f"Error looking up PACS config for {source_ae}: {e}")
        return None


def get_auth_token_from_api_key(api_key: str) -> str:
    """
    Get JWT authentication token using API key.

    Args:
        api_key: User's API key

    Returns:
        str: JWT access token
    """
    try:
        auth_url = f"{settings.BACKEND_API_URL}/users/auth/api-key/"

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                auth_url,
                json={'api_key': api_key}
            )
            response.raise_for_status()
            return response.json()['access']

    except httpx.HTTPStatusError as e:
        logger.error(f"API key authentication failed: HTTP {e.response.status_code}")
        logger.error(f"Response: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"API key authentication failed: {e}")
        raise


def get_auth_token(email: str = None, password: str = None) -> str:
    """
    Get JWT authentication token for backend API.

    Args:
        email: User email (defaults to gateway service user)
        password: User password (defaults to gateway service password)

    Returns:
        str: JWT access token
    """
    # Use provided credentials or fall back to service account
    email = email or settings.BACKEND_SERVICE_EMAIL
    password = password or settings.BACKEND_SERVICE_PASSWORD

    try:
        auth_url = f"{settings.BACKEND_API_URL}/users/auth/login/"
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                auth_url,
                json={
                    'email': email,
                    'password': password
                }
            )
            response.raise_for_status()
            return response.json()['access']
    except Exception as e:
        logger.error(f"Authentication failed for {email}: {e}")
        raise


def upload_to_backend(file_path: str, metadata: Dict[str, Any], token: str) -> Dict[str, Any]:
    """
    Upload DICOM file to backend API

    Args:
        file_path: Path to DICOM file
        metadata: DICOM metadata
        token: JWT authentication token (for specific user)

    Returns:
        dict: Backend response
    """
    logger.info(f"Uploading to backend: {file_path}")

    try:

        # Prepare multipart upload
        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f, 'application/dicom')
            }

            # Add metadata as form data
            data = {
                'metadata': str(metadata),  # JSON string
                'source': 'dicom_gateway',
            }

            # Make request to backend
            url = f"{settings.BACKEND_API_URL}/api/dicom/upload/medical/"
            headers = {'Authorization': f'Bearer {token}'}

            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    url,
                    files=files,
                    data=data,
                    headers=headers
                )

                response.raise_for_status()
                result = response.json()

                logger.info(f"Backend upload successful: {result}")
                return result

    except httpx.HTTPStatusError as e:
        logger.error(f"Backend upload failed: HTTP {e.response.status_code}")
        raise

    except Exception as e:
        logger.error(f"Backend upload failed: {str(e)}", exc_info=True)
        raise


def log_transaction(metadata: Dict[str, Any], status: str, duration: float = None,
                   error: str = None, pacs_ae_title: str = None):
    """
    Log DICOM transaction to backend

    Args:
        metadata: Transaction metadata
        status: 'success' or 'failed'
        duration: Processing duration in seconds
        error: Error message if failed
        pacs_ae_title: Source AE Title for PACS config lookup
    """
    try:
        transaction_data = {
            'transaction_type': 'C-STORE',
            'direction': 'incoming',
            'source_ae': metadata.get('source_ae') or pacs_ae_title,
            'source_ip': metadata.get('source_ip'),
            'dest_ae': settings.DICOM_AE_TITLE,
            'study_instance_uid': metadata.get('study_instance_uid'),
            'series_instance_uid': metadata.get('series_instance_uid'),
            'sop_instance_uid': metadata.get('sop_instance_uid'),
            'patient_id_hash': hashlib.sha256(
                metadata.get('patient_id', '').encode()
            ).hexdigest() if metadata.get('patient_id') else None,
            'modality': metadata.get('modality'),
            'status': status,
            'error_message': error,
            'duration_ms': int(duration * 1000) if duration else None,
            'started_at': metadata.get('received_at'),
        }

        # Send to backend audit endpoint
        url = f"{settings.BACKEND_API_URL}/api/dicom-gateway/transactions/"
        headers = {}

        if settings.BACKEND_API_KEY:
            headers['Authorization'] = f'Bearer {settings.BACKEND_API_KEY}'

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                json=transaction_data,
                headers=headers
            )

            if response.status_code == 201:
                logger.info("Transaction logged to backend")
            else:
                logger.warning(
                    f"Failed to log transaction: HTTP {response.status_code} - {response.text}"
                )

    except Exception as e:
        # Don't raise - logging failure shouldn't block processing
        logger.warning(f"Failed to log transaction: {str(e)}")


@celery_app.task
def cleanup_old_files(days_old: int = 7):
    """
    Clean up old DICOM files from temporary storage

    Args:
        days_old: Delete files older than this many days

    Returns:
        dict: Cleanup statistics
    """
    logger.info(f"Cleaning up files older than {days_old} days")

    import time
    from pathlib import Path

    storage_path = Path(settings.STORAGE_PATH)
    cutoff_time = time.time() - (days_old * 86400)  # days to seconds

    deleted_count = 0
    freed_bytes = 0

    try:
        for file_path in storage_path.rglob('*.dcm'):
            if file_path.stat().st_mtime < cutoff_time:
                file_size = file_path.stat().st_size
                file_path.unlink()
                deleted_count += 1
                freed_bytes += file_size

        logger.info(
            f"Cleanup complete: Deleted {deleted_count} files, "
            f"freed {freed_bytes / (1024**2):.2f} MB"
        )

        return {
            'deleted_count': deleted_count,
            'freed_mb': freed_bytes / (1024**2),
        }

    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}", exc_info=True)
        raise


# Periodic tasks configuration
celery_app.conf.beat_schedule = {
    'cleanup-old-files-daily': {
        'task': 'gateway.tasks.cleanup_old_files',
        'schedule': 86400.0,  # Every 24 hours
        'args': (7,)  # Delete files older than 7 days
    },
}

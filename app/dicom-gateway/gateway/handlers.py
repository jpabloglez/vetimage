"""
DICOM Event Handlers

Handles incoming DICOM network events (C-STORE, C-ECHO, etc.)
"""

import logging
import os
import time
from datetime import datetime
from typing import Optional
from pynetdicom import evt
from pydicom import dcmread
from pydicom.dataset import Dataset

from .config import settings, get_storage_path
from .tasks import process_dicom_file

logger = logging.getLogger(__name__)


class DICOMEventHandlers:
    """Handlers for DICOM network events"""

    def __init__(self):
        self.storage_path = get_storage_path()
        self.stats = {
            'total_received': 0,
            'total_success': 0,
            'total_failed': 0,
            'last_received': None,
        }

    def handle_echo(self, event):
        """
        Handle C-ECHO request (connection test)

        Returns:
            0x0000: Success status
        """
        logger.info(f"C-ECHO received from {event.assoc.remote['address']}")
        return 0x0000

    def handle_store(self, event):
        """
        Handle C-STORE request (receive DICOM image)

        Args:
            event: pynetdicom event object containing dataset

        Returns:
            int: DICOM status code (0x0000 = success)
        """
        start_time = time.time()

        try:
            # Get the dataset
            ds = event.dataset
            ds.file_meta = event.file_meta

            # Extract key identifiers
            sop_instance_uid = ds.get('SOPInstanceUID', 'UNKNOWN')
            study_uid = ds.get('StudyInstanceUID', 'UNKNOWN')
            series_uid = ds.get('SeriesInstanceUID', 'UNKNOWN')
            patient_id = ds.get('PatientID', 'UNKNOWN')

            # Log reception
            logger.info(
                f"C-STORE received: Patient={patient_id}, "
                f"Study={study_uid}, Series={series_uid}, "
                f"Instance={sop_instance_uid}"
            )

            # Generate file path
            file_path = self._generate_file_path(study_uid, series_uid, sop_instance_uid)

            # Save DICOM file
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            ds.save_as(file_path, write_like_original=False)

            # Extract metadata for task
            metadata = self._extract_metadata(ds, event)

            # Queue for async processing
            if settings.AUTO_FORWARD_TO_BACKEND:
                process_dicom_file.delay(file_path, metadata)
                logger.info(f"Queued for processing: {file_path}")

            # Update stats
            self.stats['total_received'] += 1
            self.stats['total_success'] += 1
            self.stats['last_received'] = datetime.now()

            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"C-STORE completed in {duration_ms:.2f}ms")

            # Return success
            return 0x0000

        except Exception as e:
            logger.error(f"C-STORE failed: {str(e)}", exc_info=True)
            self.stats['total_failed'] += 1

            # Return general failure status
            return 0xC000

    def handle_association_requested(self, event):
        """
        Handle association request (connection attempt)

        Validates source IP against whitelist.
        """
        requestor = event.assoc.requestor
        remote_address = event.assoc.remote['address']

        logger.info(
            f"Association requested from {remote_address} "
            f"(AE Title: {requestor.ae_title})"
        )

        # Check IP whitelist
        if not self._is_ip_allowed(remote_address):
            logger.warning(f"Rejected connection from unauthorized IP: {remote_address}")
            event.assoc.abort()
            return

        logger.info(f"Association accepted from {remote_address}")

    def handle_association_released(self, event):
        """Handle association release (connection closed)"""
        remote_address = event.assoc.remote['address']
        logger.info(f"Association released: {remote_address}")

    def handle_association_aborted(self, event):
        """Handle association abort (connection error)"""
        remote_address = event.assoc.remote.get('address', 'UNKNOWN')
        logger.warning(f"Association aborted: {remote_address}")

    def _generate_file_path(self, study_uid: str, series_uid: str, instance_uid: str) -> str:
        """
        Generate organized file path for DICOM storage

        Structure: storage/study_uid/series_uid/instance_uid.dcm
        """
        # Sanitize UIDs (remove invalid filesystem characters)
        study_uid = study_uid.replace('.', '_')[:64]
        series_uid = series_uid.replace('.', '_')[:64]
        instance_uid = instance_uid.replace('.', '_')[:64]

        file_path = os.path.join(
            self.storage_path,
            study_uid,
            series_uid,
            f"{instance_uid}.dcm"
        )

        return file_path

    def _extract_metadata(self, ds: Dataset, event) -> dict:
        """
        Extract relevant metadata from DICOM dataset

        Args:
            ds: DICOM dataset
            event: pynetdicom event (for source info)

        Returns:
            dict: Extracted metadata
        """
        metadata = {
            # Identifiers
            'sop_instance_uid': str(ds.get('SOPInstanceUID', '')),
            'study_instance_uid': str(ds.get('StudyInstanceUID', '')),
            'series_instance_uid': str(ds.get('SeriesInstanceUID', '')),
            'patient_id': str(ds.get('PatientID', '')),
            'accession_number': str(ds.get('AccessionNumber', '')),

            # Study info
            'study_date': str(ds.get('StudyDate', '')),
            'study_time': str(ds.get('StudyTime', '')),
            'study_description': str(ds.get('StudyDescription', '')),

            # Series info
            'series_number': str(ds.get('SeriesNumber', '')),
            'series_description': str(ds.get('SeriesDescription', '')),
            'modality': str(ds.get('Modality', '')),

            # Image info
            'instance_number': str(ds.get('InstanceNumber', '')),
            'rows': int(ds.get('Rows', 0)),
            'columns': int(ds.get('Columns', 0)),

            # Source info
            'source_ae': event.assoc.requestor.ae_title,
            'source_ip': event.assoc.remote['address'],
            'received_at': datetime.now().isoformat(),
        }

        return metadata

    def _is_ip_allowed(self, ip_address: str) -> bool:
        """
        Check if source IP is allowed

        Args:
            ip_address: Source IP address

        Returns:
            bool: True if allowed
        """
        # For POC, allow all
        # In production, implement proper CIDR matching
        if '0.0.0.0/0' in settings.ALLOWED_SOURCE_IPS:
            return True

        return ip_address in settings.ALLOWED_SOURCE_IPS

    def get_stats(self) -> dict:
        """Get current statistics"""
        return {
            **self.stats,
            'last_received': self.stats['last_received'].isoformat() if self.stats['last_received'] else None,
        }


# Create global handler instance
dicom_handlers = DICOMEventHandlers()


# Export handler functions for pynetdicom
def handle_echo(event):
    """C-ECHO handler"""
    return dicom_handlers.handle_echo(event)


def handle_store(event):
    """C-STORE handler"""
    return dicom_handlers.handle_store(event)


def handle_association_requested(event):
    """Association request handler"""
    return dicom_handlers.handle_association_requested(event)


def handle_association_released(event):
    """Association release handler"""
    return dicom_handlers.handle_association_released(event)


def handle_association_aborted(event):
    """Association abort handler"""
    return dicom_handlers.handle_association_aborted(event)


# Event handler mapping for pynetdicom
EVENT_HANDLERS = [
    (evt.EVT_C_ECHO, handle_echo),
    (evt.EVT_C_STORE, handle_store),
    (evt.EVT_REQUESTED, handle_association_requested),
    (evt.EVT_RELEASED, handle_association_released),
    (evt.EVT_ABORTED, handle_association_aborted),
]

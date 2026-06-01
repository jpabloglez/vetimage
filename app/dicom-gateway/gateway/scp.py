"""
DICOM Service Class Provider (SCP)

Main DICOM server implementation using pynetdicom.
"""

import logging
import signal
import sys
from pynetdicom import AE, AllStoragePresentationContexts
from pynetdicom.sop_class import Verification

from .config import settings
from .handlers import EVENT_HANDLERS, dicom_handlers

logger = logging.getLogger(__name__)


class DICOMGatewaySCP:
    """
    DICOM SCP (Server) for receiving images from PACS/modalities
    """

    def __init__(self):
        """Initialize the DICOM SCP"""

        # Create Application Entity
        self.ae = AE(ae_title=settings.DICOM_AE_TITLE)

        # Add supported presentation contexts
        # AllStoragePresentationContexts includes all standard DICOM storage SOP classes
        self.ae.supported_contexts = AllStoragePresentationContexts

        # Add verification (C-ECHO) support
        self.ae.add_supported_context(Verification)

        # Set network options
        self.ae.maximum_pdu_size = settings.DICOM_MAX_PDU_LENGTH
        self.ae.network_timeout = settings.DICOM_TIMEOUT
        self.ae.maximum_associations = settings.MAX_CONCURRENT_ASSOCIATIONS

        self.server = None
        self.running = False

        logger.info(
            f"DICOM SCP initialized: AE Title={settings.DICOM_AE_TITLE}, "
            f"Port={settings.DICOM_PORT}"
        )

    def start(self):
        """Start the DICOM SCP server"""

        logger.info(
            f"Starting DICOM SCP on {settings.DICOM_HOST}:{settings.DICOM_PORT}"
        )

        try:
            # Start the server (blocking call)
            self.running = True
            self.server = self.ae.start_server(
                (settings.DICOM_HOST, settings.DICOM_PORT),
                block=True,
                evt_handlers=EVENT_HANDLERS
            )

        except Exception as e:
            logger.error(f"Failed to start DICOM SCP: {str(e)}", exc_info=True)
            self.running = False
            raise

    def stop(self):
        """Stop the DICOM SCP server"""

        logger.info("Stopping DICOM SCP...")

        try:
            if self.server:
                self.server.shutdown()
            self.running = False
            logger.info("DICOM SCP stopped")

        except Exception as e:
            logger.error(f"Error stopping DICOM SCP: {str(e)}")

    def is_running(self) -> bool:
        """Check if server is running"""
        return self.running

    def get_status(self) -> dict:
        """Get current server status"""
        return {
            'running': self.running,
            'ae_title': settings.DICOM_AE_TITLE,
            'host': settings.DICOM_HOST,
            'port': settings.DICOM_PORT,
            'max_associations': settings.MAX_CONCURRENT_ASSOCIATIONS,
            'stats': dicom_handlers.get_stats(),
        }


# Global SCP instance
_scp_instance = None


def get_scp() -> DICOMGatewaySCP:
    """Get or create global SCP instance"""
    global _scp_instance
    if _scp_instance is None:
        _scp_instance = DICOMGatewaySCP()
    return _scp_instance


def start_scp():
    """Start the DICOM SCP server (blocking)"""
    scp = get_scp()

    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        scp.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start server
    scp.start()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Start server
    start_scp()

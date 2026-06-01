#!/usr/bin/env python3
"""
DICOM Gateway Service - Main Entry Point

Starts both the DICOM SCP server and the monitoring API in separate threads.
"""

import logging
import sys
import threading
import time
from pathlib import Path

# Add gateway package to path
sys.path.insert(0, str(Path(__file__).parent))

from gateway.config import settings, validate_settings
from gateway.scp import start_scp
from gateway.api import app


def setup_logging():
    """Configure logging for the service"""

    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    if settings.LOG_FORMAT == 'json':
        from pythonjsonlogger import jsonlogger
        formatter = jsonlogger.JsonFormatter(log_format)
    else:
        formatter = logging.Formatter(log_format)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    root_logger.addHandler(handler)

    # Reduce noise from pynetdicom
    logging.getLogger('pynetdicom').setLevel(logging.WARNING)


def start_api_server():
    """Start the FastAPI monitoring API"""
    import uvicorn

    logger = logging.getLogger(__name__)
    logger.info(f"Starting API server on {settings.API_HOST}:{settings.API_PORT}")

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )


def start_scp_server():
    """Start the DICOM SCP server"""
    logger = logging.getLogger(__name__)
    logger.info("Starting DICOM SCP server...")

    try:
        start_scp()  # This is a blocking call
    except Exception as e:
        logger.error(f"DICOM SCP failed: {str(e)}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point"""

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info(f"{settings.SERVICE_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info("=" * 60)

    # Validate configuration
    try:
        validate_settings()
        logger.info("Configuration validated successfully")
    except Exception as e:
        logger.error(f"Configuration validation failed: {str(e)}")
        sys.exit(1)

    # Print configuration
    logger.info(f"DICOM SCP: {settings.DICOM_AE_TITLE} @ {settings.DICOM_HOST}:{settings.DICOM_PORT}")
    logger.info(f"API Server: http://{settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"Storage: {settings.STORAGE_PATH}")
    logger.info(f"Backend API: {settings.BACKEND_API_URL}")

    # Start API server in separate thread
    api_thread = threading.Thread(target=start_api_server, daemon=True, name="API-Server")
    api_thread.start()
    logger.info("API server thread started")

    # Give API time to start
    time.sleep(2)

    # Start DICOM SCP in main thread (blocking)
    logger.info("Starting DICOM SCP server (blocking)...")
    start_scp_server()


if __name__ == "__main__":
    main()

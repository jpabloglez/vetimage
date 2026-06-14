"""
Gateway REST API

FastAPI application for monitoring and managing the DICOM gateway.
"""

import logging
import psutil
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from .config import settings
from .scp import get_scp
from .handlers import dicom_handlers

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="VetImage DICOM Gateway API",
    description="Monitoring and management API for the DICOM gateway service",
    version=settings.VERSION,
)


# Pydantic models
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    environment: str


class GatewayStatus(BaseModel):
    scp_running: bool
    ae_title: str
    host: str
    port: int
    max_associations: int
    stats: dict


class SystemMetrics(BaseModel):
    cpu_percent: float
    memory_used_gb: float
    memory_percent: float
    disk_free_gb: float
    disk_used_percent: float


class DICOMStats(BaseModel):
    total_received: int
    total_success: int
    total_failed: int
    success_rate: float
    last_received: Optional[str]


# Routes

@app.get("/", response_model=dict)
async def root():
    """Root endpoint with service info"""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "status": "/api/status",
            "metrics": "/api/metrics",
            "stats": "/api/stats",
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for load balancers/monitoring

    Returns:
        HealthResponse: Service health status
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
    )


@app.get("/api/status", response_model=GatewayStatus)
async def get_gateway_status():
    """
    Get DICOM gateway status

    Returns:
        GatewayStatus: Current gateway status and configuration
    """
    scp = get_scp()
    status_data = scp.get_status()

    return GatewayStatus(
        scp_running=status_data['running'],
        ae_title=status_data['ae_title'],
        host=status_data['host'],
        port=status_data['port'],
        max_associations=status_data['max_associations'],
        stats=status_data['stats'],
    )


@app.get("/api/metrics", response_model=SystemMetrics)
async def get_system_metrics():
    """
    Get system resource metrics

    Returns:
        SystemMetrics: CPU, memory, and disk usage
    """
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(settings.STORAGE_PATH)

        return SystemMetrics(
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_used_gb=memory.used / (1024 ** 3),
            memory_percent=memory.percent,
            disk_free_gb=disk.free / (1024 ** 3),
            disk_used_percent=disk.percent,
        )
    except Exception as e:
        logger.error(f"Failed to get system metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system metrics"
        )


@app.get("/api/stats", response_model=DICOMStats)
async def get_dicom_stats():
    """
    Get DICOM processing statistics

    Returns:
        DICOMStats: Reception and processing statistics
    """
    stats = dicom_handlers.get_stats()

    total = stats['total_received']
    success_rate = (stats['total_success'] / total * 100) if total > 0 else 0.0

    return DICOMStats(
        total_received=stats['total_received'],
        total_success=stats['total_success'],
        total_failed=stats['total_failed'],
        success_rate=round(success_rate, 2),
        last_received=stats.get('last_received'),
    )


@app.get("/api/config")
async def get_configuration():
    """
    Get gateway configuration (non-sensitive values only)

    Returns:
        dict: Gateway configuration
    """
    return {
        "dicom": {
            "ae_title": settings.DICOM_AE_TITLE,
            "port": settings.DICOM_PORT,
            "max_pdu_length": settings.DICOM_MAX_PDU_LENGTH,
            "timeout": settings.DICOM_TIMEOUT,
            "max_concurrent_associations": settings.MAX_CONCURRENT_ASSOCIATIONS,
        },
        "storage": {
            "path": settings.STORAGE_PATH,
            "max_gb": settings.MAX_STORAGE_GB,
        },
        "processing": {
            "auto_forward": settings.AUTO_FORWARD_TO_BACKEND,
            "anonymization_enabled": settings.ENABLE_ANONYMIZATION,
        },
        "backend": {
            "api_url": settings.BACKEND_API_URL,
        }
    }


@app.post("/api/test-echo")
async def test_echo():
    """
    Test DICOM connectivity with self C-ECHO

    Returns:
        dict: Test result
    """
    try:
        from pynetdicom import AE
        from pynetdicom.sop_class import Verification

        ae = AE(ae_title='TEST_ECHO')
        ae.add_requested_context(Verification)

        # Try to connect to self
        assoc = ae.associate(
            'localhost',
            settings.DICOM_PORT,
            ae_title=settings.DICOM_AE_TITLE
        )

        if assoc.is_established:
            status = assoc.send_c_echo()
            assoc.release()

            if status.Status == 0x0000:
                return {
                    "success": True,
                    "message": "C-ECHO successful",
                    "status": "0x0000"
                }
            else:
                return {
                    "success": False,
                    "message": "C-ECHO failed",
                    "status": hex(status.Status)
                }
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to establish DICOM association"
            )

    except Exception as e:
        logger.error(f"C-ECHO test failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"C-ECHO test failed: {str(e)}"
        )


@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """
    Prometheus metrics endpoint

    Returns:
        str: Metrics in Prometheus format
    """
    if not settings.ENABLE_PROMETHEUS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prometheus metrics disabled"
        )

    stats = dicom_handlers.get_stats()
    system_metrics = await get_system_metrics()

    metrics = []

    # DICOM metrics
    metrics.append(f"# HELP dicom_total_received Total DICOM images received")
    metrics.append(f"# TYPE dicom_total_received counter")
    metrics.append(f"dicom_total_received {stats['total_received']}")

    metrics.append(f"# HELP dicom_total_success Total successful receptions")
    metrics.append(f"# TYPE dicom_total_success counter")
    metrics.append(f"dicom_total_success {stats['total_success']}")

    metrics.append(f"# HELP dicom_total_failed Total failed receptions")
    metrics.append(f"# TYPE dicom_total_failed counter")
    metrics.append(f"dicom_total_failed {stats['total_failed']}")

    # System metrics
    metrics.append(f"# HELP system_cpu_percent CPU usage percentage")
    metrics.append(f"# TYPE system_cpu_percent gauge")
    metrics.append(f"system_cpu_percent {system_metrics.cpu_percent}")

    metrics.append(f"# HELP system_memory_percent Memory usage percentage")
    metrics.append(f"# TYPE system_memory_percent gauge")
    metrics.append(f"system_memory_percent {system_metrics.memory_percent}")

    metrics.append(f"# HELP system_disk_free_gb Disk free space in GB")
    metrics.append(f"# TYPE system_disk_free_gb gauge")
    metrics.append(f"system_disk_free_gb {system_metrics.disk_free_gb}")

    return "\n".join(metrics)


# Startup/shutdown events

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("DICOM Gateway API starting...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"DICOM AE Title: {settings.DICOM_AE_TITLE}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("DICOM Gateway API shutting down...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower()
    )

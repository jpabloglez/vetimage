"""
Configuration Management for DICOM Gateway

Loads settings from environment variables with defaults.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional, Dict
import os
import json


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    # Service Identity
    SERVICE_NAME: str = "OpenMedLab DICOM Gateway"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"

    # DICOM SCP Settings
    DICOM_AE_TITLE: str = "OPENMEDLAB"
    DICOM_PORT: int = 11112
    DICOM_HOST: str = "0.0.0.0"
    DICOM_MAX_PDU_LENGTH: int = 16384
    DICOM_TIMEOUT: int = 30  # seconds

    # Storage
    STORAGE_PATH: str = "/app/storage/dicom-temp"
    MAX_STORAGE_GB: int = 100

    # Backend API
    BACKEND_API_URL: str = "http://backend:8000"
    BACKEND_API_KEY: Optional[str] = None
    BACKEND_SERVICE_EMAIL: str = "gateway@openmedlab.system"
    BACKEND_SERVICE_PASSWORD: str = "gateway-service-key-12345"

    # PACS User API Keys (JSON format)
    # Format: {"user_email": "api_key"}
    # Generated via Django admin and configured here
    PACS_USER_API_KEYS: str = "{}"

    @property
    def pacs_user_api_keys_dict(self) -> Dict[str, str]:
        """Parse PACS_USER_API_KEYS JSON string to dictionary"""
        try:
            return json.loads(self.PACS_USER_API_KEYS)
        except json.JSONDecodeError:
            return {}

    # Database (for local transaction logging)
    DATABASE_URL: str = "postgresql://openmedlab:openmedlab@db:5432/openmedlab"

    # Redis (for Celery)
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Security
    ALLOWED_SOURCE_IPS: List[str] = ["0.0.0.0/0"]  # Default: allow all (override in production)
    ENABLE_TLS: bool = False
    TLS_CERT_PATH: Optional[str] = None
    TLS_KEY_PATH: Optional[str] = None

    # Processing
    ENABLE_ANONYMIZATION: bool = False
    AUTO_FORWARD_TO_BACKEND: bool = True
    MAX_CONCURRENT_ASSOCIATIONS: int = 10

    # Monitoring
    ENABLE_PROMETHEUS: bool = True
    PROMETHEUS_PORT: int = 9090

    # API
    API_PORT: int = 8001
    API_HOST: str = "0.0.0.0"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or console

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_storage_path() -> str:
    """Get storage path, creating if doesn't exist"""
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    return settings.STORAGE_PATH


def validate_settings():
    """Validate critical settings at startup"""
    errors = []

    # Check storage path is writable
    try:
        test_file = os.path.join(settings.STORAGE_PATH, ".write_test")
        os.makedirs(settings.STORAGE_PATH, exist_ok=True)
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
    except Exception as e:
        errors.append(f"Storage path not writable: {e}")

    # Check port is valid
    if not (1024 <= settings.DICOM_PORT <= 65535):
        errors.append(f"Invalid DICOM port: {settings.DICOM_PORT}")

    if errors:
        raise ValueError(f"Configuration validation failed:\n" + "\n".join(errors))

    return True

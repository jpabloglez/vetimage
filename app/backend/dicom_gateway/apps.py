"""
DICOM Gateway App Configuration
"""

from django.apps import AppConfig


class DicomGatewayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dicom_gateway'
    verbose_name = 'DICOM Gateway'

    def ready(self):
        """Import signals when app is ready"""
        import dicom_gateway.signals  # noqa: F401

"""
Credentials App Configuration
"""

from django.apps import AppConfig


class CredentialsConfig(AppConfig):
    """Configuration for the credentials app"""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'credentials'
    verbose_name = 'Credentials & Session Tracking'

    def ready(self):
        """Import signal handlers when app is ready"""
        try:
            import credentials.signals  # noqa
        except ImportError:
            pass

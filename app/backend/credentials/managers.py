"""
Custom model managers for credentials app
"""

from django.db import models


class UserSessionManager(models.Manager):
    """Custom manager for UserSession model"""

    def active(self):
        """Return only active sessions"""
        return self.filter(is_active=True)

    def suspicious(self):
        """Return sessions flagged as suspicious"""
        return self.filter(is_suspicious=True)


class AuditLogManager(models.Manager):
    """Custom manager for AuditLog model"""

    def failed_logins(self):
        """Return failed login attempts"""
        return self.filter(event_type='login_failed')

    def suspicious_events(self):
        """Return suspicious security events"""
        return self.filter(is_suspicious=True)

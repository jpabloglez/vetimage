"""
Signal handlers for credentials app

Automatically track sessions and create audit logs based on JWT token events.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver, Signal
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

from rest_framework_simplejwt.token_blacklist.models import (
    OutstandingToken,
    BlacklistedToken
)

from .models import UserSession, AuditLog
from .utils import (
    get_current_request,
    extract_ip_address,
    detect_device_type,
    get_ip_geolocation,
    calculate_risk_score,
    is_suspicious_ip_change
)

logger = logging.getLogger(__name__)

# Custom signals
session_terminated = Signal()
suspicious_activity_detected = Signal()


@receiver(post_save, sender=OutstandingToken)
def create_user_session(sender, instance, created, **kwargs):
    """
    Create UserSession when OutstandingToken is created (user logs in).

    This signal handler:
    1. Extracts request context from thread-local storage
    2. Parses user agent for device information
    3. Creates UserSession linked to the token
    4. Creates AuditLog entry for login
    5. Enforces concurrent session limits
    """
    # Only process newly created tokens
    if not created:
        return

    # Check if session tracking is enabled
    if not getattr(settings, 'CREDENTIALS_TRACKING_ENABLED', True):
        return

    try:
        # Get request from thread-local storage
        request = get_current_request()

        if not request:
            logger.warning(f"No request found in thread-local storage for token {instance.jti}")
            # Create session with minimal info
            _create_session_without_request(instance)
            return

        # Extract request information
        ip_address = extract_ip_address(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Detect device information
        device_info = detect_device_type(user_agent)

        # Get IP geolocation
        ip_country, ip_city = get_ip_geolocation(ip_address)

        # Create UserSession
        session = UserSession.objects.create(
            user=instance.user,
            outstanding_token=instance,
            session_type='jwt',
            user_agent=user_agent,
            device_type=device_info['device_type'],
            browser=device_info['browser'],
            browser_version=device_info['browser_version'],
            os=device_info['os'],
            os_version=device_info['os_version'],
            ip_address=ip_address,
            ip_country=ip_country or '',
            ip_city=ip_city or '',
            expires_at=instance.expires_at,
            last_activity_at=timezone.now()
        )

        # Create AuditLog entry
        if getattr(settings, 'CREDENTIALS_AUDIT_LOGGING_ENABLED', True):
            AuditLog.objects.create(
                user=instance.user,
                event_type='login_success',
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request.path if hasattr(request, 'path') else '',
                request_method=request.method if hasattr(request, 'method') else '',
                session=session,
                metadata={
                    'token_jti': str(instance.jti),
                    'device_type': device_info['device_type'],
                    'browser': device_info['browser'],
                    'os': device_info['os']
                }
            )

        # Check for IP change (suspicious activity)
        _check_ip_change_suspicious(instance.user, ip_address, session)

        # Enforce concurrent session limits
        _enforce_concurrent_session_limit(instance.user, session)

        logger.info(f"Created session {session.id} for user {instance.user.email}")

    except Exception as e:
        logger.error(f"Error creating user session: {e}", exc_info=True)


def _create_session_without_request(token):
    """
    Create a basic session when request context is not available.

    Args:
        token: OutstandingToken instance
    """
    try:
        UserSession.objects.create(
            user=token.user,
            outstanding_token=token,
            session_type='jwt',
            ip_address='0.0.0.0',  # Unknown
            device_type='unknown',
            expires_at=token.expires_at,
            last_activity_at=timezone.now()
        )
    except Exception as e:
        logger.error(f"Error creating minimal session: {e}", exc_info=True)


def _check_ip_change_suspicious(user, current_ip, current_session):
    """
    Check if IP change is suspicious compared to recent sessions.

    Args:
        user: User instance
        current_ip: Current IP address
        current_session: Current UserSession instance
    """
    try:
        # Get most recent previous session (excluding current)
        previous_session = UserSession.objects.filter(
            user=user
        ).exclude(
            id=current_session.id
        ).order_by('-created_at').first()

        if previous_session and previous_session.ip_address:
            # Check if IP change is suspicious
            if is_suspicious_ip_change(previous_session.ip_address, current_ip):
                current_session.is_suspicious = True
                current_session.suspicious_reason = f"IP changed from {previous_session.ip_address} to {current_ip}"
                current_session.save()

                # Create audit log
                if getattr(settings, 'CREDENTIALS_AUDIT_LOGGING_ENABLED', True):
                    AuditLog.objects.create(
                        user=user,
                        event_type='suspicious_activity',
                        ip_address=current_ip,
                        session=current_session,
                        is_suspicious=True,
                        risk_score=calculate_risk_score('ip_change'),
                        metadata={
                            'reason': 'ip_change',
                            'old_ip': previous_session.ip_address,
                            'new_ip': current_ip
                        }
                    )

                logger.warning(f"Suspicious IP change for user {user.email}: {previous_session.ip_address} -> {current_ip}")

    except Exception as e:
        logger.error(f"Error checking IP change: {e}", exc_info=True)


def _enforce_concurrent_session_limit(user, new_session):
    """
    Enforce concurrent session limits by terminating oldest sessions.

    Args:
        user: User instance
        new_session: Newly created UserSession instance
    """
    try:
        max_sessions = getattr(settings, 'MAX_CONCURRENT_SESSIONS_PER_USER', 5)

        # Get all active sessions for user
        active_sessions = UserSession.objects.filter(
            user=user,
            is_active=True
        ).order_by('-created_at')

        # If limit exceeded, terminate oldest sessions
        if active_sessions.count() > max_sessions:
            sessions_to_terminate = active_sessions[max_sessions:]

            for session in sessions_to_terminate:
                # Terminate session
                session.terminate(reason='concurrent_limit')

                # Blacklist associated token if it exists
                if session.outstanding_token:
                    try:
                        BlacklistedToken.objects.get_or_create(
                            token=session.outstanding_token
                        )
                    except Exception as e:
                        logger.error(f"Error blacklisting token: {e}", exc_info=True)

                # Create audit log
                if getattr(settings, 'CREDENTIALS_AUDIT_LOGGING_ENABLED', True):
                    AuditLog.objects.create(
                        user=user,
                        event_type='concurrent_session_limit',
                        ip_address=session.ip_address,
                        session=session,
                        is_suspicious=False,
                        risk_score=calculate_risk_score('concurrent_session_limit'),
                        metadata={
                            'reason': 'concurrent_session_limit',
                            'max_sessions': max_sessions,
                            'terminated_session_id': str(session.id)
                        }
                    )

            logger.info(f"Terminated {len(sessions_to_terminate)} sessions for user {user.email} due to concurrent limit")

    except Exception as e:
        logger.error(f"Error enforcing session limit: {e}", exc_info=True)


@receiver(post_save, sender=BlacklistedToken)
def terminate_user_session(sender, instance, created, **kwargs):
    """
    Terminate UserSession when token is blacklisted (user logs out).

    This signal handler:
    1. Finds the associated UserSession
    2. Marks it as terminated
    3. Creates AuditLog entry for logout
    """
    # Only process newly blacklisted tokens
    if not created:
        return

    # Check if session tracking is enabled
    if not getattr(settings, 'CREDENTIALS_TRACKING_ENABLED', True):
        return

    try:
        # Find associated session
        session = UserSession.objects.filter(
            outstanding_token=instance.token,
            is_active=True
        ).first()

        if not session:
            logger.warning(f"No active session found for blacklisted token {instance.token.jti}")
            return

        # Terminate session
        session.terminate(reason='logout')

        # Create audit log
        if getattr(settings, 'CREDENTIALS_AUDIT_LOGGING_ENABLED', True):
            AuditLog.objects.create(
                user=session.user,
                event_type='logout',
                ip_address=session.ip_address,
                session=session,
                metadata={
                    'token_jti': str(instance.token.jti),
                    'session_duration_seconds': int((session.terminated_at - session.created_at).total_seconds())
                }
            )

        logger.info(f"Terminated session {session.id} for user {session.user.email}")

    except Exception as e:
        logger.error(f"Error terminating user session: {e}", exc_info=True)


@receiver(session_terminated)
def log_session_termination(sender, session, reason, **kwargs):
    """
    Log session termination events.

    Args:
        sender: Sender of the signal
        session: UserSession instance
        reason: Termination reason
    """
    try:
        if not getattr(settings, 'CREDENTIALS_AUDIT_LOGGING_ENABLED', True):
            return

        # Calculate session duration
        duration = (session.terminated_at - session.created_at).total_seconds() if session.terminated_at else 0

        # Create audit log
        AuditLog.objects.create(
            user=session.user,
            event_type='session_terminated',
            ip_address=session.ip_address,
            session=session,
            metadata={
                'reason': reason,
                'session_duration_seconds': int(duration),
                'session_id': str(session.id)
            }
        )

        logger.info(f"Logged session termination for user {session.user.email}: {reason}")

    except Exception as e:
        logger.error(f"Error logging session termination: {e}", exc_info=True)


@receiver(suspicious_activity_detected)
def log_suspicious_activity(sender, user, event_type, ip_address, session=None, metadata=None, **kwargs):
    """
    Log suspicious activity events.

    Args:
        sender: Sender of the signal
        user: User instance
        event_type: Type of suspicious event
        ip_address: IP address
        session: Optional UserSession instance
        metadata: Optional additional metadata
    """
    try:
        if not getattr(settings, 'CREDENTIALS_AUDIT_LOGGING_ENABLED', True):
            return

        # Calculate risk score
        risk_score = calculate_risk_score(event_type)

        # Create audit log
        AuditLog.objects.create(
            user=user,
            event_type='suspicious_activity',
            ip_address=ip_address,
            session=session,
            is_suspicious=True,
            risk_score=risk_score,
            metadata=metadata or {}
        )

        # Flag session if provided
        if session:
            session.is_suspicious = True
            session.suspicious_reason = metadata.get('reason', event_type) if metadata else event_type
            session.save()

        logger.warning(f"Suspicious activity detected for user {user.email}: {event_type}")

    except Exception as e:
        logger.error(f"Error logging suspicious activity: {e}", exc_info=True)

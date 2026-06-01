"""
Business logic for credentials app

Provides helper functions for session validation, API key scope checking,
and rate limiting.
"""

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from typing import Tuple, Optional
import logging

from .models import UserSession, EnhancedAPIKey, APIKeyScope, AuditLog
from .utils import calculate_risk_score

logger = logging.getLogger(__name__)


def validate_api_key_scope(api_key, request_path: str, request_method: str) -> Tuple[bool, str]:
    """
    Validate if an API key has the required scope for a given endpoint.

    Args:
        api_key: UserAPIKey instance
        request_path: The API endpoint path
        request_method: HTTP method (GET, POST, etc.)

    Returns:
        Tuple of (allowed: bool, scope_matched: str)
    """
    try:
        # Get enhanced API key
        enhanced_key = EnhancedAPIKey.objects.filter(api_key=api_key).first()

        if not enhanced_key:
            logger.warning(f"No EnhancedAPIKey found for API key {api_key.key_prefix}")
            return False, ''

        # Get all scopes for this API key
        scopes = enhanced_key.scopes.filter(is_active=True)

        if not scopes.exists():
            logger.warning(f"API key {api_key.key_prefix} has no active scopes")
            return False, ''

        # Check if any scope matches the request
        for scope in scopes:
            if scope.matches_request(request_path, request_method):
                return True, scope.name

        # No scope matched
        logger.warning(
            f"API key {api_key.key_prefix} - No scope matched for {request_method} {request_path}"
        )
        return False, ''

    except Exception as e:
        logger.error(f"Error validating API key scope: {e}", exc_info=True)
        return False, ''


def check_api_key_rate_limit(api_key) -> Tuple[bool, str]:
    """
    Check if an API key has exceeded its rate limits.

    Args:
        api_key: UserAPIKey instance

    Returns:
        Tuple of (allowed: bool, reason: str)
    """
    try:
        # Check if rate limiting is enabled
        if not getattr(settings, 'CREDENTIALS_RATE_LIMITING_ENABLED', False):
            return True, 'allowed'

        # Get enhanced API key
        enhanced_key = EnhancedAPIKey.objects.filter(api_key=api_key).first()

        if not enhanced_key:
            # No enhanced key, allow by default
            return True, 'allowed'

        # Check rate limits
        return enhanced_key.check_rate_limit()

    except Exception as e:
        logger.error(f"Error checking API key rate limit: {e}", exc_info=True)
        # Allow on error to avoid blocking legitimate requests
        return True, 'error'


def increment_api_key_usage(api_key, request_path: str, request_method: str,
                             response_status: int, response_time_ms: int,
                             ip_address: str, scope_matched: str = '',
                             rate_limited: bool = False):
    """
    Increment API key usage counters and create usage log entry.

    Args:
        api_key: UserAPIKey instance
        request_path: The API endpoint path
        request_method: HTTP method
        response_status: HTTP response status code
        response_time_ms: Response time in milliseconds
        ip_address: Client IP address
        scope_matched: Scope that was matched (if any)
        rate_limited: Whether the request was rate limited
    """
    try:
        # Get enhanced API key
        enhanced_key = EnhancedAPIKey.objects.filter(api_key=api_key).first()

        if enhanced_key:
            # Increment usage counters
            enhanced_key.increment_usage()

        # Create usage log entry (async in production)
        from .models import APIKeyUsageLog
        APIKeyUsageLog.objects.create(
            api_key=api_key,
            request_path=request_path,
            request_method=request_method,
            response_status=response_status,
            response_time_ms=response_time_ms,
            ip_address=ip_address,
            scope_matched=scope_matched,
            rate_limited=rate_limited
        )

    except Exception as e:
        logger.error(f"Error incrementing API key usage: {e}", exc_info=True)


def log_scope_violation(api_key, user, request_path: str, request_method: str, ip_address: str):
    """
    Log an API key scope violation to the audit log.

    Args:
        api_key: UserAPIKey instance
        user: User instance
        request_path: The API endpoint path
        request_method: HTTP method
        ip_address: Client IP address
    """
    try:
        AuditLog.objects.create(
            user=user,
            event_type='scope_violation',
            ip_address=ip_address,
            request_path=request_path,
            request_method=request_method,
            is_suspicious=True,
            risk_score=calculate_risk_score('scope_violation'),
            metadata={
                'api_key_prefix': api_key.key_prefix,
                'requested_path': request_path,
                'requested_method': request_method,
                'reason': 'API key does not have required scope for this endpoint'
            }
        )

        logger.warning(
            f"Scope violation: API key {api_key.key_prefix} attempted to access "
            f"{request_method} {request_path} without permission"
        )

    except Exception as e:
        logger.error(f"Error logging scope violation: {e}", exc_info=True)


def get_active_sessions_for_user(user) -> list:
    """
    Get all active sessions for a user.

    Args:
        user: User instance

    Returns:
        List of UserSession instances
    """
    return UserSession.objects.filter(
        user=user,
        is_active=True
    ).order_by('-created_at')


def terminate_session_by_id(session_id: str, reason: str = 'manual') -> bool:
    """
    Terminate a specific session by ID.

    Args:
        session_id: UUID of the session
        reason: Reason for termination

    Returns:
        True if successful, False otherwise
    """
    try:
        session = UserSession.objects.filter(id=session_id, is_active=True).first()

        if not session:
            logger.warning(f"Session {session_id} not found or already terminated")
            return False

        session.terminate(reason=reason)

        # Blacklist the associated token if it exists
        if session.outstanding_token:
            from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
            try:
                BlacklistedToken.objects.get_or_create(
                    token=session.outstanding_token
                )
            except Exception as e:
                logger.error(f"Error blacklisting token: {e}", exc_info=True)

        logger.info(f"Terminated session {session_id} for user {session.user.email}")
        return True

    except Exception as e:
        logger.error(f"Error terminating session: {e}", exc_info=True)
        return False


def is_session_valid(session_id: str) -> bool:
    """
    Check if a session is currently valid.

    Args:
        session_id: UUID of the session

    Returns:
        True if valid, False otherwise
    """
    try:
        session = UserSession.objects.filter(id=session_id).first()

        if not session:
            return False

        return session.is_valid()

    except Exception as e:
        logger.error(f"Error checking session validity: {e}", exc_info=True)
        return False


def get_user_audit_logs(user, event_type: Optional[str] = None,
                        limit: int = 100, suspicious_only: bool = False):
    """
    Get audit logs for a specific user.

    Args:
        user: User instance
        event_type: Filter by specific event type (optional)
        limit: Maximum number of logs to return
        suspicious_only: Only return suspicious events

    Returns:
        QuerySet of AuditLog instances
    """
    logs = AuditLog.objects.filter(user=user)

    if event_type:
        logs = logs.filter(event_type=event_type)

    if suspicious_only:
        logs = logs.filter(is_suspicious=True)

    return logs.order_by('-event_timestamp')[:limit]


def clear_login_attempts(ip_address: str):
    """
    Clear failed login attempt counter for an IP address.

    This can be called after a successful login to reset the counter.

    Args:
        ip_address: IP address to clear
    """
    try:
        cache_key = f'login_attempts:{ip_address}'
        lockout_key = f'login_lockout:{ip_address}'

        cache.delete(cache_key)
        cache.delete(lockout_key)

        logger.info(f"Cleared login attempts for IP {ip_address}")

    except Exception as e:
        logger.error(f"Error clearing login attempts: {e}", exc_info=True)


def get_scope_by_name(scope_name: str) -> Optional[APIKeyScope]:
    """
    Get an API key scope by name.

    Args:
        scope_name: Name of the scope (e.g., "dicom:read")

    Returns:
        APIKeyScope instance or None
    """
    try:
        return APIKeyScope.objects.filter(name=scope_name, is_active=True).first()
    except Exception as e:
        logger.error(f"Error getting scope: {e}", exc_info=True)
        return None


def assign_scope_to_api_key(api_key, scope_name: str) -> bool:
    """
    Assign a scope to an API key.

    Args:
        api_key: UserAPIKey instance
        scope_name: Name of the scope to assign

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get or create enhanced API key
        enhanced_key, created = EnhancedAPIKey.objects.get_or_create(
            api_key=api_key,
            defaults={
                'rate_limit_per_minute': getattr(settings, 'DEFAULT_API_KEY_RATE_LIMIT_PER_MINUTE', 60),
                'rate_limit_per_hour': getattr(settings, 'DEFAULT_API_KEY_RATE_LIMIT_PER_HOUR', 3600),
                'rate_limit_per_day': getattr(settings, 'DEFAULT_API_KEY_RATE_LIMIT_PER_DAY', 86400),
            }
        )

        # Get scope
        scope = get_scope_by_name(scope_name)

        if not scope:
            logger.warning(f"Scope {scope_name} not found")
            return False

        # Assign scope
        enhanced_key.scopes.add(scope)

        logger.info(f"Assigned scope {scope_name} to API key {api_key.key_prefix}")
        return True

    except Exception as e:
        logger.error(f"Error assigning scope: {e}", exc_info=True)
        return False


def remove_scope_from_api_key(api_key, scope_name: str) -> bool:
    """
    Remove a scope from an API key.

    Args:
        api_key: UserAPIKey instance
        scope_name: Name of the scope to remove

    Returns:
        True if successful, False otherwise
    """
    try:
        enhanced_key = EnhancedAPIKey.objects.filter(api_key=api_key).first()

        if not enhanced_key:
            logger.warning(f"No EnhancedAPIKey found for API key {api_key.key_prefix}")
            return False

        scope = get_scope_by_name(scope_name)

        if not scope:
            logger.warning(f"Scope {scope_name} not found")
            return False

        enhanced_key.scopes.remove(scope)

        logger.info(f"Removed scope {scope_name} from API key {api_key.key_prefix}")
        return True

    except Exception as e:
        logger.error(f"Error removing scope: {e}", exc_info=True)
        return False

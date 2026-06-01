"""
Decorators for scope validation and rate limiting

Provides decorators to enforce API key scopes and rate limits on views.
"""

from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging
import time

from .services import (
    validate_api_key_scope,
    check_api_key_rate_limit,
    log_scope_violation,
    increment_api_key_usage
)
from .utils import extract_ip_address

logger = logging.getLogger(__name__)


def require_api_key_scope(scope_name):
    """
    Decorator to require a specific API key scope for a view.

    Usage:
        @api_view(['POST'])
        @require_api_key_scope('dicom:write')
        def upload_dicom(request):
            # Only API keys with "dicom:write" scope can access this
            ...

    Args:
        scope_name: Name of the required scope (e.g., "dicom:read")

    Returns:
        Decorated function
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Skip if user is authenticated via JWT (not API key)
            if not hasattr(request, 'auth') or request.auth is None:
                # Standard JWT authentication, allow
                return view_func(request, *args, **kwargs)

            # Check if authenticated via API key
            if hasattr(request.auth, 'key_hash'):  # UserAPIKey instance
                api_key = request.auth

                # Validate scope
                allowed, scope_matched = validate_api_key_scope(
                    api_key,
                    request.path,
                    request.method
                )

                if not allowed:
                    # Log scope violation
                    ip_address = extract_ip_address(request)
                    log_scope_violation(
                        api_key,
                        request.user,
                        request.path,
                        request.method,
                        ip_address
                    )

                    return Response({
                        'error': f'API key does not have required scope: {scope_name}',
                        'required_scope': scope_name
                    }, status=status.HTTP_403_FORBIDDEN)

            # Scope validated or JWT auth, proceed
            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def enforce_api_key_rate_limit(view_func):
    """
    Decorator to enforce API key rate limits on a view.

    Usage:
        @api_view(['POST'])
        @enforce_api_key_rate_limit
        def expensive_operation(request):
            # Automatically rate limited per API key
            ...

    Args:
        view_func: View function to wrap

    Returns:
        Decorated function
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Skip if user is authenticated via JWT (not API key)
        if not hasattr(request, 'auth') or request.auth is None:
            # Standard JWT authentication, proceed
            return view_func(request, *args, **kwargs)

        # Check if authenticated via API key
        if hasattr(request.auth, 'key_hash'):  # UserAPIKey instance
            api_key = request.auth

            # Check rate limit
            allowed, reason = check_api_key_rate_limit(api_key)

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for API key {api_key.key_prefix}: {reason}"
                )

                # Determine retry-after time based on reason
                retry_after = 60  # Default: 1 minute

                if 'minute' in reason.lower():
                    retry_after = 60
                elif 'hour' in reason.lower():
                    retry_after = 3600
                elif 'day' in reason.lower():
                    retry_after = 86400

                return Response({
                    'error': 'Rate limit exceeded',
                    'detail': f'API key rate limit exceeded: {reason}',
                    'retry_after': retry_after
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Rate limit OK, proceed
        return view_func(request, *args, **kwargs)

    return wrapper


def track_api_key_usage(view_func):
    """
    Decorator to track API key usage (requests, response time, etc.).

    This decorator records detailed usage statistics for API key requests.

    Usage:
        @api_view(['GET'])
        @track_api_key_usage
        def list_resources(request):
            # Usage will be tracked automatically
            ...

    Args:
        view_func: View function to wrap

    Returns:
        Decorated function
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Record start time
        start_time = time.time()

        # Execute the view
        response = view_func(request, *args, **kwargs)

        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)

        # Track usage if authenticated via API key
        if hasattr(request, 'auth') and request.auth and hasattr(request.auth, 'key_hash'):
            api_key = request.auth
            ip_address = extract_ip_address(request)

            # Get scope if available
            scope_matched = ''
            if hasattr(request, '_api_key_scope'):
                scope_matched = request._api_key_scope

            # Increment usage
            increment_api_key_usage(
                api_key=api_key,
                request_path=request.path,
                request_method=request.method,
                response_status=response.status_code,
                response_time_ms=response_time_ms,
                ip_address=ip_address,
                scope_matched=scope_matched,
                rate_limited=response.status_code == 429
            )

        return response

    return wrapper


def require_scope_and_rate_limit(scope_name):
    """
    Combined decorator for both scope validation and rate limiting.

    This is a convenience decorator that combines require_api_key_scope
    and enforce_api_key_rate_limit.

    Usage:
        @api_view(['POST'])
        @require_scope_and_rate_limit('dicom:write')
        def upload_dicom(request):
            # Scope and rate limit both enforced
            ...

    Args:
        scope_name: Name of the required scope

    Returns:
        Decorated function
    """
    def decorator(view_func):
        # Apply both decorators
        return require_api_key_scope(scope_name)(
            enforce_api_key_rate_limit(
                track_api_key_usage(view_func)
            )
        )
    return decorator

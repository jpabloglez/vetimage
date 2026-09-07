"""
Middleware for storing request context and audit logging
"""

from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import logging
import time

from . import session_activity
from .utils import set_current_request, clear_current_request, extract_ip_address, calculate_risk_score
from .models import AuditLog, UserSession

logger = logging.getLogger(__name__)


class RequestContextMiddleware(MiddlewareMixin):
    """
    Middleware to store request in thread-local storage.

    This allows signal handlers to access the request object
    when creating sessions and audit logs.
    """

    def process_request(self, request):
        """
        Store request in thread-local storage at the beginning of request processing.

        Args:
            request: Django HttpRequest object
        """
        # Store request in thread-local storage
        set_current_request(request)
        return None

    def process_response(self, request, response):
        """
        Clear request from thread-local storage after request processing.

        Args:
            request: Django HttpRequest object
            response: Django HttpResponse object
        """
        # Clear request from thread-local storage
        clear_current_request()
        return response

    def process_exception(self, request, exception):
        """
        Clear request from thread-local storage if an exception occurs.

        Args:
            request: Django HttpRequest object
            exception: Exception that occurred
        """
        # Clear request from thread-local storage
        clear_current_request()
        return None


class AuditLoggingMiddleware(MiddlewareMixin):
    """
    Middleware for comprehensive audit logging and security monitoring.

    Features:
    - Failed login attempt tracking
    - Brute force protection with progressive delays
    - Session activity updates for authenticated requests
    - Audit logging for authentication events
    """

    # Paths to monitor for authentication
    AUTH_PATHS = ['/users/auth/login/', '/users/auth/api-key/']

    def process_request(self, request):
        """
        Process incoming request for brute force protection.

        Args:
            request: Django HttpRequest object

        Returns:
            JsonResponse if request is blocked, None otherwise
        """
        # Check if audit logging is enabled
        if not getattr(settings, 'CREDENTIALS_AUDIT_LOGGING_ENABLED', True):
            return None

        # Check brute force protection for auth endpoints
        if request.path in self.AUTH_PATHS:
            return self._check_brute_force_protection(request)

        return None

    def process_response(self, request, response):
        """
        Process response to log failed authentication attempts and update session activity.

        Args:
            request: Django HttpRequest object
            response: Django HttpResponse object

        Returns:
            HttpResponse object
        """
        # Check if audit logging is enabled
        if not getattr(settings, 'CREDENTIALS_AUDIT_LOGGING_ENABLED', True):
            return response

        try:
            # Log failed login attempts
            if request.path in self.AUTH_PATHS and response.status_code in [400, 401, 403]:
                self._log_failed_login(request, response)

            # Update session activity for authenticated requests
            if hasattr(request, 'user') and request.user.is_authenticated:
                self._update_session_activity(request)

        except Exception as e:
            logger.error(f"Error in audit logging middleware: {e}", exc_info=True)

        return response

    def _check_brute_force_protection(self, request):
        """
        Check if IP address should be blocked due to too many failed login attempts.

        Implements progressive delay:
        - 1-5 attempts: No delay
        - 6-10 attempts: 2^(attempts-5) seconds delay
        - 10+ attempts: 60 seconds delay

        Args:
            request: Django HttpRequest object

        Returns:
            JsonResponse if blocked, None otherwise
        """
        ip_address = extract_ip_address(request)
        cache_key = f'login_attempts:{ip_address}'

        # Get current attempt count
        attempts = cache.get(cache_key, 0)

        # Check if limit exceeded
        max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)

        if attempts >= max_attempts:
            # Calculate delay (exponential backoff, max 60 seconds)
            delay = min(2 ** (attempts - max_attempts), 60)

            # Get time when attempts started
            lockout_key = f'login_lockout:{ip_address}'
            lockout_time = cache.get(lockout_key)

            if not lockout_time:
                # First time hitting limit, set lockout time
                lockout_time = time.time()
                cache.set(lockout_key, lockout_time, delay)

            # Calculate remaining delay
            elapsed = time.time() - lockout_time
            remaining = max(0, delay - elapsed)

            if remaining > 0:
                logger.warning(f"Brute force protection: Blocked IP {ip_address} ({attempts} attempts)")

                # Create audit log
                try:
                    AuditLog.objects.create(
                        user=None,
                        username_attempted='',
                        event_type='suspicious_activity',
                        ip_address=ip_address,
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        request_path=request.path,
                        request_method=request.method,
                        is_suspicious=True,
                        risk_score=calculate_risk_score('brute_force'),
                        metadata={
                            'reason': 'brute_force',
                            'attempts': attempts,
                            'delay_seconds': int(remaining)
                        }
                    )
                except Exception as e:
                    logger.error(f"Error creating brute force audit log: {e}", exc_info=True)

                return JsonResponse({
                    'error': f'Too many failed login attempts. Please try again in {int(remaining)} seconds.',
                    'retry_after': int(remaining)
                }, status=429)
            else:
                # Delay expired, reset lockout
                cache.delete(lockout_key)

        return None

    def _log_failed_login(self, request, response):
        """
        Log failed login attempt and increment attempt counter.

        Args:
            request: Django HttpRequest object
            response: Django HttpResponse object
        """
        try:
            ip_address = extract_ip_address(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')

            # Extract attempted username from request data
            username_attempted = ''
            if hasattr(request, 'data'):
                username_attempted = request.data.get('email', request.data.get('username', ''))
            elif request.method == 'POST':
                username_attempted = request.POST.get('email', request.POST.get('username', ''))

            # Increment attempt counter
            cache_key = f'login_attempts:{ip_address}'
            attempts = cache.get(cache_key, 0) + 1
            timeout = getattr(settings, 'LOGIN_ATTEMPT_TIMEOUT_SECONDS', 900)  # 15 minutes
            cache.set(cache_key, attempts, timeout)

            # Determine if suspicious
            max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
            is_suspicious = attempts >= max_attempts

            # Create audit log
            AuditLog.objects.create(
                user=None,  # Failed login - user not found
                username_attempted=username_attempted,
                event_type='login_failed',
                ip_address=ip_address,
                user_agent=user_agent,
                request_path=request.path,
                request_method=request.method,
                is_suspicious=is_suspicious,
                risk_score=calculate_risk_score('multiple_failed_logins') if is_suspicious else 0,
                metadata={
                    'status_code': response.status_code,
                    'attempts': attempts,
                    'reason': 'Invalid credentials or user not found'
                }
            )

            logger.info(f"Failed login attempt from {ip_address} (attempt #{attempts})")

        except Exception as e:
            logger.error(f"Error logging failed login: {e}", exc_info=True)

    def _update_session_activity(self, request):
        """
        Update last_activity_at for the user's active session.

        Args:
            request: Django HttpRequest object
        """
        try:
            # Skip if session tracking is disabled
            if not getattr(settings, 'CREDENTIALS_TRACKING_ENABLED', True):
                return

            # Try to get the token from the request
            jwt_auth = JWTAuthentication()

            try:
                # Validate and decode token
                validated_token = jwt_auth.get_validated_token(jwt_auth.get_raw_token(jwt_auth.get_header(request)))

                if validated_token:
                    # Match on the `sid` claim, not `jti`. OutstandingToken
                    # stores *refresh* token ids while this reads an *access*
                    # token's, so the old `outstanding_token__jti=<access jti>`
                    # lookup could never match — measured on a dev database,
                    # not one row in ~3k had `last_activity_at` off its
                    # `created_at`. `sid` is on both tokens and survives
                    # rotation, so this one actually resolves.
                    sid = validated_token.get(session_activity.SID_CLAIM)

                    if sid:
                        # A rotation chain shares one sid, so take the live row.
                        session = UserSession.objects.filter(
                            sid=sid,
                            is_active=True
                        ).order_by('-created_at').first()

                        if session:
                            time_since_activity = (timezone.now() - session.last_activity_at).total_seconds() / 60

                            # Only update if enough time has passed (avoid excessive DB writes)
                            if time_since_activity >= 1:  # Update every minute
                                session.update_activity()

                                # Check if IP changed (potential session hijacking)
                                current_ip = extract_ip_address(request)
                                if session.ip_address != current_ip:
                                    from .utils import is_suspicious_ip_change
                                    if is_suspicious_ip_change(session.ip_address, current_ip):
                                        # Log suspicious activity
                                        AuditLog.objects.create(
                                            user=request.user,
                                            event_type='suspicious_activity',
                                            ip_address=current_ip,
                                            user_agent=request.META.get('HTTP_USER_AGENT', ''),
                                            request_path=request.path,
                                            request_method=request.method,
                                            session=session,
                                            is_suspicious=True,
                                            risk_score=calculate_risk_score('ip_change'),
                                            metadata={
                                                'reason': 'ip_change_during_session',
                                                'old_ip': session.ip_address,
                                                'new_ip': current_ip
                                            }
                                        )

                                        logger.warning(
                                            f"IP change detected during session for user {request.user.email}: "
                                            f"{session.ip_address} -> {current_ip}"
                                        )

            except (InvalidToken, TokenError, AttributeError):
                # Not a JWT-authenticated request, skip
                pass

        except Exception as e:
            logger.error(f"Error updating session activity: {e}", exc_info=True)


class IdleSessionMiddleware(MiddlewareMixin):
    """
    Signs out sessions that have gone unused for
    `SESSION_ACTIVITY_TIMEOUT_MINUTES`.

    The setting predates this middleware by a long way; until now it was read
    and discarded, so a signed-in browser stayed signed in for the full 7-day
    refresh lifetime. See `credentials.session_activity` for how the clock
    works.

    **This runs in `process_request`, deliberately.** The existing activity
    tracking sits in `process_response`, where the view has already run and the
    body is already built — a check there could only close the barn door after
    the request it was meant to refuse. Rejecting before the view is the
    difference between enforcement and bookkeeping.

    Requests the *user* did not cause — the notification poll, progress
    tickers — are still checked but do not push the clock forward; the client
    marks them with `X-Background-Request`. Without that, a 30-second poll
    would keep an abandoned workstation signed in indefinitely.
    """

    #: Auth endpoints run their own checks (`CustomTokenRefreshView`) or must
    #: keep working so a client can always tidy up (`logout`).
    EXEMPT_PATHS = (
        '/users/auth/login/',
        '/users/auth/logout/',
        '/users/auth/refresh/',
        '/users/auth/register/',
        '/users/auth/api-key/',
    )

    BACKGROUND_HEADER = 'HTTP_X_BACKGROUND_REQUEST'

    def process_request(self, request):
        if not session_activity.is_enabled():
            return None
        if request.path in self.EXEMPT_PATHS:
            return None

        jwt_auth = JWTAuthentication()
        try:
            header = jwt_auth.get_header(request)
            if header is None:
                return None
            raw_token = jwt_auth.get_raw_token(header)
            if raw_token is None:
                return None
            validated_token = jwt_auth.get_validated_token(raw_token)
        except (InvalidToken, TokenError, AttributeError):
            # Not a valid JWT request — let DRF produce the auth error.
            return None

        sid = session_activity.sid_from_token(validated_token)
        if not sid:
            # No claim: an API-key token, or one minted before this shipped.
            return None

        is_background = request.META.get(self.BACKGROUND_HEADER) == '1'
        if not session_activity.observe(sid, activity=not is_background):
            return None

        try:
            user = jwt_auth.get_user(validated_token)
        except Exception:  # pragma: no cover - defensive
            user = None

        session_activity.expire(
            sid,
            user=user,
            ip_address=extract_ip_address(request),
            request=request,
        )

        return JsonResponse(
            {
                'detail': 'Signed out after a period of inactivity.',
                'code': session_activity.IDLE_TIMEOUT_CODE,
            },
            status=401,
        )

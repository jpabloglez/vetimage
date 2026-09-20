"""
Idle-session expiry.

A workstation in a consult room gets left unattended. `SESSION_ACTIVITY_TIMEOUT_MINUTES`
has existed in settings since the credentials app was written, but nothing ever
enforced it, so a signed-in browser stayed signed in for the full 7-day refresh
lifetime. This module is the enforcement.

**The clock lives in Redis, not in a column.** Each login mints a `sid` claim —
a session id that survives refresh-token rotation — and this module keeps one
cache key per `sid` whose TTL *is* the timeout. Activity re-sets the key;
Redis expires it on its own. So the check is not timestamp arithmetic but a
presence test: **if the key is gone, the session has been idle at least
`SESSION_ACTIVITY_TIMEOUT_MINUTES`.**

Two consequences worth knowing:

* It fails closed. If Redis is flushed or restarted, every key disappears and
  everyone is signed out. For a security control that is the safe direction,
  and re-authenticating is cheap.
* A token minted before this shipped carries no `sid`. Those are grandfathered
  rather than expired on sight — see `sid_from_token`.

Enforcement happens in two places, and the second is the one that matters:
`IdleSessionMiddleware` rejects the request, and `CustomTokenRefreshView`
refuses to mint anything new. Even if an access token slipped past the first,
it dies at its own 5-minute expiry with nothing to replace it.
"""

import logging
import threading
import uuid
from contextlib import contextmanager

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

#: JWT claim carrying the session id. Set once at login and copied forward
#: through every rotation, so it identifies the *login*, not the token.
SID_CLAIM = 'sid'

#: Returned in the 401 body so the client can tell "you went idle" apart from
#: "your access token aged out", and stop trying to refresh its way back in.
IDLE_TIMEOUT_CODE = 'session_idle_timeout'

_KEY = 'session_activity:{sid}'


def new_sid() -> str:
    """A fresh session id for a new login."""
    return uuid.uuid4().hex


def attach(token) -> str:
    """
    Stamp a freshly minted token with a new session id and start its clock.

    Use this at every interactive login. Machine tokens (the API-key exchange)
    deliberately skip it: a service integration that goes quiet for an hour and
    then calls is behaving normally, not idling at an unattended workstation.
    """
    sid = new_sid()
    token[SID_CLAIM] = sid
    touch(sid)
    _stamp_session(token, sid)
    return sid


def carry_forward(old_token, new_token) -> str | None:
    """
    Copy the session id across a refresh-token rotation.

    `CustomTokenRefreshView` mints the rotated token with `for_user()`, which
    builds a brand-new payload and would otherwise drop the claim — restarting
    the idle clock on every refresh and defeating the whole control.
    """
    sid = sid_from_token(old_token)
    if sid:
        new_token[SID_CLAIM] = sid
        _stamp_session(new_token, sid)
    return sid


def _stamp_session(token, sid: str) -> None:
    """
    Record the session id on the tracked session row.

    It cannot be read back off the stored token: simplejwt writes
    `OutstandingToken` inside `for_user()`, *before* any custom claim is added,
    so the row keeps a copy of the token as it was — sid-less. The row is
    already there by the time we are called (the creating signal is
    synchronous), so stamping it is a plain UPDATE.

    Best-effort: a login must not fail because session bookkeeping did.
    """
    from .models import UserSession

    try:
        jti = token.get('jti')
        if jti:
            UserSession.objects.filter(outstanding_token__jti=jti).update(sid=sid)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error('Error stamping session id: %s', exc, exc_info=True)


def timeout_minutes() -> int:
    """0 (or negative) disables idle expiry entirely."""
    return int(getattr(settings, 'SESSION_ACTIVITY_TIMEOUT_MINUTES', 30) or 0)


def is_enabled() -> bool:
    return timeout_minutes() > 0


def sid_from_token(token) -> str | None:
    """
    Read the `sid` claim from a decoded token, or None.

    None means "not subject to idle expiry": either the feature is off, or the
    token predates it. Grandfathering rather than rejecting matters because the
    alternative is signing out every user the moment this deploys, and those
    tokens age out on their own within the refresh lifetime.
    """
    if not is_enabled():
        return None
    try:
        sid = token.get(SID_CLAIM)
    except (AttributeError, TypeError):
        return None
    return sid or None


def touch(sid: str) -> None:
    """
    Mark the session active now.

    Called when a login mints tokens and on every user-initiated request. The
    TTL is the timeout, so the key outliving this call *is* the session being
    within its idle window.
    """
    if not sid or not is_enabled():
        return
    cache.set(_KEY.format(sid=sid), timezone.now().timestamp(), timeout_minutes() * 60)


def is_idle(sid: str) -> bool:
    """True when the session has gone longer than the timeout without activity."""
    if not sid or not is_enabled():
        return False
    return cache.get(_KEY.format(sid=sid)) is None


#: How stale the stored stamp may get before a request rewrites it. The point
#: is to avoid a Redis write on every single request; the TTL is what expires
#: the session, and re-setting it a minute early costs nothing.
REFRESH_INTERVAL_SECONDS = 60


def observe(sid: str, *, activity: bool) -> bool:
    """
    Look at a session on an incoming request. Returns True if it has gone idle.

    `activity=False` is for traffic the user did not cause — notification
    polls, progress tickers, the token refresh itself. Those still get checked
    (an abandoned tab should be signed out promptly, not on the user's return)
    but they do not push the clock forward. Without that distinction a 30-second
    poll would keep every tab alive for ever and the timeout would never fire.
    """
    if not sid or not is_enabled():
        return False

    key = _KEY.format(sid=sid)
    last = cache.get(key)
    if last is None:
        return True

    if activity:
        now = timezone.now().timestamp()
        if now - float(last) >= REFRESH_INTERVAL_SECONDS:
            cache.set(key, now, timeout_minutes() * 60)
    return False


def forget(sid: str) -> None:
    """Drop the key — on logout, so nothing lingers."""
    if not sid:
        return
    cache.delete(_KEY.format(sid=sid))



# ---------------------------------------------------------------------------
# Refresh-token rotation
# ---------------------------------------------------------------------------
#
# Rotation is not a logout followed by a login, but the token signals cannot
# tell the difference on their own: `CustomTokenRefreshView` blacklists the old
# refresh token and mints a new one, and each of those fires a `post_save` that
# the session signals read as an ending and a beginning.
#
# The cost was not theoretical. On a development database, 3,027 session rows
# represented 12 actual logins — chains of up to 19 rows each — and 97% of the
# audit log was fabricated: 3,035 `login_success` and 2,859 `logout` events for
# roughly a dozen real ones. The concurrent-session limit had fired 147 times,
# every one of them against a phantom.
#
# So the view says outright that it is rotating, and the signals believe it,
# rather than trying to infer it from ordering or from a cache key that a Redis
# restart would take away.

_rotation = threading.local()


@contextmanager
def rotating(sid: str | None):
    """
    Mark the current thread as rotating a refresh token for `sid`.

    The session signals consult this to relink the existing session instead of
    ending one and starting another. Re-entrant only in the sense that it
    restores whatever it replaced, so a nested use cannot strand the flag.
    """
    previous = getattr(_rotation, 'sid', None)
    _rotation.sid = sid
    try:
        yield
    finally:
        _rotation.sid = previous


def rotating_sid() -> str | None:
    """The sid being rotated on this thread, or None if no rotation is open."""
    return getattr(_rotation, 'sid', None)

def expire(sid: str, *, user=None, ip_address: str = '', request=None) -> int:
    """
    Retire everything belonging to an idle session.

    Blacklists the refresh tokens so no new access token can be minted, marks
    the tracked sessions terminated so `/monitor` stops showing them as live,
    and writes one audit row. Returns how many sessions were terminated.

    Best-effort throughout: this runs inside request handling, and failing to
    tidy up must never turn into a 500 on top of the 401 the caller is already
    getting.
    """
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

    from .models import AuditLog, UserSession
    from .utils import calculate_risk_score

    terminated = 0
    try:
        sessions = list(
            UserSession.objects.filter(sid=sid, is_active=True).select_related(
                'outstanding_token', 'user',
            )
        )
        for session in sessions:
            session.terminate(reason='idle_timeout')
            terminated += 1
            if session.outstanding_token_id:
                try:
                    BlacklistedToken.objects.get_or_create(token=session.outstanding_token)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.error('Error blacklisting idle token: %s', exc, exc_info=True)

        subject = user or (sessions[0].user if sessions else None)
        if subject and getattr(settings, 'CREDENTIALS_AUDIT_LOGGING_ENABLED', True):
            AuditLog.objects.create(
                user=subject,
                event_type='session_terminated',
                ip_address=ip_address or (sessions[0].ip_address if sessions else '0.0.0.0'),
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
                request_path=request.path if request else '',
                request_method=request.method if request else '',
                session=sessions[0] if sessions else None,
                is_suspicious=False,
                risk_score=calculate_risk_score('idle_timeout'),
                metadata={
                    'reason': 'idle_timeout',
                    'timeout_minutes': timeout_minutes(),
                    'sessions_terminated': terminated,
                },
            )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error('Error expiring idle session %s: %s', sid, exc, exc_info=True)
    finally:
        forget(sid)

    if terminated:
        logger.info('Idle timeout: terminated %s session(s) for sid %s', terminated, sid)
    return terminated

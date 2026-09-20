"""
Refresh-token rotation must not look like a logout and a new login.

The frontend rotates its refresh token every few minutes for as long as a tab
is open. Each rotation blacklists the outgoing token and mints a replacement,
and both of those fire a `post_save` that the session signals used to read as
an ending and a beginning. One login therefore became a chain of session rows,
a `logout` nobody performed, and a `login_success` nobody performed.

Measured on a development database before the fix: 3,027 session rows for 12
actual logins, chains of up to 19 rows each, and 97% of the audit log
fabricated — 3,035 `login_success` and 2,859 `logout` events. The
concurrent-session limit had fired 147 times, every one against a phantom.

Which is why the tests that matter most here are not about the row count. They
are about what must keep working once rotation stops being audited: a real
logout is still recorded, an idle session is still expired, and the
concurrent-session cap still counts genuine logins.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken

from conftest import TEST_PASSWORD
from credentials import session_activity
from credentials.models import AuditLog, UserSession

User = get_user_model()

LOGIN = '/users/auth/login/'
REFRESH = '/users/auth/refresh/'
LOGOUT = '/users/auth/logout/'
PROFILE = '/users/auth/profile/'


@pytest.fixture
def person(db):
    return User.objects.create_user(email='rot@x.test', password=TEST_PASSWORD)


def _login(api_client, person):
    resp = api_client.post(
        LOGIN, {'email': person.email, 'password': TEST_PASSWORD}, format='json',
    )
    assert resp.status_code == 200, resp.data
    access = resp.data['access']
    return access, session_activity.sid_from_token(UntypedToken(access))


def _rotate(api_client, times=1):
    for _ in range(times):
        resp = api_client.post(REFRESH)
        assert resp.status_code == 200, resp.data
    return resp.data['access']


@pytest.mark.django_db
class TestOneLoginIsOneSession:

    def test_rotating_does_not_fork_the_session(self, api_client, person):
        _, sid = _login(api_client, person)
        _rotate(api_client, times=5)

        assert UserSession.objects.filter(sid=sid).count() == 1

    def test_the_row_follows_the_current_token(self, api_client, person):
        """
        Relinking, not abandoning. If the row kept pointing at a blacklisted
        token, terminating the session would blacklist something already dead
        and leave the live token working.
        """
        _, sid = _login(api_client, person)
        _rotate(api_client, times=3)

        session = UserSession.objects.get(sid=sid)
        newest = OutstandingToken.objects.filter(user=person).order_by('-created_at').first()
        assert session.outstanding_token_id == newest.id

    def test_the_session_stays_usable_after_rotating(self, api_client, person):
        _login(api_client, person)
        access = _rotate(api_client, times=2)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        assert api_client.get(PROFILE).status_code == 200


@pytest.mark.django_db
class TestTheAuditTrailRecordsOnlyWhatHappened:
    """
    An audit log is a compliance artifact. One that is mostly invented is worse
    than none, because it is trusted.
    """

    def test_rotating_is_not_recorded_as_a_logout(self, api_client, person):
        _login(api_client, person)
        _rotate(api_client, times=5)

        assert AuditLog.objects.filter(user=person, event_type='logout').count() == 0

    def test_rotating_is_not_recorded_as_a_login(self, api_client, person):
        _login(api_client, person)
        _rotate(api_client, times=5)

        assert AuditLog.objects.filter(
            user=person, event_type='login_success',
        ).count() == 1

    def test_a_real_logout_is_still_recorded(self, api_client, person):
        """The event that must survive the change."""
        access, sid = _login(api_client, person)
        _rotate(api_client, times=3)

        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        assert api_client.post(LOGOUT).status_code == 200

        assert AuditLog.objects.filter(user=person, event_type='logout').count() == 1
        session = UserSession.objects.get(sid=sid)
        assert session.is_active is False
        assert session.termination_reason == 'logout'


@pytest.mark.django_db
class TestTheControlsThatCountSessions:
    """
    Two features read session rows. Both were being driven by phantoms.
    """

    def test_idle_expiry_still_finds_a_rotated_session(self, api_client, person):
        access, sid = _login(api_client, person)
        access = _rotate(api_client, times=3)
        session_activity.forget(sid)

        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        resp = api_client.get(PROFILE)
        assert resp.status_code == 401
        assert resp.json()['code'] == session_activity.IDLE_TIMEOUT_CODE

        session = UserSession.objects.get(sid=sid)
        assert session.termination_reason == 'idle_timeout'

    def test_rotating_does_not_consume_the_concurrent_session_limit(
        self, api_client, person, settings,
    ):
        """
        The cap is meant to count devices. Counting rotations meant a single
        open tab tripped it every few minutes and evicted its own earlier rows.
        """
        settings.MAX_CONCURRENT_SESSIONS_PER_USER = 3
        _login(api_client, person)
        _rotate(api_client, times=6)

        assert AuditLog.objects.filter(
            user=person, event_type='concurrent_session_limit',
        ).count() == 0

    def test_the_limit_still_counts_genuine_logins(self, api_client, person, settings):
        settings.MAX_CONCURRENT_SESSIONS_PER_USER = 2
        for _ in range(4):
            api_client.cookies.clear()
            _login(api_client, person)

        active = UserSession.objects.filter(user=person, is_active=True).count()
        assert active <= 2, 'the cap must still evict older logins'


@pytest.mark.django_db
class TestWhatIsNotARotation:

    def test_a_first_login_still_creates_a_session(self, api_client, person):
        """There is nothing to relink; the row has to be made."""
        _, sid = _login(api_client, person)
        assert UserSession.objects.filter(sid=sid).count() == 1

    def test_a_token_minted_outside_a_rotation_is_untouched(self, person):
        """
        The marker is thread-local and scoped to the view's rotation block, so
        anything minting a token elsewhere gets the ordinary behaviour.
        """
        assert session_activity.rotating_sid() is None
        RefreshToken.for_user(person)
        assert session_activity.rotating_sid() is None

    def test_the_marker_is_cleared_even_when_rotation_raises(self):
        """A stranded flag would silently stop auditing every later logout."""
        with pytest.raises(RuntimeError):
            with session_activity.rotating('abc123'):
                raise RuntimeError('boom')
        assert session_activity.rotating_sid() is None

    def test_nesting_restores_the_outer_marker(self):
        with session_activity.rotating('outer'):
            with session_activity.rotating('inner'):
                assert session_activity.rotating_sid() == 'inner'
            assert session_activity.rotating_sid() == 'outer'
        assert session_activity.rotating_sid() is None

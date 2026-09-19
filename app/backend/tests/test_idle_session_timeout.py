"""
Idle-session expiry.

`SESSION_ACTIVITY_TIMEOUT_MINUTES` shipped with the credentials app but was
never enforced — the middleware read it into a variable it then discarded, so a
signed-in browser stayed signed in for the full 7-day refresh lifetime. These
tests pin the behaviour that replaced it, and the two bugs underneath it:

* the activity lookup matched an access token's `jti` against
  `OutstandingToken.jti`, which stores *refresh* ids, so it never matched;
* the check lived in `process_response`, where it could not refuse anything.

The tests that matter most are the ones about what must *not* keep a session
alive (a background poll) and what must *not* be expired (a machine token).
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken

from conftest import TEST_PASSWORD
from credentials import session_activity
from credentials.models import AuditLog, UserSession

User = get_user_model()

LOGIN = '/users/auth/login/'
REFRESH = '/users/auth/refresh/'
PROFILE = '/users/auth/profile/'


@pytest.fixture
def person(db):
    return User.objects.create_user(email='idle@x.test', password=TEST_PASSWORD)


def _login(api_client, person):
    """Sign in for real, so the sid claim is minted the way production does."""
    resp = api_client.post(
        LOGIN, {'email': person.email, 'password': TEST_PASSWORD}, format='json',
    )
    assert resp.status_code == 200, resp.data
    access = resp.data['access']
    return access, session_activity.sid_from_token(UntypedToken(access))


def _go_idle(sid):
    """What Redis does on its own once the TTL runs out."""
    session_activity.forget(sid)


@pytest.mark.django_db
class TestTheClockRuns:

    def test_a_login_carries_a_session_id(self, api_client, person):
        access, sid = _login(api_client, person)
        assert sid, 'access token must carry the sid claim'
        assert not session_activity.is_idle(sid)

    def test_the_session_row_records_it(self, api_client, person):
        """
        Without this the expiry has nothing to terminate. It cannot be read back
        off the stored token: simplejwt writes OutstandingToken inside
        for_user(), before any custom claim exists.
        """
        _, sid = _login(api_client, person)
        assert UserSession.objects.filter(sid=sid).exists()

    def test_a_request_keeps_the_session_alive(self, api_client, person):
        access, sid = _login(api_client, person)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        assert api_client.get(PROFILE).status_code == 200
        assert not session_activity.is_idle(sid)


@pytest.mark.django_db
class TestGoingIdleEndsTheSession:

    def test_the_request_itself_is_refused(self, api_client, person):
        """
        In `process_response` — where the old code lived — the view has already
        run. Refusing before it runs is the whole point.
        """
        access, sid = _login(api_client, person)
        _go_idle(sid)

        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        resp = api_client.get(PROFILE)
        assert resp.status_code == 401
        assert resp.json()['code'] == session_activity.IDLE_TIMEOUT_CODE

    def test_no_new_token_can_be_minted(self, api_client, person):
        """The enforcement that actually ends the session."""
        _, sid = _login(api_client, person)
        _go_idle(sid)

        resp = api_client.post(REFRESH)
        assert resp.status_code == 401

    def test_the_refresh_token_is_blacklisted(self, api_client, person):
        access, sid = _login(api_client, person)
        _go_idle(sid)

        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        api_client.get(PROFILE)

        session = UserSession.objects.filter(sid=sid).first()
        assert BlacklistedToken.objects.filter(token=session.outstanding_token).exists()

    def test_the_session_is_marked_terminated(self, api_client, person):
        """`/monitor` must not keep showing an ended session as live."""
        access, sid = _login(api_client, person)
        _go_idle(sid)

        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        api_client.get(PROFILE)

        session = UserSession.objects.filter(sid=sid).first()
        assert session.is_active is False
        assert session.termination_reason == 'idle_timeout'

    def test_it_is_audited_but_not_flagged_suspicious(self, api_client, person):
        access, sid = _login(api_client, person)
        _go_idle(sid)

        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        api_client.get(PROFILE)

        entry = AuditLog.objects.filter(
            user=person, event_type='session_terminated',
        ).order_by('-event_timestamp').first()
        assert entry is not None
        assert entry.metadata['reason'] == 'idle_timeout'
        # Routine housekeeping — scoring it like an IP change would bury the
        # events that do deserve attention.
        assert entry.is_suspicious is False
        assert entry.risk_score == 0


@pytest.mark.django_db
class TestWhatCountsAsActivity:
    """
    The frontend polls notifications every 30 seconds on every page. If that
    counted as the user being present, no session would ever go idle and the
    whole control would be decorative.
    """

    def test_a_background_poll_does_not_postpone_the_timeout(self, api_client, person):
        access, sid = _login(api_client, person)
        session_activity.touch(sid)
        stale = cache.get(f'session_activity:{sid}') - 3600
        cache.set(f'session_activity:{sid}', stale, 1800)

        api_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {access}', HTTP_X_BACKGROUND_REQUEST='1',
        )
        assert api_client.get(PROFILE).status_code == 200
        assert cache.get(f'session_activity:{sid}') == stale

    def test_a_user_request_does(self, api_client, person):
        access, sid = _login(api_client, person)
        stale = cache.get(f'session_activity:{sid}') - 3600
        cache.set(f'session_activity:{sid}', stale, 1800)

        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        assert api_client.get(PROFILE).status_code == 200
        assert cache.get(f'session_activity:{sid}') > stale

    def test_a_background_poll_is_still_refused_once_idle(self, api_client, person):
        """An abandoned tab should be signed out promptly, not on return."""
        access, sid = _login(api_client, person)
        _go_idle(sid)

        api_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {access}', HTTP_X_BACKGROUND_REQUEST='1',
        )
        assert api_client.get(PROFILE).status_code == 401


@pytest.mark.django_db
class TestWhatIsDeliberatelyExempt:

    def test_a_token_without_the_claim_is_grandfathered(self, api_client, person):
        """
        Tokens minted before this shipped, and the API-key exchange's machine
        tokens, carry no sid. Expiring them on sight would sign out every user
        on deploy and cut off service integrations that are behaving normally.
        """
        access = str(RefreshToken.for_user(person).access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        assert api_client.get(PROFILE).status_code == 200

    def test_logging_out_still_works_when_idle(self, api_client, person):
        """A client must always be able to tidy up after itself."""
        access, sid = _login(api_client, person)
        _go_idle(sid)

        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        assert api_client.post('/users/auth/logout/').status_code == 200

    @override_settings(SESSION_ACTIVITY_TIMEOUT_MINUTES=0)
    def test_zero_disables_it(self, api_client, person):
        access = str(RefreshToken.for_user(person).access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        assert api_client.get(PROFILE).status_code == 200


@pytest.mark.django_db
class TestTheClockSurvivesRotation:
    """
    The frontend refreshes its access token every ~4 minutes, for as long as a
    tab is open. `CustomTokenRefreshView` mints the rotated token with
    `for_user()`, which builds a fresh payload — so unless the sid is carried
    over explicitly, every refresh starts a new session and the timeout never
    arrives.
    """

    def test_the_session_id_is_carried_across_a_refresh(self, api_client, person):
        _, sid = _login(api_client, person)

        resp = api_client.post(REFRESH)
        assert resp.status_code == 200

        rotated_sid = session_activity.sid_from_token(UntypedToken(resp.data['access']))
        assert rotated_sid == sid

    def test_refreshing_does_not_postpone_the_timeout(self, api_client, person):
        """A background keepalive is not the user being present."""
        _, sid = _login(api_client, person)
        stale = cache.get(f'session_activity:{sid}') - 3600
        cache.set(f'session_activity:{sid}', stale, 1800)

        assert api_client.post(REFRESH).status_code == 200
        assert cache.get(f'session_activity:{sid}') == stale

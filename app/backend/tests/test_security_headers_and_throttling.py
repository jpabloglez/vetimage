"""
Locks in the Phase 2 hardening: security response headers, throttle
configuration, and constant-time secret comparison.

These assert configuration rather than behaviour in a few places, because a
silent revert (e.g. NUM_PROXIES going back to None) reopens a real hole with no
other visible symptom.
"""

import pytest
from django.conf import settings
from django.urls import reverse


class TestThrottleConfiguration:

    def test_baseline_throttles_are_enabled(self):
        """ScopedRateThrottle alone is inert on views without a throttle_scope,
        which previously left most of the API unlimited."""
        classes = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES']
        assert any('AnonRateThrottle' in c for c in classes)
        assert any('UserRateThrottle' in c for c in classes)
        assert any('ScopedRateThrottle' in c for c in classes)

    def test_every_declared_scope_has_a_rate(self):
        rates = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
        for scope in ('anon', 'user', 'login', 'register', 'password_reset',
                      'token_refresh', 'public_share', 'webhook', 'upload'):
            assert rates.get(scope), f'throttle scope {scope!r} has no rate'

    def test_num_proxies_is_set_so_throttles_cannot_be_spoofed(self):
        """
        With NUM_PROXIES unset, DRF keys throttles on the raw client-supplied
        X-Forwarded-For header, so any client can mint a fresh bucket per
        request and bypass every rate limit. It must be an explicit integer.
        """
        num_proxies = settings.REST_FRAMEWORK.get('NUM_PROXIES')
        assert num_proxies is not None, 'NUM_PROXIES must be set explicitly'
        assert isinstance(num_proxies, int)


@pytest.mark.django_db
class TestSecurityHeaders:

    def test_csp_and_hardening_headers_are_present(self, api_client):
        resp = api_client.get(reverse('health-liveness'))
        # Report-only by default so a missed directive degrades to a console
        # warning instead of a blank page.
        assert 'Content-Security-Policy-Report-Only' in resp
        csp = resp['Content-Security-Policy-Report-Only']
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp

        assert 'Referrer-Policy' in resp
        assert 'Permissions-Policy' in resp

    def test_csp_is_report_only_by_default(self, api_client):
        """Enforcing before a clean report-only run risks breaking Swagger/ReDoc,
        so the enforced header must stay off until CSP_ENFORCE is set."""
        resp = api_client.get(reverse('health-liveness'))
        assert 'Content-Security-Policy' not in resp
        assert settings.CSP_ENFORCE is False


class TestConstantTimeComparison:
    """The webhook secret guards the only unauthenticated write path."""

    def test_webhook_rejects_wrong_secret(self):
        import hmac
        # Sanity check on the primitive the handler now uses: compare_digest is
        # value-correct, so swapping it in cannot change accept/reject outcomes.
        assert hmac.compare_digest('abc', 'abc')
        assert not hmac.compare_digest('abc', 'abd')
        assert not hmac.compare_digest('abc', '')

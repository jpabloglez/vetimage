"""
WebSocket authentication by single-use ticket.

The JWT used to travel in the socket's query string, which put live
credentials into reverse-proxy access logs. The properties that make a ticket
safe there — short-lived, single-use, opaque — are the ones asserted here.
"""

import pytest
from django.core.cache import cache
from django.urls import reverse

from core.ws_tickets import TICKET_TTL_SECONDS, issue_ticket, redeem_ticket


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestTicketLifecycle:

    def test_ticket_resolves_to_its_user(self, user):
        assert redeem_ticket(issue_ticket(user)) == user.pk

    def test_ticket_is_single_use(self, user):
        """A ticket scraped from an access log must already be spent."""
        ticket = issue_ticket(user)
        assert redeem_ticket(ticket) == user.pk
        assert redeem_ticket(ticket) is None, 'ticket must not be replayable'

    def test_unknown_ticket_is_rejected(self):
        assert redeem_ticket('never-issued') is None

    def test_empty_ticket_is_rejected(self):
        assert redeem_ticket('') is None
        assert redeem_ticket(None) is None

    def test_ticket_expires(self, user, settings):
        """Expiry is what limits the value of a leaked log line."""
        ticket = issue_ticket(user)
        # Simulate the TTL elapsing by dropping the key, which is what Redis
        # does on expiry — asserting on wall-clock would make this slow/flaky.
        cache.delete(f'ws_ticket:{ticket}')
        assert redeem_ticket(ticket) is None

    def test_ticket_is_opaque_and_carries_no_user_data(self, user):
        ticket = issue_ticket(user)
        assert str(user.pk) not in ticket
        assert user.email not in ticket
        assert len(ticket) >= 32

    def test_ttl_is_short(self):
        assert TICKET_TTL_SECONDS <= 60, (
            'a long-lived ticket reintroduces the credential-in-logs problem'
        )


@pytest.mark.django_db
class TestTicketEndpoint:

    def test_requires_authentication(self, api_client):
        resp = api_client.post(reverse('ws-ticket'))
        assert resp.status_code in (401, 403)

    def test_issues_a_usable_ticket(self, auth_client, user):
        resp = auth_client.post(reverse('ws-ticket'))
        assert resp.status_code == 200
        assert resp.data['expires_in'] == TICKET_TTL_SECONDS
        assert redeem_ticket(resp.data['ticket']) == user.pk

    def test_each_request_yields_a_distinct_ticket(self, auth_client):
        a = auth_client.post(reverse('ws-ticket')).data['ticket']
        b = auth_client.post(reverse('ws-ticket')).data['ticket']
        assert a != b

    def test_ticket_does_not_authenticate_the_rest_api(self, api_client, auth_client):
        """A ticket opens a socket and nothing else."""
        ticket = auth_client.post(reverse('ws-ticket')).data['ticket']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {ticket}')
        resp = api_client.get(reverse('dicom_images:dicomweb-studies'))
        assert resp.status_code in (401, 403)

"""
Single-use tickets for authenticating WebSocket connections.

The client used to connect with its JWT access token in the query string
(`ws://…/ws/notifications/?token=eyJhbGci…`). Query strings are routinely
written to reverse-proxy and load-balancer access logs, so live credentials
ended up in storage that is retained longer, and read more widely, than
anything holding credentials should be.

A ticket is an opaque random string that:
  - carries no user data (it's a lookup key, not a token),
  - is valid for TICKET_TTL_SECONDS, long enough to open a socket and no longer,
  - is consumed on first use, so a copy scraped from a log is already spent,
  - authenticates nothing else — it is useless against the REST API.

Tickets live in the Redis cache rather than the database: they are short-lived,
high-churn, and losing them on a cache flush costs a reconnect, nothing more.
"""

import secrets

from django.core.cache import cache

# Long enough for the browser to receive the ticket and open the socket
# (including a slow mobile connection), short enough that a leaked log line is
# almost always already useless.
TICKET_TTL_SECONDS = 30

_KEY_PREFIX = 'ws_ticket:'


def issue_ticket(user) -> str:
    """Mint a single-use ticket for *user* and return it."""
    ticket = secrets.token_urlsafe(32)
    cache.set(f'{_KEY_PREFIX}{ticket}', user.pk, timeout=TICKET_TTL_SECONDS)
    return ticket


def redeem_ticket(ticket: str):
    """
    Return the user id for *ticket* and invalidate it, or None.

    Deleting before returning is what makes this single-use: a replay of the
    same ticket — from an access log, say — finds nothing.
    """
    if not ticket:
        return None
    key = f'{_KEY_PREFIX}{ticket}'
    user_id = cache.get(key)
    if user_id is None:
        return None
    cache.delete(key)
    return user_id

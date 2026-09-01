"""
Custom WebSocket Authentication Middleware

Authenticates WebSocket connections with a single-use ticket obtained from
`POST /users/auth/ws-ticket/`.

This used to accept the JWT access token directly in the query string
(`?token=eyJhbGci…`). Query strings are routinely written to reverse-proxy and
load-balancer access logs, so live credentials ended up in log storage that is
retained longer, and read more widely, than anything holding credentials
should be. A ticket is opaque, expires in 30 seconds, and is consumed on first
use — a copy scraped from a log is already spent. See core.ws_tickets.
"""

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

from core.ws_tickets import redeem_ticket
from users.models import User

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseMiddleware):
    """
    Authenticate Django Channels WebSocket connections via single-use ticket.

    Usage in ASGI routing:
        from backend.middleware import JWTAuthMiddleware

        application = ProtocolTypeRouter({
            'websocket': JWTAuthMiddleware(
                URLRouter(websocket_urlpatterns)
            ),
        })

    WebSocket connection example:
        ws://backend/ws/monitor/tasks/?ticket=<from /users/auth/ws-ticket/>

    The class name is kept for the ASGI wiring; authentication is by ticket,
    and the ticket is issued to a JWT-authenticated caller.
    """

    async def __call__(self, scope, receive, send):
        query_params = parse_qs(scope.get('query_string', b'').decode())
        ticket = query_params.get('ticket', [None])[0]

        # Default to anonymous; consumers reject unauthenticated connections.
        scope['user'] = AnonymousUser()

        if ticket:
            try:
                user_id = await self.redeem(ticket)
                if user_id is None:
                    # Expired, already used, or never existed. Deliberately not
                    # logging the ticket value — that would recreate the problem
                    # this mechanism exists to solve.
                    logger.warning('WebSocket authentication failed: invalid or spent ticket')
                else:
                    user = await self.get_user(user_id)
                    if user:
                        scope['user'] = user
                        logger.debug(f'WebSocket authenticated: user {user.id}')
                    else:
                        logger.warning(f'WebSocket ticket valid but user {user_id} not found')
            except Exception as e:
                logger.error(f'WebSocket authentication error: {e}')

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def redeem(self, ticket):
        """Consume the ticket (cache access is sync) and return its user id."""
        return redeem_ticket(ticket)

    @database_sync_to_async
    def get_user(self, user_id):
        """Fetch the authenticated user, or None if missing/inactive."""
        try:
            return User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return None

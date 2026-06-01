"""
Custom WebSocket Authentication Middleware

Authenticates WebSocket connections using JWT tokens passed as query parameters.
This avoids session cookie issues with CORS and cross-domain requests.
"""

import logging
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from users.models import User

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware for JWT authentication in Django Channels WebSocket connections.

    Extracts JWT token from query parameters and authenticates the user.

    Usage in ASGI routing:
        from backend.middleware import JWTAuthMiddleware

        application = ProtocolTypeRouter({
            'websocket': JWTAuthMiddleware(
                URLRouter(websocket_urlpatterns)
            ),
        })

    WebSocket connection example:
        ws://backend/ws/monitor/tasks/?token=eyJhbGci...
    """

    async def __call__(self, scope, receive, send):
        """
        Intercept WebSocket connection and authenticate user.

        Extracts 'token' query parameter and validates it as a JWT access token.
        If valid, attaches the authenticated user to scope['user'].
        """
        # Parse query string to get token
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        # Default to anonymous user
        scope['user'] = AnonymousUser()

        if token:
            try:
                # Validate JWT access token
                access_token = AccessToken(token)

                # Extract user ID from token
                user_id = access_token.get('user_id')

                if user_id:
                    # Fetch user from database
                    user = await self.get_user(user_id)
                    if user:
                        scope['user'] = user
                        logger.debug(f"WebSocket authenticated: user {user.id}")
                    else:
                        logger.warning(f"WebSocket token valid but user {user_id} not found")
                else:
                    logger.warning("WebSocket token missing user_id")

            except (TokenError, InvalidToken) as e:
                logger.warning(f"WebSocket authentication failed: {e}")
            except Exception as e:
                logger.error(f"WebSocket authentication error: {e}")

        # Continue with the connection
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id):
        """
        Fetch user from database asynchronously.

        Args:
            user_id: User ID from JWT token

        Returns:
            User instance or None if not found
        """
        try:
            return User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return None

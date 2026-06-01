"""
Backend configuration API views.

Provides endpoints for frontend to fetch configuration settings.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_frontend_config(request):
    """
    Return frontend configuration including tracking mode.

    This allows the frontend to adapt its behavior based on backend settings.

    Returns:
        Response: Configuration object with:
            - websocket_based_tracking (bool): Whether to use WebSocket
            - monitor_poll_interval (int): Polling interval for task/transfer lists (seconds)
            - stats_poll_interval (int): Polling interval for statistics (seconds)
            - websocket_url (str|None): WebSocket base URL if enabled
    """
    return Response({
        'websocket_based_tracking': settings.WEBSOCKET_BASED_TRACKING,
        'monitor_poll_interval': settings.MONITOR_POLL_INTERVAL,
        'stats_poll_interval': settings.STATS_POLL_INTERVAL,
        'websocket_url': getattr(settings, 'WS_BASE_URL', None) if settings.WEBSOCKET_BASED_TRACKING else None,
    })

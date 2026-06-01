"""
WebSocket URL routing for AI Analysis real-time updates.

This module defines WebSocket URL patterns for the Monitor page.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/monitor/tasks/$', consumers.TaskMonitorConsumer.as_asgi()),
]

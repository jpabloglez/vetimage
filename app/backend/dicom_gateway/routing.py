"""
WebSocket URL routing for DICOM Gateway.

Defines WebSocket URL patterns for real-time transfer monitoring.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/monitor/transfers/$', consumers.TransferMonitorConsumer.as_asgi()),
]

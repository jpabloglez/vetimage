"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django_asgi_app = get_asgi_application()

# Import routing after Django setup to avoid AppRegistryNotReady errors
from channels.routing import ProtocolTypeRouter, URLRouter
from ai_analysis.routing import websocket_urlpatterns as ai_websockets
from dicom_gateway.routing import websocket_urlpatterns as dicom_websockets
from patients.routing import websocket_urlpatterns as patients_websockets
from backend.middleware import JWTAuthMiddleware

application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    'http': django_asgi_app,

    # WebSocket handler with JWT authentication
    # Note: AllowedHostsOriginValidator removed as JWT auth provides sufficient security
    'websocket': JWTAuthMiddleware(
        URLRouter(ai_websockets + dicom_websockets + patients_websockets)
    ),
})

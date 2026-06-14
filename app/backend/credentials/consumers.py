"""
WebSocket consumer for real-time in-app notifications.

Each authenticated user joins `notifications_user_{user_id}`. A post_save
signal on Notification (see signals.py) broadcasts `notification_created` to
that group so the navbar bell updates instantly instead of waiting for the 30s
poll. One-way push; the REST API remains the source of truth.
"""
import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


def user_notification_group(user_id) -> str:
    return f'notifications_user_{user_id}'


class NotificationConsumer(AsyncWebsocketConsumer):
    """ws://backend/ws/notifications/?token=<jwt> — live notifications."""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        self.group = user_notification_group(self.user.id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        logger.info('Notifications WS connected: user %s', self.user.id)

    async def disconnect(self, close_code):
        if hasattr(self, 'group'):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive(self, text_data):
        try:
            json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            pass

    async def notification_created(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification_created',
            'notification': event['notification'],
        }))

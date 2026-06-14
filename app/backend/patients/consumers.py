"""
WebSocket consumer for real-time owner↔clinic messaging (#22 real-time).

Each authenticated user joins a personal group `messages_user_{user_id}`. When a
message is created (see MessageViewSet), the counterpart's group receives a
`message_created` event so an open thread updates live instead of waiting for
the 30s poll. One-way push (server→client); the REST API remains the source of
truth for sending and history.
"""
import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


def user_message_group(user_id) -> str:
    return f'messages_user_{user_id}'


class MessageConsumer(AsyncWebsocketConsumer):
    """ws://backend/ws/messages/?token=<jwt> — live owner↔clinic messages."""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        self.group = user_message_group(self.user.id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        logger.info('Messages WS connected: user %s', self.user.id)

    async def disconnect(self, close_code):
        if hasattr(self, 'group'):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive(self, text_data):
        # One-way push; ignore client payloads beyond basic validation.
        try:
            json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            pass

    async def message_created(self, event):
        """Channel-layer handler: forward a new message to the client."""
        await self.send(text_data=json.dumps({
            'type': 'message_created',
            'animal_patient_id': event['animal_patient_id'],
            'message': event['message'],
        }))

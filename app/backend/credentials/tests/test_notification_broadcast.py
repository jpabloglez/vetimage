"""
Tests for the real-time notification broadcast (post_save signal → WS group).
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from credentials.models import Notification
from credentials.consumers import user_notification_group


@pytest.mark.django_db
class TestNotificationBroadcast:
    def test_creating_notification_broadcasts_to_user_group(self, user, monkeypatch):
        import channels.layers as layers
        fake_layer = MagicMock()
        fake_layer.group_send = AsyncMock()
        monkeypatch.setattr(layers, 'get_channel_layer', lambda: fake_layer)

        Notification.objects.create(user=user, message='Hello', notification_type='info')

        assert fake_layer.group_send.called
        group, payload = fake_layer.group_send.call_args.args
        assert group == user_notification_group(user.id)
        assert payload['type'] == 'notification_created'
        assert payload['notification']['message'] == 'Hello'

    def test_update_does_not_rebroadcast(self, user, monkeypatch):
        import channels.layers as layers
        fake_layer = MagicMock()
        fake_layer.group_send = AsyncMock()
        n = Notification.objects.create(user=user, message='x', notification_type='info')
        monkeypatch.setattr(layers, 'get_channel_layer', lambda: fake_layer)

        n.is_read = True
        n.save(update_fields=['is_read'])  # created=False → no broadcast

        assert not fake_layer.group_send.called

    def test_broadcast_failure_does_not_break_create(self, user, monkeypatch):
        import channels.layers as layers
        def boom():
            raise RuntimeError('redis down')
        monkeypatch.setattr(layers, 'get_channel_layer', boom)
        # Must not raise — notification still persists.
        n = Notification.objects.create(user=user, message='still here', notification_type='info')
        assert Notification.objects.filter(pk=n.pk).exists()

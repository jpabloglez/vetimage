"""
WebSocket Consumers for AI Analysis real-time monitoring.

This module provides WebSocket consumers for the Monitor page that enable
real-time updates when analysis tasks change status.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import AnalysisTask
from .serializers import AnalysisTaskMonitorSerializer

logger = logging.getLogger(__name__)


class TaskMonitorConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time task status updates.

    WebSocket URL: ws://backend/ws/monitor/tasks/

    Sends updates when analysis tasks change status.

    Group Architecture:
    - user_{user_id}: User's personal task updates
    - org_{org_id}_shared: Organization-wide shared tasks
    - dept_{dept}_shared: Department-level shared tasks
    - team_{team}_shared: Team-level shared tasks

    Security:
    - Requires Django session authentication (via AuthMiddlewareStack)
    - Only joins shared groups if user has opted-in to job sharing
    - Respects organization boundaries
    """

    async def connect(self):
        """
        Handle WebSocket connection.

        1. Verify user authentication
        2. Join user's personal group
        3. Join shared groups if opted-in
        4. Send connection confirmation
        """
        self.user = self.scope['user']

        # Reject unauthenticated connections
        if not self.user.is_authenticated:
            logger.warning("WebSocket connection rejected: user not authenticated")
            await self.close()
            return

        # Join user's personal group
        self.user_group = f'task_user_{self.user.id}'
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        # Join shared groups if user has opted-in
        profile = await self.get_user_profile()
        if profile and profile.is_sharing_jobs_with_colleagues:
            # Join organization group
            if profile.organization_id:
                org_group = f'task_org_{profile.organization_id}'
                await self.channel_layer.group_add(org_group, self.channel_name)

            # Join department group
            if profile.department:
                dept_group = f'task_dept_{profile.department}'
                await self.channel_layer.group_add(dept_group, self.channel_name)

            # Join team group
            if profile.team_name:
                team_group = f'task_team_{profile.team_name}'
                await self.channel_layer.group_add(team_group, self.channel_name)

        # Accept the WebSocket connection
        await self.accept()

        # Send connection confirmation (TEMPORARILY DISABLED FOR TESTING)
        # await self.send(text_data=json.dumps({
        #     'type': 'connection',
        #     'status': 'connected',
        #     'message': 'WebSocket connection established'
        # }))

        logger.info(f"WebSocket connected: user {self.user.id}")

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.

        Leave all channel groups to clean up resources.
        """
        # Leave user's personal group (only if it was created)
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

        if hasattr(self, 'user') and self.user.is_authenticated:
            logger.info(f"WebSocket disconnected: user {self.user.id}, code {close_code}")
        else:
            logger.info(f"WebSocket disconnected: code {close_code}")

    async def receive(self, text_data):
        """
        Handle messages received from WebSocket client.

        Currently not used - this is a one-way push mechanism from server to client.
        Can be extended in future for client commands (e.g., "subscribe to model X").
        """
        try:
            data = json.loads(text_data)
            # Future: handle client commands here
            logger.debug(f"WebSocket received from user {self.user.id}: {data}")
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received from user {self.user.id}")

    # ========================================================================
    # Channel Layer Message Handlers
    # ========================================================================

    async def task_updated(self, event):
        """
        Send task update to WebSocket client.

        Called by channel layer when a task status changes.
        """
        await self.send(text_data=json.dumps({
            'type': 'task_updated',
            'task': event['task']
        }))

    async def task_completed(self, event):
        """
        Send task completion notification to WebSocket client.

        Called by channel layer when a task completes successfully.
        """
        await self.send(text_data=json.dumps({
            'type': 'task_completed',
            'task': event['task'],
            'notification': {
                'title': 'Analysis Complete',
                'message': f"{event['task']['model_name']} finished processing"
            }
        }))

    async def task_failed(self, event):
        """
        Send task failure notification to WebSocket client.

        Called by channel layer when a task fails.
        """
        await self.send(text_data=json.dumps({
            'type': 'task_failed',
            'task': event['task'],
            'notification': {
                'title': 'Analysis Failed',
                'message': f"{event['task']['model_name']} encountered an error",
                'error': event['task'].get('error_message', 'Unknown error')
            }
        }))

    # ========================================================================
    # Database Helpers (Async-to-Sync Wrapper)
    # ========================================================================

    @database_sync_to_async
    def get_user_profile(self):
        """
        Fetch user profile from database (async-safe).

        Returns:
            UserProfile object or None if not found
        """
        try:
            return self.user.userprofile
        except Exception:
            return None

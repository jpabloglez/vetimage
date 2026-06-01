"""
WebSocket Consumers for DICOM Transfer real-time monitoring.

This module provides WebSocket consumers for the Monitor page that enable
real-time updates when DICOM transfers occur.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class TransferMonitorConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time DICOM transfer status updates.

    WebSocket URL: ws://backend/ws/monitor/transfers/

    Sends updates when DICOM transfers occur or change status.

    Group Architecture:
    - transfer_user_{user_id}: User's personal transfer updates
    - transfer_org_{org_id}: Organization-wide transfer updates
    - transfer_dept_{dept}: Department-level transfer updates
    - transfer_team_{team}: Team-level transfer updates

    Security:
    - Requires Django session authentication (via AuthMiddlewareStack)
    - Only joins shared groups if user has opted-in to job sharing
    - Respects organization boundaries

    Message Types:
    - connection: Connection established confirmation
    - transfer_updated: Transfer status changed
    - transfer_completed: Transfer finished successfully
    - transfer_failed: Transfer encountered error
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
        self.user_group = f'transfer_user_{self.user.id}'
        await self.channel_layer.group_add(self.user_group, self.channel_name)

        # Join shared groups if user has opted-in
        profile = await self.get_user_profile()
        if profile and profile.is_sharing_jobs_with_colleagues:
            # Join organization group
            if profile.organization_id:
                org_group = f'transfer_org_{profile.organization_id}'
                await self.channel_layer.group_add(org_group, self.channel_name)
                logger.info(f"User {self.user.id} joined transfer org group: {org_group}")

            # Join department group
            if profile.department:
                dept_group = f'transfer_dept_{profile.department}'
                await self.channel_layer.group_add(dept_group, self.channel_name)
                logger.info(f"User {self.user.id} joined transfer dept group: {dept_group}")

            # Join team group
            if profile.team_name:
                team_group = f'transfer_team_{profile.team_name}'
                await self.channel_layer.group_add(team_group, self.channel_name)
                logger.info(f"User {self.user.id} joined transfer team group: {team_group}")

        # Accept the WebSocket connection
        await self.accept()

        # Send connection confirmation (TEMPORARILY DISABLED FOR TESTING)
        # await self.send(text_data=json.dumps({
        #     'type': 'connection',
        #     'status': 'connected',
        #     'message': 'Connected to DICOM transfer monitoring'
        # }))

        logger.info(f"Transfer monitor WebSocket connected for user {self.user.id}")

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.

        Leaves all channel groups.
        """
        # Leave user's personal group (only if it was created)
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

        # Leave shared groups (only if user exists)
        if hasattr(self, 'user') and self.user.is_authenticated:
            profile = await self.get_user_profile()
            if profile and profile.is_sharing_jobs_with_colleagues:
                if profile.organization_id:
                    org_group = f'transfer_org_{profile.organization_id}'
                    await self.channel_layer.group_discard(org_group, self.channel_name)

                if profile.department:
                    dept_group = f'transfer_dept_{profile.department}'
                    await self.channel_layer.group_discard(dept_group, self.channel_name)

                if profile.team_name:
                    team_group = f'transfer_team_{profile.team_name}'
                    await self.channel_layer.group_discard(team_group, self.channel_name)

            logger.info(f"Transfer monitor WebSocket disconnected for user {self.user.id}: {close_code}")
        else:
            logger.info(f"Transfer monitor WebSocket disconnected: {close_code}")

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages from client.

        Currently not used - server only broadcasts to clients.
        Could be extended for client actions (e.g., pause/resume monitoring).
        """
        pass

    # Broadcast message handlers

    async def transfer_updated(self, event):
        """
        Broadcast transfer status update to client.

        Called when a transfer's status changes.
        """
        await self.send(text_data=json.dumps({
            'type': 'transfer_updated',
            'transfer': event['transfer']
        }))

    async def transfer_completed(self, event):
        """
        Broadcast transfer completion to client.

        Called when a transfer finishes successfully.
        Includes notification data for toast messages.
        """
        await self.send(text_data=json.dumps({
            'type': 'transfer_completed',
            'transfer': event['transfer'],
            'notification': event.get('notification', {
                'title': 'Transfer Complete',
                'message': f"Study received from {event['transfer'].get('source_ae', 'Unknown')}"
            })
        }))

    async def transfer_failed(self, event):
        """
        Broadcast transfer failure to client.

        Called when a transfer encounters an error.
        Includes notification data for error toast messages.
        """
        await self.send(text_data=json.dumps({
            'type': 'transfer_failed',
            'transfer': event['transfer'],
            'notification': event.get('notification', {
                'title': 'Transfer Failed',
                'message': f"Failed to receive from {event['transfer'].get('source_ae', 'Unknown')}",
                'error': event['transfer'].get('error_message', 'Unknown error')
            })
        }))

    # Helper methods

    @database_sync_to_async
    def get_user_profile(self):
        """
        Fetch user profile from database (async).

        Returns user's profile or None if not found.
        """
        try:
            return self.user.userprofile
        except:
            return None

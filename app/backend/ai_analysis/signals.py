"""
Django signals for broadcasting AI Analysis task updates via WebSocket.

This module listens for AnalysisTask model changes and broadcasts updates
to relevant WebSocket groups for real-time monitoring.
"""

import logging
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import AnalysisTask
from .serializers import AnalysisTaskMonitorSerializer

logger = logging.getLogger(__name__)


@receiver(post_save, sender=AnalysisTask)
def broadcast_task_update(sender, instance, created, **kwargs):
    """
    Broadcast task updates via WebSocket when a task is saved.

    Triggered by Django's post_save signal on the AnalysisTask model.

    Args:
        sender: The model class (AnalysisTask)
        instance: The actual task instance that was saved
        created: Boolean indicating if this is a new task
        **kwargs: Additional signal arguments

    Broadcasting Logic:
    1. Always send to task owner (user_{user_id} group)
    2. If owner has sharing enabled, also send to:
       - Organization group (org_{org_id}_shared)
       - Department group (dept_{dept}_shared)
       - Team group (team_{team}_shared)

    Message Types:
    - task_updated: General status update
    - task_completed: Task successfully finished
    - task_failed: Task encountered error
    """
    channel_layer = get_channel_layer()

    # Serialize task data for WebSocket transmission
    # Note: We can't pass request context in signals, so privacy filtering
    # happens in the serializer's SerializerMethodField logic
    try:
        task_data = AnalysisTaskMonitorSerializer(
            instance,
            context={'request': None}
        ).data
    except Exception as e:
        logger.error(f"Failed to serialize task {instance.id}: {e}")
        return

    # ========================================================================
    # Send to Task Owner (Always)
    # ========================================================================

    user_group = f'task_user_{instance.created_by_id}'

    try:
        # General update message
        async_to_sync(channel_layer.group_send)(
            user_group,
            {
                'type': 'task_updated',
                'task': task_data
            }
        )

        # Additional notification for completed tasks
        if instance.status == 'COMPLETED':
            async_to_sync(channel_layer.group_send)(
                user_group,
                {
                    'type': 'task_completed',
                    'task': task_data
                }
            )

        # Additional notification for failed tasks
        elif instance.status == 'FAILED':
            async_to_sync(channel_layer.group_send)(
                user_group,
                {
                    'type': 'task_failed',
                    'task': task_data
                }
            )

        logger.debug(f"Broadcast task {instance.id} update to user {instance.created_by_id}")

    except Exception as e:
        logger.error(f"Failed to broadcast to user group {user_group}: {e}")

    # ========================================================================
    # Send to Shared Groups (If Opted-In)
    # ========================================================================

    try:
        profile = instance.created_by.userprofile

        # Only broadcast to colleagues if user has opted-in
        if not profile.is_sharing_jobs_with_colleagues:
            return

        # Broadcast to organization group
        if profile.organization_id:
            org_group = f'task_org_{profile.organization_id}'
            try:
                async_to_sync(channel_layer.group_send)(
                    org_group,
                    {
                        'type': 'task_updated',
                        'task': task_data
                    }
                )
                logger.debug(f"Broadcast task {instance.id} to org {profile.organization_id}")
            except Exception as e:
                logger.error(f"Failed to broadcast to org group {org_group}: {e}")

        # Broadcast to department group
        if profile.department:
            dept_group = f'task_dept_{profile.department}'
            try:
                async_to_sync(channel_layer.group_send)(
                    dept_group,
                    {
                        'type': 'task_updated',
                        'task': task_data
                    }
                )
                logger.debug(f"Broadcast task {instance.id} to dept {profile.department}")
            except Exception as e:
                logger.error(f"Failed to broadcast to dept group {dept_group}: {e}")

        # Broadcast to team group
        if profile.team_name:
            team_group = f'task_team_{profile.team_name}'
            try:
                async_to_sync(channel_layer.group_send)(
                    team_group,
                    {
                        'type': 'task_updated',
                        'task': task_data
                    }
                )
                logger.debug(f"Broadcast task {instance.id} to team {profile.team_name}")
            except Exception as e:
                logger.error(f"Failed to broadcast to team group {team_group}: {e}")

    except Exception as e:
        # Don't fail the save operation if broadcasting fails
        logger.warning(f"Could not broadcast to shared groups for task {instance.id}: {e}")


@receiver(post_save, sender=AnalysisTask)
def trigger_dicom_seg_on_completion(sender, instance, created, **kwargs):
    """
    After a segmentation task reaches COMPLETED, schedule DICOM SEG creation.

    Conditions that must ALL be true before scheduling:
    - Task transitioned to COMPLETED (not a brand-new task)
    - Task has a result_file_path (the NIfTI mask to convert)
    - Task's model has a non-empty label_map (required by itkimage2segimage)
    - DICOM SEG has not already been created (idempotency guard)

    Uses ``transaction.on_commit`` to ensure the DB row is fully committed
    before the Celery worker tries to read it.
    """
    if created:
        return
    if instance.status != 'COMPLETED':
        return
    if not instance.result_file_path:
        return
    # Idempotency: skip if SEG was already produced (or task is still pending SEG)
    if instance.result_metadata and instance.result_metadata.get('dicom_seg_series_uid'):
        return

    model = instance.model
    if not model or not model.label_map:
        return

    task_id = str(instance.id)

    def _dispatch():
        try:
            from .tasks import create_dicom_seg_task
            create_dicom_seg_task.delay(task_id)
            logger.info("Scheduled DICOM SEG conversion for task %s", task_id)
        except Exception as exc:
            logger.error(
                "Failed to schedule DICOM SEG task for task %s: %s", task_id, exc
            )

    transaction.on_commit(_dispatch)

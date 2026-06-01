"""
Django Signals for DICOM Transfer Broadcasting.

This module handles real-time WebSocket broadcasting when DICOM transfers occur.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Count, Sum, Avg, Min, Max, Q
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import DICOMTransaction, PACSConfiguration
from dicom_images.models import MedicalStudy

logger = logging.getLogger(__name__)


def _aggregate_study_transfer_data(study_instance_uid):
    """
    Aggregate all DICOMTransaction records for a study.

    Returns study-level transfer data suitable for broadcasting.
    """
    try:
        # Get all transactions for this study
        transactions = DICOMTransaction.objects.filter(
            study_instance_uid=study_instance_uid,
            transaction_type='C-STORE',
            direction='incoming'
        )

        # Calculate aggregates
        total = transactions.count()
        if total == 0:
            return None

        successful = transactions.filter(status='success').count()
        failed = transactions.filter(status='failure').count()
        pending = transactions.filter(status='pending').count()

        # Aggregate timing and size
        agg = transactions.aggregate(
            total_size=Sum('file_size_bytes'),
            first_started=Min('started_at'),
            last_completed=Max('completed_at'),
            avg_duration=Avg('duration_ms')
        )

        # Get first transaction for source info
        first_transaction = transactions.first()

        # Determine overall status
        if pending > 0:
            status = 'in_progress'
        elif failed == total:
            status = 'failed'
        elif failed > 0:
            status = 'partial'
        else:
            status = 'success'

        # Calculate total duration
        if agg['last_completed'] and agg['first_started']:
            duration = agg['last_completed'] - agg['first_started']
            total_duration_ms = int(duration.total_seconds() * 1000)
        else:
            total_duration_ms = None

        # Get PACS name
        source_pacs_name = 'Unknown'
        if first_transaction and first_transaction.source_ae:
            try:
                pacs = PACSConfiguration.objects.filter(
                    ae_title=first_transaction.source_ae
                ).first()
                source_pacs_name = pacs.name if pacs else first_transaction.source_ae
            except:
                source_pacs_name = first_transaction.source_ae

        # Try to get study info
        study_date = None
        study_description = 'In Progress'
        try:
            study = MedicalStudy.objects.get(study_instance_uid=study_instance_uid)
            study_date = study.study_date.isoformat() if study.study_date else None
            study_description = study.study_description or ''
        except MedicalStudy.DoesNotExist:
            pass

        # Build transfer data
        transfer_data = {
            'study_instance_uid': study_instance_uid,
            'patient_id_hash': first_transaction.patient_id_hash if first_transaction else '',
            'study_date': study_date,
            'study_description': study_description,
            'source_pacs_name': source_pacs_name,
            'source_ae': first_transaction.source_ae if first_transaction else '',
            'source_ip': first_transaction.source_ip if first_transaction else '',
            'total_instances': total,
            'successful_instances': successful,
            'failed_instances': failed,
            'pending_instances': pending,
            'transfer_status': status,
            'first_transfer_at': agg['first_started'].isoformat() if agg['first_started'] else None,
            'last_transfer_at': agg['last_completed'].isoformat() if agg['last_completed'] else None,
            'total_duration_ms': total_duration_ms,
            'total_size_bytes': agg['total_size'] or 0,
            'modality': first_transaction.modality if first_transaction else '',
        }

        return transfer_data

    except Exception as e:
        logger.error(f"Error aggregating transfer data for study {study_instance_uid}: {e}")
        return None


@receiver(post_save, sender=DICOMTransaction)
def broadcast_transfer_update(sender, instance, created, **kwargs):
    """
    Broadcast transfer updates when DICOMTransaction is saved.

    Triggers:
    - When transaction is created (study reception started)
    - When transaction completes (success/failure)

    Broadcasting Logic:
    1. Only broadcast for incoming C-STORE transfers
    2. Aggregate study-level data from all transactions
    3. Find the study owner
    4. Broadcast to owner's personal group
    5. If owner has sharing enabled, broadcast to org/dept/team groups
    """
    # Only broadcast for C-STORE incoming transfers
    if instance.transaction_type != 'C-STORE' or instance.direction != 'incoming':
        return

    # Aggregate study-level data
    study_data = _aggregate_study_transfer_data(instance.study_instance_uid)
    if not study_data:
        logger.warning(f"Could not aggregate data for study {instance.study_instance_uid}")
        return

    # Find study owner
    try:
        study = MedicalStudy.objects.select_related(
            'uploaded_by',
            'uploaded_by__userprofile'
        ).get(study_instance_uid=instance.study_instance_uid)
        owner = study.uploaded_by
    except MedicalStudy.DoesNotExist:
        # Study not yet created (transfer in progress)
        # Could broadcast to all users or skip - for now, skip
        logger.info(f"Study {instance.study_instance_uid} not yet created, skipping broadcast")
        return

    # Get channel layer
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.error("Channel layer not available for broadcasting")
        return

    # Determine message type based on status
    transfer_status = study_data['transfer_status']
    if transfer_status == 'success' and instance.status == 'success' and not created:
        message_type = 'transfer_completed'
    elif transfer_status == 'failed' and instance.status == 'failure':
        message_type = 'transfer_failed'
    else:
        message_type = 'transfer_updated'

    # Broadcast to owner's personal group
    user_group = f'transfer_user_{owner.id}'
    try:
        async_to_sync(channel_layer.group_send)(
            user_group,
            {
                'type': message_type,
                'transfer': study_data
            }
        )
        logger.info(f"Broadcasted {message_type} to {user_group}")
    except Exception as e:
        logger.error(f"Error broadcasting to {user_group}: {e}")

    # Broadcast to shared groups if owner has opted-in
    try:
        profile = owner.userprofile
        if profile.is_sharing_jobs_with_colleagues:
            groups_to_notify = []

            # Organization group
            if profile.organization_id:
                groups_to_notify.append(f'transfer_org_{profile.organization_id}')

            # Department group
            if profile.department:
                groups_to_notify.append(f'transfer_dept_{profile.department}')

            # Team group
            if profile.team_name:
                groups_to_notify.append(f'transfer_team_{profile.team_name}')

            # Broadcast to all shared groups
            for group_name in groups_to_notify:
                try:
                    async_to_sync(channel_layer.group_send)(
                        group_name,
                        {
                            'type': message_type,
                            'transfer': study_data
                        }
                    )
                    logger.info(f"Broadcasted {message_type} to {group_name}")
                except Exception as e:
                    logger.error(f"Error broadcasting to {group_name}: {e}")

    except Exception as e:
        logger.error(f"Error accessing user profile for broadcasting: {e}")

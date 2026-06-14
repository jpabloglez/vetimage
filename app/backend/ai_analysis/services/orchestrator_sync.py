"""
Orchestrator status synchronization service.

Polls orchestrator for job status updates and syncs them to VetImage database.
"""

import logging
from django.utils import timezone
from ..models import AnalysisTask
from ..orchestrator_client import OrchestratorClient

logger = logging.getLogger(__name__)


class OrchestratorStatusSync:
    """Sync job status from orchestrator to VetImage."""

    @staticmethod
    def sync_task_status(task):
        """
        Poll orchestrator for task status and update database.

        Args:
            task: AnalysisTask instance

        Returns:
            bool: True if status was updated, False otherwise
        """
        if not task.orchestrator_job_id:
            return False

        # Skip terminal states
        if task.status in ['COMPLETED', 'FAILED', 'CANCELLED']:
            return False

        try:
            client = OrchestratorClient()
            status_info = client.get_job_status(task.orchestrator_job_id)
            client.close()

            new_status = status_info['status']
            if new_status == task.status:
                return False  # No change

            logger.info(f"Task {task.id}: {task.status} → {new_status}")

            task.status = new_status

            # Update timestamps
            if new_status == 'PROCESSING' and not task.started_processing_at:
                task.started_processing_at = timezone.now()

            elif new_status in ['COMPLETED', 'FAILED', 'CANCELLED']:
                task.completed_at = timezone.now()

                if new_status == 'COMPLETED':
                    raw_uri = status_info.get('output_uri', '')
                    # Translate container-internal /output/ path to the backend-accessible
                    # /fastsurfer_output mount (added to backend via docker-compose.services.yml)
                    if raw_uri.startswith('/output/'):
                        accessible_uri = '/fastsurfer_output' + raw_uri[len('/output'):]
                    else:
                        accessible_uri = raw_uri
                    task.result_file_path = accessible_uri
                    task.result_metadata = {
                        **status_info.get('result_metadata', {}),
                        'output_keys': status_info.get('output_keys', []),
                    }
                elif new_status == 'FAILED':
                    task.error_message = status_info.get('error_message', '')

            # Save triggers Django signals → WebSocket broadcast
            task.save()
            return True

        except Exception as e:
            logger.error(f"Status sync failed for task {task.id}: {e}")
            return False

    @staticmethod
    def sync_all_active_tasks():
        """
        Sync all active orchestrator tasks.

        Returns:
            dict: Summary with total and updated counts
        """
        active_tasks = AnalysisTask.objects.filter(
            orchestrator_job_id__isnull=False,
            status__in=['PENDING', 'QUEUED', 'DISPATCHED', 'PROCESSING']
        )

        total = active_tasks.count()
        updated = 0

        for task in active_tasks:
            if OrchestratorStatusSync.sync_task_status(task):
                updated += 1

        logger.info(f"Orchestrator sync: {total} tasks, {updated} updated")
        return {'total': total, 'updated': updated}

"""
Webhook Handler Service

This module processes webhook callbacks from AI services.
It validates webhooks, enforces status transitions, and updates task records.
"""

from django.utils import timezone
from ..models import AnalysisTask
import logging

logger = logging.getLogger(__name__)


class WebhookHandler:
    """
    Service for processing webhook callbacks from AI services.

    AI services POST to the webhook URL when:
    - Processing starts (status: PROCESSING)
    - Processing completes successfully (status: COMPLETED)
    - Processing fails (status: FAILED)

    Security:
    - Each task has a unique webhook_secret
    - Webhook must provide the correct secret
    - Only valid status transitions are allowed
    - Idempotent: multiple deliveries don't corrupt state
    """

    # Valid status transitions to prevent malicious state manipulation
    VALID_TRANSITIONS = {
        'DISPATCHED': ['PROCESSING', 'FAILED'],
        'PROCESSING': ['COMPLETED', 'FAILED'],
    }

    @staticmethod
    def process_webhook(task_id, payload, secret):
        """
        Process webhook callback and update task status.

        Args:
            task_id: UUID of the task
            payload: Dict with keys:
                - status: New status (PROCESSING, COMPLETED, FAILED)
                - result_file_path: Path to result file (for COMPLETED)
                - metadata: Dict with processing info (for COMPLETED)
                - error_message: Error description (for FAILED)
            secret: Webhook secret for authentication

        Returns:
            Dict with keys:
                - success: Boolean
                - message: String description

        Raises:
            ValueError: If validation fails or transition is invalid
        """
        # Fetch task
        try:
            task = AnalysisTask.objects.get(id=task_id)
        except AnalysisTask.DoesNotExist:
            error_msg = f"Task {task_id} not found"
            logger.error(f"Webhook error: {error_msg}")
            raise ValueError(error_msg)

        # Validate webhook secret
        if task.webhook_secret != secret:
            logger.warning(
                f"Invalid webhook secret for task {task_id}. "
                f"Possible security breach or misconfiguration."
            )
            raise ValueError("Invalid webhook secret")

        # Get new status from payload
        new_status = payload.get('status')
        if not new_status:
            raise ValueError("Missing 'status' in webhook payload")

        # Validate status transition
        current_status = task.status

        # If task is already in a terminal state, ignore webhook (idempotency)
        if task.is_terminal:
            logger.warning(
                f"Task {task_id} is already in terminal state '{current_status}'. "
                f"Ignoring webhook with status '{new_status}'."
            )
            return {
                'success': True,
                'message': f'Task already in terminal state ({current_status})'
            }

        # Check if transition is valid
        if current_status not in WebhookHandler.VALID_TRANSITIONS:
            raise ValueError(
                f"Task in unexpected state '{current_status}'. "
                f"Cannot process webhook."
            )

        if new_status not in WebhookHandler.VALID_TRANSITIONS[current_status]:
            raise ValueError(
                f"Invalid status transition: {current_status} -> {new_status}. "
                f"Allowed transitions from {current_status}: "
                f"{', '.join(WebhookHandler.VALID_TRANSITIONS[current_status])}"
            )

        # Process based on new status
        if new_status == 'PROCESSING':
            WebhookHandler._handle_processing(task, payload)

        elif new_status == 'COMPLETED':
            WebhookHandler._handle_completed(task, payload)

        elif new_status == 'FAILED':
            WebhookHandler._handle_failed(task, payload)

        logger.info(
            f"Webhook processed for task {task_id}: {current_status} -> {new_status}"
        )

        return {
            'success': True,
            'message': f'Task status updated to {new_status}'
        }

    @staticmethod
    def _handle_processing(task, payload):
        """
        Handle PROCESSING status update.

        Args:
            task: AnalysisTask instance
            payload: Webhook payload
        """
        task.status = 'PROCESSING'
        task.started_processing_at = timezone.now()
        task.save(update_fields=['status', 'started_processing_at'])

        logger.info(f"Task {task.id} started processing")

    @staticmethod
    def _handle_completed(task, payload):
        """
        Handle COMPLETED status update.

        Args:
            task: AnalysisTask instance
            payload: Webhook payload with result_file_path and metadata
        """
        task.status = 'COMPLETED'
        task.completed_at = timezone.now()

        # Store result file path (relative to MEDIA_ROOT)
        result_file_path = payload.get('result_file_path', '')
        if result_file_path:
            # Remove absolute path prefix if present
            # AI service might send: "/var/www/app/backend/media/ai_results/..."
            # We want to store: "media/ai_results/..." or "ai_results/..."
            if result_file_path.startswith('/var/www/app/backend/'):
                result_file_path = result_file_path.replace('/var/www/app/backend/', '')
            task.result_file_path = result_file_path
        else:
            logger.warning(f"Task {task.id} completed but no result_file_path provided")

        # Store metadata (processing time, model version, etc.)
        task.result_metadata = payload.get('metadata', {})

        task.save(update_fields=[
            'status',
            'completed_at',
            'result_file_path',
            'result_metadata'
        ])

        logger.info(
            f"Task {task.id} completed successfully. "
            f"Result: {task.result_file_path}"
        )

    @staticmethod
    def _handle_failed(task, payload):
        """
        Handle FAILED status update.

        Args:
            task: AnalysisTask instance
            payload: Webhook payload with error_message
        """
        task.status = 'FAILED'
        task.completed_at = timezone.now()
        task.error_message = payload.get('error_message', 'Unknown error from AI service')

        # Optionally store partial results or metadata
        if 'metadata' in payload:
            task.result_metadata = payload['metadata']

        task.save(update_fields=[
            'status',
            'completed_at',
            'error_message',
            'result_metadata'
        ])

        logger.error(
            f"Task {task.id} failed in AI service. "
            f"Error: {task.error_message}"
        )

    @staticmethod
    def validate_payload(payload):
        """
        Validate webhook payload structure.

        Args:
            payload: Dict from webhook request

        Returns:
            True if valid

        Raises:
            ValueError: If payload is invalid
        """
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object")

        required_fields = ['status', 'webhook_secret']
        for field in required_fields:
            if field not in payload:
                raise ValueError(f"Missing required field: {field}")

        valid_statuses = ['PROCESSING', 'COMPLETED', 'FAILED']
        if payload['status'] not in valid_statuses:
            raise ValueError(
                f"Invalid status '{payload['status']}'. "
                f"Must be one of: {', '.join(valid_statuses)}"
            )

        # Status-specific validation
        if payload['status'] == 'COMPLETED':
            if 'result_file_path' not in payload:
                logger.warning(
                    "COMPLETED webhook missing result_file_path. "
                    "This is unusual but not blocking."
                )

        if payload['status'] == 'FAILED':
            if 'error_message' not in payload:
                logger.warning(
                    "FAILED webhook missing error_message. "
                    "Will use default message."
                )

        return True

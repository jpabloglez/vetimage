"""
Base AI Connector - Abstract interface for AI service communication

This module defines the abstract base class that all AI service connectors must implement.
It provides common functionality for parameter validation, webhook URL generation, and file path handling.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any
from django.conf import settings


class BaseAIConnector(ABC):
    """
    Abstract base class for AI service connectors.

    All AI service connectors must inherit from this class and implement the dispatch_job method.
    This ensures a consistent interface across different AI models while allowing for
    model-specific implementations.
    """

    def __init__(self, ai_model):
        """
        Initialize the connector with an AIModel instance.

        Args:
            ai_model: AIModel instance containing configuration (endpoint, timeout, etc.)
        """
        self.ai_model = ai_model
        self.endpoint_url = ai_model.endpoint_url
        self.timeout = ai_model.timeout_seconds

    def prepare_input(self, task) -> Dict[str, Any]:
        """
        Pre-process inputs before orchestrator dispatch.

        Connectors override this for format conversions (e.g., DICOM → NIfTI).
        Returns a dict of extra params merged into task.parameters before dispatch.
        Default implementation is a no-op.

        Args:
            task: AnalysisTask instance

        Returns:
            Dict of extra parameters to merge into task.parameters (may be empty).
        """
        return {}

    @abstractmethod
    def dispatch_job(self, task) -> Dict[str, Any]:
        """
        Send analysis job to AI service.

        This is the main method that subclasses must implement. It should:
        1. Build the payload for the AI service
        2. Send an HTTP request to the service
        3. Return the service's response

        Args:
            task: AnalysisTask instance containing input data and parameters

        Returns:
            Dict with keys:
                - 'service_job_id': Unique identifier returned by the AI service
                - 'status': Initial status (usually 'queued')

        Raises:
            TimeoutError: If connection to AI service times out
            ConnectionError: If cannot connect to AI service
            ValueError: For HTTP errors or invalid responses
        """
        pass

    def validate_parameters(self, parameters: Dict) -> bool:
        """
        Validate task parameters against model's required parameters schema.

        Args:
            parameters: Dict of parameters provided by user

        Returns:
            True if validation passes

        Raises:
            ValueError: If required parameters are missing
        """
        required = self.ai_model.required_parameters

        for param, schema in required.items():
            if param not in parameters:
                raise ValueError(f"Missing required parameter: {param}")

            # Additional validation can be added here based on schema
            # For example, checking parameter types, ranges, or allowed values

        return True

    def get_webhook_url(self, task) -> str:
        """
        Generate webhook URL for result delivery.

        The AI service will POST results to this URL when processing is complete.

        Args:
            task: AnalysisTask instance

        Returns:
            Full webhook URL including task ID
        """
        base_url = settings.BACKEND_BASE_URL or "http://backend-openmedlab:3080"
        return f"{base_url}/api/ai-analysis/webhook/{task.id}/"

    def build_file_path(self, file_field) -> str:
        """
        Convert Django FileField to absolute container path.

        The AI service needs absolute paths to access files within the shared Docker volume.

        Args:
            file_field: Django FileField instance

        Returns:
            Absolute path to file in container (e.g., '/var/www/app/backend/media/dicom/...')
            None if file_field is None or empty
        """
        if not file_field:
            return None

        # file_field.name is relative to MEDIA_ROOT (e.g., 'dicom/2024/12/25/file.dcm')
        # We need to convert it to absolute path within container
        return os.path.join('/var/www/app/backend', file_field.name)

    def build_base_payload(self, task) -> Dict[str, Any]:
        """
        Build common payload fields that all AI services need.

        Subclasses can call this method and then add service-specific fields.

        Args:
            task: AnalysisTask instance

        Returns:
            Dict with common payload fields
        """
        return {
            'task_id': str(task.id),
            'source_file_path': self.build_file_path(task.input_image.file),
            'parameters': task.parameters,
            'webhook_url': self.get_webhook_url(task),
            'webhook_secret': task.webhook_secret,
        }

    def check_status(self, task) -> Dict[str, Any]:
        """
        Optional: Poll for status update from AI service.

        This is an alternative to webhooks. Most implementations should use webhooks,
        but this method is provided for services that don't support callbacks.

        Args:
            task: AnalysisTask instance

        Returns:
            Dict with current status information

        Raises:
            NotImplementedError: If the service doesn't support polling
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement status polling. "
            "Use webhook-based updates instead."
        )

    def get_results(self, task) -> Dict[str, Any]:
        """
        Optional: Retrieve results directly from AI service.

        This is an alternative to webhook-delivered results.

        Args:
            task: AnalysisTask instance

        Returns:
            Dict with result data

        Raises:
            NotImplementedError: If the service doesn't support direct result retrieval
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement direct result retrieval. "
            "Use webhook-based result delivery instead."
        )

    def __str__(self):
        return f"{self.__class__.__name__} for {self.ai_model.name}"

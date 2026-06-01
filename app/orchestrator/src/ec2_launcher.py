"""
EC2 Instance Launcher

Provides interface and stub implementation for launching EC2 instances
for model services. Real implementation to be added in future.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict


logger = logging.getLogger(__name__)


class ModelInstanceLauncher(ABC):
    """Abstract interface for model instance launching"""

    @abstractmethod
    def launch_instance(self, model_name: str, instance_config: Dict) -> str:
        """
        Launch EC2 instance for model

        Args:
            model_name: Name of model to launch
            instance_config: Instance configuration dictionary

        Returns:
            instance_id: EC2 instance ID

        Raises:
            NotImplementedError: If not implemented
        """
        pass

    @abstractmethod
    def terminate_instance(self, instance_id: str) -> bool:
        """
        Terminate EC2 instance

        Args:
            instance_id: EC2 instance ID

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_instance_status(self, instance_id: str) -> Dict:
        """
        Get instance status

        Args:
            instance_id: EC2 instance ID

        Returns:
            Status dictionary
        """
        pass


class EC2Launcher(ModelInstanceLauncher):
    """
    EC2-specific launcher implementation

    NOTE: This is a placeholder for future implementation.
    Real implementation would:
    1. Use boto3 to launch EC2 instances
    2. Select AMI with model pre-installed
    3. Configure GPU instance type
    4. Wait for instance to be running
    5. Wait for model service health check
    6. Register in model registry
    """

    def __init__(self, boto3_client=None):
        """
        Initialize EC2 launcher

        Args:
            boto3_client: Optional boto3 EC2 client
        """
        self.ec2_client = boto3_client
        logger.info("EC2Launcher initialized (stub mode)")

    def launch_instance(self, model_name: str, instance_config: Dict) -> str:
        """
        Launch EC2 instance with model service

        Args:
            model_name: Model name
            instance_config: Configuration dictionary containing:
                - instance_type: EC2 instance type (e.g., "p3.2xlarge")
                - ami_id: AMI ID with model pre-installed
                - security_group: Security group ID
                - subnet_id: Subnet ID
                - key_name: SSH key pair name

        Returns:
            instance_id: EC2 instance ID

        Raises:
            NotImplementedError: This is a stub
        """
        logger.warning(
            f"EC2 launching not yet implemented. "
            f"Would launch instance for model '{model_name}' with config: {instance_config}"
        )
        raise NotImplementedError(
            "EC2 instance launching not yet implemented. "
            "This is a placeholder for future auto-scaling functionality."
        )

    def terminate_instance(self, instance_id: str) -> bool:
        """
        Terminate EC2 instance

        Args:
            instance_id: EC2 instance ID

        Returns:
            True if successful

        Raises:
            NotImplementedError: This is a stub
        """
        logger.warning(f"EC2 termination not yet implemented. Would terminate instance: {instance_id}")
        raise NotImplementedError("EC2 instance termination not yet implemented")

    def get_instance_status(self, instance_id: str) -> Dict:
        """
        Get instance status

        Args:
            instance_id: EC2 instance ID

        Returns:
            Status dictionary

        Raises:
            NotImplementedError: This is a stub
        """
        logger.warning(f"EC2 status check not yet implemented. Would check instance: {instance_id}")
        raise NotImplementedError("EC2 instance status check not yet implemented")


class StubLauncher(ModelInstanceLauncher):
    """
    Stub implementation for development

    This logs actions without actually launching instances.
    Useful for testing orchestrator logic without AWS infrastructure.
    """

    def __init__(self):
        """Initialize stub launcher"""
        logger.info("StubLauncher initialized (development mode)")

    def launch_instance(self, model_name: str, instance_config: Dict) -> str:
        """
        Simulate instance launch

        Args:
            model_name: Model name
            instance_config: Instance configuration

        Returns:
            Fake instance ID
        """
        instance_id = f"i-stub-{model_name}-{id(instance_config)}"
        logger.info(
            f"[STUB] Would launch EC2 instance for model '{model_name}' "
            f"with config: {instance_config}. "
            f"Fake instance ID: {instance_id}"
        )
        return instance_id

    def terminate_instance(self, instance_id: str) -> bool:
        """
        Simulate instance termination

        Args:
            instance_id: Instance ID

        Returns:
            True (always successful in stub mode)
        """
        logger.info(f"[STUB] Would terminate EC2 instance: {instance_id}")
        return True

    def get_instance_status(self, instance_id: str) -> Dict:
        """
        Simulate status check

        Args:
            instance_id: Instance ID

        Returns:
            Fake status dictionary
        """
        logger.info(f"[STUB] Would check status of EC2 instance: {instance_id}")
        return {
            "instance_id": instance_id,
            "status": "running",
            "stub": True,
            "public_ip": "192.0.2.1",  # TEST-NET-1 (documentation IP)
        }

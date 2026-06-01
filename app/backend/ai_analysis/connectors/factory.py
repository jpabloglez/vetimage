"""
Connector Factory - Dynamic connector instantiation

This module implements the factory pattern for creating AI connector instances.
It dynamically loads connector classes based on the connector_class path stored
in the AIModel, allowing for pluggable AI service integrations.
"""

import importlib
import logging

logger = logging.getLogger(__name__)


class ConnectorFactory:
    """
    Factory for creating AI connector instances dynamically.

    This factory uses Python's importlib to dynamically load connector classes
    based on the module path stored in AIModel.connector_class. This allows
    adding new AI models without modifying the factory code.

    Example:
        connector_class = 'ai_analysis.connectors.mirage.MirageConnector'
        connector = ConnectorFactory.create(ai_model)
    """

    @staticmethod
    def create(ai_model):
        """
        Dynamically load and instantiate a connector class.

        Args:
            ai_model: AIModel instance with connector_class attribute

        Returns:
            Instance of the connector class (subclass of BaseAIConnector)

        Raises:
            ValueError: If connector_class is invalid or cannot be loaded
        """
        connector_class_path = ai_model.connector_class

        try:
            # Split module path and class name
            # Example: 'ai_analysis.connectors.mirage.MirageConnector'
            # -> module='ai_analysis.connectors.mirage', class_name='MirageConnector'
            module_path, class_name = connector_class_path.rsplit('.', 1)

        except ValueError:
            error_msg = (
                f"Invalid connector_class format: '{connector_class_path}'. "
                "Expected format: 'module.path.ClassName'"
            )
            logger.error(f"AIModel {ai_model.key}: {error_msg}")
            raise ValueError(error_msg)

        try:
            # Import the module
            module = importlib.import_module(module_path)

            # Get the class from the module
            connector_class = getattr(module, class_name)

            # Instantiate the connector
            connector = connector_class(ai_model)

            logger.debug(
                f"Created connector {class_name} for AIModel '{ai_model.key}'"
            )

            return connector

        except ImportError as e:
            error_msg = (
                f"Cannot import module '{module_path}' for connector_class "
                f"'{connector_class_path}': {str(e)}"
            )
            logger.error(f"AIModel {ai_model.key}: {error_msg}")
            raise ValueError(error_msg)

        except AttributeError as e:
            error_msg = (
                f"Module '{module_path}' does not have class '{class_name}': {str(e)}"
            )
            logger.error(f"AIModel {ai_model.key}: {error_msg}")
            raise ValueError(error_msg)

        except TypeError as e:
            error_msg = (
                f"Cannot instantiate connector '{class_name}': {str(e)}. "
                "Make sure the class has a valid __init__(ai_model) method."
            )
            logger.error(f"AIModel {ai_model.key}: {error_msg}")
            raise ValueError(error_msg)

    @staticmethod
    def validate_connector_class(connector_class_path):
        """
        Validate that a connector class path is valid without instantiating it.

        This is useful for validating AIModel.connector_class before saving.

        Args:
            connector_class_path: String module path (e.g., 'ai_analysis.connectors.mirage.MirageConnector')

        Returns:
            True if valid

        Raises:
            ValueError: If connector class path is invalid
        """
        # Check format
        if '.' not in connector_class_path:
            raise ValueError(
                f"Invalid connector_class format: '{connector_class_path}'. "
                "Expected format: 'module.path.ClassName'"
            )

        try:
            module_path, class_name = connector_class_path.rsplit('.', 1)
            module = importlib.import_module(module_path)
            connector_class = getattr(module, class_name)

            # Check if it's a class
            if not isinstance(connector_class, type):
                raise ValueError(
                    f"'{class_name}' in '{module_path}' is not a class"
                )

            return True

        except (ImportError, AttributeError) as e:
            raise ValueError(
                f"Cannot load connector class '{connector_class_path}': {str(e)}"
            )

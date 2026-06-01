"""
Model Registry

Central registry for model service discovery, routing, and health management.
"""

import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass

import yaml
import grpc
import redis

# Import generated proto stubs (will be generated after proto compilation)
try:
    from model_service_pb2 import HealthCheckRequest
    from model_service_pb2_grpc import ModelServiceStub
except ImportError:
    # Graceful fallback for development
    logging.warning("Proto stubs not yet generated. Run 'make proto' in protos/ directory.")
    HealthCheckRequest = None
    ModelServiceStub = None


logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Model configuration dataclass"""
    name: str
    version: str
    endpoint: str
    supported_tasks: List[str]
    supported_modalities: List[str]
    model_sizes: List[str]
    health_check_interval: int
    timeout: int
    auto_launch: bool = False


class CircuitBreaker:
    """Simple circuit breaker pattern for model services"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of consecutive failures before opening
            timeout: Seconds before attempting to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half_open

    def record_success(self):
        """Record successful call"""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        """Record failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def is_open(self) -> bool:
        """Check if circuit is open"""
        if self.state == "open":
            # Check if timeout elapsed
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half_open"
                logger.info("Circuit breaker entering half-open state")
                return False
            return True
        return False


class ModelRegistry:
    """Central registry for model services"""

    def __init__(self, config_path: str, redis_client: redis.Redis, launcher=None):
        """
        Initialize model registry

        Args:
            config_path: Path to models.yaml configuration file
            redis_client: Redis client for health caching
            launcher: Optional EC2 instance launcher
        """
        self.redis = redis_client
        self.launcher = launcher
        self.models: Dict[str, ModelConfig] = {}
        self.grpc_channels: Dict[str, grpc.Channel] = {}
        self.grpc_stubs: Dict[str, ModelServiceStub] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Load configuration
        self._load_config(config_path)

        # Initialize gRPC connections
        self._initialize_connections()

        logger.info(f"ModelRegistry initialized with {len(self.models)} models")

    def _load_config(self, config_path: str):
        """Load model configurations from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            for model_cfg in config.get('models', []):
                model = ModelConfig(
                    name=model_cfg['name'],
                    version=model_cfg['version'],
                    endpoint=model_cfg['endpoint'],
                    supported_tasks=model_cfg['supported_tasks'],
                    supported_modalities=model_cfg['supported_modalities'],
                    model_sizes=model_cfg['model_sizes'],
                    health_check_interval=model_cfg.get('health_check_interval', 30),
                    timeout=model_cfg.get('timeout', 300),
                    auto_launch=model_cfg.get('auto_launch', False)
                )
                self.models[model.name] = model
                logger.info(f"Loaded model config: {model.name} v{model.version}")

        except Exception as e:
            logger.error(f"Failed to load model config from {config_path}: {e}")
            raise

    def _initialize_connections(self):
        """Initialize gRPC channels and stubs for all models"""
        if ModelServiceStub is None:
            logger.warning("Cannot initialize gRPC stubs - proto files not compiled")
            return

        for name, config in self.models.items():
            try:
                # Create gRPC channel
                channel = grpc.insecure_channel(config.endpoint)

                # Create stub
                stub = ModelServiceStub(channel)

                # Store
                self.grpc_channels[name] = channel
                self.grpc_stubs[name] = stub

                # Initialize circuit breaker
                self.circuit_breakers[name] = CircuitBreaker()

                logger.info(f"Initialized gRPC connection to {name} at {config.endpoint}")

            except Exception as e:
                logger.error(f"Failed to initialize connection to {name}: {e}")

    def select_model(self, task_type: str, modalities: List[str],
                     model_name: Optional[str] = None) -> Optional[str]:
        """
        Select appropriate model for request

        Selection priority:
        1. If model_name specified, use that (if healthy)
        2. Find first healthy model supporting task + modalities
        3. Return None if no model available

        Args:
            task_type: Requested task type
            modalities: List of input modalities
            model_name: Optional explicit model name

        Returns:
            Model name, or None if no suitable model found
        """
        # Explicit model requested
        if model_name:
            if model_name not in self.models:
                logger.warning(f"Requested model '{model_name}' not found in registry")
                return None

            if self.is_model_healthy(model_name):
                logger.info(f"Selected explicitly requested model: {model_name}")
                return model_name
            else:
                logger.warning(f"Requested model '{model_name}' is unhealthy")
                return None

        # Auto-select based on capabilities
        for name, config in self.models.items():
            # Check task support
            if task_type not in config.supported_tasks:
                continue

            # Check modality support
            if not all(m in config.supported_modalities for m in modalities):
                continue

            # Check health
            if not self.is_model_healthy(name):
                continue

            logger.info(f"Auto-selected model: {name} for task={task_type}, modalities={modalities}")
            return name

        logger.error(f"No healthy model found for task={task_type}, modalities={modalities}")
        return None

    def is_model_healthy(self, model_name: str) -> bool:
        """
        Check if model is healthy (with Redis caching)

        Args:
            model_name: Model name

        Returns:
            True if healthy, False otherwise
        """
        if model_name not in self.models:
            return False

        # Check circuit breaker
        if model_name in self.circuit_breakers:
            if self.circuit_breakers[model_name].is_open():
                logger.debug(f"Circuit breaker open for {model_name}")
                return False

        # Get cached health status
        health_key = f'orchestrator:model:{model_name}:health'
        health_data = self.redis.hgetall(health_key)

        if health_data:
            # Decode bytes
            if isinstance(health_data, dict):
                health_data = {
                    k.decode('utf-8') if isinstance(k, bytes) else k:
                    v.decode('utf-8') if isinstance(v, bytes) else v
                    for k, v in health_data.items()
                }

            # Check cache freshness
            last_check = int(health_data.get('last_check_time', 0))
            config = self.models[model_name]

            if time.time() - last_check < config.health_check_interval:
                # Cache is fresh — compare case-insensitively (str(True) = 'True')
                is_healthy = health_data.get('is_healthy', '').lower() == 'true'
                logger.debug(f"Using cached health status for {model_name}: {is_healthy}")
                return is_healthy

        # Cache stale or missing, perform health check
        return self.check_model_health(model_name)

    def check_model_health(self, model_name: str) -> bool:
        """
        Perform actual health check via gRPC

        Args:
            model_name: Model name

        Returns:
            True if healthy, False otherwise
        """
        if model_name not in self.grpc_stubs:
            logger.error(f"No gRPC stub for model {model_name}")
            return False

        if HealthCheckRequest is None:
            logger.warning("HealthCheckRequest not available - proto files not compiled")
            return False

        try:
            stub = self.grpc_stubs[model_name]
            response = stub.HealthCheck(HealthCheckRequest(), timeout=5)

            is_healthy = response.healthy

            # Cache result in Redis
            health_key = f'orchestrator:model:{model_name}:health'
            self.redis.hset(health_key, mapping={
                'is_healthy': str(is_healthy),
                'last_check_time': str(int(time.time())),
                'endpoint': self.models[model_name].endpoint,
                'consecutive_failures': '0' if is_healthy else '1'
            })
            self.redis.expire(health_key, 300)  # 5 min TTL

            # Update circuit breaker
            if model_name in self.circuit_breakers:
                if is_healthy:
                    self.circuit_breakers[model_name].record_success()
                else:
                    self.circuit_breakers[model_name].record_failure()

            logger.info(f"Health check for {model_name}: {'healthy' if is_healthy else 'unhealthy'}")
            return is_healthy

        except grpc.RpcError as e:
            logger.error(f"Health check failed for {model_name}: {e.code()} - {e.details()}")

            # Update circuit breaker
            if model_name in self.circuit_breakers:
                self.circuit_breakers[model_name].record_failure()

            # Cache failure
            health_key = f'orchestrator:model:{model_name}:health'
            failures = int(self.redis.hget(health_key, 'consecutive_failures') or 0) + 1
            self.redis.hset(health_key, mapping={
                'is_healthy': 'false',
                'last_check_time': str(int(time.time())),
                'consecutive_failures': str(failures)
            })

            return False

        except Exception as e:
            logger.error(f"Unexpected error during health check for {model_name}: {e}")
            return False

    def get_model_stub(self, model_name: str) -> Optional[ModelServiceStub]:
        """
        Get gRPC stub for model service

        Args:
            model_name: Model name

        Returns:
            gRPC stub, or None if not found
        """
        if model_name not in self.grpc_stubs:
            logger.error(f"No gRPC stub available for {model_name}")
            return None

        # Check circuit breaker
        if model_name in self.circuit_breakers:
            if self.circuit_breakers[model_name].is_open():
                logger.error(f"Circuit breaker open for {model_name}")
                return None

        return self.grpc_stubs[model_name]

    def list_models(self, only_healthy: bool = False) -> List[Dict]:
        """
        List all registered models

        Args:
            only_healthy: If True, only return healthy models

        Returns:
            List of model info dictionaries
        """
        result = []

        for name, config in self.models.items():
            is_healthy = self.is_model_healthy(name)

            if only_healthy and not is_healthy:
                continue

            result.append({
                'name': name,
                'version': config.version,
                'supported_tasks': config.supported_tasks,
                'supported_modalities': config.supported_modalities,
                'model_sizes': config.model_sizes,
                'is_healthy': is_healthy,
                'endpoint': config.endpoint
            })

        return result

    def record_success(self, model_name: str):
        """Record successful model service call"""
        if model_name in self.circuit_breakers:
            self.circuit_breakers[model_name].record_success()

    def record_failure(self, model_name: str):
        """Record failed model service call"""
        if model_name in self.circuit_breakers:
            self.circuit_breakers[model_name].record_failure()

    def ensure_model_available(self, model_name: str) -> bool:
        """
        Ensure model service is available, launch if needed

        Args:
            model_name: Model name

        Returns:
            True if model is available, False otherwise
        """
        if self.is_model_healthy(model_name):
            return True

        # Check if auto-launch enabled
        if model_name not in self.models:
            return False

        config = self.models[model_name]
        if not config.auto_launch or self.launcher is None:
            logger.warning(f"Model {model_name} unhealthy, auto-launch disabled")
            return False

        # Launch instance (stub for now)
        logger.info(f"Attempting to launch instance for {model_name}")
        try:
            instance_id = self.launcher.launch_instance(model_name, {})
            logger.info(f"Launched instance {instance_id} for {model_name}")

            # TODO: Wait for health check to pass
            # For now, just return False
            return False

        except Exception as e:
            logger.error(f"Failed to launch instance for {model_name}: {e}")
            return False

    def shutdown(self):
        """Gracefully shutdown all gRPC connections"""
        logger.info("Shutting down ModelRegistry...")

        for name, channel in self.grpc_channels.items():
            try:
                channel.close()
                logger.info(f"Closed gRPC channel for {name}")
            except Exception as e:
                logger.error(f"Error closing channel for {name}: {e}")

        logger.info("ModelRegistry shutdown complete")

"""
Orchestrator Main Entry Point

Initializes all components and starts the gRPC server.
"""

import os
import sys
import logging
import signal
from concurrent import futures

import redis
import grpc
from prometheus_client import start_http_server

# Import generated proto stubs
try:
    from orchestrator_pb2_grpc import add_OrchestratorServiceServicer_to_server
except ImportError:
    logging.error(
        "Proto stubs not generated! "
        "Please run 'cd protos && make proto' to compile protocol buffers."
    )
    sys.exit(1)

from orchestrator.job_queue import JobQueueManager
from orchestrator.model_registry import ModelRegistry
from orchestrator.worker import JobWorker
from orchestrator.health_monitor import HealthMonitor
from orchestrator.grpc_server import OrchestratorServiceImpl
from orchestrator.ec2_launcher import StubLauncher


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class OrchestratorServer:
    """Main orchestrator server"""

    def __init__(self):
        """Initialize orchestrator components"""
        self.server = None
        self.redis_client = None
        self.job_queue = None
        self.model_registry = None
        self.worker = None
        self.health_monitor = None

        logger.info("Initializing Orchestrator Server...")

        # Get configuration from environment
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.grpc_port = int(os.getenv('GRPC_PORT', 50050))
        self.metrics_port = int(os.getenv('METRICS_PORT', 8080))
        self.num_workers = int(os.getenv('NUM_WORKERS', 1))
        self.models_config = os.getenv('MODELS_CONFIG', 'orchestrator/config/models.yaml')

        logger.info(f"Configuration: Redis={self.redis_host}:{self.redis_port}, "
                   f"gRPC Port={self.grpc_port}, Workers={self.num_workers}")

        # Initialize components
        self._initialize_redis()
        self._initialize_model_registry()
        self._initialize_job_queue()
        self._initialize_workers()
        self._initialize_health_monitor()
        self._initialize_grpc_server()

        logger.info("Orchestrator Server initialized successfully")

    def _initialize_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=10
            )

            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_host}:{self.redis_port}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _initialize_model_registry(self):
        """Initialize model registry"""
        try:
            # Create EC2 launcher (stub for now)
            launcher = StubLauncher()

            self.model_registry = ModelRegistry(
                config_path=self.models_config,
                redis_client=self.redis_client,
                launcher=launcher
            )

            logger.info("Model registry initialized")

        except Exception as e:
            logger.error(f"Failed to initialize model registry: {e}")
            raise

    def _initialize_job_queue(self):
        """Initialize job queue manager"""
        try:
            self.job_queue = JobQueueManager(self.redis_client)
            logger.info("Job queue manager initialized")

        except Exception as e:
            logger.error(f"Failed to initialize job queue: {e}")
            raise

    def _initialize_workers(self):
        """Initialize background workers"""
        try:
            self.worker = JobWorker(
                job_queue=self.job_queue,
                model_registry=self.model_registry,
                num_workers=self.num_workers
            )

            self.worker.start()
            logger.info(f"Started {self.num_workers} worker thread(s)")

        except Exception as e:
            logger.error(f"Failed to initialize workers: {e}")
            raise

    def _initialize_health_monitor(self):
        """Initialize health monitor"""
        try:
            health_check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL', 30))

            self.health_monitor = HealthMonitor(
                job_queue=self.job_queue,
                model_registry=self.model_registry,
                check_interval=health_check_interval
            )

            self.health_monitor.start()
            logger.info(f"Health monitor started with {health_check_interval}s interval")

        except Exception as e:
            logger.error(f"Failed to initialize health monitor: {e}")
            raise

    def _initialize_grpc_server(self):
        """Initialize gRPC server"""
        try:
            # Create gRPC server
            self.server = grpc.server(
                futures.ThreadPoolExecutor(max_workers=10),
                options=[
                    ('grpc.max_send_message_length', 50 * 1024 * 1024),  # 50MB
                    ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
                ]
            )

            # Add orchestrator service
            orchestrator_service = OrchestratorServiceImpl(
                job_queue=self.job_queue,
                model_registry=self.model_registry
            )

            add_OrchestratorServiceServicer_to_server(orchestrator_service, self.server)

            # Bind to port
            self.server.add_insecure_port(f'[::]:{self.grpc_port}')

            logger.info(f"gRPC server configured on port {self.grpc_port}")

        except Exception as e:
            logger.error(f"Failed to initialize gRPC server: {e}")
            raise

    def start(self):
        """Start the orchestrator server"""
        try:
            # Start Prometheus metrics server
            start_http_server(self.metrics_port)
            logger.info(f"Prometheus metrics server started on port {self.metrics_port}")

            # Start gRPC server
            self.server.start()
            logger.info(f"Orchestrator gRPC server started on port {self.grpc_port}")
            logger.info("Orchestrator is ready to accept requests")

            # Wait for termination
            self.server.wait_for_termination()

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            self.shutdown()
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
            self.shutdown()
            raise

    def shutdown(self):
        """Gracefully shutdown the orchestrator"""
        logger.info("Shutting down orchestrator...")

        # Stop gRPC server
        if self.server:
            logger.info("Stopping gRPC server...")
            self.server.stop(grace=10)
            logger.info("gRPC server stopped")

        # Stop health monitor
        if self.health_monitor:
            self.health_monitor.stop()

        # Stop workers
        if self.worker:
            self.worker.stop()

        # Shutdown model registry (close gRPC channels)
        if self.model_registry:
            self.model_registry.shutdown()

        # Close Redis connection
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

        logger.info("Orchestrator shutdown complete")


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("MIRAGE ML Model Orchestrator")
    logger.info("Version: 1.0.0")
    logger.info("=" * 60)

    # Create and start server
    orchestrator = OrchestratorServer()

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        orchestrator.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start server
    orchestrator.start()


if __name__ == '__main__':
    main()

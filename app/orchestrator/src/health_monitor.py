"""
Health Monitor

Background thread that monitors:
1. Job timeouts
2. Model service health
"""

import logging
import threading
import time

from orchestrator.job_queue import JobQueueManager
from orchestrator.model_registry import ModelRegistry


logger = logging.getLogger(__name__)


class HealthMonitor:
    """Background health monitoring for jobs and model services"""

    def __init__(self, job_queue: JobQueueManager, model_registry: ModelRegistry,
                 check_interval: int = 30):
        """
        Initialize health monitor

        Args:
            job_queue: Job queue manager
            model_registry: Model registry
            check_interval: Check interval in seconds
        """
        self.job_queue = job_queue
        self.model_registry = model_registry
        self.check_interval = check_interval
        self.running = False
        self.thread = None

        logger.info(f"HealthMonitor initialized with {check_interval}s interval")

    def start(self):
        """Start health monitoring thread"""
        if self.running:
            logger.warning("HealthMonitor already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("HealthMonitor started")

    def stop(self):
        """Stop health monitoring thread"""
        logger.info("Stopping HealthMonitor...")
        self.running = False

        if self.thread:
            self.thread.join(timeout=self.check_interval + 5)
            if self.thread.is_alive():
                logger.warning("HealthMonitor did not stop gracefully")
            else:
                logger.info("HealthMonitor stopped")

        self.thread = None

    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("HealthMonitor loop started")

        while self.running:
            try:
                # Check for timed out jobs
                self._check_job_timeouts()

                # Check model service health
                self._check_model_health()

                # Sleep until next check
                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"HealthMonitor error: {e}", exc_info=True)
                time.sleep(5)  # Brief sleep on error

        logger.info("HealthMonitor loop stopped")

    def _check_job_timeouts(self):
        """Check for jobs that have exceeded their timeout"""
        try:
            timed_out_jobs = self.job_queue.get_timed_out_jobs()

            for job_id in timed_out_jobs:
                logger.warning(f"Job {job_id} timed out")

                # Mark job as failed
                self.job_queue.set_error(
                    job_id,
                    "Job execution timed out. The model service took too long to process the request.",
                    "ERROR_CODE_TIMEOUT"
                )

                # Clear from processing queue
                self.job_queue.clear_job_deadline(job_id)

            if timed_out_jobs:
                logger.info(f"Marked {len(timed_out_jobs)} jobs as timed out")

        except Exception as e:
            logger.error(f"Error checking job timeouts: {e}", exc_info=True)

    def _check_model_health(self):
        """Refresh model service health cache"""
        try:
            models = self.model_registry.list_models(only_healthy=False)

            healthy_count = 0
            unhealthy_count = 0

            for model in models:
                model_name = model['name']

                # This will refresh the health cache
                is_healthy = self.model_registry.check_model_health(model_name)

                if is_healthy:
                    healthy_count += 1
                else:
                    unhealthy_count += 1

            logger.debug(
                f"Model health check complete: "
                f"{healthy_count} healthy, {unhealthy_count} unhealthy"
            )

        except Exception as e:
            logger.error(f"Error checking model health: {e}", exc_info=True)

    def get_status(self) -> dict:
        """
        Get health monitor status

        Returns:
            Status dictionary
        """
        return {
            "running": self.running,
            "check_interval": self.check_interval,
            "thread_alive": self.thread.is_alive() if self.thread else False
        }

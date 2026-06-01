"""
Redis-based Job Queue Manager

Manages job lifecycle using Redis data structures:
- LIST for FIFO queue
- HASH for job metadata
- ZSET for status indexing and timeout tracking
"""

import json
import time
import uuid
import logging
from typing import Dict, List, Optional

import redis


logger = logging.getLogger(__name__)


class JobQueueManager:
    """Redis-based job queue with persistent storage and state management"""

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize job queue manager

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.retry_attempts = 3
        self.retry_delay = 2  # seconds

        # Redis key prefixes
        self.QUEUE_PENDING = "orchestrator:queue:pending"
        self.JOB_PREFIX = "orchestrator:job:"
        self.JOBS_BY_STATUS_PREFIX = "orchestrator:jobs:by_status:"
        self.JOBS_PROCESSING = "orchestrator:jobs:processing"
        self.RESULT_CACHE_PREFIX = "orchestrator:result:"

        # TTL values (seconds)
        self.JOB_TTL = 86400  # 24 hours
        self.RESULT_CACHE_TTL = 3600  # 1 hour

        logger.info("JobQueueManager initialized")

    def _execute_with_retry(self, func, *args, **kwargs):
        """
        Execute Redis command with retry logic

        Args:
            func: Redis function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            redis.RedisError: If all retries fail
        """
        for attempt in range(self.retry_attempts):
            try:
                return func(*args, **kwargs)
            except redis.ConnectionError as e:
                if attempt == self.retry_attempts - 1:
                    logger.error(f"Redis connection failed after {self.retry_attempts} attempts")
                    raise
                logger.warning(f"Redis connection error, retry {attempt + 1}/{self.retry_attempts}")
                time.sleep(self.retry_delay)
            except redis.TimeoutError as e:
                logger.error(f"Redis timeout error: {e}")
                raise

    def enqueue_job(self, job_data: Dict) -> str:
        """
        Enqueue a new job

        Args:
            job_data: Job metadata dictionary containing:
                - model_service: str
                - task_type: str
                - input_images: list
                - output_destination: str
                - metadata: dict (optional)

        Returns:
            job_id: UUID string
        """
        job_id = str(uuid.uuid4())
        current_time = int(time.time() * 1000)  # Unix ms

        # Prepare job metadata
        job_hash = {
            "job_id": job_id,
            "status": "queued",
            "model_service": job_data.get("model_service", ""),
            "task_type": job_data.get("task_type", ""),
            "input_images": json.dumps(job_data.get("input_images", [])),
            "output_destination": job_data.get("output_destination", ""),
            "output_format": job_data.get("output_format", ""),
            "num_classes": str(job_data.get("num_classes", 0)),
            "class_names": json.dumps(job_data.get("class_names", [])),
            "metadata": json.dumps(job_data.get("metadata", {})),
            "created_at": str(current_time),
            "updated_at": str(current_time),
            "started_at": "0",
            "completed_at": "0",
            "progress_percent": "0.0",
            "progress_message": "",
            "error_message": "",
            "error_code": "",
            "output_keys": json.dumps([]),
        }

        def _enqueue():
            # Create job hash
            job_key = f"{self.JOB_PREFIX}{job_id}"
            self.redis.hset(job_key, mapping=job_hash)

            # Add to pending queue
            self.redis.rpush(self.QUEUE_PENDING, job_id)

            # Add to status index
            status_key = f"{self.JOBS_BY_STATUS_PREFIX}queued"
            self.redis.zadd(status_key, {job_id: current_time})

            logger.info(f"Job {job_id} enqueued successfully")

        self._execute_with_retry(_enqueue)
        return job_id

    def dequeue_job(self) -> Optional[str]:
        """
        Dequeue a job from the pending queue and mark as processing

        Returns:
            job_id: UUID string, or None if queue is empty
        """
        def _dequeue():
            # Pop from pending queue
            job_id = self.redis.lpop(self.QUEUE_PENDING)

            if not job_id:
                return None

            # Decode if bytes
            if isinstance(job_id, bytes):
                job_id = job_id.decode('utf-8')

            current_time = int(time.time() * 1000)
            timeout_time = time.time() + 300  # 5 min default timeout

            # Update job status
            job_key = f"{self.JOB_PREFIX}{job_id}"
            self.redis.hset(job_key, mapping={
                "status": "processing",
                "started_at": str(current_time),
                "updated_at": str(current_time)
            })

            # Update status indexes
            queued_key = f"{self.JOBS_BY_STATUS_PREFIX}queued"
            self.redis.zrem(queued_key, job_id)

            # Add to processing with timeout
            self.redis.zadd(self.JOBS_PROCESSING, {job_id: timeout_time})

            logger.info(f"Job {job_id} dequeued and marked as processing")
            return job_id

        return self._execute_with_retry(_dequeue)

    def update_job_status(self, job_id: str, status: str, **kwargs):
        """
        Update job status

        Args:
            job_id: Job UUID
            status: New status (queued, processing, completed, failed)
            **kwargs: Additional fields to update
        """
        def _update():
            job_key = f"{self.JOB_PREFIX}{job_id}"
            current_time = int(time.time() * 1000)

            # Prepare update
            update_data = {
                "status": status,
                "updated_at": str(current_time)
            }
            update_data.update(kwargs)

            # Update job hash
            self.redis.hset(job_key, mapping=update_data)

            # Update status index
            new_status_key = f"{self.JOBS_BY_STATUS_PREFIX}{status}"
            self.redis.zadd(new_status_key, {job_id: current_time})

            logger.debug(f"Job {job_id} status updated to {status}")

        self._execute_with_retry(_update)

    def set_result(self, job_id: str, output_uri: str, output_keys: List[str]):
        """
        Mark job as completed with results

        Args:
            job_id: Job UUID
            output_uri: Base output URI
            output_keys: List of output file keys
        """
        def _set_result():
            job_key = f"{self.JOB_PREFIX}{job_id}"
            current_time = int(time.time() * 1000)

            # Update job
            self.redis.hset(job_key, mapping={
                "status": "completed",
                "completed_at": str(current_time),
                "updated_at": str(current_time),
                "output_uri": output_uri,
                "output_keys": json.dumps(output_keys),
                "progress_percent": "100.0"
            })

            # Remove from processing
            self.redis.zrem(self.JOBS_PROCESSING, job_id)

            # Update status indexes
            processing_key = f"{self.JOBS_BY_STATUS_PREFIX}processing"
            completed_key = f"{self.JOBS_BY_STATUS_PREFIX}completed"
            self.redis.zrem(processing_key, job_id)
            self.redis.zadd(completed_key, {job_id: current_time})

            # Set TTL on job
            self.redis.expire(job_key, self.JOB_TTL)

            # Cache result
            result_cache_key = f"{self.RESULT_CACHE_PREFIX}{job_id}"
            result_data = {
                "output_uri": output_uri,
                "output_keys": output_keys
            }
            self.redis.setex(result_cache_key, self.RESULT_CACHE_TTL, json.dumps(result_data))

            logger.info(f"Job {job_id} completed successfully")

        self._execute_with_retry(_set_result)

    def set_error(self, job_id: str, error_message: str, error_code: str = "ERROR_CODE_UNSPECIFIED"):
        """
        Mark job as failed with error details

        Args:
            job_id: Job UUID
            error_message: Error description
            error_code: Error code from ErrorCode enum
        """
        def _set_error():
            job_key = f"{self.JOB_PREFIX}{job_id}"
            current_time = int(time.time() * 1000)

            # Update job
            self.redis.hset(job_key, mapping={
                "status": "failed",
                "completed_at": str(current_time),
                "updated_at": str(current_time),
                "error_message": error_message,
                "error_code": error_code
            })

            # Remove from processing
            self.redis.zrem(self.JOBS_PROCESSING, job_id)

            # Update status indexes
            processing_key = f"{self.JOBS_BY_STATUS_PREFIX}processing"
            failed_key = f"{self.JOBS_BY_STATUS_PREFIX}failed"
            self.redis.zrem(processing_key, job_id)
            self.redis.zadd(failed_key, {job_id: current_time})

            # Set TTL on job
            self.redis.expire(job_key, self.JOB_TTL)

            logger.error(f"Job {job_id} failed: {error_message}")

        self._execute_with_retry(_set_error)

    def get_job(self, job_id: str) -> Optional[Dict]:
        """
        Retrieve job details

        Args:
            job_id: Job UUID

        Returns:
            Job metadata dictionary, or None if not found
        """
        def _get_job():
            job_key = f"{self.JOB_PREFIX}{job_id}"
            job_data = self.redis.hgetall(job_key)

            if not job_data:
                logger.warning(f"Job {job_id} not found")
                return None

            # Decode bytes to strings
            if isinstance(job_data, dict) and job_data:
                job_data = {
                    k.decode('utf-8') if isinstance(k, bytes) else k:
                    v.decode('utf-8') if isinstance(v, bytes) else v
                    for k, v in job_data.items()
                }

            # Parse JSON fields
            for field in ['input_images', 'class_names', 'metadata', 'output_keys']:
                if field in job_data and job_data[field]:
                    try:
                        job_data[field] = json.loads(job_data[field])
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON field {field} for job {job_id}")
                        job_data[field] = []

            return job_data

        return self._execute_with_retry(_get_job)

    def get_timed_out_jobs(self) -> List[str]:
        """
        Find jobs that have exceeded their timeout

        Returns:
            List of timed-out job IDs
        """
        def _get_timed_out():
            current_time = time.time()
            timed_out = self.redis.zrangebyscore(
                self.JOBS_PROCESSING,
                0,
                current_time
            )

            # Decode bytes
            timed_out = [
                job_id.decode('utf-8') if isinstance(job_id, bytes) else job_id
                for job_id in timed_out
            ]

            if timed_out:
                logger.warning(f"Found {len(timed_out)} timed-out jobs")

            return timed_out

        return self._execute_with_retry(_get_timed_out)

    def set_job_deadline(self, job_id: str, deadline_timestamp: float):
        """
        Set timeout deadline for a job

        Args:
            job_id: Job UUID
            deadline_timestamp: Unix timestamp (seconds) when job should timeout
        """
        def _set_deadline():
            self.redis.zadd(self.JOBS_PROCESSING, {job_id: deadline_timestamp})
            logger.debug(f"Job {job_id} deadline set to {deadline_timestamp}")

        self._execute_with_retry(_set_deadline)

    def clear_job_deadline(self, job_id: str):
        """
        Remove job from timeout tracking

        Args:
            job_id: Job UUID
        """
        def _clear_deadline():
            self.redis.zrem(self.JOBS_PROCESSING, job_id)
            logger.debug(f"Job {job_id} deadline cleared")

        self._execute_with_retry(_clear_deadline)

    def get_queue_stats(self) -> Dict[str, int]:
        """
        Get queue statistics

        Returns:
            Dictionary with counts for each status
        """
        def _get_stats():
            stats = {
                "queued": self.redis.llen(self.QUEUE_PENDING),
                "processing": self.redis.zcard(self.JOBS_PROCESSING),
            }

            # Count jobs by status
            for status in ["completed", "failed"]:
                status_key = f"{self.JOBS_BY_STATUS_PREFIX}{status}"
                stats[status] = self.redis.zcard(status_key)

            return stats

        return self._execute_with_retry(_get_stats)

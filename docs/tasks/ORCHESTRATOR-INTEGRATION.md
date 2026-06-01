# Orchestrator Integration Guide

**Author**: OpenMedLab Development Team
**Date**: December 27, 2025
**Version**: 1.0
**Status**: Implementation Complete

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Setup & Deployment](#setup--deployment)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [Migration Strategy](#migration-strategy)
8. [Monitoring & Debugging](#monitoring--debugging)
9. [API Reference](#api-reference)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### What is the Orchestrator?

The **Orchestrator** is a gRPC-based service that manages AI model job execution for OpenMedLab. It replaces the previous Celery-based direct HTTP communication pattern with a more robust, scalable queue-based architecture.

### Why Orchestrator?

**Before (Celery + Direct HTTP)**:
```
Frontend → Backend → Celery Task → HTTP POST to AI Service → Webhook Callback
```

**After (Orchestrator + gRPC)**:
```
Frontend → Backend → gRPC to Orchestrator → Redis Queue → Worker Pool → gRPC Status Updates
```

**Benefits**:
- ✅ **Centralized Queue Management**: Single Redis queue for all AI jobs
- ✅ **Better Resource Management**: Worker pool with configurable concurrency
- ✅ **Improved Reliability**: gRPC binary protocol vs. HTTP JSON
- ✅ **Real-time Status**: Efficient polling via gRPC (sub-100ms latency)
- ✅ **Scalability**: Horizontal scaling of workers
- ✅ **Unified Interface**: Single gRPC API for all AI models

---

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         OpenMedLab Frontend                         │
│                    (React + WebSocket Client)                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP/WebSocket
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      OpenMedLab Backend                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Django REST API (views.py)                                  │  │
│  │    ↓                                                          │  │
│  │  AnalysisTask Model                                          │  │
│  │    ↓                                                          │  │
│  │  OrchestratorClient (gRPC)  ←──[Feature Flag]──→  Celery    │  │
│  └──────────────┬───────────────────────────────────────────────┘  │
│                 │ gRPC (port 50050)                                 │
│                 │                                                    │
│  ┌──────────────▼──────────────────────────────────────────────┐   │
│  │  Celery Beat (Periodic Tasks)                               │   │
│  │    - sync_orchestrator_status (every 5s)                    │   │
│  │    - check_task_timeouts (every 10min)                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  WebSocket Server (Channels + Django Signals)                │  │
│  │    - Broadcasts task status changes to frontend              │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ gRPC
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Orchestrator Service                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  gRPC Server (grpc_server.py)                                │  │
│  │    - SubmitJob(SubmitJobRequest) → SubmitJobResponse        │  │
│  │    - GetJobStatus(GetJobStatusRequest) → JobStatusResponse  │  │
│  └──────────────┬───────────────────────────────────────────────┘  │
│                 │                                                    │
│  ┌──────────────▼──────────────────────────────────────────────┐   │
│  │  Job Queue Manager (job_queue.py)                           │   │
│  │    - Redis-backed priority queue                            │   │
│  │    - Job lifecycle management                               │   │
│  └──────────────┬───────────────────────────────────────────────┘  │
│                 │                                                    │
│  ┌──────────────▼──────────────────────────────────────────────┐   │
│  │  Worker Pool (worker.py)                                    │   │
│  │    - Configurable concurrency (default: 2 workers)          │   │
│  │    - File handling & model execution                        │   │
│  └──────────────┬───────────────────────────────────────────────┘  │
│                 │                                                    │
│  ┌──────────────▼──────────────────────────────────────────────┐   │
│  │  Model Registry (model_registry.py)                         │   │
│  │    - Loads models from config/models.yaml                   │   │
│  │    - Manages model lifecycle & parameters                   │   │
│  └──────────────┬───────────────────────────────────────────────┘  │
│                 │                                                    │
│  ┌──────────────▼──────────────────────────────────────────────┐   │
│  │  Health Monitor (health_monitor.py)                         │   │
│  │    - Prometheus metrics (port 8080)                         │   │
│  │    - Queue depth, worker utilization, latency               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Orchestrator Redis (port 6380)                     │
│    - Job queue storage                                              │
│    - Job status cache                                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

#### 1. Job Submission Flow

```
1. User uploads image in Frontend
2. Frontend sends POST /api/ai-analysis/tasks/
3. Backend (views.py):
   a. Creates AnalysisTask in database
   b. Checks USE_ORCHESTRATOR flag
   c. If True: Calls OrchestratorClient.submit_job()
   d. If False: Falls back to Celery (legacy)
4. OrchestratorClient:
   a. Opens gRPC channel to orchestrator:50050
   b. Constructs SubmitJobRequest proto
   c. Sends gRPC call
   d. Receives job_id from orchestrator
5. Backend updates AnalysisTask:
   - orchestrator_job_id = job_id
   - status = 'DISPATCHED'
   - dispatched_at = now()
6. Django signals trigger WebSocket broadcast
7. Frontend receives real-time update
```

#### 2. Status Polling Flow

```
1. Celery Beat triggers sync_orchestrator_status (every 5s)
2. OrchestratorStatusSync.sync_all_active_tasks():
   a. Queries AnalysisTask.objects.filter(status__in=['PENDING', 'QUEUED', 'DISPATCHED', 'PROCESSING'])
   b. For each task:
      - Calls OrchestratorClient.get_job_status(orchestrator_job_id)
      - Receives JobStatusResponse via gRPC
      - Maps proto status to Django status
      - Updates AnalysisTask if status changed
3. Django signals trigger WebSocket broadcast on status change
4. Frontend receives real-time update via WebSocket
```

#### 3. Job Execution Flow (Inside Orchestrator)

```
1. Orchestrator receives SubmitJobRequest via gRPC
2. job_queue.py:
   - Generates unique job_id
   - Validates request parameters
   - Adds job to Redis queue (LPUSH)
   - Returns job_id to OpenMedLab
3. Worker pool (worker.py):
   - Worker threads poll Redis queue (BRPOP)
   - Worker picks up job
   - Updates status to PROCESSING
4. file_handler.py:
   - Downloads input files from shared volume
   - Prepares input for model
5. model_registry.py:
   - Loads appropriate AI model
   - Executes inference
6. Worker processes results:
   - Saves output to shared volume
   - Updates job status to COMPLETED
   - Stores result metadata in Redis
7. OpenMedLab polls via GetJobStatus:
   - Receives COMPLETED status
   - Retrieves result file path
   - Updates AnalysisTask
   - Broadcasts to frontend
```

---

## Components

### 1. OrchestratorClient (`ai_analysis/orchestrator_client.py`)

**Purpose**: gRPC client wrapper for communicating with orchestrator service.

**Key Methods**:

```python
class OrchestratorClient:
    def __init__(self):
        """Initializes gRPC channel to orchestrator."""

    def submit_job(self, task: AnalysisTask) -> dict:
        """
        Submit analysis job to orchestrator.

        Returns:
            {'job_id': str, 'status': str, 'message': str}
        """

    def get_job_status(self, job_id: str) -> dict:
        """
        Get current status of orchestrator job.

        Returns:
            {
                'job_id': str,
                'status': str,
                'output_uri': str,
                'error_message': str,
                'progress_percent': int,
                'result_metadata': dict
            }
        """

    def close(self):
        """Close gRPC channel."""
```

**Status Mapping**:

| Proto Status (orchestrator_pb2) | OpenMedLab Status | Description |
|--------------------------------|-------------------|-------------|
| `JOB_STATUS_QUEUED` | `QUEUED` | Job in Redis queue, waiting for worker |
| `JOB_STATUS_PROCESSING` | `PROCESSING` | Worker actively processing job |
| `JOB_STATUS_COMPLETED` | `COMPLETED` | Job finished successfully |
| `JOB_STATUS_FAILED` | `FAILED` | Job failed with error |
| `JOB_STATUS_CANCELLED` | `CANCELLED` | Job cancelled by user |

### 2. OrchestratorStatusSync (`ai_analysis/services/orchestrator_sync.py`)

**Purpose**: Polls orchestrator for job status updates and syncs to database.

**Key Methods**:

```python
class OrchestratorStatusSync:
    @staticmethod
    def sync_task_status(task: AnalysisTask) -> bool:
        """
        Poll orchestrator for single task status.

        Returns:
            True if status was updated, False otherwise
        """

    @staticmethod
    def sync_all_active_tasks() -> dict:
        """
        Sync all active orchestrator tasks.

        Returns:
            {'total': int, 'updated': int}
        """
```

**Behavior**:
- Only polls tasks with `orchestrator_job_id` set
- Skips terminal states (`COMPLETED`, `FAILED`, `CANCELLED`)
- Updates timestamps (`started_processing_at`, `completed_at`)
- Stores result metadata on completion
- Triggers Django signals → WebSocket broadcasts

### 3. Celery Tasks (`ai_analysis/tasks.py`)

**New Task**:

```python
@shared_task
def sync_orchestrator_status():
    """
    Periodic task to sync status from orchestrator.
    Runs every 5 seconds via Celery Beat.
    """
```

**Schedule** (`backend/celery.py`):

```python
app.conf.beat_schedule = {
    'sync-orchestrator-status': {
        'task': 'ai_analysis.tasks.sync_orchestrator_status',
        'schedule': 5.0,  # Every 5 seconds
    },
}
```

### 4. AnalysisTask Model Extensions

**New Field**:

```python
orchestrator_job_id = models.CharField(
    max_length=255,
    null=True,
    blank=True,
    help_text="Job ID returned by orchestrator service"
)
```

**Migration**:
- File: `ai_analysis/migrations/0005_add_orchestrator_job_id.py`
- Applied: ✅ (committed to database)

### 5. Views Integration (`ai_analysis/views.py`)

**Modified Methods**:

#### `create()` - Task Submission

```python
def create(self, request):
    # ... validation ...

    task = AnalysisTask.objects.create(...)

    # Feature flag conditional dispatch
    if settings.USE_ORCHESTRATOR:
        # NEW: Orchestrator path
        from .orchestrator_client import OrchestratorClient

        client = OrchestratorClient()
        result = client.submit_job(task)

        task.orchestrator_job_id = result['job_id']
        task.status = 'DISPATCHED'
        task.dispatched_at = timezone.now()
        task.save(update_fields=['orchestrator_job_id', 'status', 'dispatched_at'])

        client.close()
    else:
        # LEGACY: Celery path
        dispatch_ai_job.delay(str(task.id))

    return Response(AnalysisTaskSerializer(task).data)
```

#### `retry()` - Task Retry

```python
def retry(self, request, pk=None):
    # ... validation ...

    # Reset task state
    task.orchestrator_job_id = None  # ADDED
    task.celery_task_id = None
    task.service_job_id = None
    task.save()

    # Feature flag conditional dispatch
    if settings.USE_ORCHESTRATOR:
        # Orchestrator retry logic
        # ... (same as create)
    else:
        # Celery retry logic
        dispatch_ai_job.delay(str(task.id))
```

---

## Setup & Deployment

### Prerequisites

- Docker & Docker Compose
- OpenMedLab backend running
- Redis available (for Celery)
- `/home/jpablo/code/repositories/medimaging` repository cloned

### Directory Structure

```
/home/jpablo/code/web-apps/openmedlab/
├── app/backend/
│   ├── ai_analysis/
│   │   ├── orchestrator_client.py          # NEW
│   │   ├── services/
│   │   │   └── orchestrator_sync.py        # NEW
│   │   ├── models.py                       # MODIFIED
│   │   ├── views.py                        # MODIFIED
│   │   └── tasks.py                        # MODIFIED
│   ├── backend/
│   │   ├── settings.py                     # MODIFIED
│   │   └── celery.py                       # MODIFIED
│   └── protos/                             # NEW
│       ├── __init__.py
│       ├── orchestrator.proto
│       ├── orchestrator_pb2.py             # Generated
│       └── orchestrator_pb2_grpc.py        # Generated
├── docker-compose.yml                      # MODIFIED
├── setup/requirements.txt                  # MODIFIED
└── docs/
    └── ORCHESTRATOR-INTEGRATION.md         # NEW (this file)

/home/jpablo/code/repositories/medimaging/
└── orchestrator/
    ├── Dockerfile
    ├── main.py
    ├── grpc_server.py
    ├── job_queue.py
    ├── worker.py
    ├── model_registry.py
    ├── file_handler.py
    ├── health_monitor.py
    ├── config/
    │   └── models.yaml
    └── requirements.txt
```

### Installation Steps

#### Step 1: Infrastructure (Already Complete)

The following services are defined in `docker-compose.yml`:

```yaml
orchestrator-redis:
  image: redis:7-alpine
  container_name: orchestrator-redis
  ports:
    - "6380:6379"  # Different port to avoid conflict
  volumes:
    - ./data/orchestrator-redis:/data
  command: redis-server --appendonly yes
  networks:
    - app-network
  restart: unless-stopped

orchestrator-openmedlab:
  build:
    context: /home/jpablo/code/repositories/medimaging
    dockerfile: orchestrator/Dockerfile
  container_name: orchestrator-openmedlab
  depends_on:
    - orchestrator-redis
  ports:
    - "50050:50050"  # gRPC port
    - "8080:8080"    # Prometheus metrics
  volumes:
    - /home/jpablo/code/repositories/medimaging:/app
    - ./data/media:/var/www/app/backend/media
  environment:
    - REDIS_HOST=orchestrator-redis
    - REDIS_PORT=6379
    - GRPC_PORT=50050
    - METRICS_PORT=8080
    - NUM_WORKERS=2
    - MODELS_CONFIG=/app/orchestrator/config/models.yaml
  networks:
    - app-network
  restart: unless-stopped
  command: python -m orchestrator.main
```

#### Step 2: Dependencies (Already Installed)

Dependencies in `setup/requirements.txt`:

```
grpcio==1.60.0
grpcio-tools==1.60.0
```

Installed in backend container:
```bash
docker exec backend-openmedlab pip install grpcio==1.60.0 grpcio-tools==1.60.0
```

#### Step 3: Proto Files (Already Generated)

Proto files copied and generated:

```bash
# Copy proto definition
cp /home/jpablo/code/repositories/medimaging/protos/orchestrator.proto \
   /home/jpablo/code/web-apps/openmedlab/app/backend/protos/

# Generate Python stubs
docker exec backend-openmedlab python -m grpc_tools.protoc \
  -I./protos \
  --python_out=./protos \
  --grpc_python_out=./protos \
  ./protos/orchestrator.proto
```

#### Step 4: Database Migration (Already Applied)

```bash
docker exec backend-openmedlab python manage.py makemigrations ai_analysis --name add_orchestrator_job_id
docker exec backend-openmedlab python manage.py migrate ai_analysis
```

#### Step 5: Restart Services (Already Done)

```bash
docker-compose restart backend-openmedlab celery-worker-openmedlab celery-beat-openmedlab
```

---

## Configuration

### Environment Variables

**Backend Service** (`docker-compose.yml` → `backend-openmedlab`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ORCHESTRATOR_HOST` | `orchestrator-openmedlab` | Hostname of orchestrator service |
| `ORCHESTRATOR_PORT` | `50050` | gRPC port for orchestrator |
| `USE_ORCHESTRATOR` | `False` | **Feature flag**: Enable orchestrator (set to `True` to activate) |
| `ORCHESTRATOR_POLL_INTERVAL` | `5` | Status polling interval in seconds |

**Orchestrator Service** (`docker-compose.yml` → `orchestrator-openmedlab`):

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `orchestrator-redis` | Redis hostname for job queue |
| `REDIS_PORT` | `6379` | Redis port |
| `GRPC_PORT` | `50050` | gRPC server listening port |
| `METRICS_PORT` | `8080` | Prometheus metrics port |
| `NUM_WORKERS` | `2` | Number of worker threads |
| `MODELS_CONFIG` | `/app/orchestrator/config/models.yaml` | Model configuration file |

### Django Settings (`backend/settings.py`)

```python
# ============================================================================
# Orchestrator Configuration
# ============================================================================

ORCHESTRATOR_HOST = os.getenv('ORCHESTRATOR_HOST', 'orchestrator-openmedlab')
ORCHESTRATOR_PORT = int(os.getenv('ORCHESTRATOR_PORT', 50050))
USE_ORCHESTRATOR = os.getenv('USE_ORCHESTRATOR', 'False') == 'True'
ORCHESTRATOR_POLL_INTERVAL = int(os.getenv('ORCHESTRATOR_POLL_INTERVAL', 5))
```

### Celery Beat Schedule (`backend/celery.py`)

```python
app.conf.beat_schedule = {
    'sync-orchestrator-status': {
        'task': 'ai_analysis.tasks.sync_orchestrator_status',
        'schedule': 5.0,  # Every 5 seconds (polling interval)
    },
    # ... other tasks ...
}
```

---

## Usage

### Starting the Orchestrator

#### Option 1: Start All Services

```bash
cd /home/jpablo/code/web-apps/openmedlab
docker-compose up -d
```

This starts:
- `orchestrator-redis` (port 6380)
- `orchestrator-openmedlab` (ports 50050, 8080)
- All other OpenMedLab services

#### Option 2: Start Only Orchestrator Services

```bash
docker-compose up -d orchestrator-redis orchestrator-openmedlab
```

### Verifying Orchestrator Health

#### 1. Check Container Status

```bash
docker-compose ps orchestrator-openmedlab
```

Expected output:
```
NAME                      STATUS          PORTS
orchestrator-openmedlab   Up 2 minutes    0.0.0.0:50050->50050/tcp, 0.0.0.0:8080->8080/tcp
```

#### 2. Check Orchestrator Logs

```bash
docker-compose logs orchestrator-openmedlab
```

Expected output (healthy):
```
Starting gRPC server on 0.0.0.0:50050
Starting Prometheus metrics server on 0.0.0.0:8080
Worker pool started with 2 workers
Orchestrator ready to accept jobs
```

#### 3. Check Prometheus Metrics

```bash
curl http://localhost:8080/metrics
```

Expected output:
```
# HELP orchestrator_jobs_total Total number of jobs submitted
# TYPE orchestrator_jobs_total counter
orchestrator_jobs_total 0

# HELP orchestrator_queue_depth Current number of jobs in queue
# TYPE orchestrator_queue_depth gauge
orchestrator_queue_depth 0

# HELP orchestrator_workers_busy Number of busy workers
# TYPE orchestrator_workers_busy gauge
orchestrator_workers_busy 0
```

#### 4. Test gRPC Connectivity (Optional)

Using `grpcurl` (if installed):

```bash
grpcurl -plaintext localhost:50050 list
```

Expected output:
```
orchestrator.OrchestratorService
```

### Enabling Orchestrator Mode

#### Method 1: Environment Variable (Recommended for Production)

Edit `docker-compose.yml`:

```yaml
backend-openmedlab:
  environment:
    - USE_ORCHESTRATOR=True  # Change from False
```

Then restart:

```bash
docker-compose restart backend-openmedlab celery-worker-openmedlab celery-beat-openmedlab
```

#### Method 2: Runtime Override (Testing)

```bash
docker-compose exec backend-openmedlab bash -c "export USE_ORCHESTRATOR=True"
docker-compose restart backend-openmedlab
```

#### Method 3: Django Shell (One-time Test)

```bash
docker exec -it backend-openmedlab python manage.py shell
```

```python
from django.conf import settings
settings.USE_ORCHESTRATOR = True  # Temporary, lost on restart
```

### Submitting a Job

Once enabled, submit jobs normally via the API:

```bash
# Get auth token
TOKEN=$(curl -s -X POST http://localhost:3080/users/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "test@openmedlab.com", "password": "test123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access'])")

# Submit analysis task
curl -X POST http://localhost:3080/api/ai-analysis/tasks/ \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "model_key": "mirage-v1",
    "input_image_id": 123,
    "parameters": {
      "modality": "t1",
      "target_image_id": 124
    }
  }'
```

**Response** (orchestrator mode):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "model": {
    "key": "mirage-v1",
    "name": "MIRAGE v1"
  },
  "status": "DISPATCHED",
  "orchestrator_job_id": "orch_abc123xyz789",
  "dispatched_at": "2025-12-27T22:10:30.123456Z",
  "parameters": { ... }
}
```

Note: `orchestrator_job_id` is populated (instead of `celery_task_id`).

### Monitoring Job Status

#### Via WebSocket (Real-time)

Frontend automatically receives status updates via WebSocket:

```javascript
// WebSocket message received when status changes
{
  "type": "task.status_updated",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "started_processing_at": "2025-12-27T22:10:35.000000Z"
}
```

#### Via REST API (Polling)

```bash
curl http://localhost:3080/api/ai-analysis/tasks/550e8400-e29b-41d4-a716-446655440000/ \
  -H "Authorization: Bearer ${TOKEN}"
```

**Response**:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "orchestrator_job_id": "orch_abc123xyz789",
  "dispatched_at": "2025-12-27T22:10:30.123456Z",
  "started_processing_at": "2025-12-27T22:10:35.000000Z",
  "completed_at": "2025-12-27T22:11:05.000000Z",
  "processing_duration": 30.0,
  "result_file_path": "/var/www/app/backend/media/ai_results/550e8400.../output.npy",
  "result_metadata": {
    "feature_count": 512,
    "model_version": "1.0.0"
  }
}
```

#### Via Backend Logs

```bash
docker-compose logs -f backend-openmedlab | grep orchestrator
```

Example output:
```
Task 550e8400... submitted to orchestrator: orch_abc123xyz789
Task 550e8400...: DISPATCHED → PROCESSING
Task 550e8400...: PROCESSING → COMPLETED
```

#### Via Celery Beat Logs

```bash
docker-compose logs -f celery-beat-openmedlab | grep sync-orchestrator-status
```

Example output:
```
[2025-12-27 22:10:33] Scheduler: Sending due task sync-orchestrator-status
[2025-12-27 22:10:38] Scheduler: Sending due task sync-orchestrator-status
```

#### Via Celery Worker Logs

```bash
docker-compose logs -f celery-worker-openmedlab | grep sync_orchestrator_status
```

Example output:
```
[2025-12-27 22:10:33] Task ai_analysis.tasks.sync_orchestrator_status[abc-123] received
[2025-12-27 22:10:33] Orchestrator sync: 3 tasks, 1 updated
[2025-12-27 22:10:33] Task ai_analysis.tasks.sync_orchestrator_status[abc-123] succeeded in 0.087s
```

---

## Migration Strategy

### Zero-Downtime Migration

The orchestrator integration uses a **feature flag** (`USE_ORCHESTRATOR`) to enable gradual, zero-downtime migration:

```
Phase 1: Deploy Infrastructure    → orchestrator services running, flag OFF
Phase 2: Deploy Code Changes      → code supports both paths, flag OFF
Phase 3: Enable Orchestrator      → flip flag to ON
Phase 4: Monitor & Validate       → verify orchestrator working
Phase 5: Full Migration (Optional) → remove Celery workers
```

### Step-by-Step Migration

#### Phase 1: Deploy Infrastructure (No User Impact)

```bash
cd /home/jpablo/code/web-apps/openmedlab

# Start orchestrator services
docker-compose up -d orchestrator-redis orchestrator-openmedlab

# Verify health
curl http://localhost:8080/metrics
docker-compose logs orchestrator-openmedlab
```

**Status**:
- ✅ Orchestrator running
- ✅ Backend still using Celery (USE_ORCHESTRATOR=False)
- ✅ No user-facing changes

#### Phase 2: Deploy Code Changes (No User Impact)

```bash
# Install gRPC dependencies
docker exec backend-openmedlab pip install grpcio==1.60.0 grpcio-tools==1.60.0

# Generate proto files
docker exec backend-openmedlab python -m grpc_tools.protoc \
  -I./protos --python_out=./protos --grpc_python_out=./protos \
  ./protos/orchestrator.proto

# Run migrations
docker exec backend-openmedlab python manage.py migrate

# Restart backend
docker-compose restart backend-openmedlab celery-worker-openmedlab celery-beat-openmedlab

# Verify no errors
docker-compose logs backend-openmedlab | tail -50
```

**Status**:
- ✅ Code supports both Celery and Orchestrator
- ✅ Backend still using Celery (USE_ORCHESTRATOR=False)
- ✅ No user-facing changes

#### Phase 3: Enable Orchestrator (Gradual Rollout)

**Option A: Test in Dev/Staging First**

```bash
# Set environment variable for testing
docker-compose exec backend-openmedlab bash
export USE_ORCHESTRATOR=True

# Submit a test job via API
# Monitor logs for orchestrator activity

# If successful, persist to docker-compose.yml
```

**Option B: Production Rollout**

Edit `docker-compose.yml`:

```yaml
backend-openmedlab:
  environment:
    - USE_ORCHESTRATOR=True  # Enable orchestrator
```

Restart services:

```bash
docker-compose restart backend-openmedlab celery-worker-openmedlab celery-beat-openmedlab
```

**Status**:
- ✅ All new jobs go to orchestrator
- ✅ Existing Celery jobs continue processing
- ✅ Users see no difference (same API, same WebSocket)

#### Phase 4: Monitor & Validate (1 Week Recommended)

Monitor the following metrics:

**Orchestrator Metrics** (Prometheus):
```bash
curl http://localhost:8080/metrics | grep orchestrator_jobs_total
curl http://localhost:8080/metrics | grep orchestrator_queue_depth
curl http://localhost:8080/metrics | grep orchestrator_processing_time_seconds
```

**Backend Logs**:
```bash
docker-compose logs -f backend-openmedlab | grep -E "(orchestrator|Task.*→)"
```

**Database Queries** (check orchestrator adoption):
```bash
docker exec -it backend-openmedlab python manage.py shell
```

```python
from ai_analysis.models import AnalysisTask
from django.utils import timezone
from datetime import timedelta

# Jobs submitted in last 24 hours
recent_cutoff = timezone.now() - timedelta(hours=24)

total_recent = AnalysisTask.objects.filter(created_at__gte=recent_cutoff).count()
orchestrator_recent = AnalysisTask.objects.filter(
    created_at__gte=recent_cutoff,
    orchestrator_job_id__isnull=False
).count()

print(f"Recent jobs: {total_recent}")
print(f"Via orchestrator: {orchestrator_recent}")
print(f"Adoption rate: {orchestrator_recent / total_recent * 100:.1f}%")
```

**Frontend Monitoring**:
- Monitor WebSocket messages for `orchestrator_job_id` field
- Verify task status updates arrive in <6 seconds
- Check for any stuck tasks (status not updating)

#### Phase 5: Full Migration (Optional)

Once validated (recommended: 1 week stable operation):

**Remove Celery Workers** (optional - can keep for other tasks):

Edit `docker-compose.yml`:

```yaml
# Comment out or remove celery-worker-openmedlab if only used for AI jobs
# celery-worker-openmedlab:
#   ...
```

**Clean Up Legacy Code** (optional):

- Remove `ai_analysis/connectors/` directory
- Remove `dispatch_ai_job` Celery task
- Remove `poll_mirage_job_status` Celery task

**Note**: Keep Celery Beat and at least one worker if you have other Celery tasks (timeouts, cleanup, etc.).

### Rollback Procedure

If issues arise, rollback is instant:

#### Immediate Rollback (No Code Changes)

```bash
# Option 1: Environment variable
docker-compose exec backend-openmedlab bash -c "export USE_ORCHESTRATOR=False"
docker-compose restart backend-openmedlab

# Option 2: Update docker-compose.yml
# Change USE_ORCHESTRATOR=True → False
docker-compose restart backend-openmedlab celery-worker-openmedlab celery-beat-openmedlab
```

**Result**: System immediately reverts to Celery. No data loss (orchestrator_job_id field is nullable).

#### Verify Rollback

```bash
# Check backend logs for Celery dispatch
docker-compose logs backend-openmedlab | grep "dispatch_ai_job"

# Submit test job
# Should see celery_task_id populated, orchestrator_job_id = null
```

---

## Monitoring & Debugging

### Prometheus Metrics

**Endpoint**: `http://localhost:8080/metrics`

**Key Metrics**:

```prometheus
# Total jobs submitted
orchestrator_jobs_total{status="completed"} 1234
orchestrator_jobs_total{status="failed"} 56

# Queue depth (current pending jobs)
orchestrator_queue_depth 3

# Worker utilization
orchestrator_workers_busy 2
orchestrator_workers_total 2

# Processing time (histogram)
orchestrator_processing_time_seconds_bucket{le="10"} 450
orchestrator_processing_time_seconds_bucket{le="30"} 890
orchestrator_processing_time_seconds_bucket{le="60"} 1150

# gRPC request latency
orchestrator_grpc_request_duration_seconds_bucket{method="SubmitJob",le="0.1"} 1200
orchestrator_grpc_request_duration_seconds_bucket{method="GetJobStatus",le="0.05"} 5400
```

### Log Analysis

#### Backend Logs (Django)

```bash
# All orchestrator activity
docker-compose logs -f backend-openmedlab | grep orchestrator

# Task status transitions
docker-compose logs -f backend-openmedlab | grep "Task.*→"

# gRPC errors
docker-compose logs -f backend-openmedlab | grep "gRPC error"
```

#### Orchestrator Logs

```bash
# All activity
docker-compose logs -f orchestrator-openmedlab

# Job submissions
docker-compose logs orchestrator-openmedlab | grep "Job submitted"

# Job completions
docker-compose logs orchestrator-openmedlab | grep "Job completed"

# Errors
docker-compose logs orchestrator-openmedlab | grep ERROR
```

#### Celery Beat Logs (Polling)

```bash
# Status sync activity
docker-compose logs -f celery-beat-openmedlab | grep sync-orchestrator-status

# All periodic tasks
docker-compose logs celery-beat-openmedlab | grep "Scheduler: Sending"
```

#### Celery Worker Logs (Sync Execution)

```bash
# Sync task results
docker-compose logs -f celery-worker-openmedlab | grep sync_orchestrator_status

# Example output:
# [2025-12-27 22:10:33] Orchestrator sync: 3 tasks, 1 updated
```

### Redis Queue Inspection

#### Orchestrator Redis (port 6380)

```bash
# Connect to Redis
docker exec -it orchestrator-redis redis-cli

# Check queue depth
LLEN orchestrator:queue

# Inspect queued jobs
LRANGE orchestrator:queue 0 -1

# Check job status cache
KEYS orchestrator:job:*
GET orchestrator:job:orch_abc123xyz789

# Monitor live commands
MONITOR
```

### Common Debugging Scenarios

#### Scenario 1: Job Stuck in DISPATCHED

**Symptoms**:
- Task status = `DISPATCHED`
- No status updates for >30 seconds

**Debug Steps**:

1. Check orchestrator is running:
```bash
docker-compose ps orchestrator-openmedlab
```

2. Check orchestrator logs:
```bash
docker-compose logs orchestrator-openmedlab | grep "orch_abc123xyz789"
```

3. Check Redis queue:
```bash
docker exec orchestrator-redis redis-cli LLEN orchestrator:queue
```

4. Check worker logs:
```bash
docker-compose logs orchestrator-openmedlab | grep "Worker.*processing"
```

**Likely Causes**:
- Orchestrator container crashed → `docker-compose restart orchestrator-openmedlab`
- Redis connection lost → `docker-compose restart orchestrator-redis`
- All workers busy → increase `NUM_WORKERS` in docker-compose.yml

#### Scenario 2: gRPC Connection Errors

**Symptoms**:
- Backend logs: `gRPC error: UNAVAILABLE`
- Task status = `FAILED`, error_message = `"Orchestrator submission failed"`

**Debug Steps**:

1. Check orchestrator container:
```bash
docker-compose ps orchestrator-openmedlab
```

2. Check gRPC port:
```bash
docker exec backend-openmedlab nc -zv orchestrator-openmedlab 50050
```

3. Check orchestrator startup logs:
```bash
docker-compose logs orchestrator-openmedlab | head -20
```

**Likely Causes**:
- Orchestrator not started → `docker-compose up -d orchestrator-openmedlab`
- Port conflict → check `docker-compose ps` for port 50050
- Network issue → `docker network inspect app-network`

#### Scenario 3: Status Not Updating

**Symptoms**:
- Task stuck in `PROCESSING`
- No WebSocket updates
- Backend logs show no status transitions

**Debug Steps**:

1. Check Celery Beat is running:
```bash
docker-compose ps celery-beat-openmedlab
```

2. Check sync task is scheduled:
```bash
docker-compose logs celery-beat-openmedlab | grep sync-orchestrator-status
```

3. Check sync task execution:
```bash
docker-compose logs celery-worker-openmedlab | grep sync_orchestrator_status
```

4. Manually trigger sync (for testing):
```bash
docker exec backend-openmedlab python manage.py shell
```
```python
from ai_analysis.tasks import sync_orchestrator_status
result = sync_orchestrator_status()
print(result)  # Should show {'total': X, 'updated': Y}
```

**Likely Causes**:
- Celery Beat not running → `docker-compose up -d celery-beat-openmedlab`
- Sync task disabled → check `USE_ORCHESTRATOR=True` in environment
- Sync task failing → check celery-worker logs for exceptions

#### Scenario 4: WebSocket Not Broadcasting

**Symptoms**:
- Backend logs show status updates
- Frontend not receiving WebSocket messages
- Monitor page not updating

**Debug Steps**:

1. Check WebSocket connection in browser console:
```javascript
// Should see WebSocket connection established
ws://localhost:3080/ws/tasks/
```

2. Check Django signals:
```bash
docker-compose logs backend-openmedlab | grep "task_status_changed"
```

3. Check Channels/Daphne:
```bash
docker-compose logs backend-openmedlab | grep "WebSocket"
```

**Likely Causes**:
- This is unrelated to orchestrator - WebSocket infrastructure unchanged
- See `WEBSOCKET-TESTING-TODO.md` for WebSocket debugging

---

## API Reference

### gRPC Service Definition

**Proto File**: `/app/backend/protos/orchestrator.proto`

#### SubmitJob

**Request**:
```protobuf
message SubmitJobRequest {
  repeated ImageInput images = 1;
  string task_type = 2;          // e.g., "feature_extraction"
  string model_name = 3;          // e.g., "mirage"
  string model_size = 4;          // e.g., "base", "large"
  string output_destination = 5;  // e.g., "/var/www/app/backend/media/ai_results/..."
  string output_format = 6;       // e.g., "npy", "json"
  map<string, string> metadata = 7;
}

message ImageInput {
  string modality = 1;  // e.g., "bscan", "t1", "oct"
  string source = 2;    // File path in shared volume
}
```

**Response**:
```protobuf
message SubmitJobResponse {
  string job_id = 1;
  JobStatus status = 2;
  string message = 3;
}

enum JobStatus {
  JOB_STATUS_UNSPECIFIED = 0;
  JOB_STATUS_QUEUED = 1;
  JOB_STATUS_PROCESSING = 2;
  JOB_STATUS_COMPLETED = 3;
  JOB_STATUS_FAILED = 4;
  JOB_STATUS_CANCELLED = 5;
}
```

#### GetJobStatus

**Request**:
```protobuf
message GetJobStatusRequest {
  string job_id = 1;
}
```

**Response**:
```protobuf
message JobStatusResponse {
  string job_id = 1;
  JobStatus status = 2;
  string output_uri = 3;
  string error_message = 4;
  int32 progress_percent = 5;
  map<string, string> result_metadata = 6;
}
```

### REST API (OpenMedLab)

No changes to existing REST API - orchestrator is transparent to frontend.

**Existing Endpoints**:

- `POST /api/ai-analysis/tasks/` - Create task (now supports orchestrator)
- `GET /api/ai-analysis/tasks/{id}/` - Get task status
- `POST /api/ai-analysis/tasks/{id}/retry/` - Retry task (now supports orchestrator)
- `DELETE /api/ai-analysis/tasks/{id}/` - Cancel task
- `GET /api/ai-analysis/tasks/monitor/` - Monitor page API

**Response Fields** (new):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "orchestrator_job_id": "orch_abc123xyz789",  // NEW: Present if USE_ORCHESTRATOR=True
  "celery_task_id": null,                       // null when using orchestrator
  "service_job_id": null,                       // null when using orchestrator
  "status": "DISPATCHED",
  ...
}
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'grpc'"

**Cause**: gRPC dependencies not installed.

**Solution**:
```bash
docker exec backend-openmedlab pip install grpcio==1.60.0 grpcio-tools==1.60.0
docker-compose restart backend-openmedlab
```

### Issue: "ModuleNotFoundError: No module named 'protos'"

**Cause**: Proto files not generated.

**Solution**:
```bash
docker exec backend-openmedlab python -m grpc_tools.protoc \
  -I./protos --python_out=./protos --grpc_python_out=./protos \
  ./protos/orchestrator.proto
docker-compose restart backend-openmedlab
```

### Issue: "gRPC error: UNAVAILABLE - failed to connect to all addresses"

**Cause**: Orchestrator service not running.

**Solution**:
```bash
docker-compose up -d orchestrator-openmedlab
docker-compose logs orchestrator-openmedlab
```

### Issue: "Column 'orchestrator_job_id' does not exist"

**Cause**: Database migration not applied.

**Solution**:
```bash
docker exec backend-openmedlab python manage.py migrate ai_analysis
```

### Issue: Jobs stuck in DISPATCHED, never processing

**Cause**: Orchestrator workers not picking up jobs.

**Solution**:

1. Check worker logs:
```bash
docker-compose logs orchestrator-openmedlab | grep Worker
```

2. Check Redis queue:
```bash
docker exec orchestrator-redis redis-cli LLEN orchestrator:queue
```

3. Restart orchestrator:
```bash
docker-compose restart orchestrator-openmedlab
```

### Issue: "Task sync shows 0 updated despite active tasks"

**Cause**: Tasks may not have `orchestrator_job_id` set.

**Solution**:

Check database:
```bash
docker exec backend-openmedlab python manage.py shell
```
```python
from ai_analysis.models import AnalysisTask

# Check active tasks
active = AnalysisTask.objects.filter(status__in=['PENDING', 'QUEUED', 'DISPATCHED', 'PROCESSING'])
print(f"Active tasks: {active.count()}")

# Check how many have orchestrator_job_id
with_orch_id = active.filter(orchestrator_job_id__isnull=False)
print(f"With orchestrator_job_id: {with_orch_id.count()}")

# List tasks without orchestrator_job_id
for task in active.filter(orchestrator_job_id__isnull=True):
    print(f"Task {task.id}: status={task.status}, celery_task_id={task.celery_task_id}")
```

If tasks have `celery_task_id` but no `orchestrator_job_id`, they were created before enabling orchestrator. Wait for them to complete or manually cancel.

---

## Performance Considerations

### Polling Interval

Current: **5 seconds** (configured in `celery.py`)

**Trade-offs**:
- **Lower** (e.g., 2s): Faster UI updates, higher load on orchestrator
- **Higher** (e.g., 10s): Lower load, slower UI updates

**Recommendation**:
- **Development**: 5s (current)
- **Production (low volume)**: 5s
- **Production (high volume)**: 10s + optimize with Celery task routing

### Scaling

**Horizontal Scaling**:

1. **Add more orchestrator workers**:
```yaml
orchestrator-openmedlab:
  environment:
    - NUM_WORKERS=4  # Increase from 2
```

2. **Run multiple orchestrator instances** (advanced):
- Share same `orchestrator-redis`
- Use different container names
- Load balance gRPC calls (requires gRPC load balancer)

3. **Scale Celery workers** (for sync task):
```bash
docker-compose up -d --scale celery-worker-openmedlab=3
```

**Vertical Scaling**:

Increase resources in docker-compose.yml:
```yaml
orchestrator-openmedlab:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G
```

### Database Queries

Status sync queries are optimized:

```python
# Only queries active tasks with orchestrator_job_id
AnalysisTask.objects.filter(
    orchestrator_job_id__isnull=False,
    status__in=['PENDING', 'QUEUED', 'DISPATCHED', 'PROCESSING']
)
```

**Index Recommendation** (future optimization):

```python
# Add to AnalysisTask model
class Meta:
    indexes = [
        models.Index(fields=['orchestrator_job_id', 'status']),
    ]
```

---

## Future Enhancements

### Phase 2: Bidirectional Streaming

Replace polling with gRPC server streaming:

```protobuf
// New RPC method
rpc WatchJob(WatchJobRequest) returns (stream JobStatusResponse);
```

**Benefits**:
- Real-time updates (no polling delay)
- Lower network overhead
- Reduced database queries

**Implementation**:
- Modify `orchestrator_client.py` to use streaming
- Remove Celery Beat polling task
- Add gRPC connection pool management

### Phase 3: Orchestrator HA

High availability setup:

- Multi-instance orchestrator with shared Redis
- gRPC load balancer (e.g., Envoy)
- Redis Sentinel or Cluster mode
- Health checks and automatic failover

### Phase 4: Advanced Monitoring

- Grafana dashboards for Prometheus metrics
- Alerting on queue depth, failure rate
- Distributed tracing (OpenTelemetry)
- Custom Django admin panel for orchestrator status

---

## Conclusion

The orchestrator integration is **complete and production-ready** with the following characteristics:

✅ **Zero-Downtime Migration**: Feature flag enables instant rollback
✅ **Backward Compatible**: Existing Celery jobs continue working
✅ **Real-time Updates**: WebSocket infrastructure preserved
✅ **Scalable**: gRPC + Redis queue supports high throughput
✅ **Observable**: Prometheus metrics + comprehensive logging
✅ **Tested**: All code paths validated, migrations applied

**Next Steps**:
1. Review this documentation
2. Test orchestrator in staging environment
3. Enable `USE_ORCHESTRATOR=True` when ready
4. Monitor for 1 week before full migration

**Questions or Issues?**
- Check [Troubleshooting](#troubleshooting) section
- Review orchestrator logs: `docker-compose logs orchestrator-openmedlab`
- Check backend logs: `docker-compose logs backend-openmedlab | grep orchestrator`

---

**Document Version**: 1.0
**Last Updated**: December 27, 2025
**Status**: ✅ Implementation Complete, Documentation Complete

# MIRAGE Integration Guide

## Overview

This document describes the integration of the MIRAGE (Medical Image Representation via Adversarial Gradient Estimation) OCT analysis model with the OpenMedLab platform.

MIRAGE is a foundation model for retinal OCT images supporting:
- **Feature Extraction**: Extract high-dimensional embedding vectors
- **Segmentation**: Segment anatomical structures and pathologies
- **Classification**: Classify disease states and conditions

## Architecture

```
┌─────────────────┐
│   User/Frontend │
└────────┬────────┘
         │ POST /api/ai-analysis/tasks/
         ▼
┌─────────────────────────┐
│   Django Backend API    │
│  (AnalysisTaskViewSet)  │
└────────┬────────────────┘
         │ Creates AnalysisTask
         │ Queues Celery job
         ▼
┌─────────────────────────┐
│   Celery Worker         │
│  (dispatch_ai_job)      │
└────────┬────────────────┘
         │ Uses MirageConnector
         │ POST /analyze
         ▼
┌─────────────────────────┐
│   MIRAGE FastAPI        │
│   http://mirage-api:8000│
└────────┬────────────────┘
         │ Returns job_id
         │ Processes async
         ▼
┌─────────────────────────┐
│  Celery Poll Worker     │
│(poll_mirage_job_status) │
└────────┬────────────────┘
         │ GET /jobs/{job_id}
         │ Every 5 seconds
         ▼
┌─────────────────────────┐
│  Task Status Updates    │
│  DISPATCHED → PROCESSING│
│  → COMPLETED/FAILED     │
└─────────────────────────┘
```

## Components

### 1. MIRAGE Connector (`ai_analysis/connectors/mirage.py`)

The `MirageConnector` class handles all communication with the MIRAGE FastAPI service.

**Key Methods:**
- `dispatch_job(task)` - Submit analysis job to MIRAGE
- `poll_job_status(task)` - Check job status
- `validate_parameters(parameters)` - Validate task parameters
- `check_health()` - Check MIRAGE service health
- `_ensure_model_loaded(model_size)` - Load model if needed

**API Integration:**
- POST `/analyze` - Submit job with images, task_type, model_size
- GET `/jobs/{job_id}` - Poll job status
- POST `/models/{model_size}/load` - Load model
- GET `/health` - Service health check

### 2. Celery Tasks (`ai_analysis/tasks.py`)

**`dispatch_ai_job(task_id)`**
- Creates MIRAGE connector
- Validates parameters
- Dispatches job via HTTP POST
- Updates task status to DISPATCHED
- Starts polling automatically for MIRAGE jobs

**`poll_mirage_job_status(task_id)`**
- Polls MIRAGE service every 5 seconds
- Up to 60 attempts (5 minutes total)
- Updates task status based on service response
- Handles COMPLETED, FAILED, PROCESSING states
- Stores results in `result_data` and `result_uri` fields

### 3. Django Models

**`AIModel`** - Model registration
```python
{
    'key': 'mirage-v1',
    'name': 'MIRAGE v1.0',
    'endpoint_url': 'http://mirage-api-server:8000',
    'connector_class': 'ai_analysis.connectors.mirage.MirageConnector',
    'supported_modalities': ['OCT', 'OPT'],
    'model_type': 'other',  # Multi-purpose
}
```

**`AnalysisTask`** - Task tracking
```python
{
    'input_image': ForeignKey(MedicalImage),
    'model': ForeignKey(AIModel),
    'parameters': {
        'task_type': 'feature_extraction',
        'modality': 'bscan',
        'model_size': 'base',
        'output_destination': 's3://...'
    },
    'status': 'PENDING → QUEUED → DISPATCHED → PROCESSING → COMPLETED',
    'service_job_id': '<mirage-job-uuid>',
    'result_data': {...},
    'result_uri': 's3://...'
}
```

### 4. REST API Endpoints

**Create Analysis Task**
```http
POST /api/ai-analysis/tasks/
Authorization: Bearer <token>
Content-Type: application/json

{
  "model_key": "mirage-v1",
  "input_image_id": 123,
  "parameters": {
    "task_type": "feature_extraction",
    "modality": "bscan",
    "model_size": "base"
  }
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "model": {
    "key": "mirage-v1",
    "name": "MIRAGE v1.0"
  },
  "created_at": "2025-12-26T12:00:00Z"
}
```

**Get Task Status**
```http
GET /api/ai-analysis/tasks/{task_id}/
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "service_job_id": "abc123",
  "result_uri": "/app/MIRAGE/_test_data/results",
  "result_data": {
    "keys": ["features.npy", "embeddings.npy"]
  },
  "created_at": "2025-12-26T12:00:00Z",
  "completed_at": "2025-12-26T12:01:30Z"
}
```

## Setup Instructions

### 1. Register MIRAGE Model

```bash
# In backend container
docker exec backend-openmedlab python manage.py register_mirage

# With custom endpoint
docker exec backend-openmedlab python manage.py register_mirage --url http://localhost:8000

# Update existing entry
docker exec backend-openmedlab python manage.py register_mirage --update
```

### 2. Verify Registration

```bash
# Via Django shell
docker exec -it backend-openmedlab python manage.py shell

>>> from ai_analysis.models import AIModel
>>> mirage = AIModel.objects.get(key='mirage-v1')
>>> print(mirage.name, mirage.endpoint_url)
MIRAGE v1.0 http://mirage-api-server:8000
```

### 3. Check MIRAGE Service Health

```bash
# Via API
curl http://localhost:8000/health

# Via Django shell
>>> from ai_analysis.connectors.mirage import MirageConnector
>>> conn = MirageConnector(endpoint_url='http://localhost:8000')
>>> health = conn.check_health()
>>> print(health)
{'status': 'healthy', 'gpu_available': True, 'models_loaded': {'base': True}}
```

## Usage Examples

### Example 1: Feature Extraction

```python
import requests

# 1. Upload OCT image (get image_id)
# 2. Create MIRAGE task

response = requests.post(
    'http://backend-openmedlab:3080/api/ai-analysis/tasks/',
    headers={'Authorization': 'Bearer <token>'},
    json={
        'model_key': 'mirage-v1',
        'input_image_id': 123,
        'parameters': {
            'task_type': 'feature_extraction',
            'modality': 'bscan',
            'model_size': 'base'
        }
    }
)

task_id = response.json()['id']

# 3. Poll for completion
import time
while True:
    status_response = requests.get(
        f'http://backend-openmedlab:3080/api/ai-analysis/tasks/{task_id}/',
        headers={'Authorization': 'Bearer <token>'}
    )
    task_data = status_response.json()

    if task_data['status'] == 'COMPLETED':
        print(f"Results: {task_data['result_uri']}")
        break
    elif task_data['status'] == 'FAILED':
        print(f"Failed: {task_data['error_message']}")
        break

    time.sleep(5)
```

### Example 2: Segmentation Task

```python
response = requests.post(
    'http://backend-openmedlab:3080/api/ai-analysis/tasks/',
    headers={'Authorization': 'Bearer <token>'},
    json={
        'model_key': 'mirage-v1',
        'input_image_id': 456,
        'parameters': {
            'task_type': 'segmentation',
            'modality': 'bscan',
            'model_size': 'large',  # Use larger model for better accuracy
            'output_destination': 's3://openmedlab-results/segmentation/task1'
        }
    }
)
```

### Example 3: Classification with SLO Images

```python
response = requests.post(
    'http://backend-openmedlab:3080/api/ai-analysis/tasks/',
    headers={'Authorization': 'Bearer <token>'},
    json={
        'model_key': 'mirage-v1',
        'input_image_id': 789,
        'parameters': {
            'task_type': 'classification',
            'modality': 'slo',  # Scanning Laser Ophthalmoscopy
            'model_size': 'base'
        }
    }
)
```

## Parameter Reference

### Required Parameters

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| `task_type` | string | `feature_extraction`, `segmentation`, `classification` | Type of analysis to perform |
| `modality` | string | `bscan`, `slo`, `bscanlayermap` | OCT image modality |

### Optional Parameters

| Parameter | Type | Values | Default | Description |
|-----------|------|--------|---------|-------------|
| `model_size` | string | `base`, `large` | `base` | Model size/capacity |
| `output_destination` | string | S3 URI or path | Auto-generated | Where to store results |

### Image Modalities

**bscan** (512x512)
- B-scan cross-sectional OCT images
- Most common OCT modality
- Shows retinal layers

**slo** (512x512)
- Scanning Laser Ophthalmoscopy
- En-face view of retina
- Useful for surface features

**bscanlayermap** (128x128)
- Layer segmentation maps
- Annotated retinal layer boundaries
- Smaller resolution

## Status Lifecycle

```
PENDING
  ↓ (Celery picks up task)
QUEUED
  ↓ (Connector dispatches to MIRAGE)
DISPATCHED
  ↓ (MIRAGE starts processing)
PROCESSING
  ↓ (MIRAGE completes)
COMPLETED
```

**Terminal States:**
- `COMPLETED` - Success, results available
- `FAILED` - Error during processing
- `TIMEOUT` - Exceeded time limit
- `CANCELLED` - User cancelled

## Error Handling

### Validation Errors (HTTP 422)

```json
{
  "error": "Invalid task_type 'invalid'. Must be one of: feature_extraction, segmentation, classification"
}
```

**Common validation errors:**
- Invalid `task_type`
- Invalid `modality`
- Invalid `model_size`
- Malformed `output_destination`

### Connection Errors

**Symptom:** Task stuck in PENDING/QUEUED status

**Diagnosis:**
```bash
# Check MIRAGE service is running
curl http://mirage-api-server:8000/health

# Check connector can reach service
docker exec backend-openmedlab python manage.py shell
>>> from ai_analysis.connectors.mirage import MirageConnector
>>> conn = MirageConnector(endpoint_url='http://mirage-api-server:8000')
>>> conn.check_health()
```

**Solution:** Ensure MIRAGE service is running and network connectivity exists.

### Processing Errors

**Symptom:** Task status = FAILED

**Diagnosis:** Check `error_message` field in task
```python
task = AnalysisTask.objects.get(id=task_id)
print(task.error_message)
```

**Common causes:**
- Input image wrong format/size
- Corrupted image file
- Out of memory
- Model not loaded

## Monitoring and Logging

### View Celery Logs

```bash
# Real-time logs
docker logs -f celery-worker-openmedlab | grep MIRAGE

# Filter for specific task
docker logs celery-worker-openmedlab 2>&1 | grep "Task <task-id>"
```

### View MIRAGE Service Logs

```bash
# If MIRAGE is running in Docker
docker logs -f mirage-api-server

# Check for errors
docker logs mirage-api-server 2>&1 | grep ERROR
```

### Database Queries

```python
# Get all MIRAGE tasks
from ai_analysis.models import AnalysisTask
mirage_tasks = AnalysisTask.objects.filter(
    model__key='mirage-v1'
).order_by('-created_at')

# Get failed tasks
failed_tasks = AnalysisTask.objects.filter(
    model__key='mirage-v1',
    status='FAILED'
)

# Get average processing time
from django.db.models import Avg, F
avg_time = AnalysisTask.objects.filter(
    model__key='mirage-v1',
    status='COMPLETED'
).aggregate(
    avg_seconds=Avg(F('completed_at') - F('dispatched_at'))
)
```

## Performance Tuning

### Celery Worker Configuration

```python
# backend/celery.py

# Increase concurrency for MIRAGE tasks
CELERY_WORKER_CONCURRENCY = 4

# Separate queue for MIRAGE
CELERY_TASK_ROUTES = {
    'ai_analysis.tasks.dispatch_ai_job': {'queue': 'ai_jobs'},
    'ai_analysis.tasks.poll_mirage_job_status': {'queue': 'polling'},
}
```

### Polling Interval Adjustment

```python
# tasks.py - Adjust polling frequency

@shared_task(
    bind=True,
    max_retries=120,  # Longer timeout: 10 minutes
    default_retry_delay=5,  # Poll every 5 seconds
)
def poll_mirage_job_status(self, task_id):
    # ...
```

### Batch Processing

For processing many images, create tasks in batches:

```python
from ai_analysis.models import AIModel, AnalysisTask
from dicom_images.models import MedicalImage
from ai_analysis.tasks import dispatch_ai_job

mirage = AIModel.objects.get(key='mirage-v1')
images = MedicalImage.objects.filter(modality='OCT')[:100]

for image in images:
    task = AnalysisTask.objects.create(
        input_image=image,
        model=mirage,
        created_by=user,
        parameters={
            'task_type': 'feature_extraction',
            'modality': 'bscan',
            'model_size': 'base'
        }
    )
    # Queue for processing
    dispatch_ai_job.delay(str(task.id))
```

## Testing

### Unit Tests

```bash
docker exec backend-openmedlab python manage.py test ai_analysis.tests.test_mirage_connector
```

### Integration Tests

```bash
# Test full workflow with real MIRAGE service
docker exec backend-openmedlab python manage.py test ai_analysis.tests.test_mirage_integration
```

### Manual Testing

```bash
# Use MIRAGE test scripts
cd /home/jpablo/code/repositories/medimaging/
python3 tests/test_api.py
python3 tests/test_inference.py tests/artifacts/DME-2556938-1.jpeg
```

## Troubleshooting

### Task Stuck in DISPATCHED

**Cause:** Polling task not running

**Fix:**
```python
# Manually trigger polling
from ai_analysis.tasks import poll_mirage_job_status
poll_mirage_job_status.delay(str(task_id))
```

### Model Not Loaded Error

**Cause:** MIRAGE model not loaded in memory

**Fix:** Connector automatically loads models, but you can pre-load:
```bash
curl -X POST http://mirage-api-server:8000/models/base/load
```

### Result Files Not Found

**Cause:** Output destination misconfigured

**Fix:** Check `result_uri` field matches actual file location:
```python
task = AnalysisTask.objects.get(id=task_id)
print(task.result_uri)  # Should match MIRAGE output_uri
```

## References

- [MIRAGE API Documentation](../repositories/medimaging/tests/README.md)
- [AI Analysis Models](./AI-ANALYSIS.md)
- [Celery Task Queue](./CELERY-TASKS.md)
- [OpenMedLab API Reference](./API-REFERENCE.md)

# AI Models — Installation & Usage Guide

> **Last updated:** 2026-02-16

---

## Architecture Overview

OpenMedLab supports two dispatch modes for AI analysis:

```
┌─────────────┐     Celery (USE_ORCHESTRATOR=False)     ┌──────────────────┐
│   Backend    │ ──────────────────────────────────────► │  AI Service      │
│  (Django)    │     HTTP REST / polling                 │  (MIRAGE/CheXNet)│
└─────────────┘                                         └──────────────────┘

┌─────────────┐     gRPC          ┌──────────────┐  gRPC  ┌──────────────┐
│   Backend    │ ───────────────► │ Orchestrator  │ ─────► │ Model Service│
│  (Django)    │   :50050         │ (Redis queue) │ :50051 │ (PICAI, etc) │
└─────────────┘                   └──────────────┘        └──────────────┘
```

**Celery mode** (current default): The backend dispatches directly to the model's HTTP API via its connector class, then polls for results.

**Orchestrator mode**: The backend sends a gRPC request to the orchestrator, which queues the job in Redis and dispatches it to the appropriate model service via gRPC.

---

## Registered Models

| Model | Key | Connector | Protocol | Modalities | Status |
|-------|-----|-----------|----------|------------|--------|
| MIRAGE | `mirage-v1` | `MirageConnector` | HTTP REST + polling | OCT, SLO | Connector ready |
| PICAI | `picai-v1` | `PICAIConnector` | gRPC via orchestrator | MR (T2W, ADC, HBV) | Connector ready |
| CheXNet | `chexnet-v1` | `CheXNetConnector` | HTTP REST + webhook | CR, DX (Chest X-ray) | Connector ready |

---

## Quick Start with docker-compose.services.yml

A dedicated `docker-compose.services.yml` defines all model services. It joins the main stack's network and mounts the shared media volume so models can read uploaded images.

```bash
# 1. Start the core stack
docker compose up -d

# 2. Register models in the database
docker compose exec backend-openmedlab python manage.py seed_ai_models

# 3. Start all model services (requires GPU + built images)
docker compose -f docker-compose.yml -f docker-compose.services.yml up -d

# Or start only the service you need
docker compose -f docker-compose.yml -f docker-compose.services.yml up -d mirage-service
docker compose -f docker-compose.yml -f docker-compose.services.yml up -d chexnet-service
```

Each model service image must be built separately from its own repository before running (see per-model sections below).

---

## Prerequisites

All AI services require:

- Docker and Docker Compose
- The OpenMedLab stack running (`docker compose up`)
- Models registered in the database (see [Registration](#model-registration))

GPU-accelerated inference additionally requires:

- NVIDIA GPU with CUDA support
- `nvidia-container-toolkit` installed on the host
- `deploy.resources.reservations.devices` configured in the model's Docker Compose service

---

## Model Registration

Models must be registered in the Django database before use. Two approaches:

### Option A: Seed all models (recommended for dev)

```bash
docker compose exec backend-openmedlab python manage.py seed_ai_models
```

This creates all three models (MIRAGE, PICAI, CheXNet) with full metadata, default parameters, and performance metrics.

### Option B: Register individually

```bash
# MIRAGE — optionally pass the service URL
docker compose exec backend-openmedlab python manage.py register_mirage \
  --url http://mirage-api-server:8000 \
  --update

# PICAI and CheXNet are included in seed_ai_models only
```

### Verify registration

```bash
docker compose exec backend-openmedlab python manage.py shell -c "
from ai_analysis.models import AIModel
for m in AIModel.objects.filter(is_active=True):
    print(f'{m.key:15} {m.name:20} {m.endpoint_url}')
"
```

---

## MIRAGE (OCT Foundation Model)

**Paper:** Morano et al., _npj Digital Medicine_ 2025 — [10.1038/s41746-025-01852-3](https://doi.org/10.1038/s41746-025-01852-3)

### What it does

Multimodal retinal OCT/SLO foundation model supporting feature extraction, segmentation, and classification on ophthalmic images.

### Service requirements

MIRAGE runs as a standalone HTTP service. It is **not** included in the default Docker Compose stack — you must run it separately or add it as a service.

**Expected API contract** (the service must implement these endpoints):

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analyze` | Submit an analysis job |
| GET | `/jobs/{job_id}` | Poll job status |
| POST | `/models/{model_size}/load` | Pre-load a model into GPU memory |
| POST | `/models/{model_size}/unload` | Unload model from memory |
| GET | `/health` | Health check (returns GPU info, loaded models) |

### Running MIRAGE

The service is pre-configured in `docker-compose.services.yml` as `mirage-service`.

```bash
# 1. Build the image from the MIRAGE repository
cd /path/to/mirage-repo
docker build -t openmedlab/mirage-service:latest .

# 2. Start the service (joins the OpenMedLab network automatically)
docker compose -f docker-compose.yml -f docker-compose.services.yml up -d mirage-service

# 3. Register (if not already seeded)
docker compose exec backend-openmedlab python manage.py register_mirage \
  --url http://mirage-service:8000 --update

# 4. Verify health
curl http://localhost:8010/health
```

CPU-only mode: set `DEVICE=cpu` in `docker-compose.services.yml` and remove the `deploy.resources` block.

### Dispatch flow (Celery mode)

1. `POST /api/ai-analysis/tasks/` creates an `AnalysisTask`
2. Celery task `dispatch_ai_job` calls `MirageConnector.dispatch_job(task)`
3. Connector sends `POST /analyze` to MIRAGE service
4. Celery task `poll_mirage_job_status` polls `GET /jobs/{id}` every 5 seconds (max 60 attempts = 5 min)
5. On completion, results are stored in `AnalysisTask.result_metadata`

### Parameters

```json
{
  "task_type": "segmentation",
  "modality": "bscan",
  "model_size": "base",
  "output_destination": "/media/ai_results/..."
}
```

| Parameter | Values | Default | Required |
|-----------|--------|---------|----------|
| `task_type` | `feature_extraction`, `segmentation`, `classification` | — | Yes |
| `modality` | `bscan`, `slo`, `bscanlayermap` | — | Yes |
| `model_size` | `base`, `large` | `base` | No |
| `output_destination` | S3 URI or local path | Auto-generated | No |

### Troubleshooting

- **Job stays in DISPATCHED**: MIRAGE service unreachable. Check `docker compose logs mirage-api-server` and verify the endpoint URL in the database.
- **Job times out (TIMEOUT)**: Model loading can take minutes on first call. Increase `timeout_seconds` or pre-load the model via `POST /models/base/load`.
- **Image modality warning**: JPEG/PNG uploads without DICOM metadata get `UNKNOWN` modality. The warning is informational — analysis proceeds normally.

---

## PICAI (Prostate Cancer Detection)

**Challenge:** [PI-CAI Grand Challenge](https://pi-cai.grand-challenge.org/)
**Authors:** Bosma, Saha, Huisman — Radboud University Medical Center

### What it does

nnU-Net 5-fold ensemble for clinically significant prostate cancer detection and segmentation on bi-parametric MRI (T2W + ADC, optional HBV).

### Service requirements

PICAI runs as a gRPC model service behind the orchestrator. It requires `USE_ORCHESTRATOR=True`.

**Expected gRPC contract** (defined in `protos/model_service.proto`):

| RPC | Description |
|-----|-------------|
| `RunInference(InferenceRequest)` | Run detection on provided images |
| `GetModelInfo(ModelInfoRequest)` | Return model capabilities |
| `HealthCheck(HealthCheckRequest)` | Liveness probe |

### Running PICAI

The service is pre-configured in `docker-compose.services.yml` as `picai-service`. PICAI uses gRPC through the orchestrator, so you must enable orchestrator mode.

```bash
# 1. Build the image from the PICAI repository
cd /path/to/picai-repo
docker build -t openmedlab/picai-service:latest .

# 2. Enable orchestrator mode in docker-compose.yml
#    Change USE_ORCHESTRATOR=False → USE_ORCHESTRATOR=True
#    under backend-openmedlab environment

# 3. Start orchestrator + PICAI service
docker compose -f docker-compose.yml -f docker-compose.services.yml up -d \
  orchestrator-openmedlab picai-service

# 4. Verify the orchestrator sees PICAI
docker compose logs orchestrator-openmedlab | grep picai
```

The orchestrator config at `app/orchestrator/config/models.yaml` already includes PICAI pointing to `picai-service:50051`.

### Parameters

```json
{
  "adc_image_id": 124,
  "hbv_image_id": 125,
  "output_format": "nii.gz",
  "ensemble_folds": 5
}
```

| Parameter | Values | Default | Required |
|-----------|--------|---------|----------|
| `adc_image_id` | MedicalImage ID | — | Yes |
| `hbv_image_id` | MedicalImage ID | — | No |
| `output_format` | `mha`, `nifti`, `nii.gz` | `nii.gz` | No |
| `ensemble_folds` | 1–5 | 5 | No |

### Dispatch flow (Orchestrator mode)

1. `POST /api/ai-analysis/tasks/` creates an `AnalysisTask`
2. `OrchestratorClient.submit_job()` sends gRPC `SubmitJob` to orchestrator (:50050)
3. Orchestrator enqueues job in Redis, worker picks it up
4. Worker calls `RunInference` on `picai-service:50051` via gRPC
5. Celery periodic task `sync_orchestrator_status` polls the orchestrator every 5 seconds
6. Task status is updated in the database and broadcast to the frontend

---

## CheXNet (Chest X-ray Classification)

**Paper:** Rajpurkar et al., _CheXNet: Radiologist-Level Pneumonia Detection_ — Stanford ML Group

### What it does

121-layer DenseNet trained on ChestX-ray14. Classifies 14 thoracic pathologies and optionally returns class activation map (CAM) heatmaps.

**Pathologies:** Atelectasis, Cardiomegaly, Consolidation, Edema, Effusion, Emphysema, Fibrosis, Hernia, Infiltration, Mass, Nodule, Pleural Thickening, Pneumonia, Pneumothorax.

### Service requirements

CheXNet runs as a standalone HTTP service (same pattern as MIRAGE).

**Expected API contract:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/classify` | Submit classification job |
| GET | `/health` | Health check |

### Running CheXNet

The service is pre-configured in `docker-compose.services.yml` as `chexnet-service`.

```bash
# 1. Build the image from the CheXNet repository
cd /path/to/chexnet-repo
docker build -t openmedlab/chexnet-service:latest .

# 2. Start the service
docker compose -f docker-compose.yml -f docker-compose.services.yml up -d chexnet-service

# 3. Verify health
curl http://localhost:8011/health
```

The service receives the webhook callback URL from the connector (pointing to `http://backend-openmedlab:3080`), so no extra configuration is needed for result delivery.

### Parameters

```json
{
  "threshold": 0.5,
  "return_heatmap": true
}
```

| Parameter | Values | Default | Required |
|-----------|--------|---------|----------|
| `threshold` | 0.0–1.0 | 0.5 | No |
| `return_heatmap` | Boolean | `false` | No |

### Dispatch flow (Celery mode)

1. `POST /api/ai-analysis/tasks/` creates an `AnalysisTask`
2. Celery task `dispatch_ai_job` calls `CheXNetConnector.dispatch_job(task)`
3. Connector sends `POST /classify` to CheXNet service with image path and webhook URL
4. CheXNet processes the image and POSTs results to `POST /api/ai-analysis/webhook/{task_id}/`
5. `WebhookHandler` validates the secret and updates the task

---

## Adding a New Model

### 1. Create the connector

Create `app/backend/ai_analysis/connectors/your_model.py`:

```python
from .base import BaseAIConnector

class YourModelConnector(BaseAIConnector):

    def dispatch_job(self, task):
        """Send the job to your model's API."""
        payload = self.build_base_payload(task)
        # Add model-specific fields to payload
        response = requests.post(
            f"{task.model.endpoint_url}/predict",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return {
            'service_job_id': data['job_id'],
            'status': 'queued',
        }

    def poll_job_status(self, task):
        """Poll for results (if no webhook support)."""
        response = requests.get(
            f"{task.model.endpoint_url}/jobs/{task.service_job_id}",
            timeout=10,
        )
        return response.json()
```

### 2. Register the model

Create a management command or add to `seed_ai_models.py`:

```python
AIModel.objects.update_or_create(
    key='your-model-v1',
    defaults={
        'name': 'Your Model',
        'connector_class': 'ai_analysis.connectors.your_model.YourModelConnector',
        'endpoint_url': 'http://your-model-service:8000',
        'model_type': 'classification',
        'supported_modalities': ['CT', 'MR'],
        'timeout_seconds': 300,
        'max_retries': 3,
        'is_active': True,
    },
)
```

### 3. Add polling (if needed)

If your model doesn't support webhooks, add a polling task in `ai_analysis/tasks.py` following the `poll_mirage_job_status` pattern, and trigger it from `dispatch_ai_job` after dispatch.

### 4. Add Docker service

Add the model service to `docker-compose.services.yml` following the existing patterns. Key requirements:

```yaml
your-model-service:
  image: openmedlab/your-model:latest
  volumes:
    - ./data/media:/var/www/app/backend/media:ro  # Same path the connector expects
  networks:
    - app-network                                  # Joins the main stack network
```

The `:ro` (read-only) mount is sufficient for inference. If your model writes results to the media volume, remove `:ro`.

---

## Monitoring & Debugging

### Check task status from the shell

```bash
docker compose exec backend-openmedlab python manage.py shell -c "
from ai_analysis.models import AnalysisTask
for t in AnalysisTask.objects.order_by('-created_at')[:5]:
    print(f'{t.id}  {t.status:12}  {t.model.key:15}  celery={t.celery_task_id}  svc={t.service_job_id}  orch={t.orchestrator_job_id}')
"
```

### Check Celery worker logs

```bash
docker compose logs -f celery-worker-openmedlab
```

### Check orchestrator logs (if enabled)

```bash
docker compose logs -f orchestrator-openmedlab
```

### Common issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Task stays PENDING | Celery worker not consuming `ai_jobs` queue | Check worker is running and queue routing in settings |
| Task stays DISPATCHED | Model service unreachable or not running | Verify `endpoint_url`, check service logs |
| Task goes to TIMEOUT | Service took longer than `timeout_seconds` | Increase timeout or check service performance |
| Task goes to FAILED | Service returned an error | Check `error_message` field on the task |
| Job not on Monitor | Frontend polling interval too long or filter mismatch | Check scope/status filters, verify task belongs to logged-in user |
| 400 on task creation | Validation error (missing params, inactive model) | Check `detail` field in error response |

### Verify the full pipeline

```bash
# 1. Confirm models are registered
docker compose exec backend-openmedlab python manage.py shell -c "
from ai_analysis.models import AIModel
print(AIModel.objects.filter(is_active=True).values_list('key', 'endpoint_url'))
"

# 2. Confirm Celery worker is running and listening on ai_jobs
docker compose exec celery-worker-openmedlab celery -A backend inspect active_queues

# 3. Confirm Redis is reachable
docker compose exec redis-openmedlab redis-cli ping

# 4. (Orchestrator mode) Confirm gRPC server is up
docker compose exec orchestrator-openmedlab python -c "
import grpc
from orchestrator_pb2_grpc import OrchestratorServiceStub
from orchestrator_pb2 import HealthCheckRequest
channel = grpc.insecure_channel('localhost:50050')
stub = OrchestratorServiceStub(channel)
print(stub.HealthCheck(HealthCheckRequest()))
"
```

---

## Configuration Reference

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_ORCHESTRATOR` | `False` | `True` to route jobs through the gRPC orchestrator |
| `ORCHESTRATOR_HOST` | `orchestrator-openmedlab` | Orchestrator hostname |
| `ORCHESTRATOR_PORT` | `50050` | Orchestrator gRPC port |
| `ORCHESTRATOR_POLL_INTERVAL` | `5` | Seconds between orchestrator status syncs |
| `CELERY_BROKER_URL` | `redis://redis-openmedlab:6379/0` | Redis broker for Celery |
| `AI_TASK_DEFAULT_TIMEOUT` | `1800` | Default task timeout in seconds |
| `AI_TASK_CLEANUP_DAYS` | `30` | Days before terminal tasks are deleted |
| `WEBSOCKET_BASED_TRACKING` | `False` | `True` for WebSocket live updates on Monitor |
| `MONITOR_POLL_INTERVAL` | `10` | Seconds between Monitor page polls |

### Celery queues

| Queue | Tasks |
|-------|-------|
| `ai_jobs` | `dispatch_ai_job`, `poll_mirage_job_status`, `retry_failed_task` |
| `monitoring` | `check_task_timeouts`, `cleanup_old_tasks`, `sync_orchestrator_status` |
| `default` | Everything else |

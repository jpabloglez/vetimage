# OpenSpec: Medical AI Analysis Orchestrator (MAIO)

| Metadata | Details |
| --- | --- |
| **Project Name** | MAIO (Multimodal AI Orchestrator) |
| **Version** | 0.1.0 (Draft) |
| **Status** | Proposed |
| **Target Infrastructure** | AWS (ECS, S3, EC2/GPU) |
| **Core Stack** | Django, React, Celery, Docker, FastAPI |

---

## 1. Executive Summary

The objective is to build a scalable, modular platform capable of ingesting medical imaging data (MRI, CT, etc.) and executing various AI models for analysis. The system decouples the **Control Plane** (Web App) from the **Compute Plane** (AI Models) to ensure stability, scalability, and the ability to integrate heterogeneous research models (e.g., PyTorch Geometric, TensorFlow) without dependency conflicts.

## 2. System Architecture

The architecture follows an **Asynchronous Microservices Pattern**. The Core Application acts as the orchestrator, dispatching jobs to specialized containers running on AWS ECS.

### 2.1 High-Level Data Flow

1. **Ingestion:** User uploads DICOM/NIfTI images via React Frontend  S3 Bucket (`/raw`).
2. **Dispatch:** Django creates a `Task` record and pushes a job to the Celery Queue.
3. **Routing:** The Celery Worker identifies the required AI Model (e.g., MIRAGE) and sends an HTTP payload to the corresponding ECS Service.
4. **Processing:** The AI Container (FastAPI) acknowledges the request, downloads data from S3, processes it on GPU, and uploads results to S3 (`/processed`).
5. **Completion:** The AI Container notifies Django (via Webhook) or Django polls for completion.
6. **Visualization:** Frontend retrieves the result URL and renders it.

---

## 3. Component Specifications

### 3.1 The Control Plane (Django Core)

This component manages users, data, and the orchestration logic.

**Data Models (Abstracted):**

```python
# Core logic for strategy pattern
class AIModel(models.Model):
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=50, unique=True) # e.g., 'mirage-v1'
    endpoint_url = models.URLField() # Internal DNS in AWS ECS
    is_active = models.BooleanField(default=True)

class AnalysisTask(models.Model):
    STATUS_CHOICES = [('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed')]
    
    input_image = models.ForeignKey('MedicalImage', on_delete=models.CASCADE)
    model = models.ForeignKey(AIModel, on_delete=models.SET_NULL)
    status = models.CharField(choices=STATUS_CHOICES, default='PENDING')
    result_s3_path = models.CharField(max_length=255, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

```

**Connector Interface (Strategy Pattern):**
The application must implement a base connector class to standardize interactions with different containers.

* `dispatch_job(payload: dict) -> job_id`
* `check_status(job_id) -> status`
* `get_results(job_id) -> result_data`

### 3.2 The Compute Plane (AI Microservices)

Each AI model runs as an isolated Docker container exposing a lightweight HTTP API (FastAPI).

**Reference Implementation: MIRAGE Service**

* **Base Image:** `pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime`
* **Hardware Req:** NVIDIA GPU (AWS `g4dn` instance family).
* **Dependencies:** `torch-geometric`, `scikit-image`, `nibabel`.

**API Contract (Internal Microservice):**

* **Endpoint:** `POST /predict`
* **Payload:**
```json
{
  "task_id": "uuid-string",
  "s3_bucket": "med-images-bucket",
  "source_key": "raw/patient_01/t1.nii.gz",
  "target_key": "raw/patient_01/template.nii.gz",
  "parameters": {
    "modality": "t1",
    "landmarks": false
  }
}

```


* **Response (Immediate):**
```json
{
  "status": "queued",
  "service_job_id": "internal-id-123"
}

```



---

## 4. Infrastructure & Security (AWS)

### 4.1 Storage (S3)

A single S3 bucket with strict prefix separation and lifecycle policies.

* `/uploads`: Temporary storage for user uploads (Lifecycle: Delete after 24h if not processed).
* `/datasets`: Permanent storage for referenced datasets.
* `/results`: Output from AI models.

### 4.2 Networking (VPC)

* **Public Subnet:** Load Balancer (ALB) for the Django Web App.
* **Private Subnet:** ECS Tasks (Django, Redis, AI Containers) and RDS Database.
* **Security Groups:** AI Containers accept traffic *only* from the Django Security Group on port 8000.

### 4.3 IAM Roles

* **TaskExecutionRole:** Allows ECS to pull images from ECR and send logs to CloudWatch.
* **TaskRole:** Specific permission for the AI Container to run `s3:GetObject` and `s3:PutObject`. **Crucial:** Do not hardcode AWS keys in the Docker container. Use IAM Role injection.

---

## 5. Implementation Roadmap

### Phase 1: Containerization of Reference Model (MIRAGE)

1. Fork MIRAGE repository.
2. Create `Dockerfile` optimizing for Layer Caching (install PyTorch Geometric before copying source code).
3. Write `ai_service.py` wrapper using FastAPI.
4. Test locally using `docker-compose` with GPU support (`--gpus all`).

### Phase 2: Core Connector Implementation

1. Implement `Celery` task queue in Django.
2. Create the `BaseAIConnector` abstract class.
3. Implement `MirageConnector` subclass using `requests` library to hit the local Docker container.
4. Validate S3 upload/download flow locally using `MinIO` or a dev S3 bucket.

### Phase 3: Cloud Deployment (AWS)

1. Push Docker images to **AWS ECR**.
2. Provision **ECS Cluster** (EC2 Launch Type for GPU support).
3. Define **Task Definitions** mapping ports and mounting volumes (if ephemeral storage is needed).
4. Deploy Django and AI Service.

### Phase 4: Lifecycle Management

1. Implement "Result Polling" or "Webhook Receiver" in Django to update Task status in the UI.
2. Implement error handling (e.g., if OOM error occurs in GPU, catch it and update DB status to `FAILED`).

---

## 6. Verification & Success Criteria

1. **Isolation:** Failure in the MIRAGE container must not crash the Django Web App.
2. **Scalability:** The system must handle 5 concurrent requests without timeout (queueing them via Celery).
3. **Reproducibility:** The output of the containerized model must match the local execution of the original MIRAGE code bit-for-bit.
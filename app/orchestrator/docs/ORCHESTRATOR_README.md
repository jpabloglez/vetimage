# ML Model Orchestrator

A high-performance gRPC-based orchestrator service that routes machine learning inference requests from web applications to appropriate model services. Built with Redis for persistent job queuing, designed for reliability and scalability.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Overview

The ML Model Orchestrator is a production-ready service that:

- **Receives inference requests** from user-facing applications via gRPC
- **Routes requests** to appropriate ML model services based on task type and capabilities
- **Manages job queue** using Redis for persistence and reliability
- **Monitors health** of model services with circuit breaker pattern
- **Supports multiple models** with extensible architecture
- **Handles both S3 and local file paths** for inputs and outputs

### Why gRPC?

- **Performance**: Binary protocol with efficient serialization
- **Streaming**: Support for long-running operations
- **Strong typing**: Protocol Buffers provide clear contracts
- **Multi-language**: Easy to generate clients in any language

## Architecture

```
┌─────────────────┐
│   Web App       │
│  (User-facing)  │
└────────┬────────┘
         │ gRPC
         v
┌─────────────────────────────────────────────────┐
│         Orchestrator Service                    │
│  ┌──────────────┐  ┌──────────────┐             │
│  │ gRPC Server  │  │ Model Router │             │
│  └──────┬───────┘  └──────┬───────┘             │
│         │                 │                     │
│  ┌──────v─────────────────v────────┐            │
│  │     Job Queue Manager (Redis)   │            │
│  └─────────────────────────────────┘            │
│         │                                       │
│  ┌──────v─────────────────────────────┐         │
│  │  Model Registry & Health Monitor   │         │
│  └────────────────────────────────────┘         │
└────────────┬────────────────┬──────────────────┘
             │ gRPC           │ gRPC
             v                v
     ┌───────────────┐  ┌───────────────┐
     │ MIRAGE Model  │  │  Future Model │
     │   Service     │  │   Service     │
     └───────────────┘  └───────────────┘
```

### Key Components

1. **gRPC Server** (`orchestrator/grpc_server.py`)
   - Accepts requests from clients
   - Validates input and selects appropriate model
   - Returns job IDs immediately for asynchronous processing

2. **Job Queue Manager** (`orchestrator/job_queue.py`)
   - Redis-based persistent queue (survives restarts)
   - Job state management (queued → processing → completed/failed)
   - TTL-based cleanup for old jobs

3. **Model Registry** (`orchestrator/model_registry.py`)
   - Dynamic model discovery from configuration
   - Health checking with Redis caching
   - Circuit breaker pattern for fault tolerance
   - Intelligent routing based on capabilities

4. **Worker Pool** (`orchestrator/worker.py`)
   - Background threads processing jobs
   - Exponential backoff retry logic
   - Timeout handling

5. **Health Monitor** (`orchestrator/health_monitor.py`)
   - Periodic health checks of model services
   - Job timeout detection and cleanup

## Features

### Core Capabilities

- **Asynchronous Processing**: Submit jobs and poll for results
- **Job Persistence**: Redis-based queue survives service restarts
- **Health Monitoring**: Automatic health checking with configurable intervals
- **Circuit Breaker**: Prevents cascade failures from unhealthy services
- **Retry Logic**: Exponential backoff for transient failures
- **Security**: Path validation prevents directory traversal attacks
- **Multi-Model Support**: Extensible to support any number of model services
- **Metrics**: Prometheus-compatible metrics endpoint

### Supported Tasks

- **Segmentation**: OCT layer segmentation, lesion detection
- **Classification**: Disease classification, quality assessment
- **Feature Extraction**: Embeddings, biomarkers

### Supported Input Sources

- **S3 URIs**: `s3://bucket/path/to/file.npy`
- **Local Paths**: `/app/data/images/file.npy` (whitelisted directories)

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- NVIDIA Docker runtime (for GPU support)
- AWS credentials (if using S3)

## Quick Start

### 1. Build Services

```bash
# Build all services (orchestrator + MIRAGE + Redis)
docker-compose -f docker-compose-orchestrator.yml build
```

### 2. Start Services

```bash
# Start in background
docker-compose -f docker-compose-orchestrator.yml up -d

# Or start with logs
docker-compose -f docker-compose-orchestrator.yml up
```

### 3. Check Health

```bash
# Using Python test client
python tests/test_orchestrator_client.py --skip-models --output /tmp/test

# Using grpcurl (if installed)
grpcurl -plaintext localhost:50050 orchestrator.OrchestratorService/HealthCheck
```

### 4. Submit a Test Job

```bash
# Segmentation task
python tests/test_orchestrator_client.py \
    --task segmentation \
    --image tests/artifacts/DME-2556938-1.npy \
    --modality bscan \
    --output /app/MIRAGE/_test_data/orchestrator_results

# Classification task
python tests/test_orchestrator_client.py \
    --task classification \
    --image tests/artifacts/DME-2556938-1.npy \
    --modality bscan \
    --num-classes 3 \
    --class-names Normal DME AMD \
    --output /app/MIRAGE/_test_data/orchestrator_results
```

### 5. Monitor Logs

```bash
# All services
docker-compose -f docker-compose-orchestrator.yml logs -f

# Orchestrator only
docker-compose -f docker-compose-orchestrator.yml logs -f orchestrator

# MIRAGE service only
docker-compose -f docker-compose-orchestrator.yml logs -f mirage-service
```

## Configuration

### Environment Variables

Configure the orchestrator via environment variables in `docker-compose-orchestrator.yml`:

```yaml
environment:
  # Redis connection
  - REDIS_HOST=redis                # Redis hostname
  - REDIS_PORT=6379                 # Redis port

  # gRPC server
  - GRPC_PORT=50050                 # Orchestrator gRPC port

  # Metrics
  - METRICS_PORT=8080               # Prometheus metrics port

  # Workers
  - NUM_WORKERS=1                   # Number of background workers

  # Health monitoring
  - HEALTH_CHECK_INTERVAL=30        # Model health check interval (seconds)

  # Configuration
  - MODELS_CONFIG=orchestrator/config/models.yaml  # Model registry config

  # Logging
  - LOG_LEVEL=INFO                  # Log level (DEBUG, INFO, WARNING, ERROR)
```

### Model Configuration

Edit `orchestrator/config/models.yaml` to add or modify models:

```yaml
models:
  - name: mirage
    version: "1.0"
    endpoint: "mirage-service:50051"
    supported_tasks:
      - segmentation
      - classification
      - feature_extraction
    supported_modalities:
      - bscan
      - slo
      - bscanlayermap
    model_sizes:
      - base
      - large
    health_check_interval: 30
    timeout: 300
    auto_launch: false

  # Add more models here
  # - name: my-model
  #   version: "1.0"
  #   endpoint: "my-model-service:50051"
  #   ...
```

### Security Configuration

File path whitelist is configured in `orchestrator/file_handler.py`:

```python
ALLOWED_LOCAL_PATHS = [
    '/app/data',
    '/app/MIRAGE/__datasets',
    '/app/MIRAGE/_test_data',
    '/tmp',
    '/app/local_images'
]
```

To add more directories, modify this list and rebuild the orchestrator image.

## Usage

### Python Client Example

```python
import grpc
from orchestrator import orchestrator_pb2, orchestrator_pb2_grpc

# Connect to orchestrator
channel = grpc.insecure_channel('localhost:50050')
stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)

# Submit job
request = orchestrator_pb2.SubmitJobRequest(
    images=[
        orchestrator_pb2.ImageInput(
            modality='bscan',
            source='/path/to/image.npy'
        )
    ],
    task_type='segmentation',
    model_size='base',
    output_destination='/output/path'
)

response = stub.SubmitJob(request)
job_id = response.job_id
print(f"Job submitted: {job_id}")

# Poll for status
import time
while True:
    status_request = orchestrator_pb2.GetJobStatusRequest(job_id=job_id)
    status = stub.GetJobStatus(status_request)

    if status.status == orchestrator_pb2.JOB_STATUS_COMPLETED:
        print(f"Job completed! Output: {status.output_uri}")
        break
    elif status.status == orchestrator_pb2.JOB_STATUS_FAILED:
        print(f"Job failed: {status.error_message}")
        break

    time.sleep(2)

channel.close()
```

### Using S3 Paths

```python
# Input from S3
request = orchestrator_pb2.SubmitJobRequest(
    images=[
        orchestrator_pb2.ImageInput(
            modality='bscan',
            source='s3://my-bucket/input/image.npy'
        )
    ],
    task_type='segmentation',
    output_destination='s3://my-bucket/output/'
)
```

### Classification with Custom Classes

```python
request = orchestrator_pb2.SubmitJobRequest(
    images=[...],
    task_type='classification',
    num_classes=3,
    class_names=['Normal', 'DME', 'AMD'],
    output_destination='/output/path'
)
```

### Listing Available Models

```python
request = orchestrator_pb2.ListModelsRequest(only_healthy=True)
response = stub.ListModels(request)

for model in response.models:
    print(f"Model: {model.name} (v{model.version})")
    print(f"  Endpoint: {model.endpoint}")
    print(f"  Tasks: {', '.join(model.supported_tasks)}")
    print(f"  Healthy: {model.is_healthy}")
```

## API Reference

### gRPC Service: OrchestratorService

#### SubmitJob

Submit an inference job for asynchronous processing.

**Request:**
```protobuf
message SubmitJobRequest {
  repeated ImageInput images = 1;
  string task_type = 2;
  string model_name = 3;              // Optional
  string model_size = 4;              // "base" or "large"
  string output_destination = 5;
  string output_format = 6;           // Optional: "npy", "png", "jpg"
  int32 num_classes = 7;              // For classification
  repeated string class_names = 8;    // For classification
  map<string, string> metadata = 9;   // Optional metadata
}
```

**Response:**
```protobuf
message SubmitJobResponse {
  string job_id = 1;
  JobStatus status = 2;
  string message = 3;
}
```

**Errors:**
- `INVALID_ARGUMENT`: Invalid input (empty images, unsupported task type, invalid paths)
- `FAILED_PRECONDITION`: No healthy model available
- `INTERNAL`: Redis connection error

#### GetJobStatus

Get the current status of a job.

**Request:**
```protobuf
message GetJobStatusRequest {
  string job_id = 1;
}
```

**Response:**
```protobuf
message JobStatusResponse {
  string job_id = 1;
  JobStatus status = 2;
  string model_service = 3;
  string output_uri = 4;
  repeated string output_keys = 5;
  ErrorCode error_code = 6;
  string error_message = 7;
  int64 created_at = 8;
  int64 started_at = 9;
  int64 completed_at = 10;
}
```

**Status Values:**
- `JOB_STATUS_UNKNOWN`: Invalid job ID
- `JOB_STATUS_QUEUED`: Waiting to be processed
- `JOB_STATUS_PROCESSING`: Currently being processed
- `JOB_STATUS_COMPLETED`: Successfully completed
- `JOB_STATUS_FAILED`: Failed with error

#### ListModels

List available model services and their capabilities.

**Request:**
```protobuf
message ListModelsRequest {
  bool only_healthy = 1;  // Filter to only healthy models
}
```

**Response:**
```protobuf
message ListModelsResponse {
  repeated ModelInfo models = 1;
}

message ModelInfo {
  string name = 1;
  string version = 2;
  string endpoint = 3;
  repeated string supported_tasks = 4;
  repeated string supported_modalities = 5;
  bool is_healthy = 6;
}
```

#### HealthCheck

Check orchestrator and model service health.

**Request:**
```protobuf
message HealthCheckRequest {}
```

**Response:**
```protobuf
message HealthCheckResponse {
  bool healthy = 1;
  string version = 2;
  int32 queued_jobs = 3;
  int32 active_jobs = 4;
  repeated ModelHealthInfo model_health = 5;
}
```

## Monitoring

### Prometheus Metrics

Metrics are exposed on port 8080 at `/metrics`:

```bash
curl http://localhost:8080/metrics
```

**Key Metrics:**

- `orchestrator_jobs_submitted_total{model_name, task_type}` - Total jobs submitted
- `orchestrator_jobs_completed_total{model_name, task_type, status}` - Total jobs completed
- `orchestrator_jobs_failed_total{model_name, error_code}` - Total jobs failed
- `orchestrator_job_processing_seconds{model_name, task_type}` - Job processing time histogram
- `orchestrator_queue_depth{status}` - Current queue depth by status
- `orchestrator_model_service_health{model_name}` - Model health (1=healthy, 0=unhealthy)

### Logging

Structured JSON logging to stdout:

```json
{
  "timestamp": "2025-01-15T10:30:00.000Z",
  "level": "INFO",
  "event_type": "job_started",
  "job_id": "abc123",
  "model_service": "mirage",
  "task_type": "segmentation"
}
```

### Redis Monitoring

Connect to Redis CLI:

```bash
docker exec -it orchestrator-redis redis-cli

# Check queue depth
LLEN orchestrator:queue:pending

# Check job status
HGETALL orchestrator:job:<job_id>

# List all jobs by status
ZRANGE orchestrator:jobs:by_status:completed 0 -1 WITHSCORES
```

## Troubleshooting

### Job Stuck in Queued State

**Symptoms:** Job status remains `QUEUED` for extended period

**Possible Causes:**
1. Worker threads not running
2. Model service unhealthy
3. Redis connection issues

**Solutions:**
```bash
# Check worker logs
docker-compose -f docker-compose-orchestrator.yml logs orchestrator | grep worker

# Check model health
python tests/test_orchestrator_client.py --skip-models --output /tmp

# Check Redis
docker exec -it orchestrator-redis redis-cli ping
```

### Job Failed with DEADLINE_EXCEEDED

**Symptoms:** Job fails with timeout error

**Possible Causes:**
1. Model taking too long to process
2. Model service hung
3. Timeout too short

**Solutions:**
```bash
# Increase timeout in models.yaml
timeout: 600  # 10 minutes

# Check model service logs
docker-compose -f docker-compose-orchestrator.yml logs mirage-service

# Restart model service
docker-compose -f docker-compose-orchestrator.yml restart mirage-service
```

### gRPC Connection Refused

**Symptoms:** Client cannot connect to orchestrator

**Possible Causes:**
1. Orchestrator not running
2. Port not exposed
3. Firewall blocking

**Solutions:**
```bash
# Check orchestrator is running
docker-compose -f docker-compose-orchestrator.yml ps

# Check port is listening
netstat -an | grep 50050

# Test from inside container
docker exec -it ml-orchestrator python -c "import grpc; grpc.insecure_channel('localhost:50050')"
```

### Model Service Unhealthy

**Symptoms:** ListModels shows `is_healthy: false`

**Possible Causes:**
1. Model service crashed
2. Model loading failed
3. GPU out of memory

**Solutions:**
```bash
# Check model service health
curl http://localhost:8000/health

# Check GPU memory
docker exec mirage-model-service nvidia-smi

# Restart model service
docker-compose -f docker-compose-orchestrator.yml restart mirage-service
```

### Redis Connection Errors

**Symptoms:** Orchestrator logs show Redis connection failures

**Solutions:**
```bash
# Check Redis is running
docker-compose -f docker-compose-orchestrator.yml ps redis

# Check Redis logs
docker-compose -f docker-compose-orchestrator.yml logs redis

# Restart Redis (jobs will be lost)
docker-compose -f docker-compose-orchestrator.yml restart redis
```

## Development

### Project Structure

```
medimaging/
├── orchestrator/              # Orchestrator service
│   ├── __init__.py
│   ├── main.py               # Entry point
│   ├── grpc_server.py        # gRPC service implementation
│   ├── job_queue.py          # Redis job queue
│   ├── model_registry.py     # Model discovery & routing
│   ├── worker.py             # Background job processor
│   ├── health_monitor.py     # Health monitoring
│   ├── file_handler.py       # Path validation
│   ├── ec2_launcher.py       # EC2 launcher (stub)
│   ├── config/
│   │   └── models.yaml       # Model registry
│   ├── requirements.txt
│   └── Dockerfile
│
├── protos/                    # Protocol Buffer definitions
│   ├── orchestrator.proto    # Orchestrator service
│   ├── model_service.proto   # Model service interface
│   └── Makefile              # Proto compilation
│
├── MIRAGE/
│   ├── grpc_adapter.py       # gRPC wrapper for FastAPI
│   └── supervisord.conf      # Multi-service management
│
└── tests/
    └── test_orchestrator_client.py  # Test client
```

### Compiling Proto Files

```bash
cd protos
make proto
```

This generates Python files in `orchestrator/`:
- `orchestrator_pb2.py` - Message classes
- `orchestrator_pb2_grpc.py` - Service stubs
- `model_service_pb2.py` - Message classes
- `model_service_pb2_grpc.py` - Service stubs

### Running Tests

```bash
# Unit tests (TODO: implement)
pytest tests/unit/

# Integration test with live services
python tests/test_orchestrator_client.py \
    --task segmentation \
    --image tests/artifacts/DME-2556938-1.npy \
    --modality bscan \
    --output /tmp/test
```

### Adding a New Model Service

1. **Implement gRPC service** following `protos/model_service.proto`
2. **Add to models.yaml**:
   ```yaml
   - name: my-model
     version: "1.0"
     endpoint: "my-model:50051"
     supported_tasks: [segmentation]
     supported_modalities: [bscan]
     model_sizes: [base]
     health_check_interval: 30
     timeout: 300
   ```
3. **Add to docker-compose**:
   ```yaml
   my-model:
     build: ./my-model
     ports: ["50052:50051"]
     networks: [orchestrator_network]
   ```
4. **Restart orchestrator** to load new config

### Debugging

Enable debug logging:

```yaml
environment:
  - LOG_LEVEL=DEBUG
```

Attach to running container:

```bash
docker exec -it ml-orchestrator bash
```

## Performance Tuning

### Worker Pool Size

Increase `NUM_WORKERS` for higher throughput:

```yaml
environment:
  - NUM_WORKERS=4  # Process 4 jobs concurrently
```

**Note:** Ensure model services can handle concurrent requests.

### Health Check Interval

Reduce frequency to lower overhead:

```yaml
# In models.yaml
health_check_interval: 60  # Check every 60 seconds
```

### Redis Connection Pool

Edit `orchestrator/main.py`:

```python
self.redis = redis.Redis(
    host=self.redis_host,
    port=self.redis_port,
    max_connections=20,  # Increase pool size
    decode_responses=True
)
```

### Job TTL

Configure how long completed jobs are retained:

```python
# In job_queue.py
COMPLETED_JOB_TTL = 86400  # 24 hours
FAILED_JOB_TTL = 86400     # 24 hours
```

## Future Enhancements

- [ ] Streaming RPC for progress updates
- [ ] EC2 auto-scaling implementation
- [ ] Authentication (API keys, JWT)
- [ ] Rate limiting per user
- [ ] Multi-region deployment
- [ ] Model versioning support
- [ ] Batch job submission
- [ ] Job scheduling (delayed execution)
- [ ] Web dashboard for job monitoring

## License

[Add license information]

## Support

For issues and questions:
- Check troubleshooting section above
- Review logs: `docker-compose -f docker-compose-orchestrator.yml logs`
- Check health: `python tests/test_orchestrator_client.py --skip-models --output /tmp`

## Acknowledgments

Built with:
- gRPC (https://grpc.io/)
- Redis (https://redis.io/)
- Protocol Buffers (https://protobuf.dev/)
- Prometheus (https://prometheus.io/)

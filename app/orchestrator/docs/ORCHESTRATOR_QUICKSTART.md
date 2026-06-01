# Orchestrator Quickstart Guide

Get the ML Model Orchestrator running in 5 minutes.

## Prerequisites

Check you have:

```bash
# Docker 20.10+
docker --version

# Docker Compose 2.0+
docker-compose --version

# NVIDIA Docker (for GPU)
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# AWS credentials (if using S3)
aws configure list
```

## Step 1: Download Model Weights

If you haven't already, download MIRAGE model weights:

```bash
# Create weights directory
mkdir -p data/weights

# Download base model
wget -P data/weights https://huggingface.co/PRIME-MIR/MIRAGE-OCT-base/resolve/main/MIRAGE_base_checkpoint.pth

# Or download large model
wget -P data/weights https://huggingface.co/PRIME-MIR/MIRAGE-OCT-large/resolve/main/MIRAGE_large_checkpoint.pth
```

## Step 2: Build Services

```bash
# Build all services (orchestrator, MIRAGE, Redis)
docker-compose -f docker-compose-orchestrator.yml build

# This takes 5-10 minutes on first build
```

## Step 3: Start Services

```bash
# Start all services in background
docker-compose -f docker-compose-orchestrator.yml up -d

# Check all services are running
docker-compose -f docker-compose-orchestrator.yml ps
```

You should see:
- `orchestrator-redis` - Running
- `ml-orchestrator` - Running
- `mirage-model-service` - Running

## Step 4: Verify Health

```bash
# Check orchestrator health
python tests/test_orchestrator_client.py \
    --skip-models \
    --skip-health \
    --image tests/artifacts/DME-2556938-1.npy \
    --output /tmp/test_output
```

If you see "Job completed successfully", everything is working!

## Step 5: Run Your First Job

### Segmentation

```bash
python tests/test_orchestrator_client.py \
    --task segmentation \
    --image tests/artifacts/DME-2556938-1.npy \
    --modality bscan \
    --output /app/MIRAGE/_test_data/orchestrator_results
```

### Classification

```bash
python tests/test_orchestrator_client.py \
    --task classification \
    --image tests/artifacts/DME-2556938-1.npy \
    --modality bscan \
    --num-classes 3 \
    --class-names Normal DME AMD \
    --output /app/MIRAGE/_test_data/orchestrator_results
```

### With S3

```bash
python tests/test_orchestrator_client.py \
    --task segmentation \
    --image s3://my-bucket/input/image.npy \
    --modality bscan \
    --output s3://my-bucket/output/
```

## Expected Output

You should see:

```
==============================================================
Health Check
==============================================================

ℹ Connected to orchestrator at localhost:50050
ℹ Orchestrator Version: 1.0.0
ℹ Overall Health: HEALTHY
ℹ Queued Jobs: 0
ℹ Active Jobs: 0

Model Services:
  - mirage: ✓ HEALTHY

✓ Orchestrator is healthy

==============================================================
Submit Job
==============================================================

ℹ Task: segmentation
ℹ Model: auto-select (base)
ℹ Images: 1
  - bscan: tests/artifacts/DME-2556938-1.npy
ℹ Output: /app/MIRAGE/_test_data/orchestrator_results
✓ Job submitted: abc123-def456-...

==============================================================
Polling Job abc123-def456-...
==============================================================

  Status: JOB_STATUS_PROCESSING (elapsed: 45s)
✓ Job completed!

Job Details:
  Job ID: abc123-def456-...
  Model: mirage
  Status: JOB_STATUS_COMPLETED
  Output URI: /app/MIRAGE/_test_data/orchestrator_results/abc123-def456-...
  Output Files:
    - segmentation_mask.npy
  Processing Time: 42.31s
```

## Viewing Results

Results are saved to the output directory:

```bash
# List output files
ls -lh /app/MIRAGE/_test_data/orchestrator_results/

# Or if running on host
docker exec mirage-model-service ls -lh /app/MIRAGE/_test_data/orchestrator_results/
```

## Monitoring

### View Logs

```bash
# All services
docker-compose -f docker-compose-orchestrator.yml logs -f

# Just orchestrator
docker-compose -f docker-compose-orchestrator.yml logs -f orchestrator

# Just MIRAGE
docker-compose -f docker-compose-orchestrator.yml logs -f mirage-service
```

### Check Metrics

```bash
# Prometheus metrics
curl http://localhost:8080/metrics
```

### Check Queue Status

```bash
# Connect to Redis
docker exec -it orchestrator-redis redis-cli

# Check pending jobs
LLEN orchestrator:queue:pending

# Check job details
HGETALL orchestrator:job:<job_id>
```

## Using from Python

Create a simple client:

```python
import grpc
from orchestrator import orchestrator_pb2, orchestrator_pb2_grpc

# Connect
channel = grpc.insecure_channel('localhost:50050')
stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)

# Submit job
request = orchestrator_pb2.SubmitJobRequest(
    images=[
        orchestrator_pb2.ImageInput(
            modality='bscan',
            source='tests/artifacts/DME-2556938-1.npy'
        )
    ],
    task_type='segmentation',
    model_size='base',
    output_destination='/app/MIRAGE/_test_data/results'
)

response = stub.SubmitJob(request)
print(f"Job ID: {response.job_id}")

# Poll for status
import time
while True:
    status = stub.GetJobStatus(
        orchestrator_pb2.GetJobStatusRequest(job_id=response.job_id)
    )

    if status.status == orchestrator_pb2.JOB_STATUS_COMPLETED:
        print(f"Complete! Output: {status.output_uri}")
        break
    elif status.status == orchestrator_pb2.JOB_STATUS_FAILED:
        print(f"Failed: {status.error_message}")
        break

    time.sleep(2)

channel.close()
```

## Stopping Services

```bash
# Stop all services
docker-compose -f docker-compose-orchestrator.yml down

# Stop and remove volumes (clears Redis queue)
docker-compose -f docker-compose-orchestrator.yml down -v
```

## Common Issues

### Port Already in Use

If you see "port is already allocated":

```bash
# Check what's using the port
lsof -i :50050
lsof -i :8000

# Stop conflicting services or change ports in docker-compose-orchestrator.yml
```

### MIRAGE Service Unhealthy

If MIRAGE shows as unhealthy:

```bash
# Check logs
docker-compose -f docker-compose-orchestrator.yml logs mirage-service

# Common issue: Model weights not found
# Solution: Download weights to data/weights/

# Restart service
docker-compose -f docker-compose-orchestrator.yml restart mirage-service
```

### Job Times Out

If jobs timeout:

```bash
# Increase timeout in orchestrator/config/models.yaml
timeout: 600  # 10 minutes

# Rebuild and restart
docker-compose -f docker-compose-orchestrator.yml up -d --build orchestrator
```

### GPU Not Available

If you see "CUDA not available":

```bash
# Check NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# If that fails, install nvidia-docker2:
# https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
```

## Next Steps

1. **Read the full documentation**: See `ORCHESTRATOR_README.md` for detailed API reference
2. **Add more models**: Edit `orchestrator/config/models.yaml`
3. **Integrate with your app**: Use the gRPC client in your application
4. **Monitor in production**: Set up Prometheus + Grafana
5. **Scale up**: Increase `NUM_WORKERS` for higher throughput

## Generating gRPC Client for Other Languages

### Python (already done)

Proto files are pre-compiled in the orchestrator image.

### Go

```bash
cd protos
protoc --go_out=. --go-grpc_out=. orchestrator.proto
```

### JavaScript/TypeScript

```bash
cd protos
npm install -g grpc-tools
grpc_tools_node_protoc --js_out=import_style=commonjs,binary:. --grpc_out=grpc_js:. orchestrator.proto
```

### Java

```bash
cd protos
protoc --java_out=. --grpc-java_out=. orchestrator.proto
```

See https://grpc.io/docs/languages/ for other languages.

## Support

- **Full documentation**: `ORCHESTRATOR_README.md`
- **Troubleshooting**: See README troubleshooting section
- **Logs**: `docker-compose -f docker-compose-orchestrator.yml logs`

## Architecture Overview

```
Web App → gRPC → Orchestrator → Redis Queue → Workers → Model Services (MIRAGE)
                      ↓
                 Health Monitor
                      ↓
                Model Registry
```

The orchestrator:
- Accepts gRPC requests
- Validates input and routes to appropriate model
- Queues jobs in Redis (persistent)
- Background workers process jobs
- Returns results via polling or streaming

For detailed architecture, see `ORCHESTRATOR_README.md`.

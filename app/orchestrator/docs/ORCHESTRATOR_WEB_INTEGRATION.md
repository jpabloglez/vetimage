# Orchestrator Web App Integration Guide

This guide explains how to deploy the orchestrator alongside your web application and implement job status display for end users.

## Deployment Architecture

### Recommended: Separate Services (Can be Same Server)

The orchestrator should be a **separate service** from the web app, but they **can run on the same physical server** if resources allow. Here's why:

```
┌─────────────────────────────────────────┐
│         Physical Server (Optional)       │
│                                          │
│  ┌────────────────┐  ┌────────────────┐ │
│  │   Web App      │  │  Orchestrator  │ │
│  │   (Port 3000)  │  │  (Port 50050)  │ │
│  │                │  │                │ │
│  │  - UI/Frontend │  │  - gRPC Server │ │
│  │  - REST API    │  │  - Job Queue   │ │
│  │  - Auth        │  │  - Workers     │ │
│  └────────┬───────┘  └────────┬───────┘ │
│           │                   │          │
│           └────── gRPC ───────┘          │
│                                          │
│  ┌────────────────┐  ┌────────────────┐ │
│  │     Redis      │  │ MIRAGE Service │ │
│  │  (Port 6379)   │  │ (Port 50051)   │ │
│  └────────────────┘  └────────────────┘ │
└─────────────────────────────────────────┘
```

### Benefits of Separation

1. **Independent Scaling**: Scale web app and orchestrator separately
2. **Resource Isolation**: Web app crashes don't affect job processing
3. **Different Tech Stacks**: Web app (Node.js/Python/Go) vs Orchestrator (Python)
4. **Easier Maintenance**: Update/restart services independently
5. **Security**: Orchestrator can be internal-only, web app public-facing

### Same Server is OK When:
- Small to medium workload
- Cost constraints (single server)
- Sufficient resources (CPU, RAM, GPU)
- Proper containerization (Docker)

## How Web App Displays Job Status

The orchestrator **provides complete APIs** for the web app to display job progress. Here are the integration patterns:

### Pattern 1: Polling (Simple, Recommended for MVP)

This is the simplest approach and works everywhere. The frontend periodically asks the backend for updates.

**Web App Backend (Node.js/TypeScript):**

```javascript
// Using @grpc/grpc-js
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';

// Load proto file
const PROTO_PATH = './protos/orchestrator.proto';
const packageDefinition = protoLoader.loadSync(PROTO_PATH);
const orchestrator = grpc.loadPackageDefinition(packageDefinition).orchestrator;

// Create client
const client = new orchestrator.OrchestratorService(
  'localhost:50050',
  grpc.credentials.createInsecure()
);

// Submit job
async function submitJob(userId, imageData, taskType) {
  return new Promise((resolve, reject) => {
    const request = {
      images: [{
        modality: 'bscan',
        source: imageData.path
      }],
      task_type: taskType,
      model_size: 'base',
      output_destination: `/app/results/${userId}`
    };

    client.SubmitJob(request, (error, response) => {
      if (error) {
        reject(error);
        return;
      }

      // Store job_id in database with user_id
      db.jobs.insert({
        user_id: userId,
        job_id: response.job_id,
        status: 'queued',
        task_type: taskType,
        created_at: new Date()
      });

      resolve(response.job_id);
    });
  });
}

// Poll job status (called by frontend every 2-5 seconds)
async function getJobStatus(jobId) {
  return new Promise((resolve, reject) => {
    const request = { job_id: jobId };

    client.GetJobStatus(request, async (error, response) => {
      if (error) {
        reject(error);
        return;
      }

      // Update database
      await db.jobs.update(jobId, {
        status: response.status,
        output_uri: response.output_uri,
        error_message: response.error_message,
        completed_at: response.completed_at ? new Date(response.completed_at) : null
      });

      resolve({
        status: statusToString(response.status),
        progress: calculateProgress(response),
        output_uri: response.output_uri,
        output_keys: response.output_keys,
        error_message: response.error_message,
        processing_time: response.completed_at && response.started_at
          ? (response.completed_at - response.started_at) / 1000
          : null
      });
    });
  });
}

// Helper function
function statusToString(status) {
  const statusMap = {
    0: 'UNKNOWN',
    1: 'QUEUED',
    2: 'PROCESSING',
    3: 'COMPLETED',
    4: 'FAILED'
  };
  return statusMap[status] || 'UNKNOWN';
}

function calculateProgress(response) {
  if (response.status === 3) return 100; // COMPLETED
  if (response.status === 4) return 0;   // FAILED
  if (response.status === 2) {
    // PROCESSING - estimate based on elapsed time
    const elapsed = Date.now() - response.started_at;
    return Math.min(90, Math.floor(elapsed / 1000)); // Cap at 90%
  }
  return 0; // QUEUED
}
```

**Web App REST API Endpoints:**

```javascript
// Express.js endpoints
const express = require('express');
const router = express.Router();

// Submit new job
router.post('/api/jobs', async (req, res) => {
  try {
    const { image_path, task_type } = req.body;
    const userId = req.user.id; // From auth middleware

    const jobId = await submitJob(userId, { path: image_path }, task_type);

    res.json({
      job_id: jobId,
      status: 'queued',
      message: 'Job submitted successfully'
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get job status
router.get('/api/jobs/:jobId/status', async (req, res) => {
  try {
    const status = await getJobStatus(req.params.jobId);
    res.json(status);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// List user's jobs
router.get('/api/jobs', async (req, res) => {
  const userId = req.user.id;
  const jobs = await db.jobs.findByUser(userId);
  res.json(jobs);
});

// Download results
router.get('/api/jobs/:jobId/results', async (req, res) => {
  const job = await db.jobs.findById(req.params.jobId);

  if (!job || job.status !== 'COMPLETED') {
    return res.status(404).json({ error: 'Results not available' });
  }

  // Stream file from output_uri
  const filePath = job.output_uri;
  res.download(filePath);
});

module.exports = router;
```

**Python/FastAPI Alternative:**

```python
from fastapi import FastAPI, HTTPException, Depends
import grpc
from orchestrator import orchestrator_pb2, orchestrator_pb2_grpc

app = FastAPI()

# Create gRPC client
channel = grpc.insecure_channel('localhost:50050')
orchestrator_stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)

@app.post("/api/jobs")
async def submit_job(image_path: str, task_type: str, user_id: str):
    request = orchestrator_pb2.SubmitJobRequest(
        images=[orchestrator_pb2.ImageInput(
            modality='bscan',
            source=image_path
        )],
        task_type=task_type,
        model_size='base',
        output_destination=f'/app/results/{user_id}'
    )

    try:
        response = orchestrator_stub.SubmitJob(request)

        # Save to database
        await db.jobs.insert({
            'user_id': user_id,
            'job_id': response.job_id,
            'status': 'queued',
            'task_type': task_type
        })

        return {
            'job_id': response.job_id,
            'status': 'queued',
            'message': response.message
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    request = orchestrator_pb2.GetJobStatusRequest(job_id=job_id)

    try:
        response = orchestrator_stub.GetJobStatus(request)

        return {
            'status': orchestrator_pb2.JobStatus.Name(response.status),
            'output_uri': response.output_uri,
            'output_keys': list(response.output_keys),
            'error_message': response.error_message,
            'created_at': response.created_at,
            'started_at': response.started_at,
            'completed_at': response.completed_at
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Pattern 2: Server-Sent Events (Better UX)

Server-Sent Events provide real-time updates without WebSocket complexity.

```javascript
// Web app backend endpoint
app.get('/api/jobs/:jobId/stream', async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const jobId = req.params.jobId;

  // Poll orchestrator and send updates to frontend
  const interval = setInterval(async () => {
    try {
      const status = await getJobStatus(jobId);

      // Send update to frontend
      res.write(`data: ${JSON.stringify(status)}\n\n`);

      // Stop if job completed/failed
      if (status.status === 'COMPLETED' || status.status === 'FAILED') {
        clearInterval(interval);
        res.end();
      }
    } catch (error) {
      clearInterval(interval);
      res.end();
    }
  }, 2000); // Poll every 2 seconds

  req.on('close', () => clearInterval(interval));
});
```

**Frontend (SSE):**

```javascript
function subscribeToJobUpdates(jobId, callback) {
  const eventSource = new EventSource(`/api/jobs/${jobId}/stream`);

  eventSource.onmessage = (event) => {
    const status = JSON.parse(event.data);
    callback(status);

    if (status.status === 'COMPLETED' || status.status === 'FAILED') {
      eventSource.close();
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
  };

  return eventSource;
}
```

### Pattern 3: WebSockets (Real-time)

For bi-directional communication and multiple concurrent subscriptions.

```javascript
// Web app backend (Socket.io)
const io = require('socket.io')(server);

io.on('connection', (socket) => {
  socket.on('subscribe_job', async (jobId) => {
    console.log(`Client subscribed to job ${jobId}`);

    // Poll orchestrator and emit updates
    const interval = setInterval(async () => {
      try {
        const status = await getJobStatus(jobId);
        socket.emit('job_update', status);

        if (status.status === 'COMPLETED' || status.status === 'FAILED') {
          clearInterval(interval);
          socket.emit('job_complete', status);
        }
      } catch (error) {
        clearInterval(interval);
        socket.emit('job_error', { error: error.message });
      }
    }, 2000);

    socket.on('unsubscribe_job', () => {
      clearInterval(interval);
    });

    socket.on('disconnect', () => {
      clearInterval(interval);
    });
  });
});
```

**Frontend (Socket.io):**

```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:3000');

function subscribeToJob(jobId, onUpdate) {
  socket.emit('subscribe_job', jobId);

  socket.on('job_update', onUpdate);

  socket.on('job_complete', (status) => {
    console.log('Job completed!', status);
  });

  return () => {
    socket.emit('unsubscribe_job', jobId);
  };
}
```

### Pattern 4: gRPC Streaming (Most Efficient)

Use the orchestrator's streaming RPC directly (requires gRPC-Web for browsers).

```javascript
// Web app backend using gRPC streaming
async function streamJobStatus(jobId, callback) {
  const request = { job_id: jobId };

  const stream = client.StreamJobStatus(request);

  stream.on('data', (response) => {
    callback({
      status: statusToString(response.status),
      progress: calculateProgress(response),
      output_uri: response.output_uri,
      error_message: response.error_message
    });
  });

  stream.on('end', () => {
    console.log('Stream ended');
  });

  stream.on('error', (error) => {
    console.error('Stream error:', error);
  });

  return stream;
}

// Expose via WebSocket to frontend
io.on('connection', (socket) => {
  socket.on('subscribe_job', (jobId) => {
    const stream = streamJobStatus(jobId, (status) => {
      socket.emit('job_update', status);
    });

    socket.on('disconnect', () => {
      stream.cancel();
    });
  });
});
```

## Frontend Display Examples

### React Component (Polling)

```typescript
import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface JobStatus {
  status: string;
  progress: number;
  output_uri?: string;
  error_message?: string;
  processing_time?: number;
}

function JobStatusDisplay({ jobId }: { jobId: string }) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Poll backend every 3 seconds
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`/api/jobs/${jobId}/status`);
        setStatus(response.data);
        setLoading(false);

        // Stop polling if completed or failed
        if (response.data.status === 'COMPLETED' || response.data.status === 'FAILED') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Error fetching status:', error);
        setLoading(false);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [jobId]);

  if (loading) {
    return <div className="loading">Loading job status...</div>;
  }

  if (!status) {
    return <div className="error">Failed to load job status</div>;
  }

  return (
    <div className="job-status">
      <h3>Job {jobId}</h3>

      {/* Status badge */}
      <StatusBadge status={status.status} />

      {/* Progress bar */}
      {status.status === 'PROCESSING' && (
        <div className="progress">
          <ProgressBar progress={status.progress} />
          <p>Processing... {status.progress}%</p>
        </div>
      )}

      {/* Queued state */}
      {status.status === 'QUEUED' && (
        <div className="queued">
          <p>Your job is queued and will start processing soon...</p>
        </div>
      )}

      {/* Results */}
      {status.status === 'COMPLETED' && (
        <div className="results">
          <h4>Results Ready!</h4>
          <p>Processing time: {status.processing_time?.toFixed(2)}s</p>
          <a
            href={`/api/jobs/${jobId}/results`}
            className="download-btn"
            download
          >
            Download Results
          </a>
          <div className="preview">
            <img src={`/api/jobs/${jobId}/preview`} alt="Result preview" />
          </div>
        </div>
      )}

      {/* Error */}
      {status.status === 'FAILED' && (
        <div className="error">
          <h4>Job Failed</h4>
          <p>{status.error_message || 'Unknown error occurred'}</p>
          <button onClick={() => retryJob(jobId)}>Retry</button>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors = {
    QUEUED: 'bg-yellow-500',
    PROCESSING: 'bg-blue-500',
    COMPLETED: 'bg-green-500',
    FAILED: 'bg-red-500'
  };

  return (
    <span className={`badge ${colors[status] || 'bg-gray-500'}`}>
      {status}
    </span>
  );
}

function ProgressBar({ progress }: { progress: number }) {
  return (
    <div className="progress-bar">
      <div
        className="progress-fill"
        style={{ width: `${progress}%` }}
      />
    </div>
  );
}
```

### React Component (SSE)

```typescript
import React, { useState, useEffect } from 'react';

function JobStatusDisplay({ jobId }: { jobId: string }) {
  const [status, setStatus] = useState<JobStatus | null>(null);

  useEffect(() => {
    // Connect to SSE endpoint
    const eventSource = new EventSource(`/api/jobs/${jobId}/stream`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data);
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [jobId]);

  // Same rendering logic as above...
}
```

### Vue Component (WebSocket)

```vue
<template>
  <div class="job-status">
    <h3>Job {{ jobId }}</h3>

    <div v-if="loading">Loading...</div>

    <div v-else>
      <StatusBadge :status="status.status" />

      <ProgressBar
        v-if="status.status === 'PROCESSING'"
        :progress="status.progress"
      />

      <div v-if="status.status === 'COMPLETED'" class="results">
        <h4>Results Ready!</h4>
        <a :href="`/api/jobs/${jobId}/results`" download>
          Download Results
        </a>
      </div>

      <div v-if="status.status === 'FAILED'" class="error">
        <h4>Job Failed</h4>
        <p>{{ status.error_message }}</p>
      </div>
    </div>
  </div>
</template>

<script>
import io from 'socket.io-client';

export default {
  props: ['jobId'],
  data() {
    return {
      status: null,
      loading: true,
      socket: null
    };
  },
  mounted() {
    this.socket = io('http://localhost:3000');

    this.socket.emit('subscribe_job', this.jobId);

    this.socket.on('job_update', (status) => {
      this.status = status;
      this.loading = false;
    });
  },
  beforeUnmount() {
    if (this.socket) {
      this.socket.emit('unsubscribe_job', this.jobId);
      this.socket.disconnect();
    }
  }
};
</script>
```

## Deployment Options

### Option 1: Same Server, Separate Containers (Recommended)

Create a unified docker-compose file that includes both web app and orchestrator:

```yaml
# docker-compose-full-stack.yml
version: '3.8'

services:
  # Frontend (React/Vue/Angular)
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  # Backend (Node.js/Python/Go)
  backend:
    build: ./backend
    ports:
      - "3000:3000"
    environment:
      - ORCHESTRATOR_URL=orchestrator:50050
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp
    depends_on:
      - orchestrator
      - db

  # Orchestrator service
  orchestrator:
    build:
      context: .
      dockerfile: orchestrator/Dockerfile
    ports:
      - "50050:50050"
      - "8080:8080"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - GRPC_PORT=50050
      - METRICS_PORT=8080
      - NUM_WORKERS=2
    depends_on:
      redis:
        condition: service_healthy
    volumes:
      - ./orchestrator/config:/app/orchestrator/config
    networks:
      - app_network

  # Redis for job queue
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app_network

  # MIRAGE model service
  mirage-service:
    build:
      context: .
      dockerfile: setup/Dockerfile.mirage
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    ports:
      - "8000:8000"
      - "50051:50051"
    environment:
      - MIRAGE_MODEL_SIZE=base
      - MIRAGE_PRELOAD_MODEL=true
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    volumes:
      - ./data/weights:/app/MIRAGE/__weights
      - ./data/datasets:/app/MIRAGE/__datasets
    networks:
      - app_network

  # PostgreSQL database (for web app)
  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - db_data:/var/lib/postgresql/data
    networks:
      - app_network

volumes:
  redis_data:
  db_data:

networks:
  app_network:
    driver: bridge
```

**Start everything:**

```bash
docker-compose -f docker-compose-full-stack.yml up -d
```

### Option 2: Separate Servers (Production)

For production deployments, you might want to separate public-facing and internal services:

```
┌─────────────────┐         ┌─────────────────────┐
│  Server 1       │         │  Server 2           │
│  (Public)       │         │  (Internal)         │
│                 │         │                     │
│  - Frontend     │         │  - Orchestrator     │
│  - Backend API  │  gRPC   │  - Redis            │
│  - Nginx        │────────▶│  - MIRAGE           │
│                 │         │  - GPU Workers      │
│  Port 80/443    │         │                     │
└─────────────────┘         │  Port 50050         │
                            │  (Internal only)    │
                            └─────────────────────┘
```

**Backend configuration:**

```javascript
// Connect to remote orchestrator
const client = new orchestrator.OrchestratorService(
  'orchestrator.internal.company.com:50050',
  grpc.credentials.createInsecure()
);
```

**Security considerations:**
- Use VPC/private network between servers
- Firewall rules: Only backend can reach orchestrator
- Consider mTLS for gRPC in production

### Option 3: Kubernetes (Cloud Native)

For cloud deployments with auto-scaling:

```yaml
# orchestrator-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: orchestrator
  template:
    metadata:
      labels:
        app: orchestrator
    spec:
      containers:
      - name: orchestrator
        image: mycompany/orchestrator:latest
        ports:
        - containerPort: 50050
        - containerPort: 8080
        env:
        - name: REDIS_HOST
          value: redis-service
        - name: NUM_WORKERS
          value: "2"
---
apiVersion: v1
kind: Service
metadata:
  name: orchestrator-service
spec:
  selector:
    app: orchestrator
  ports:
  - name: grpc
    port: 50050
    targetPort: 50050
  - name: metrics
    port: 8080
    targetPort: 8080
```

## API Endpoints Summary

### Orchestrator Provides (gRPC)

1. **SubmitJob** - Submit new inference job
   - Input: images, task_type, model_name, output_destination
   - Output: job_id, status, message

2. **GetJobStatus** - Poll job status
   - Input: job_id
   - Output: status, output_uri, output_keys, error details, timestamps

3. **StreamJobStatus** - Real-time streaming (optional)
   - Input: job_id
   - Output: Stream of status updates

4. **ListModels** - Show available models
   - Input: only_healthy (boolean)
   - Output: List of models with capabilities

5. **HealthCheck** - System health
   - Input: None
   - Output: healthy, version, queue stats, model health

### Web App Should Implement (REST/GraphQL)

1. **POST /api/jobs** - Submit job (calls orchestrator.SubmitJob)
2. **GET /api/jobs/:id/status** - Get status (calls orchestrator.GetJobStatus)
3. **GET /api/jobs/:id/stream** - Stream updates (SSE, optional)
4. **GET /api/jobs/:id/results** - Download results
5. **GET /api/jobs** - List user's jobs (from web app database)
6. **GET /api/models** - List available models (calls orchestrator.ListModels)
7. **GET /api/health** - Health check (calls orchestrator.HealthCheck)

### Web App Database Schema (Example)

```sql
CREATE TABLE jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  orchestrator_job_id VARCHAR(255) NOT NULL UNIQUE,
  task_type VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL,
  image_path TEXT,
  output_uri TEXT,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  metadata JSONB
);

CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
```

## Monitoring and Observability

### What to Monitor

1. **Job Metrics**
   - Jobs submitted per minute
   - Jobs completed/failed
   - Average processing time
   - Queue depth

2. **Model Health**
   - Model availability
   - Inference latency
   - GPU utilization

3. **System Health**
   - Orchestrator uptime
   - Redis connection status
   - Worker thread health

### Implementation

**Prometheus + Grafana:**

```yaml
# Add to docker-compose
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'

grafana:
  image: grafana/grafana
  ports:
    - "3001:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

**Prometheus config:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'orchestrator'
    static_configs:
      - targets: ['orchestrator:8080']
```

**Web app metrics endpoint:**

```javascript
// Add Prometheus client
const promClient = require('prom-client');

const jobSubmissions = new promClient.Counter({
  name: 'webapp_jobs_submitted_total',
  help: 'Total jobs submitted by web app',
  labelNames: ['task_type', 'user_type']
});

const jobDuration = new promClient.Histogram({
  name: 'webapp_job_duration_seconds',
  help: 'Job duration from submission to completion',
  labelNames: ['task_type']
});

// Expose metrics
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', promClient.register.contentType);
  res.end(await promClient.register.metrics());
});
```

## Performance Considerations

### Scaling Web App

- **Horizontal scaling**: Run multiple backend instances behind load balancer
- **Connection pooling**: Reuse gRPC connections to orchestrator
- **Caching**: Cache model list, health status (short TTL)

```javascript
// Connection pool example
const grpc = require('@grpc/grpc-js');
const clients = [];
const POOL_SIZE = 5;

for (let i = 0; i < POOL_SIZE; i++) {
  const client = new orchestrator.OrchestratorService(
    'localhost:50050',
    grpc.credentials.createInsecure()
  );
  clients.push(client);
}

function getClient() {
  return clients[Math.floor(Math.random() * clients.length)];
}
```

### Scaling Orchestrator

- **Increase workers**: Set `NUM_WORKERS=4` or more
- **Vertical scaling**: More CPU/RAM for orchestrator container
- **Horizontal scaling**: Run multiple orchestrator instances (requires Redis)

### Optimizing Polling

- **Adaptive polling**: Poll faster when processing, slower when queued
- **Long polling**: Backend waits for changes before responding
- **Use SSE/WebSocket**: Better than regular polling for UX

## Security Best Practices

1. **Authentication**: Web app handles user auth, passes user_id to orchestrator in metadata
2. **Authorization**: Verify user owns job before returning status
3. **Input validation**: Validate file paths, prevent path traversal
4. **Rate limiting**: Limit job submissions per user
5. **Network isolation**: Orchestrator on internal network only
6. **Secrets management**: Use environment variables, not hardcoded
7. **TLS**: Use TLS for gRPC in production (mTLS recommended)

```javascript
// Authorization middleware
async function authorizeJob(req, res, next) {
  const jobId = req.params.jobId;
  const userId = req.user.id;

  const job = await db.jobs.findById(jobId);

  if (!job) {
    return res.status(404).json({ error: 'Job not found' });
  }

  if (job.user_id !== userId) {
    return res.status(403).json({ error: 'Unauthorized' });
  }

  next();
}

router.get('/api/jobs/:jobId/status', authorizeJob, async (req, res) => {
  // ...
});
```

## Testing

### Integration Tests

```javascript
// test/integration/orchestrator.test.js
describe('Orchestrator Integration', () => {
  it('should submit and complete a job', async () => {
    // Submit job
    const response = await request(app)
      .post('/api/jobs')
      .send({
        image_path: '/test/image.npy',
        task_type: 'segmentation'
      })
      .expect(200);

    const jobId = response.body.job_id;

    // Poll for completion
    let status;
    for (let i = 0; i < 30; i++) {
      const statusRes = await request(app)
        .get(`/api/jobs/${jobId}/status`)
        .expect(200);

      status = statusRes.body;

      if (status.status === 'COMPLETED' || status.status === 'FAILED') {
        break;
      }

      await sleep(2000);
    }

    expect(status.status).toBe('COMPLETED');
    expect(status.output_uri).toBeTruthy();
  });
});
```

## Summary

**Deployment**:
- ✅ Separate services (can be same server)
- ✅ Use docker-compose for easy deployment
- ✅ Orchestrator on port 50050, web app on port 3000

**Status Display**:
- ✅ Orchestrator provides complete gRPC APIs
- ✅ Web app implements REST endpoints that call orchestrator
- ✅ Frontend polls backend every 2-5 seconds (or uses SSE/WebSocket)
- ✅ Show status: QUEUED → PROCESSING → COMPLETED/FAILED
- ✅ Display progress bars, results, errors

**What Web App Provides**:
- User authentication and authorization
- Job submission interface (upload files, select task type)
- Status display with polling/streaming
- Results download
- Job history and management
- User dashboard

**What Orchestrator Provides**:
- Job queueing and persistence (Redis)
- Model routing and health monitoring
- Background job processing
- Status tracking and results
- Metrics and observability

The orchestrator is **production-ready** and provides all the APIs your web app needs. You just need to implement:
1. Web app backend with gRPC client to orchestrator
2. REST/GraphQL API for frontend
3. Frontend UI components to display status
4. User authentication and job ownership

**Next Steps**:
1. Choose your integration pattern (polling, SSE, or WebSocket)
2. Implement web app backend with gRPC client
3. Create frontend components for job submission and status
4. Deploy using docker-compose-full-stack.yml
5. Test end-to-end flow
6. Add monitoring and alerts

The separation of concerns makes the system:
- **Scalable**: Scale web app and orchestrator independently
- **Maintainable**: Clear boundaries, easy to debug
- **Flexible**: Swap web frameworks without touching orchestrator
- **Reliable**: Orchestrator continues processing if web app restarts

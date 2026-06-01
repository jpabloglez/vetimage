# DICOM Gateway Service

DICOM networking gateway for receiving medical images from PACS/modalities and integrating with OpenMedLab backend for AI analysis.

## Features

- **DICOM SCP**: Receives images via C-STORE from PACS/modalities
- **Multi-format Support**: DICOM, with automatic metadata extraction
- **Async Processing**: Celery-based queue for reliable processing
- **Monitoring API**: RESTful API for health monitoring and metrics
- **Audit Logging**: Complete transaction and PHI access logs
- **Auto-forwarding**: Automatic upload to backend for AI analysis

## Architecture

```
PACS/Modality → [DICOM SCP:11112] → Celery Queue → Backend API → AI Analysis
                       ↓
                 [Monitoring API:8001]
```

## Quick Start

### 1. Build and Start

```bash
# From repository root
docker-compose up -d dicom-gateway-openmedlab

# Check logs
docker logs -f dicom-gateway-openmedlab
```

### 2. Verify Health

```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-25T...",
  "version": "0.1.0",
  "environment": "development"
}
```

### 3. Check Gateway Status

```bash
curl http://localhost:8001/api/status
```

### 4. Test DICOM Connectivity

```bash
# C-ECHO test (from another container or machine with DICOM tools)
echoscu -aec OPENMEDLAB localhost 11112

# Or use internal test endpoint
curl -X POST http://localhost:8001/api/test-echo
```

### 5. Send Test DICOM File

```bash
# Using storescu (DICOM toolkit)
storescu -aec OPENMEDLAB localhost 11112 /path/to/dicom/file.dcm

# Or use the provided test script
python tests/send_dicom_test.py
```

## Configuration

Configuration is managed via environment variables (see `.env.example`):

### Core Settings

- `DICOM_AE_TITLE`: Application Entity title (default: OPENMEDLAB)
- `DICOM_PORT`: DICOM SCP port (default: 11112)
- `BACKEND_API_URL`: Backend API endpoint
- `STORAGE_PATH`: Temporary DICOM storage path

### Processing

- `AUTO_FORWARD_TO_BACKEND`: Auto-upload to backend (default: true)
- `ENABLE_ANONYMIZATION`: Anonymize PHI before forwarding (default: false)

### Security

- `ALLOWED_SOURCE_IPS`: IP whitelist (JSON array)
- `ENABLE_TLS`: Enable DICOM TLS (default: false)

## API Endpoints

### Health & Monitoring

- `GET /health` - Health check
- `GET /api/status` - Gateway status
- `GET /api/metrics` - System resource metrics
- `GET /api/stats` - DICOM processing statistics
- `GET /api/config` - Current configuration

### Testing

- `POST /api/test-echo` - Self C-ECHO test

### Prometheus Metrics

- `GET /metrics` - Prometheus-format metrics

## Monitoring

### Dashboard

Access the monitoring dashboard at:
```
http://localhost:3000/gateway-monitor
```

### Prometheus Integration

Add to `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'dicom-gateway'
    static_configs:
      - targets: ['dicom-gateway-openmedlab:9090']
```

### Logs

View real-time logs:
```bash
docker logs -f dicom-gateway-openmedlab
```

## Development

### Local Setup

```bash
cd app/dicom-gateway

# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py
```

### Run Tests

```bash
pytest tests/
```

### Environment Variables

Copy and customize:
```bash
cp .env.example .env
# Edit .env with your settings
```

## Troubleshooting

### Gateway Not Receiving Images

1. Check firewall: Port 11112 must be open
2. Verify AE title matches PACS configuration
3. Check PACS destination AE title = `OPENMEDLAB`
4. Review logs: `docker logs dicom-gateway-openmedlab`

### Backend Upload Failures

1. Verify backend is running: `curl http://localhost:3080/health`
2. Check `BACKEND_API_URL` is correct
3. Review Celery worker logs: `docker logs gateway-celery-worker`

### High Memory Usage

1. Check storage path disk space
2. Verify old files are being cleaned up (Celery beat task)
3. Adjust `MAX_STORAGE_GB` setting

## Integration with Test PACS (Orthanc)

Orthanc test PACS is included in Docker Compose:

```bash
# Start Orthanc
docker-compose up -d orthanc-test-pacs

# Access web interface
open http://localhost:8042
# Username: orthanc
# Password: orthanc

# Configure Orthanc to send to gateway:
# Go to: Configuration > Modalities
# Add modality:
#   AET: OPENMEDLAB
#   Host: dicom-gateway-openmedlab
#   Port: 11112
```

## Production Deployment

### Security Hardening

1. **Enable TLS**: Set `ENABLE_TLS=true` and provide certificates
2. **IP Whitelisting**: Set `ALLOWED_SOURCE_IPS` to hospital IPs
3. **API Authentication**: Set `BACKEND_API_KEY`
4. **Firewall**: Restrict port 11112 to trusted networks

### Scaling

Horizontal scaling via replicas:
```yaml
dicom-gateway:
  deploy:
    replicas: 3
    resources:
      limits:
        cpus: '2'
        memory: 4G
```

### Monitoring

- Enable Prometheus metrics
- Set up alerting for:
  - High error rates
  - Queue backlog
  - Disk space
  - Failed PACS connections

## Architecture Notes

- **Microservice Design**: Runs independently from main backend
- **Stateless**: Can scale horizontally
- **Queue-based**: Reliable async processing
- **Audit Trail**: Complete HIPAA-compliant logging

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/openmedlab/issues
- Documentation: `/docs/DICOM-Gateway-Evaluation.md`

## License

See main repository LICENSE file.

# DICOM-DIMSE Gateway Evaluation
## pynetdicom Integration for PACS/RIS/Modality Communication

**Date:** 2025-12-25
**Project:** OpenMedLab
**Objective:** Evaluate implementation of a DICOM-DIMSE gateway for hospital integration

---

## Executive Summary

Implementing a DICOM-DIMSE gateway using pynetdicom would transform OpenMedLab from a web-upload-only platform into a clinically-integrated AI analysis system capable of real-time hospital integration. This evaluation recommends a **microservice architecture** deployed as a separate service for maximum flexibility, scalability, and security across both cloud and on-premises environments.

**Key Recommendation:** Deploy as a containerized microservice with dual-mode operation (push/pull) and comprehensive audit logging.

---

## 1. Benefits Analysis

### 1.1 Clinical Integration Benefits

**Seamless Workflow Integration**
- Eliminates manual file export/upload steps from PACS to AI platform
- Enables real-time AI analysis as part of clinical workflow
- Reduces time from image acquisition to AI results (minutes vs hours)
- Supports automated routing of specific studies to AI models

**DICOM Standards Compliance**
- Native support for DICOM networking protocols (C-STORE, C-FIND, C-MOVE, C-GET)
- Maintains complete DICOM metadata and patient context
- Ensures compatibility with all DICOM-compliant modalities and PACS
- Supports DICOM Modality Worklist (MWL) for study scheduling

**Data Quality & Integrity**
- Receives original DICOM data without lossy conversions
- Preserves all technical parameters and calibration data
- Maintains complete imaging chain metadata for traceability
- Supports DICOM structured reporting for AI results

### 1.2 Operational Benefits

**Scalability**
- Handle high-volume hospital imaging (100-1000+ studies/day)
- Support multiple simultaneous PACS/modality connections
- Queue-based processing prevents system overload
- Horizontal scaling for peak load handling

**Reliability**
- Automatic retry for failed transmissions
- Transaction logging for data loss prevention
- Health monitoring and alerting
- Graceful degradation under load

**Auditability**
- Complete audit trail of all DICOM transactions
- Patient privacy tracking (PHI access logs)
- Compliance reporting for regulatory requirements
- Performance metrics and SLA monitoring

### 1.3 Business Benefits

**Market Positioning**
- Enables B2B hospital sales (vs individual researchers)
- Meets enterprise procurement requirements
- Supports clinical trial data acquisition
- Competitive differentiation vs upload-only platforms

**Revenue Opportunities**
- Per-study pricing for hospital integrations
- Premium support contracts for clinical deployments
- Value-added services (worklist integration, reporting)
- Data analytics on aggregated de-identified data

---

## 2. Architecture Options

### 2.1 Option A: Integrated Backend Service

**Description:** Add DICOM networking capabilities directly to the Django backend.

```
┌─────────────────────────────────────┐
│      Django Backend                 │
│  ┌──────────────────────────────┐   │
│  │  Web API (REST)              │   │
│  ├──────────────────────────────┤   │
│  │  DICOM Gateway Service       │   │
│  │  (pynetdicom SCP/SCU)        │   │
│  ├──────────────────────────────┤   │
│  │  Database (PostgreSQL)       │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

**Pros:**
- ✅ Simplified deployment (single service)
- ✅ Direct database access (no API overhead)
- ✅ Shared authentication/authorization
- ✅ Easier development in early stages

**Cons:**
- ❌ Tight coupling increases complexity
- ❌ DICOM traffic impacts web API performance
- ❌ Difficult to scale independently
- ❌ Security: DICOM port exposure requires web server hardening
- ❌ Deployment inflexibility (must deploy entire backend)
- ❌ Resource contention between web and DICOM services

**Use Case:** Small-scale deployments (<50 studies/day), proof-of-concept

### 2.2 Option B: Microservice Architecture (RECOMMENDED)

**Description:** Deploy DICOM gateway as a separate containerized service.

```
┌──────────────────┐         ┌─────────────────────┐
│  Hospital PACS   │◄───────►│  DICOM Gateway      │
│  (DICOM C-STORE) │  DICOM  │  (pynetdicom SCP)   │
└──────────────────┘  11112  │                     │
                              │  ┌──────────────┐   │
                              │  │ Queue Worker │   │
                              │  │ (Celery)     │   │
                              │  └──────────────┘   │
                              └─────────┬───────────┘
                                        │ REST API
                                        ▼
                              ┌─────────────────────┐
                              │  Django Backend     │
                              │  (Web API)          │
                              └─────────────────────┘
                                        │
                                        ▼
                              ┌─────────────────────┐
                              │  PostgreSQL + Redis │
                              └─────────────────────┘
```

**Pros:**
- ✅ **Independent scaling** (scale DICOM gateway separately from web API)
- ✅ **Security isolation** (DICOM network segment isolation)
- ✅ **Technology flexibility** (upgrade gateway without touching Django)
- ✅ **Performance** (dedicated resources for DICOM processing)
- ✅ **Deployment flexibility** (deploy gateway on-prem, API in cloud)
- ✅ **Fault isolation** (gateway failure doesn't crash web API)
- ✅ **Development agility** (teams can work independently)

**Cons:**
- ⚠️ Additional infrastructure complexity
- ⚠️ Network latency for API calls
- ⚠️ More services to monitor and maintain

**Use Case:** Production deployments, hospital integrations, enterprise sales

### 2.3 Option C: Hybrid Architecture

**Description:** Microservice with shared database for performance.

```
┌──────────────────┐         ┌─────────────────────┐
│  Hospital PACS   │◄───────►│  DICOM Gateway      │
└──────────────────┘         │  (Direct DB Write)  │
                              └─────────┬───────────┘
                                        │ Direct SQL
                                        ▼
                  ┌──────────────────────────────────┐
                  │      Shared PostgreSQL           │
                  └────────────┬─────────────────────┘
                               │
                               ▼
                  ┌─────────────────────┐
                  │  Django Backend     │
                  └─────────────────────┘
```

**Pros:**
- ✅ Best performance (no API overhead)
- ✅ Still allows independent deployment
- ✅ Simpler than full microservice

**Cons:**
- ❌ Database coupling reduces flexibility
- ❌ Schema changes impact both services
- ❌ Reduced isolation

**Use Case:** High-performance requirements, trusted network environments

---

## 3. Deployment Strategies

### 3.1 Cloud Deployment

#### Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Cloud (AWS/GCP/Azure)              │
│                                                     │
│  ┌────────────────────────────────────────────┐    │
│  │  VPC / Virtual Network                     │    │
│  │                                            │    │
│  │  ┌──────────────┐      ┌──────────────┐   │    │
│  │  │  Public      │      │  Private     │   │    │
│  │  │  Subnet      │      │  Subnet      │   │    │
│  │  │              │      │              │   │    │
│  │  │  ┌────────┐  │      │ ┌──────────┐ │   │    │
│  │  │  │  ALB   │  │      │ │  DICOM   │ │   │    │
│  │  │  │ (HTTPS)│  │      │ │ Gateway  │ │   │    │
│  │  │  └────┬───┘  │      │ │ (11112)  │ │   │    │
│  │  │       │      │      │ └────┬─────┘ │   │    │
│  │  │  ┌────▼───┐  │      │      │       │   │    │
│  │  │  │Django  │  │      │      │       │   │    │
│  │  │  │Backend │  │      │      │       │   │    │
│  │  │  └────────┘  │      │      │       │   │    │
│  │  └──────────────┘      └──────┼───────┘   │    │
│  │                                │           │    │
│  │  ┌─────────────────────────────▼───────┐   │    │
│  │  │  Managed Database (RDS/Cloud SQL)   │   │    │
│  │  │  + Redis/ElastiCache               │   │    │
│  │  └─────────────────────────────────────┘   │    │
│  └────────────────────────────────────────────┘    │
│                                                     │
│  ┌────────────────────────────────────────────┐    │
│  │  VPN Gateway / Direct Connect              │    │
│  └────────────────────────────────────────────┘    │
└─────────────────┬───────────────────────────────────┘
                  │ Encrypted Tunnel
                  ▼
         ┌────────────────┐
         │ Hospital PACS  │
         │ (On-Premises)  │
         └────────────────┘
```

#### Connectivity Options

**1. VPN Tunnel (Site-to-Site VPN)**
- Use Case: Small to medium hospitals
- Security: IPsec encryption
- Cost: $50-200/month
- Latency: 50-150ms
- Bandwidth: 100Mbps - 1Gbps

**2. Direct Connect / ExpressRoute**
- Use Case: Large hospital systems, high volume
- Security: Dedicated fiber connection
- Cost: $500-5000/month
- Latency: <10ms
- Bandwidth: 1-100Gbps

**3. Cloud DICOM Proxy (Recommended for Multi-Site)**
```
Hospital A PACS ──┐
                  │
Hospital B PACS ──┼──► On-Prem DICOM Relay ──VPN──► Cloud Gateway
                  │
Hospital C PACS ──┘
```

#### Cloud Deployment Challenges

**Data Residency & Compliance**
- HIPAA: PHI must be encrypted in transit and at rest
- GDPR: Patient data may need to stay in specific regions
- Local regulations: Some countries prohibit cloud PHI storage
- **Solution:** Regional cloud deployments, encryption at rest/transit

**Network Reliability**
- Internet outages break DICOM connectivity
- Variable latency affects real-time workflows
- **Solution:** Local caching, queue-and-forward architecture

**Cost Considerations**
- Data transfer costs ($0.05-0.12/GB egress)
- High-volume imaging = high monthly bandwidth costs
- Example: 500 studies/day × 500MB/study × 30 days = 7.5TB/month = $375-900/month in egress alone
- **Solution:** Compression, regional processing, tiered storage

**Security Concerns**
- Shared responsibility model complexity
- Attack surface via internet exposure
- **Solution:** Private endpoints, security groups, WAF

### 3.2 On-Premises Deployment

#### Architecture

```
┌─────────────────────────────────────────────────────┐
│              Hospital Network (On-Prem)             │
│                                                     │
│  ┌────────────────┐       ┌────────────────────┐   │
│  │  Hospital PACS │       │  OpenMedLab Stack  │   │
│  │  10.0.1.10     │◄─────►│                    │   │
│  └────────────────┘ DICOM │  ┌──────────────┐  │   │
│                     11112 │  │ DICOM Gateway│  │   │
│  ┌────────────────┐       │  │ (Container)  │  │   │
│  │  Modalities    │◄─────►│  └──────────────┘  │   │
│  │  (CT/MRI/etc)  │       │                    │   │
│  └────────────────┘       │  ┌──────────────┐  │   │
│                           │  │  Django      │  │   │
│  ┌────────────────┐       │  │  Backend     │  │   │
│  │  Workstations  │◄─────►│  └──────────────┘  │   │
│  │  (Radiologists)│ HTTPS │                    │   │
│  └────────────────┘       │  ┌──────────────┐  │   │
│                           │  │  PostgreSQL  │  │   │
│                           │  │  + Redis     │  │   │
│                           │  └──────────────┘  │   │
│                           └────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

#### Deployment Methods

**1. Docker Compose (Small Sites)**
```yaml
version: '3.8'
services:
  dicom-gateway:
    image: openmedlab/dicom-gateway:latest
    ports:
      - "11112:11112"  # DICOM C-STORE
      - "11113:11113"  # DICOM Query/Retrieve
    environment:
      - AE_TITLE=OPENMEDLAB
      - PACS_HOST=10.0.1.10
      - PACS_PORT=11112
      - PACS_AE_TITLE=HOSPITAL_PACS
    volumes:
      - /data/dicom-temp:/app/storage
    networks:
      - hospital-net

  backend:
    image: openmedlab/backend:latest
    depends_on:
      - db
      - redis

  db:
    image: postgres:17
    volumes:
      - pg-data:/var/lib/postgresql/data

  redis:
    image: redis:7
```

**2. Kubernetes (Enterprise)**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dicom-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dicom-gateway
  template:
    spec:
      containers:
      - name: gateway
        image: openmedlab/dicom-gateway:latest
        ports:
        - containerPort: 11112
          protocol: TCP
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          exec:
            command:
            - /app/healthcheck.sh
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: dicom-gateway-lb
spec:
  type: LoadBalancer
  loadBalancerIP: 10.0.1.50  # Static hospital network IP
  ports:
  - port: 11112
    targetPort: 11112
    protocol: TCP
  selector:
    app: dicom-gateway
```

#### On-Prem Advantages

**Performance**
- Low latency (<5ms to PACS)
- High bandwidth (10Gbps hospital network)
- No internet dependency

**Security**
- PHI stays within hospital network
- Meets strict data residency requirements
- Simpler compliance (no cloud provider agreements)

**Cost**
- No cloud egress fees
- No monthly cloud infrastructure costs
- Predictable CapEx hardware costs

**Integration**
- Direct access to hospital Active Directory
- Integration with existing monitoring systems
- Custom firewall rules

#### On-Prem Challenges

**Resource Requirements**
- Hospital must provide compute/storage
- IT staff for maintenance and monitoring
- Backup and disaster recovery responsibilities

**Scalability**
- Limited by hospital hardware
- Manual capacity planning
- Difficult to handle peak loads

**Updates & Maintenance**
- Manual deployment of updates
- Scheduled downtime windows required
- Longer time to deploy new features

### 3.3 Hybrid Deployment (RECOMMENDED for Enterprise)

**Architecture: Gateway On-Prem, Processing Cloud**

```
┌──────────────────────────────┐
│  Hospital (On-Premises)      │
│                              │
│  ┌────────────┐              │
│  │ PACS       │              │
│  └─────┬──────┘              │
│        │ DICOM               │
│        ▼                     │
│  ┌────────────────────┐      │
│  │ DICOM Gateway      │      │
│  │ (Lightweight)      │      │
│  │ - Receive DICOM    │      │
│  │ - Metadata Extract │      │
│  │ - Anonymization    │      │
│  │ - Queue Upload     │      │
│  └─────┬──────────────┘      │
│        │ HTTPS (Encrypted)   │
└────────┼─────────────────────┘
         │ VPN/Direct Connect
         ▼
┌────────────────────────────────┐
│  Cloud                         │
│                                │
│  ┌──────────────────────┐      │
│  │ Django Backend       │      │
│  │ - API                │      │
│  │ - AI Processing      │      │
│  │ - Result Storage     │      │
│  └──────────────────────┘      │
│                                │
│  ┌──────────────────────┐      │
│  │ Database + Storage   │      │
│  └──────────────────────┘      │
└────────────────────────────────┘
```

**Benefits:**
- ✅ PHI stays on-prem (compliance)
- ✅ Cloud scalability for AI processing
- ✅ Fast DICOM reception (local network)
- ✅ Reduced cloud costs (only anonymized data transferred)
- ✅ Best of both worlds

**Implementation:**
1. On-prem gateway receives DICOM from PACS
2. Extract metadata and anonymize
3. Upload anonymized images + metadata to cloud via HTTPS
4. Cloud performs AI analysis
5. Results returned to on-prem gateway
6. Gateway forwards results back to PACS (DICOM SR)

---

## 4. Technical Implementation Approach

### 4.1 Core DICOM Services

#### Service Control Point (SCP) - Receive Images

```python
from pynetdicom import AE, evt, StoragePresentationContexts
from pynetdicom.sop_class import Verification

class OpenMedLabSCP:
    """
    DICOM SCP (Server) to receive images from PACS/modalities
    """

    def __init__(self, ae_title='OPENMEDLAB', port=11112):
        self.ae = AE(ae_title=ae_title)
        self.ae.supported_contexts = StoragePresentationContexts
        self.ae.add_supported_context(Verification)
        self.port = port

    def handle_store(self, event):
        """Handle incoming C-STORE request"""
        ds = event.dataset

        # Extract patient info
        patient_id = ds.get('PatientID', 'UNKNOWN')
        study_uid = ds.get('StudyInstanceUID')
        series_uid = ds.get('SeriesInstanceUID')

        # Log the reception
        logger.info(f"Received image: Patient={patient_id}, Study={study_uid}")

        # Save to temporary storage
        file_path = self._save_dicom_file(ds, study_uid, series_uid)

        # Queue for processing
        self._queue_for_processing(file_path, ds)

        # Return success status
        return 0x0000  # Success

    def start(self):
        """Start the SCP server"""
        handlers = [(evt.EVT_C_STORE, self.handle_store)]
        self.ae.start_server(('0.0.0.0', self.port), evt_handlers=handlers)
        logger.info(f"DICOM SCP started on port {self.port}")
```

#### Service Class User (SCU) - Query/Retrieve

```python
class OpenMedLabSCU:
    """
    DICOM SCU (Client) to query and retrieve images from PACS
    """

    def __init__(self, ae_title='OPENMEDLAB'):
        self.ae = AE(ae_title=ae_title)
        # Add requested contexts for C-FIND and C-MOVE
        self.ae.add_requested_context('1.2.840.10008.5.1.4.1.2.1.1')  # Study Root Find
        self.ae.add_requested_context('1.2.840.10008.5.1.4.1.2.1.2')  # Study Root Move

    def find_studies(self, pacs_host, pacs_port, pacs_ae,
                     patient_id=None, study_date=None, modality=None):
        """Query PACS for studies matching criteria"""
        from pydicom.dataset import Dataset

        # Create query dataset
        ds = Dataset()
        ds.QueryRetrieveLevel = 'STUDY'
        ds.PatientID = patient_id or ''
        ds.StudyDate = study_date or ''
        ds.Modality = modality or ''
        ds.StudyInstanceUID = ''

        # Associate with PACS
        assoc = self.ae.associate(pacs_host, pacs_port, ae_title=pacs_ae)

        if assoc.is_established:
            responses = assoc.send_c_find(ds, '1.2.840.10008.5.1.4.1.2.1.1')

            studies = []
            for (status, identifier) in responses:
                if status and identifier:
                    studies.append(identifier)

            assoc.release()
            return studies
        else:
            raise ConnectionError(f"Failed to connect to PACS at {pacs_host}:{pacs_port}")

    def retrieve_study(self, pacs_host, pacs_port, pacs_ae, study_uid, dest_ae):
        """Trigger C-MOVE to retrieve study from PACS"""
        from pydicom.dataset import Dataset

        ds = Dataset()
        ds.QueryRetrieveLevel = 'STUDY'
        ds.StudyInstanceUID = study_uid

        assoc = self.ae.associate(pacs_host, pacs_port, ae_title=pacs_ae)

        if assoc.is_established:
            responses = assoc.send_c_move(ds, dest_ae, '1.2.840.10008.5.1.4.1.2.1.2')

            for (status, identifier) in responses:
                if status:
                    logger.info(f"C-MOVE status: {status.Status}")

            assoc.release()
```

### 4.2 Processing Pipeline

```python
from celery import shared_task
from dicom_images.metadata_extractors import MetadataExtractorFactory
from ai_analysis.services.model_recommender import ModelRecommender

@shared_task
def process_incoming_dicom(file_path, metadata):
    """
    Celery task to process incoming DICOM file

    Steps:
    1. Validate DICOM file
    2. Extract metadata
    3. Create database records (Study/Series/Image)
    4. Anonymize if required
    5. Recommend AI models
    6. Optionally auto-trigger analysis
    7. Send acknowledgment back to PACS
    """

    # Step 1: Extract metadata
    extractor = MetadataExtractorFactory.get_extractor(file_path)
    full_metadata = extractor.extract(file_path)

    # Step 2: Create database records
    from dicom_images.models import Study, Series, MedicalImage

    study, _ = Study.objects.get_or_create(
        study_instance_uid=full_metadata['study_instance_uid'],
        defaults={
            'patient_id': full_metadata['patient_id'],
            'study_date': full_metadata['study_date'],
            'study_description': full_metadata.get('study_description', ''),
            'modality': full_metadata['modality'],
        }
    )

    series, _ = Series.objects.get_or_create(
        series_instance_uid=full_metadata['series_instance_uid'],
        study=study,
        defaults={
            'series_number': full_metadata.get('series_number'),
            'series_description': full_metadata.get('series_description', ''),
        }
    )

    # Step 3: Store image
    image = MedicalImage.objects.create(
        series=series,
        sop_instance_uid=full_metadata['sop_instance_uid'],
        instance_number=full_metadata.get('instance_number'),
        dicom_tags=full_metadata,
        file_path=file_path,
    )

    # Step 4: Recommend models
    recommendations = ModelRecommender.recommend_models(full_metadata)

    # Step 5: Log audit trail
    log_dicom_reception(
        study_uid=study.study_instance_uid,
        source_ae=metadata.get('source_ae'),
        source_ip=metadata.get('source_ip'),
        timestamp=timezone.now(),
        image_count=1,
    )

    # Step 6: Auto-trigger analysis if configured
    if study.auto_analyze_enabled:
        trigger_auto_analysis(image, recommendations)

    return {
        'status': 'success',
        'image_id': image.id,
        'recommendations': len(recommendations),
    }
```

### 4.3 Configuration Management

```python
# dicom_gateway/models.py

class PACSConfiguration(models.Model):
    """Configuration for connected PACS systems"""

    name = models.CharField(max_length=200)
    ae_title = models.CharField(max_length=16, unique=True)
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=11112)

    # Connection settings
    max_pdu_length = models.IntegerField(default=16384)
    timeout = models.IntegerField(default=30)  # seconds

    # Security
    tls_enabled = models.BooleanField(default=False)
    tls_cert_path = models.CharField(max_length=500, blank=True)
    allowed_source_ips = models.JSONField(default=list)  # IP whitelist

    # Workflow
    auto_retrieve_enabled = models.BooleanField(default=False)
    auto_analyze_enabled = models.BooleanField(default=False)
    default_model_key = models.CharField(max_length=100, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    last_connected = models.DateTimeField(null=True, blank=True)
    connection_status = models.CharField(
        max_length=20,
        choices=[
            ('connected', 'Connected'),
            ('disconnected', 'Disconnected'),
            ('error', 'Error'),
        ],
        default='disconnected'
    )

    def test_connection(self):
        """Verify PACS is reachable with C-ECHO"""
        from pynetdicom import AE
        from pynetdicom.sop_class import Verification

        ae = AE(ae_title='OPENMEDLAB_TEST')
        ae.add_requested_context(Verification)

        assoc = ae.associate(self.host, self.port, ae_title=self.ae_title)

        if assoc.is_established:
            status = assoc.send_c_echo()
            assoc.release()

            self.connection_status = 'connected'
            self.last_connected = timezone.now()
            self.save()
            return True
        else:
            self.connection_status = 'error'
            self.save()
            return False


class DICOMTransaction(models.Model):
    """Audit log for all DICOM transactions"""

    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True)
    pacs_config = models.ForeignKey(PACSConfiguration, on_delete=models.SET_NULL, null=True)

    # Transaction details
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ('C-STORE', 'Store'),
            ('C-FIND', 'Find'),
            ('C-MOVE', 'Move'),
            ('C-GET', 'Get'),
            ('C-ECHO', 'Echo'),
        ]
    )
    direction = models.CharField(
        max_length=10,
        choices=[('incoming', 'Incoming'), ('outgoing', 'Outgoing')]
    )

    # Source/Destination
    source_ae = models.CharField(max_length=16)
    source_ip = models.GenericIPAddressField()
    dest_ae = models.CharField(max_length=16)

    # Study/Image info
    study_instance_uid = models.CharField(max_length=64, db_index=True)
    series_instance_uid = models.CharField(max_length=64, blank=True)
    sop_instance_uid = models.CharField(max_length=64, blank=True)
    patient_id_hash = models.CharField(max_length=64)  # Hashed for privacy

    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failure', 'Failure'),
            ('pending', 'Pending'),
        ]
    )
    error_message = models.TextField(blank=True)

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True)  # milliseconds

    # Metadata
    file_size_bytes = models.BigIntegerField(null=True)
    modality = models.CharField(max_length=16, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['started_at']),
            models.Index(fields=['study_instance_uid']),
            models.Index(fields=['status']),
        ]
        ordering = ['-started_at']
```

---

## 5. Monitoring & Auditing Requirements

### 5.1 Real-Time Monitoring Dashboard

**Key Metrics to Track:**

```python
# Gateway Health Metrics
- SCP Uptime (%)
- Active Connections (count)
- Queue Depth (pending studies)
- Processing Throughput (studies/hour)
- Average Processing Time (seconds)
- Error Rate (%)

# PACS Connectivity
- Connected PACS (count)
- Last Successful C-ECHO (timestamp per PACS)
- Connection Errors (count, last 24h)

# Resource Utilization
- CPU Usage (%)
- Memory Usage (GB)
- Disk I/O (MB/s)
- Network I/O (MB/s)
- Storage Capacity (% free)

# Transaction Metrics
- Total Transactions (last hour/day/week)
- C-STORE Success Rate (%)
- C-FIND Queries (count)
- Average Study Size (MB)
- Failed Transmissions (count)
```

**Dashboard Implementation:**

```python
# dicom_gateway/views.py

class DICOMGatewayMonitorView(APIView):
    """Real-time monitoring dashboard API"""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        """Get gateway statistics"""

        # Query recent transactions
        last_hour = timezone.now() - timedelta(hours=1)
        recent_transactions = DICOMTransaction.objects.filter(
            started_at__gte=last_hour
        )

        stats = {
            'gateway_health': {
                'status': get_gateway_status(),  # 'running' | 'stopped' | 'error'
                'uptime_seconds': get_uptime(),
                'active_connections': get_active_connection_count(),
                'queue_depth': get_pending_task_count(),
            },
            'pacs_connectivity': [
                {
                    'name': pacs.name,
                    'ae_title': pacs.ae_title,
                    'status': pacs.connection_status,
                    'last_connected': pacs.last_connected,
                    'test_result': pacs.test_connection(),
                }
                for pacs in PACSConfiguration.objects.filter(is_active=True)
            ],
            'transactions_last_hour': {
                'total': recent_transactions.count(),
                'c_store': recent_transactions.filter(transaction_type='C-STORE').count(),
                'c_find': recent_transactions.filter(transaction_type='C-FIND').count(),
                'success_rate': (
                    recent_transactions.filter(status='success').count() /
                    max(recent_transactions.count(), 1) * 100
                ),
                'avg_duration_ms': recent_transactions.aggregate(
                    avg=Avg('duration_ms')
                )['avg'],
            },
            'resource_usage': {
                'cpu_percent': psutil.cpu_percent(),
                'memory_used_gb': psutil.virtual_memory().used / (1024**3),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_free_gb': psutil.disk_usage('/data').free / (1024**3),
            },
            'alerts': get_active_alerts(),
        }

        return Response(stats)
```

### 5.2 Audit Trail Requirements

**Regulatory Compliance Logging:**

```python
class AuditEvent(models.Model):
    """HIPAA-compliant audit logging"""

    # Who
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    user_role = models.CharField(max_length=50)
    source_ip = models.GenericIPAddressField()

    # What
    event_type = models.CharField(
        max_length=50,
        choices=[
            ('dicom.receive', 'DICOM Image Received'),
            ('dicom.send', 'DICOM Image Sent'),
            ('phi.access', 'PHI Accessed'),
            ('phi.export', 'PHI Exported'),
            ('config.change', 'Configuration Changed'),
            ('pacs.connect', 'PACS Connection'),
            ('analysis.create', 'Analysis Task Created'),
        ]
    )
    action_description = models.TextField()

    # When
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Where
    component = models.CharField(max_length=50)  # 'gateway', 'backend', 'frontend'

    # Context
    study_uid = models.CharField(max_length=64, blank=True, db_index=True)
    patient_id_hash = models.CharField(max_length=64, blank=True)  # Never store real patient ID
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.IntegerField(null=True, blank=True)

    # Outcome
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    # Additional metadata
    metadata = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['timestamp', 'event_type']),
            models.Index(fields=['study_uid']),
            models.Index(fields=['user', 'timestamp']),
        ]

    @classmethod
    def log_phi_access(cls, user, study_uid, patient_id, action, source_ip):
        """Log access to protected health information"""
        import hashlib

        patient_id_hash = hashlib.sha256(patient_id.encode()).hexdigest()

        return cls.objects.create(
            user=user,
            user_role=user.role if hasattr(user, 'role') else 'unknown',
            source_ip=source_ip,
            event_type='phi.access',
            action_description=action,
            component='gateway',
            study_uid=study_uid,
            patient_id_hash=patient_id_hash,
        )
```

**Audit Report Generation:**

```python
def generate_audit_report(start_date, end_date, report_type='summary'):
    """Generate compliance audit report"""

    events = AuditEvent.objects.filter(
        timestamp__range=(start_date, end_date)
    )

    if report_type == 'summary':
        return {
            'period': f"{start_date} to {end_date}",
            'total_events': events.count(),
            'phi_access_count': events.filter(event_type='phi.access').count(),
            'failed_events': events.filter(success=False).count(),
            'unique_users': events.values('user').distinct().count(),
            'unique_studies': events.values('study_uid').distinct().count(),
            'events_by_type': events.values('event_type').annotate(
                count=Count('id')
            ),
            'events_by_user': events.values('user__username').annotate(
                count=Count('id')
            ).order_by('-count')[:10],
        }
    elif report_type == 'detailed':
        return events.values(
            'timestamp', 'user__username', 'event_type',
            'action_description', 'success', 'source_ip'
        ).order_by('-timestamp')
```

### 5.3 Alerting System

```python
class AlertRule(models.Model):
    """Configurable alert rules"""

    name = models.CharField(max_length=200)
    alert_type = models.CharField(
        max_length=50,
        choices=[
            ('connection_failure', 'PACS Connection Failure'),
            ('high_error_rate', 'High Error Rate'),
            ('queue_backup', 'Queue Backup'),
            ('disk_space_low', 'Low Disk Space'),
            ('unauthorized_access', 'Unauthorized Access Attempt'),
        ]
    )

    # Thresholds
    threshold_value = models.FloatField()
    threshold_duration_minutes = models.IntegerField(default=5)

    # Actions
    send_email = models.BooleanField(default=True)
    email_recipients = models.JSONField(default=list)
    send_sms = models.BooleanField(default=False)
    webhook_url = models.URLField(blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    last_triggered = models.DateTimeField(null=True, blank=True)


def check_alert_conditions():
    """Periodic task to check alert rules"""

    for rule in AlertRule.objects.filter(is_active=True):

        if rule.alert_type == 'connection_failure':
            # Check if any PACS connection has failed
            failed_pacs = PACSConfiguration.objects.filter(
                is_active=True,
                connection_status='error'
            )
            if failed_pacs.exists():
                trigger_alert(rule, f"PACS connection failures: {failed_pacs.count()}")

        elif rule.alert_type == 'high_error_rate':
            # Check error rate in last N minutes
            since = timezone.now() - timedelta(minutes=rule.threshold_duration_minutes)
            total = DICOMTransaction.objects.filter(started_at__gte=since).count()
            errors = DICOMTransaction.objects.filter(
                started_at__gte=since, status='failure'
            ).count()

            if total > 0 and (errors / total * 100) > rule.threshold_value:
                trigger_alert(rule, f"Error rate: {errors/total*100:.1f}%")

        elif rule.alert_type == 'queue_backup':
            # Check pending task queue depth
            pending = get_pending_task_count()
            if pending > rule.threshold_value:
                trigger_alert(rule, f"Queue depth: {pending} tasks pending")
```

---

## 6. Security & Compliance Considerations

### 6.1 HIPAA Compliance

**Technical Safeguards:**

```python
# Encryption at rest
- Database encryption (PostgreSQL pgcrypto)
- File system encryption (LUKS/dm-crypt)
- Backup encryption (AES-256)

# Encryption in transit
- TLS 1.3 for all HTTPS connections
- DICOM TLS for PACS connections (when supported)
- VPN tunnels for cloud deployments

# Access control
- Role-based access control (RBAC)
- Multi-factor authentication (MFA)
- Automatic session timeout
- Audit logging of all PHI access

# Data integrity
- DICOM file checksums (MD5/SHA-256)
- Database transaction logging
- Immutable audit logs
```

**Implementation:**

```python
# dicom_gateway/security.py

from cryptography.fernet import Fernet
from django.conf import settings

class PHIEncryption:
    """Encrypt sensitive patient data"""

    def __init__(self):
        self.cipher = Fernet(settings.PHI_ENCRYPTION_KEY)

    def encrypt_field(self, plaintext: str) -> str:
        """Encrypt a PHI field"""
        if not plaintext:
            return ''
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt_field(self, ciphertext: str) -> str:
        """Decrypt a PHI field"""
        if not ciphertext:
            return ''
        return self.cipher.decrypt(ciphertext.encode()).decode()


class DICOMAccessControl:
    """Control access to DICOM data"""

    @staticmethod
    def can_access_study(user, study):
        """Check if user can access study"""

        # Admin can access all
        if user.is_staff:
            return True

        # Check if user's organization owns the study
        if hasattr(user, 'organization'):
            if study.organization == user.organization:
                return True

        # Check if study is shared with user
        if study.shared_with.filter(id=user.id).exists():
            return True

        return False

    @staticmethod
    def log_access(user, study, action, request):
        """Log PHI access for audit"""
        AuditEvent.log_phi_access(
            user=user,
            study_uid=study.study_instance_uid,
            patient_id=study.patient_id,
            action=action,
            source_ip=get_client_ip(request),
        )
```

### 6.2 Network Security

```python
# dicom_gateway/middleware.py

class DICOMSourceIPWhitelist:
    """Only accept DICOM connections from approved IPs"""

    def __init__(self):
        self.allowed_ips = self._load_whitelist()

    def _load_whitelist(self):
        """Load allowed IPs from database"""
        ips = []
        for pacs in PACSConfiguration.objects.filter(is_active=True):
            ips.extend(pacs.allowed_source_ips)
        return set(ips)

    def is_allowed(self, source_ip):
        """Check if source IP is whitelisted"""
        return source_ip in self.allowed_ips

    def handle_connection(self, event):
        """Check source IP before accepting DICOM connection"""
        source_ip = event.assoc.remote['address']

        if not self.is_allowed(source_ip):
            logger.warning(f"Rejected DICOM connection from {source_ip}")
            event.assoc.abort()

            # Create security alert
            AuditEvent.objects.create(
                event_type='security.unauthorized_connection',
                action_description=f'Blocked DICOM connection from {source_ip}',
                source_ip=source_ip,
                success=False,
            )
            return False

        return True
```

### 6.3 Data Anonymization

```python
# dicom_gateway/anonymization.py

from pydicom import dcmread

class DICOMAnonymizer:
    """Remove/hash PHI from DICOM files"""

    # Tags to remove (DICOM Standard PS3.15 Annex E)
    TAGS_TO_REMOVE = [
        'PatientName',
        'PatientBirthDate',
        'PatientAddress',
        'PatientTelephoneNumbers',
        'InstitutionName',
        'InstitutionAddress',
        'ReferringPhysicianName',
        'PerformingPhysicianName',
        'OperatorsName',
        'StudyDescription',
        'SeriesDescription',
        # ... (full list from DICOM standard)
    ]

    # Tags to hash (keep for linking but de-identify)
    TAGS_TO_HASH = [
        'PatientID',
        'AccessionNumber',
        'StudyInstanceUID',  # Only if creating new UIDs
    ]

    def anonymize_file(self, file_path, output_path=None):
        """Anonymize a DICOM file"""
        import hashlib

        ds = dcmread(file_path)

        # Remove PHI tags
        for tag_name in self.TAGS_TO_REMOVE:
            if tag_name in ds:
                delattr(ds, tag_name)

        # Hash identifiers
        for tag_name in self.TAGS_TO_HASH:
            if tag_name in ds:
                original_value = str(getattr(ds, tag_name))
                hashed_value = hashlib.sha256(
                    (original_value + settings.ANONYMIZATION_SALT).encode()
                ).hexdigest()[:16]  # Use first 16 chars
                setattr(ds, tag_name, hashed_value)

        # Set to anonymized
        ds.PatientIdentityRemoved = 'YES'
        ds.DeidentificationMethod = 'OpenMedLab Auto-Anonymization'

        # Save
        output_path = output_path or file_path
        ds.save_as(output_path)

        logger.info(f"Anonymized DICOM file: {file_path}")
        return output_path
```

---

## 7. Recommended Architecture

Based on the evaluation, the recommended architecture is:

### **Microservice + Hybrid Deployment**

```
┌─────────────────────────────────────────────────────────────┐
│                      Hospital Environment                    │
│                                                              │
│  ┌──────────────┐         ┌───────────────────────────┐     │
│  │ Hospital     │  DICOM  │  DICOM Gateway            │     │
│  │ PACS         ├────────►│  (Docker Container)       │     │
│  │              │  11112  │                           │     │
│  └──────────────┘         │  - pynetdicom SCP         │     │
│                           │  - Metadata extraction    │     │
│  ┌──────────────┐         │  - Anonymization          │     │
│  │ Modalities   ├────────►│  - Local queue (Redis)    │     │
│  │ (CT/MR/etc)  │         │  - Monitoring agent       │     │
│  └──────────────┘         └───────────┬───────────────┘     │
│                                       │                      │
│                                       │ HTTPS/TLS            │
└───────────────────────────────────────┼──────────────────────┘
                                        │ VPN Tunnel
                                        │
┌───────────────────────────────────────▼──────────────────────┐
│                       Cloud Environment                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Django Backend (Auto-scaling)                       │   │
│  │  - REST API                                          │   │
│  │  - AI Model Registry                                 │   │
│  │  - Task Management                                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Celery Workers (GPU-enabled)                        │   │
│  │  - AI Model Inference                                │   │
│  │  - Result Processing                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Database Cluster                                    │   │
│  │  - PostgreSQL (RDS/Cloud SQL)                        │   │
│  │  - Redis (ElastiCache/Memorystore)                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Object Storage                                      │   │
│  │  - S3/GCS/Azure Blob                                 │   │
│  │  - Anonymized DICOM files                            │   │
│  │  - AI results                                        │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**Key Decisions:**

1. **DICOM Gateway On-Premises:**
   - PHI stays within hospital network
   - Low latency DICOM communication
   - Meets data residency requirements
   - Lightweight deployment (2-4 CPU cores, 8GB RAM)

2. **AI Processing in Cloud:**
   - Scalable GPU resources
   - Only anonymized data leaves hospital
   - Cost-effective for burst workloads
   - Easy model updates

3. **Communication:**
   - Encrypted HTTPS over VPN
   - JWT authentication
   - Compression for large images
   - Queue-and-forward for reliability

---

## 8. Implementation Roadmap

### Phase 1: Proof of Concept (4-6 weeks)

**Deliverables:**
- [ ] Basic DICOM SCP receiving C-STORE
- [ ] Metadata extraction and database storage
- [ ] Simple monitoring dashboard
- [ ] Single PACS configuration
- [ ] Docker Compose deployment

**Success Criteria:**
- Successfully receive DICOM from test PACS
- Process 100 studies/day
- <5 second processing time per image

### Phase 2: Production MVP (8-10 weeks)

**Deliverables:**
- [ ] Full DICOM service support (C-FIND, C-MOVE, C-ECHO)
- [ ] Multi-PACS configuration management
- [ ] Anonymization pipeline
- [ ] Audit logging and compliance reporting
- [ ] Alert system
- [ ] Admin UI for configuration
- [ ] Kubernetes deployment manifests

**Success Criteria:**
- Support 3+ simultaneous PACS connections
- Process 500+ studies/day
- 99% uptime
- HIPAA audit report generation

### Phase 3: Enterprise Features (10-12 weeks)

**Deliverables:**
- [ ] Auto-routing based on study characteristics
- [ ] DICOM SR (Structured Reporting) for AI results
- [ ] Worklist (MWL) integration
- [ ] Advanced monitoring (Prometheus/Grafana)
- [ ] Multi-tenancy support
- [ ] HL7 integration for RIS connectivity
- [ ] Disaster recovery procedures

**Success Criteria:**
- Support 10+ hospitals
- Process 5,000+ studies/day
- <10 minute end-to-end latency
- 99.9% uptime SLA

### Phase 4: Advanced Capabilities (Ongoing)

**Deliverables:**
- [ ] DICOM Web (DICOMweb) support
- [ ] FHIR integration for EHR connectivity
- [ ] Real-time inference streaming
- [ ] Multi-region deployment
- [ ] Advanced analytics dashboard
- [ ] Automated model selection (ML-based routing)

---

## 9. Cost Analysis

### Cloud + On-Prem Hybrid (Recommended)

**On-Premises Gateway (Per Hospital):**
- Hardware: $2,000 - $5,000 (one-time)
  - 1U server or VM allocation
  - 4 cores, 16GB RAM, 500GB SSD
- Network: $100-500/month (VPN connection)
- Maintenance: $200-500/month (monitoring, updates)

**Cloud Infrastructure (Shared):**
- Compute (Backend): $500-1,500/month
  - 2-4 instances, auto-scaling
- Compute (GPU Workers): $1,000-3,000/month
  - 2-4 GPU instances for AI inference
- Database: $300-800/month
  - PostgreSQL RDS, multi-AZ
- Storage: $200-1,000/month
  - S3/GCS for anonymized images and results
- Data Transfer: $300-1,500/month
  - Varies by volume

**Total Monthly Cost (10 hospitals):**
- On-prem (per hospital): $300-1,000/month × 10 = $3,000-10,000
- Cloud (shared): $2,300-7,800/month
- **Total: $5,300-17,800/month**

**Revenue Model:**
- Per-study pricing: $5-20/study
- At 500 studies/day across 10 hospitals: 5,000 studies/day
- Monthly revenue: 5,000 × 30 × $10 = $1,500,000/month
- **Gross margin: 98%+**

---

## 10. Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **PACS compatibility issues** | High | Comprehensive testing with major vendors (GE, Siemens, Philips), maintain compatibility matrix |
| **Network reliability** | High | Queue-and-forward architecture, local buffering, automatic retry |
| **Data loss** | Critical | Transaction logging, backup storage, redundant connections |
| **Security breach** | Critical | Defense in depth, encryption, access controls, regular audits |
| **Regulatory non-compliance** | Critical | HIPAA expert consultation, compliance automation, regular audits |
| **Scalability bottlenecks** | Medium | Load testing, horizontal scaling, performance monitoring |
| **Vendor lock-in** | Medium | Container-based deployment, cloud-agnostic architecture |

---

## 11. Conclusion

Implementing a DICOM-DIMSE gateway is a **strategic imperative** for OpenMedLab to transition from a research tool to a clinical-grade AI platform. The recommended **microservice + hybrid deployment** architecture provides:

✅ **Clinical Integration:** Seamless PACS connectivity without workflow disruption
✅ **Compliance:** HIPAA-compliant with PHI staying on-premises
✅ **Scalability:** Cloud AI processing with on-demand GPU resources
✅ **Flexibility:** Support both cloud and on-premises deployments
✅ **Economics:** High margins with per-study pricing model

**Recommended Next Steps:**

1. **Immediate (Week 1-2):**
   - Review and approve this evaluation
   - Identify pilot hospital partner
   - Set up test PACS environment (Orthanc or dcm4chee)

2. **Short-term (Month 1-2):**
   - Develop Phase 1 POC
   - Test with pilot hospital
   - Gather feedback and refine

3. **Medium-term (Month 3-6):**
   - Build production MVP
   - Obtain HIPAA compliance certification
   - Onboard 3-5 hospital customers

4. **Long-term (Month 6-12):**
   - Scale to 10+ hospitals
   - Add enterprise features
   - Expand to international markets

**ROI Projection:**
- Development cost: $200K-400K (6 months, 2-3 engineers)
- Break-even: ~5 hospitals at 500 studies/day each
- Expected ROI: 300-500% in Year 1

---

## Appendix A: Technology Stack

```yaml
DICOM Gateway Service:
  Language: Python 3.11+
  Framework: asyncio + pynetdicom
  Queue: Celery + Redis
  Database: PostgreSQL 17
  Monitoring: Prometheus + Grafana
  Deployment: Docker + Kubernetes

Integration Libraries:
  - pynetdicom: 2.1.1 (DICOM networking)
  - pydicom: 3.0.1 (DICOM parsing)
  - celery: 5.4.0 (async tasks)
  - redis: 5.2.1 (queue + cache)
  - sqlalchemy: 2.0+ (ORM, optional for gateway)

Security:
  - cryptography: 44.0+ (encryption)
  - django-encrypted-model-fields: 0.6+ (field-level encryption)

Monitoring:
  - prometheus-client: 0.21+
  - sentry-sdk: 2.19+ (error tracking)
  - structlog: 24.4+ (structured logging)
```

## Appendix B: DICOM Conformance Statement Template

*(Required for hospital integration, defines supported SOP classes, transfer syntaxes, and capabilities)*

## Appendix C: Sample Hospital Integration Checklist

- [ ] Legal: BAA (Business Associate Agreement) signed
- [ ] Security: Network security review completed
- [ ] Technical: PACS connection details obtained (AE title, IP, port)
- [ ] Compliance: PHI handling procedures documented
- [ ] Testing: Connection test successful (C-ECHO)
- [ ] Training: Hospital IT staff trained on monitoring
- [ ] Go-live: Cutover plan approved
- [ ] Support: 24/7 support contact established

---

**Document Version:** 1.0
**Last Updated:** 2025-12-25
**Author:** OpenMedLab Technical Team
**Status:** Pending Approval

# DICOM Transfer Pipeline — Architecture, Configuration & Fix Reference

> Last updated: 2026-03-18
> Status: ✅ All components operational

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Component Descriptors](#2-component-descriptors)
3. [Full Transfer Workflow](#3-full-transfer-workflow)
4. [Processing Flowchart](#4-processing-flowchart)
5. [Configuration Reference](#5-configuration-reference)
6. [Data Models](#6-data-models)
7. [API Endpoints](#7-api-endpoints)
8. [Fix History](#8-fix-history)
9. [Health Checks & Troubleshooting](#9-health-checks--troubleshooting)

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        External DICOM Sources                                │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │  Orthanc     │  │  Modality    │  │  PACS System │  │  Worklist MWL   │ │
│  │  Test PACS   │  │  (CT / MR)   │  │  (External)  │  │  (Optional)     │ │
│  │  :4242/:8042 │  │              │  │              │  │                 │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────────────┘ │
│         │  C-STORE         │  C-STORE          │  C-STORE                   │
└─────────┼──────────────────┼───────────────────┼────────────────────────────┘
          │                  │                   │
          └──────────────────┴───────────────────┘
                             │ DICOM (port 11112)
                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     DICOM Gateway Service                                     │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  DICOMGatewaySCP (pynetdicom)                         :11112        │    │
│  │  AE Title: OPENMEDLAB                                               │    │
│  │  - AllStoragePresentationContexts                                   │    │
│  │  - C-ECHO (Verification)                                            │    │
│  │  - IP whitelist check on EVT_REQUESTED                              │    │
│  └─────────────────────┬───────────────────────────────────────────────┘    │
│                         │ EVT_C_STORE                                        │
│                         ▼                                                    │
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │  DICOMEventHandlers.handle_store()                                 │     │
│  │  1. Save .dcm to /app/storage/dicom-temp/{study}/{series}/{uid}.dcm│     │
│  │  2. Extract metadata dict (UIDs, modality, source AE/IP, dims)     │     │
│  │  3. process_dicom_file.delay(file_path, metadata)  ──►  Redis      │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  FastAPI Management API  :8001                                               │
│  /health  /api/status  /api/stats  /api/config  /metrics                    │
└──────────────────────────────────────────────────────────────────────────────┘
                             │ Celery task (dicom_processing queue)
                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Gateway Celery Worker                                      │
│                    queue: dicom_processing                                    │
│                                                                              │
│  process_dicom_file(file_path, metadata)                                     │
│  ├── 1. Validate DICOM file (pydicom.dcmread)                                │
│  ├── 2. Optional: anonymize_dicom.delay(file_path)                           │
│  ├── 3. PACS user lookup → get_pacs_api_key(source_ae)                       │
│  │       └── POST /api/dicom/gateway/pacs-lookup/?ae_title=<AE>              │
│  ├── 4. JWT auth → get_auth_token_from_api_key(api_key)                      │
│  │       └── POST /users/auth/api-key/  →  Bearer <token>                   │
│  ├── 5. Upload DICOM → upload_to_backend(file_path, metadata, token)         │
│  │       └── POST /api/dicom/upload/medical/  (multipart/form-data)          │
│  └── 6. Audit log → log_transaction(metadata, 'success', duration)           │
│          └── POST /api/dicom/gateway/transactions/                           │
└──────────────────────────────────────────────────────────────────────────────┘
                             │ HTTP REST (internal Docker network)
                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Backend (Django + DRF)  :3080                        │
│                                                                              │
│  /api/dicom/upload/medical/          MedicalStudy ─► MedicalSeries           │
│  POST multipart DICOM file           ──► MedicalImage (FileField)            │
│                                                                              │
│  /api/dicom/gateway/transactions/    DICOMTransaction (audit log)            │
│  POST JSON payload                                                           │
│                                                                              │
│  /api/dicom/gateway/monitor/         DICOMTransferViewSet (read-only)        │
│  GET study-level aggregated view                                             │
│                                                                              │
│  PostgreSQL  ─────────────────────────────────────────────────────────────  │
│  ├── dicom_images_medicalstudy                                               │
│  ├── dicom_images_medicalseries                                              │
│  ├── dicom_images_medicalimage                                               │
│  ├── dicom_gateway_dicomtransaction   (audit trail)                          │
│  ├── dicom_gateway_pacsconfiguration  (PACS registry)                        │
│  └── dicom_gateway_gatewayhealth      (health snapshots)                     │
└──────────────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Frontend React :3000                                   │
│                                                                              │
│  /monitor                                                                    │
│  ├── TransferMonitorPanel (polling /api/dicom/gateway/monitor/)              │
│  ├── StatsDashboard (polling /api/dicom/gateway/monitor/stats/)              │
│  └── DICOMTransactionList (pagination, filters, search)                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Descriptors

### 2.1 DICOMGatewaySCP (`app/dicom-gateway/gateway/scp.py`)

| Property | Value |
|---|---|
| Protocol | DICOM upper layer (DIMSE) — TCP |
| Library | `pynetdicom` |
| Default AE Title | `OPENMEDLAB` |
| Default Port | `11112` |
| Accepted SOP classes | `AllStoragePresentationContexts` + C-ECHO Verification |
| Max PDU size | 16,384 bytes (configurable) |
| Max concurrent associations | 10 (configurable) |
| Network timeout | 30 s (configurable) |

**Lifecycle:**
- Single global `DICOMGatewaySCP` instance created at startup.
- `ae.start_server(block=True)` runs the DICOM listener on the main thread.
- `SIGINT` / `SIGTERM` handlers call `ae.shutdown_server()` for graceful teardown.

**Supported DICOM events:**

| Event | Handler | Description |
|---|---|---|
| `EVT_C_ECHO` | `handle_echo()` | Returns `0x0000` — used for connection testing |
| `EVT_C_STORE` | `handle_store()` | Saves DICOM file, queues async processing |
| `EVT_REQUESTED` | `handle_association_requested()` | IP whitelist enforcement |
| `EVT_RELEASED` | `handle_association_released()` | Log association close |
| `EVT_ABORTED` | `handle_association_aborted()` | Log unexpected abort |

---

### 2.2 DICOMEventHandlers (`app/dicom-gateway/gateway/handlers.py`)

Stateful handler class (single global instance `dicom_handlers`). Maintains in-memory statistics (`total_received`, `total_success`, `total_failed`, `last_received`).

**`handle_store()` steps:**

1. Extract `SOPInstanceUID`, `StudyInstanceUID`, `SeriesInstanceUID`, `PatientID` from dataset.
2. Compute storage path: `STORAGE_PATH/{study_uid}/{series_uid}/{instance_uid}.dcm`
3. `ds.save_as(file_path, write_like_original=False)` — saves raw DICOM to disk.
4. `_extract_metadata(ds, event)` — builds metadata dict (UIDs, modality, spatial dims, source AE/IP, timestamp).
5. If `AUTO_FORWARD_TO_BACKEND=True`: `process_dicom_file.delay(file_path, metadata)`.
6. Returns DICOM status `0x0000` (success) or `0xC000` (failure).

**File path scheme:**
```
/app/storage/dicom-temp/
  └── {study_uid_sanitized}/
        └── {series_uid_sanitized}/
              └── {instance_uid_sanitized}.dcm
```
UIDs are sanitized: dots replaced with underscores, truncated to 64 chars.

---

### 2.3 Gateway Celery Worker (`app/dicom-gateway/gateway/tasks.py`)

| Property | Value |
|---|---|
| Queue | `dicom_processing` |
| Broker | Redis (`redis://redis-openmedlab:6379/0`) |
| Task time limit | 600 s hard / 540 s soft |
| Max retries | 3 (60 s countdown between retries) |

**`process_dicom_file(file_path, metadata)` — main task:**

```
process_dicom_file
├── os.path.exists(file_path)          → FileNotFoundError if missing
├── dcmread(file_path)                 → validates DICOM structure
├── [if ENABLE_ANONYMIZATION]
│     anonymize_dicom.delay(file_path) → removes PHI tags, hashes PatientID
├── get_pacs_api_key(source_ae)
│     └── GET /api/dicom/gateway/pacs-lookup/?ae_title=<AE>
│           returns: user_email, api_key (via PACSConfiguration.node_user FK)
│           fallback: gateway service account credentials
├── get_auth_token_from_api_key(api_key)
│     └── POST /users/auth/api-key/  →  { access: "<JWT>" }
├── upload_to_backend(file_path, metadata, token)
│     └── POST /api/dicom/upload/medical/
│           multipart/form-data: file=<DICOM bytes>, metadata=<JSON>
│           returns: { uploaded_images: [{id, study_id, ...}] }
└── log_transaction(metadata, 'success'|'failure', duration, pacs_ae_title)
      └── POST /api/dicom/gateway/transactions/
            body: { transaction_type, direction, source_ae, source_ip,
                    study_instance_uid, series_instance_uid, sop_instance_uid,
                    patient_id_hash, status, file_size_bytes, modality,
                    transfer_duration_ms, error_message }
```

**`anonymize_dicom(file_path)` — optional PHI removal:**

Removes: `PatientName`, `PatientBirthDate`, `PatientAddress`, `PatientTelephoneNumbers`, `InstitutionName`, `InstitutionAddress`, `ReferringPhysicianName`, `PerformingPhysicianName`, `OperatorsName`.
Hashes `PatientID` with SHA-256 (first 16 chars of hex digest).
Adds `PatientIdentityRemoved = YES` and `DeidentificationMethod` tag.

---

### 2.4 Gateway FastAPI Service (`app/dicom-gateway/gateway/api.py`)

Internal management API, not exposed externally. Accessible within Docker network on port 8001.

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Health check (returns `{"status": "healthy"}`) |
| `/health` | GET | Full health response with SCP status |
| `/api/status` | GET | `GatewayStatus`: running, AE title, port, connections, queue |
| `/api/metrics` | GET | `SystemMetrics`: CPU%, memory%, disk% |
| `/api/stats` | GET | `DICOMStats`: received/success/failed counts, last received |
| `/api/config` | GET | Non-sensitive config (excludes passwords and API keys) |
| `/api/test-echo` | POST | Self C-ECHO test to verify SCP is responsive |
| `/metrics` | GET | Prometheus metrics (if `ENABLE_PROMETHEUS=True`) |

---

### 2.5 Backend Django App — `dicom_gateway` (`app/backend/dicom_gateway/`)

Provides the REST API layer that the gateway Celery worker calls into.

| View/ViewSet | URL | Purpose |
|---|---|---|
| `DICOMTransactionViewSet` | `/api/dicom/gateway/transactions/` | Create audit records from gateway; list/filter for monitoring |
| `DICOMTransferViewSet.monitor()` | `/api/dicom/gateway/monitor/` | Study-level aggregated transfer view for frontend |
| `DICOMTransferViewSet.stats()` | `/api/dicom/gateway/monitor/stats/` | Aggregate statistics (counts, rates, breakdowns by modality/PACS) |
| `pacs_lookup()` | `/api/dicom/gateway/pacs-lookup/` | Unauthenticated lookup: AE title → user ID + API key prefix |

**Permission model:**
- `pacs_lookup()` — no authentication (internal use only; returns no secrets).
- `DICOMTransactionViewSet.create()` — uses `AllowInternalCreatePermission` (bypasses standard JWT auth for gateway service).
- All read endpoints — require JWT, filter by organization scope.

---

### 2.6 PACSConfiguration Model

Represents a registered PACS system that can send DICOM to the gateway.

| Field | Type | Description |
|---|---|---|
| `name` | CharField | Human-readable PACS name |
| `ae_title` | CharField (unique) | DICOM Application Entity Title |
| `host` | CharField | PACS hostname/IP |
| `port` | IntegerField | DICOM port (default 104) |
| `node_user` | FK → User | Platform user who owns uploads from this PACS |
| `receiving_organization` | FK → Organization | Data scoping |
| `is_active` | BooleanField | Whether this PACS is enabled |
| `auto_analyze` | BooleanField | Trigger AI analysis on receipt |
| `auto_retrieve` | BooleanField | C-MOVE retrieve (Phase 2 roadmap) |
| `tls_enabled` | BooleanField | TLS transport for DICOM |
| `allowed_ips` | TextField | Comma-separated IP whitelist |

`test_connection()` method sends a C-ECHO to verify the PACS is reachable.

---

### 2.7 DICOMTransaction Model

Immutable audit record created once per DICOM instance transfer.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `transaction_type` | CharField | Always `'C-STORE'` currently |
| `direction` | CharField | `'incoming'` \| `'outgoing'` |
| `source_ae` | CharField | Sending AE title |
| `source_ip` | CharField | Sending IP address |
| `dest_ae` | CharField | Receiving AE title (OPENMEDLAB) |
| `study_instance_uid` | CharField | DICOM Study UID |
| `series_instance_uid` | CharField | DICOM Series UID |
| `sop_instance_uid` | CharField | DICOM Instance UID |
| `patient_id_hash` | CharField | SHA-256 hash of PatientID (privacy-safe) |
| `status` | CharField | `'success'` \| `'failure'` \| `'partial'` \| `'in_progress'` |
| `error_message` | TextField (null=True) | Failure reason; NULL for successful transfers |
| `file_size_bytes` | BigIntegerField | Raw DICOM file size |
| `modality` | CharField | DICOM modality (CT, MR, CR, etc.) |
| `transfer_duration_ms` | FloatField | End-to-end latency in ms |
| `started_at` | DateTimeField | Reception timestamp |
| `completed_at` | DateTimeField | Processing completion timestamp |

> **Fix applied (2026-01-06):** `error_message` was missing `null=True`. Gateway sent `error_message=None` for successful transfers, causing a `NOT NULL` constraint violation. See §8 for details.

---

## 3. Full Transfer Workflow

```
External PACS / Modality
        │
        │  (1) C-STORE request  [DICOM port 11112]
        │      DICOM file + DIMSE metadata
        ▼
DICOMGatewaySCP  [pynetdicom, blocking thread]
        │
        │  EVT_C_STORE fires synchronously
        ▼
DICOMEventHandlers.handle_store()
        │
        ├── (2) Save file:  /app/storage/dicom-temp/{study}/{series}/{uid}.dcm
        │
        ├── (3) Extract metadata:  UIDs, modality, source AE/IP, dims, timestamp
        │
        └── (4) Return 0x0000 to sender  [ACK — file received]
                 + enqueue async task ───────────────────────────────────────┐
                                                                             │
                                                                     Redis queue
                                                              'dicom_processing'
                                                                             │
                                                                             ▼
                                                          Gateway Celery Worker
                                                          process_dicom_file()
                                                                             │
        ┌────────────────────────────────────────────────────────────────────┘
        │
        │  (5) Validate:  dcmread() confirms valid DICOM structure
        │
        │  (6) Auth:  lookup PACSConfiguration by source AE title
        │             → returns node_user.id
        │             get_pacs_api_key() → GET /api/dicom/gateway/pacs-lookup/
        │             get_auth_token_from_api_key() → POST /users/auth/api-key/
        │             → Bearer <JWT access token>
        │
        │  (7) Upload:  POST /api/dicom/upload/medical/
        │               multipart: file=<bytes>, metadata=<JSON>
        │               → { uploaded_images: [{id, study_id, series_id}] }
        │               → MedicalStudy / MedicalSeries / MedicalImage rows created
        │
        │  (8) Audit:  POST /api/dicom/gateway/transactions/
        │              { transaction_type, source_ae, source_ip, UIDs,
        │                patient_id_hash, status='success', duration_ms }
        │              → DICOMTransaction row created
        ▼
Backend PostgreSQL
   ├── dicom_images_medicalstudy      (new or merged study)
   ├── dicom_images_medicalseries     (new or merged series)
   ├── dicom_images_medicalimage      (one row per DICOM instance)
   └── dicom_gateway_dicomtransaction (one row per DICOM instance — audit)
        │
        ▼
Frontend /monitor  (polling every 10 s)
   GET /api/dicom/gateway/monitor/
   → StudyTransferSerializer: aggregated per-study view
   → TransferStatsSerializer: overall counts, success rate, modality breakdown
```

---

## 4. Processing Flowchart

```
START: DICOM SCP receives EVT_C_STORE
          │
          ▼
 ┌─────────────────────┐
 │ IP in whitelist?    │──── NO ──► EVT_REQUESTED aborts association → END
 └─────────────────────┘
          │ YES
          ▼
 ┌──────────────────────────┐
 │ ds.save_as(file_path)    │──── FAIL ──► return 0xC000 (DICOM failure) → END
 └──────────────────────────┘
          │ OK
          ▼
 ┌────────────────────────────────┐
 │ process_dicom_file.delay()     │
 │ (returns 0x0000 immediately)   │
 └────────────────────────────────┘
          │
          ▼  [async, Gateway Celery Worker]
 ┌─────────────────────┐
 │ File exists?        │──── NO ──► log_transaction(failure) → RETRY (max 3) → END
 └─────────────────────┘
          │ YES
          ▼
 ┌─────────────────────┐
 │ dcmread() valid?    │──── NO ──► log_transaction(failure) → RETRY → END
 └─────────────────────┘
          │ YES
          ▼
 ┌───────────────────────────────────┐
 │ ENABLE_ANONYMIZATION?             │──── YES ──► anonymize_dicom.delay()
 └───────────────────────────────────┘              (runs in parallel)
          │ (continue regardless)
          ▼
 ┌─────────────────────────────────────────────────────┐
 │ PACSConfiguration for source_ae?                    │
 │  YES: GET /api/dicom/gateway/pacs-lookup/           │
 │       → user_email, api_key                         │
 │       → POST /users/auth/api-key/ → JWT             │
 │  NO:  use gateway service account JWT               │
 └─────────────────────────────────────────────────────┘
          │
          ▼
 ┌────────────────────────────────────────────┐
 │ POST /api/dicom/upload/medical/            │
 │ multipart: file + metadata JSON            │──── FAIL ──► RETRY (max 3)
 │ Authorization: Bearer <JWT>                │               → log_transaction(failure)
 └────────────────────────────────────────────┘               → END
          │ HTTP 200
          ▼
 ┌──────────────────────────────────────────────────────┐
 │ POST /api/dicom/gateway/transactions/                │
 │ { transaction_type: "C-STORE", direction: "incoming" │
 │   source_ae, source_ip, study/series/sop UIDs        │
 │   patient_id_hash (SHA-256), status: "success"       │
 │   file_size_bytes, modality, transfer_duration_ms    │
 │   error_message: null  ← requires null=True on field │
 └──────────────────────────────────────────────────────┘
          │
          ▼
        END — transaction visible in /monitor within one polling cycle
```

---

## 5. Configuration Reference

### 5.1 Gateway Service — Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DICOM_AE_TITLE` | `OPENMEDLAB` | Application Entity Title advertised to PACS systems |
| `DICOM_PORT` | `11112` | TCP port the DICOM SCP listens on |
| `DICOM_HOST` | `0.0.0.0` | Bind address (0.0.0.0 = all interfaces) |
| `DICOM_MAX_PDU_LENGTH` | `16384` | Maximum PDU data unit in bytes |
| `DICOM_TIMEOUT` | `30` | Network inactivity timeout in seconds |
| `MAX_CONCURRENT_ASSOCIATIONS` | `10` | Max simultaneous DICOM connections |
| `STORAGE_PATH` | `/app/storage/dicom-temp` | Temporary DICOM file storage |
| `MAX_STORAGE_GB` | `100` | Storage quota (soft limit for alerts) |
| `BACKEND_API_URL` | `http://backend:8000` | Django backend base URL (internal Docker network) |
| `BACKEND_SERVICE_EMAIL` | `gateway@openmedlab.system` | Service account email |
| `BACKEND_SERVICE_PASSWORD` | — | Service account password (set via Docker secrets) |
| `PACS_USER_API_KEYS` | `{}` | JSON: `{"user@email": "oml_...key"}` — maps PACS owners to API keys |
| `REDIS_URL` | `redis://redis:6379/0` | Redis broker URL |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Celery broker |
| `ALLOWED_SOURCE_IPS` | `["0.0.0.0/0"]` | IP whitelist for incoming associations (CIDR list) |
| `ENABLE_TLS` | `False` | Enable DICOM TLS transport |
| `ENABLE_ANONYMIZATION` | `False` | Auto-anonymize on receipt before backend upload |
| `AUTO_FORWARD_TO_BACKEND` | `True` | Queue Celery processing task on receipt |
| `API_PORT` | `8001` | FastAPI management port |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `ENABLE_PROMETHEUS` | `True` | Expose `/metrics` endpoint |

### 5.2 Backend — Relevant Settings (`backend/settings.py`)

| Setting | Default | Description |
|---|---|---|
| `ORTHANC_URL` | `http://orthanc-test-pacs:8042` | Orthanc REST API base URL (used for DICOM SEG uploads) |
| `ORTHANC_USERNAME` | `orthanc` | Orthanc basic auth username |
| `ORTHANC_PASSWORD` | `orthanc` | Orthanc basic auth password |
| `MEDIA_ROOT` | `/var/www/app/backend/media` | Local file storage root |

### 5.3 Docker Compose Services — Port Map

| Service | Container Name | Exposed Ports | Description |
|---|---|---|---|
| `frontend-openmedlab` | `frontend-openmedlab` | `3000:3000` | React dev server |
| `backend-openmedlab` | `backend-openmedlab` | `3080:3080` | Django ASGI (Daphne) |
| `db-openmedlab` | `db-openmedlab` | `5444:5432` | PostgreSQL 17 |
| `redis-openmedlab` | `redis-openmedlab` | `6379:6379` | Redis 7 (broker + cache) |
| `celery-worker-openmedlab` | — | — | Queues: `ai_jobs`, `monitoring`, `default` |
| `celery-beat-openmedlab` | — | — | Periodic task scheduler |
| `dicom-gateway-openmedlab` | `dicom-gateway` | `11112:11112`, `8001:8001` | DICOM SCP + FastAPI |
| `gateway-celery-worker` | `gateway-celery-worker` | — | Queue: `dicom_processing` |
| `orthanc-test-pacs` | `orthanc-test-pacs` | `4242:4242`, `8042:8042` | Test PACS server |
| `orchestrator-openmedlab` | `orchestrator-openmedlab` | `50050:50050` | gRPC AI orchestrator |
| `orchestrator-redis` | `orchestrator-redis` | `6380:6379` | Separate Redis for orchestrator |

### 5.4 Celery Queue Routing

| Queue | Worker | Tasks |
|---|---|---|
| `ai_jobs` | `celery-worker-openmedlab` | `dispatch_ai_job`, `retry_failed_task` |
| `monitoring` | `celery-worker-openmedlab` | `check_task_timeouts`, `sync_orchestrator_status` |
| `default` | `celery-worker-openmedlab` | `cleanup_old_tasks`, `create_dicom_seg_task`, anonymization/conversion/batch tasks |
| `dicom_processing` | `gateway-celery-worker` | `process_dicom_file`, `anonymize_dicom`, `cleanup_old_files` |

### 5.5 Orthanc Configuration (`setup/orthanc.json`) — Key Settings

| Setting | Value | Notes |
|---|---|---|
| `Name` | `Orthanc Test PACS` | Human-readable name |
| `AETitleOfOrthancInstance` | `ORTHANC` | AE Title for outbound C-STORE |
| `HttpPort` | `8042` | REST API and OHIF WebViewer |
| `DicomPort` | `4242` | DICOM SCP port on Orthanc side |
| `StorageDirectory` | `/var/lib/orthanc/db` | Persistent study storage |
| `AuthenticationEnabled` | `true` | Requires `orthanc:orthanc` credentials |

**Configured DICOM modalities (remote AE entries for C-STORE):**
- `OPENMEDLAB` → `dicom-gateway-openmedlab:11112` — the gateway, used when sending studies from Orthanc to the platform.

---

## 6. Data Models

### DICOMTransaction — Full Schema

```
dicom_gateway_dicomtransaction
──────────────────────────────────────────────────────────
id                    UUID        PK, auto
transaction_type      VARCHAR(20) 'C-STORE' | 'C-FIND' | 'C-MOVE' | 'C-GET'
direction             VARCHAR(20) 'incoming' | 'outgoing'
source_ae             VARCHAR(16)
source_ip             VARCHAR(45) (supports IPv6)
dest_ae               VARCHAR(16)
study_instance_uid    VARCHAR(64) indexed
series_instance_uid   VARCHAR(64)
sop_instance_uid      VARCHAR(64) indexed
patient_id_hash       VARCHAR(64) SHA-256 hash (privacy-safe)
status                VARCHAR(20) 'success' | 'failure' | 'partial' | 'in_progress'
error_message         TEXT        NULL=True, BLANK=True  ← fixed 2026-01-06
file_size_bytes       BIGINT
modality              VARCHAR(16)
transfer_duration_ms  FLOAT
pacs_config           FK → PACSConfiguration (nullable)
started_at            TIMESTAMPTZ indexed
completed_at          TIMESTAMPTZ
```

### PACSConfiguration — Full Schema

```
dicom_gateway_pacsconfiguration
──────────────────────────────────────────────────────────
id                      INTEGER     PK, auto
name                    VARCHAR(100)
ae_title                VARCHAR(16) unique, indexed
description             TEXT
manufacturer            VARCHAR(100)
host                    VARCHAR(255)
port                    INTEGER     default 104
pdu_length              INTEGER     default 16384
timeout_seconds         INTEGER     default 30
node_user               FK → User   nullable (maps PACS → platform user)
receiving_organization  FK → Organization nullable
is_active               BOOLEAN     default True
auto_retrieve           BOOLEAN     default False
auto_analyze            BOOLEAN     default False
tls_enabled             BOOLEAN     default False
tls_cert_path           VARCHAR(500)
allowed_ips             TEXT        comma-separated CIDRs
created_at              TIMESTAMPTZ
updated_at              TIMESTAMPTZ
last_seen_at            TIMESTAMPTZ
total_transfers         INTEGER
successful_transfers    INTEGER
failed_transfers        INTEGER
```

---

## 7. API Endpoints

### 7.1 `GET /api/dicom/gateway/monitor/`

Study-level aggregated transfer view for the Monitor frontend panel.

**Query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `scope` | string | `own` \| `colleagues` \| `department` \| `team` |
| `status` | string | `success` \| `failure` \| `partial` \| `in_progress` |
| `modality` | string | Filter by DICOM modality |
| `source_ae` | string | Filter by sending AE title |
| `date_from` | date | ISO 8601 start date |
| `date_to` | date | ISO 8601 end date |
| `search` | string | Search on study UID or patient hash |
| `page` | int | Page number (page size: 20) |

**Response:** `StudyTransferSerializer` — one entry per study with aggregated counts:
```json
{
  "count": 12,
  "results": [{
    "study_instance_uid": "1.2.840...",
    "source_pacs_name": "Orthanc Test PACS",
    "source_ae_title": "ORTHANC",
    "modality": "MR",
    "total_instances": 176,
    "successful_instances": 176,
    "failed_instances": 0,
    "first_received": "2026-01-06T09:00:00Z",
    "last_received":  "2026-01-06T09:00:45Z",
    "transfer_duration_seconds": 45,
    "total_size_bytes": 12400000
  }]
}
```

### 7.2 `GET /api/dicom/gateway/monitor/stats/`

Dashboard statistics. No query parameters required.

**Response:** `TransferStatsSerializer`:
```json
{
  "total_transfers": 56,
  "total_instances": 8400,
  "success_count": 54,
  "failure_count": 2,
  "partial_count": 0,
  "in_progress_count": 0,
  "success_rate": 96.4,
  "avg_transfer_time_seconds": 38.2,
  "total_data_bytes": 714000000,
  "by_modality": {"MR": 32, "CT": 18, "CR": 6},
  "by_source_pacs": {"ORTHANC": 56},
  "by_status": {"success": 54, "failure": 2}
}
```

### 7.3 `POST /api/dicom/gateway/transactions/`

Called by the gateway Celery worker after each DICOM instance is processed.
Uses `AllowInternalCreatePermission` — no user JWT required.

**Request body:**
```json
{
  "transaction_type": "C-STORE",
  "direction": "incoming",
  "source_ae": "ORTHANC",
  "source_ip": "172.20.0.5",
  "dest_ae": "OPENMEDLAB",
  "study_instance_uid": "1.2.840...",
  "series_instance_uid": "1.2.840...",
  "sop_instance_uid": "1.2.840...",
  "patient_id_hash": "a3f7b2c1...",
  "status": "success",
  "error_message": null,
  "file_size_bytes": 524288,
  "modality": "MR",
  "transfer_duration_ms": 412.5
}
```

### 7.4 `GET /api/dicom/gateway/pacs-lookup/?ae_title=ORTHANC`

Unauthenticated endpoint for the gateway to resolve an AE title to a platform user and API key.

**Response:**
```json
{
  "found": true,
  "user_id": 3,
  "user_email": "radiologist@hospital.com",
  "api_key_prefix": "oml_abc12",
  "organization_id": 1,
  "pacs_name": "Radiology PACS"
}
```
Returns `{"found": false}` if no PACSConfiguration matches the AE title.

---

## 8. Fix History

### Fix 5 (Current) — 2026-01-06: NULL error_message Database Constraint

**Problem:** `DICOMTransaction.error_message` was defined as `TextField(blank=True)` with no `null=True`. Django created the column as `NOT NULL`. The gateway sent `error_message=None` for successful transfers, causing:
```
psycopg2.errors.NotNullViolation: null value in column "error_message"
of relation "dicom_gateway_dicomtransaction" violates not-null constraint
```

**Impact:**
- No audit trail for any incoming transfers (all transaction creates failed with HTTP 500)
- Monitor panel showed empty data
- Statistics not calculated

**Fix:**
```python
# app/backend/dicom_gateway/models.py  line 189
# Before:
error_message = models.TextField(blank=True)
# After:
error_message = models.TextField(blank=True, null=True)
```

Migration `0002_allow_null_error_message` applied to alter the column constraint.

---

### Fix 4 — Status Field Value Mismatch

**Problem:** Gateway sent `status='failed'`; model choices required `'failure'`.
**Fix:** Updated `log_transaction()` in `gateway/tasks.py` to use `'failure'`.

### Fix 3 — Authentication Failure

**Problem:** Gateway service account did not exist in the platform database.
**Fix:** Created `gateway@openmedlab.system` user via `setup_project` management command. Added to `docker-compose.yml` init sequence.

### Fix 2 — `ALLOWED_HOSTS` Rejection

**Problem:** Django rejected requests from `backend-openmedlab` hostname (Docker internal name).
**Fix:** Added `backend-openmedlab` to `ALLOWED_HOSTS` in `settings.py`.

### Fix 1 — Queue Routing Mismatch

**Problem:** `task_default_queue` was not set in the gateway Celery config; tasks were routed to the `default` queue but the gateway worker listened on `dicom_processing`.
**Fix:** Added `task_default_queue='dicom_processing'` to `celery_app.conf.update()` in `gateway/tasks.py`.

---

## 9. Health Checks & Troubleshooting

### Quick Status Check
```bash
# All services running
docker compose ps

# Gateway SCP listening
docker compose logs dicom-gateway-openmedlab | grep "DICOM SCP"

# Gateway Celery ready
docker compose logs gateway-celery-worker | grep "ready"

# Backend API reachable
curl http://localhost:3080/api/docs/

# Transaction count
docker compose exec backend-openmedlab python manage.py shell -c "
from dicom_gateway.models import DICOMTransaction
print(f'Total: {DICOMTransaction.objects.count()}')
print(f'Success: {DICOMTransaction.objects.filter(status=\"success\").count()}')
print(f'Failed:  {DICOMTransaction.objects.filter(status=\"failure\").count()}')
"
```

### Send a Test DICOM (from Orthanc)

1. Open `http://localhost:8042` (credentials: `orthanc / orthanc`)
2. Upload a DICOM study via the Orthanc web UI
3. In the study view, click **Send to DICOM modality** → `OPENMEDLAB`
4. Monitor:
```bash
# Watch gateway receive
docker compose logs -f dicom-gateway-openmedlab | grep "C-STORE"

# Watch Celery process
docker compose logs -f gateway-celery-worker | grep -E "Uploaded|Transaction|success|error"

# Verify DB record
docker compose exec backend-openmedlab python manage.py shell -c "
from dicom_gateway.models import DICOMTransaction
from django.utils import timezone; from datetime import timedelta
recent = DICOMTransaction.objects.filter(
    started_at__gte=timezone.now()-timedelta(minutes=5)
).order_by('-started_at')[:5]
for tx in recent:
    print(f'{tx.started_at:%H:%M:%S} | {tx.modality:4} | {tx.status:8} | {tx.source_ae}')
"
```

### Test Direct Transaction Create (verifies DB constraint fix)
```bash
docker compose exec backend-openmedlab python manage.py shell -c "
from dicom_gateway.models import DICOMTransaction
tx = DICOMTransaction.objects.create(
    transaction_type='C-STORE', direction='incoming',
    source_ae='TEST', source_ip='127.0.0.1', dest_ae='OPENMEDLAB',
    study_instance_uid='1.2.3.TEST', series_instance_uid='1.2.3.TEST.1',
    sop_instance_uid='1.2.3.TEST.1.1', patient_id_hash='testhash',
    status='success', error_message=None
)
print(f'Created: {tx.id} | error_message={tx.error_message}')
"
```

### Verify Migrations Are Applied
```bash
docker compose exec backend-openmedlab python manage.py showmigrations dicom_gateway
# Expected:
#  [X] 0001_initial
#  [X] 0002_allow_null_error_message
```

### Common Failure Patterns

| Symptom | Probable Cause | Resolution |
|---|---|---|
| Monitor panel empty | Transactions failing to create | Check Celery logs for HTTP 500 errors |
| `NotNullViolation` on `error_message` | Missing migration | Run `migrate dicom_gateway` |
| `ALLOWED_HOSTS` 400 error | Backend hostname not whitelisted | Add container name to `ALLOWED_HOSTS` |
| `401 Unauthorized` on upload | Service account missing or wrong password | Re-run `setup_project` command |
| Tasks stuck in queue | Gateway worker not running or wrong queue | Check `gateway-celery-worker` logs |
| `0xC000` C-STORE failure | File save failed (disk full, permissions) | Check `STORAGE_PATH` disk usage |
| No transactions after successful upload | `log_transaction()` failing silently | Check Celery task logs for `log_transaction` errors |

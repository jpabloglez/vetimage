# OpenMedLab — Feature Opportunities

> Last updated: 2026-03-18
> Sources: ROADMAP Phase 5–6, OpenMEDLab research (docs/references/), OMLAB-012 BIDS work

---

## How to use this document

Each entry includes: what it is, why it matters, the technical approach, estimated effort, and priority.
Effort is relative to the current codebase size (S = 1–2 days, M = 3–7 days, L = 1–3 weeks).

---

## Section 1 — AI Models & Connectors

### 1.1 nnU-Net Universal Connector

**What:** A single `NNUNetConnector` class that covers STU-Net, MIS-FM, A-Eval, and any other model built on nnU-Net — the de-facto segmentation framework used by most OpenMEDLab models.

**Why:** All nnU-Net models share an identical CLI: `nnUNet_predict -i <dir> -o <dir> -t <task_id> -m 3d_fullres`. Writing one connector handles many models instead of one per model.

**Technical approach:**
```python
# ai_analysis/connectors/nnunet.py
class NNUNetConnector(BaseAIConnector):
    def prepare_input(self, task):
        # DICOM → NIfTI via dcm2niix (reuse bids_utils.run_dcm2niix)
        from dicom_images.services.bids_utils import run_dcm2niix
        ...

    def dispatch_job(self, task):
        task_id = task.model.metadata.get('nnunet_task_id')
        subprocess.run(['nnUNet_predict', '-i', input_dir, '-o', output_dir,
                        '-t', task_id, '-m', '3d_fullres'], ...)
```

Add `nnunet_task_id` and `nnunet_config` to `AIModel.metadata`. Register STU-Net-S/B/L/H and MIS-FM as rows pointing to `NNUNetConnector` with different `task_id` values.

**No gRPC orchestrator needed** — local subprocess, same pattern as FastSurfer.

**Effort:** M | **Priority:** High

---

### 1.2 DICOM SEG Round-Trip (Segmentation → OHIF Overlay)

**What:** After a segmentation task completes, convert the NIfTI mask output back to a DICOM SEG object, push it to Orthanc, and surface a "View in Viewer" button in the Monitor panel that opens OHIF with the overlay pre-loaded.

**Why:** All segmentation models output `.nii.gz` masks; these are currently only available as file downloads. Radiologists need the overlay on the original image in the viewer to act on results.

**Technical approach:**
```python
# dicom_images/tasks.py (new post-processing task)
@app.task(queue='default')
def convert_seg_to_dicom_seg(task_id):
    task = AnalysisTask.objects.get(id=task_id)
    nifti_mask = task.result_file_path
    source_series = task.input_image.series

    # highdicom or pydicom-seg
    seg_dcm = create_dicom_seg(nifti_mask, source_series, label_map=task.model.label_map)
    orthanc_client.upload(seg_dcm)
    task.result_metadata['dicom_seg_series_uid'] = seg_dcm.SeriesInstanceUID
    task.save()
```

Frontend: after task `COMPLETED`, show "View in Viewer" button opening OHIF with `SeriesInstanceUID` of the SEG object.

**Libraries:** `highdicom` (modern, pip-installable) or `pydicom-seg` (simpler API).

**Effort:** L | **Priority:** High

---

### 1.3 Organ Label Taxonomy in AIModel Registry

**What:** Add a `label_map` JSON field to `AIModel` mapping integer labels to anatomy names. Use it in the `ReportBuilder` to produce structured volume measurements instead of generic "Segmentation completed, N labels found."

**Why:** Segmentation masks without a label map are uninterpretable. TotalSegmentator uses 104-organ maps; A-Eval defines 8 cross-dataset shared organs.

**Technical approach:**
```python
# dicom_images/models.py
label_map = models.JSONField(
    default=dict,
    help_text='e.g. {"1": "liver", "2": "spleen", "3": "right_kidney"}'
)
```

```python
# ai_analysis/services/report_builder.py
# Instead of: "Segmentation completed, 5 labels found"
# Generate:   "Liver: 1,245 cm³ | Spleen: 187 cm³ | Right Kidney: 142 cm³"
```

Reference: [TotalSegmentator label map](https://github.com/wasserth/TotalSegmentator/blob/master/totalsegmentator/map_to_binary.py) for all 104 organs.

**Effort:** S | **Priority:** Medium

---

### 1.4 Automated Radiology Report Generation

**What:** After AI analysis completes on a chest X-ray (or other imaging modality), provide an optional "Generate Draft Report" button. A Celery task calls a report-gen microservice and pre-fills the `Report.content.findings` field for radiologist review.

**Why:** XrayPULSE (MedCLIP + Q-former + LLM) demonstrates the pattern. Radiologists save time reviewing a draft versus writing from scratch.

**Technical approach:**
```python
# ai_analysis/connectors/report_gen.py
class ReportGenConnector(BaseAIConnector):
    def dispatch_job(self, task):
        image_b64 = encode_dicom_thumbnail(task.input_image)
        response = requests.post(self.endpoint_url, json={
            "image": image_b64,
            "modality": task.input_image.series.modality,
            "findings": task.result_metadata.get("findings", {}),
        })
        return response.json()["report_text"]
```

The returned text pre-fills `Report.content.findings`. Radiologist reviews and sets `status: DRAFT → FINAL`.

**Open-source LLM options (non-CC-BY-NC):**
- Meditron-7B (EPFL, Apache 2.0)
- BioMistral-7B (Apache 2.0)

**Effort:** L | **Priority:** High

---

### 1.5 Few-Shot Adapter Fine-Tuning Workflow

**What:** Let clinicians adapt a foundation model to their institution's specific pathology/protocol using as few as 1–10 labeled examples, without retraining the full model.

**Why:** MedFM (NeurIPS 2023) demonstrates that adapter-only fine-tuning with a frozen backbone is competitive with full fine-tuning in low-data regimes. Clinical datasets are small and access-restricted.

**Technical approach:**
```python
# ai_analysis/tasks.py
@app.task(queue='ai_jobs')
def run_adapter_finetuning(base_model_key, dataset_zip_path, num_shots, user_id):
    # Unzip, validate format (NIfTI + label file)
    # Run MMPreTrain adapter training (config-driven, no base weight modification)
    # Register new AIModel row with parent_model=base_model_key
```

Add a "Fine-tune" tab to the AIModel detail page. Training progress streamed via existing WebSocket consumer.

**Framework:** MMPreTrain (used by MedFM), supports config-driven adapter training.

**Effort:** L | **Priority:** Medium (Future)

---

### 1.6 Anonymization as Mandatory Pre-processing Gate

**What:** Add a `requires_anonymization` flag to `AIModel`. When `True`, creating an analysis task on that model requires a completed `AnonymizationJob` with `profile in ['full', 'research']` for the same study.

**Why:** All public training datasets (FLARE22, AMOS, BTCV, etc.) required full DICOM de-identification before use. This enforces the same requirement programmatically for models intended for research/publication workflows.

**Technical approach:**
```python
# ai_analysis/models.py
requires_anonymization = models.BooleanField(default=False)

# ai_analysis/views.py — in create():
if task.model.requires_anonymization:
    anon_job = AnonymizationJob.objects.filter(
        study=task.input_image.series.study,
        status='COMPLETED',
        profile__in=['full', 'research'],
    ).first()
    if not anon_job:
        raise ValidationError(
            "This model requires the study to be anonymized first."
        )
```

**Effort:** S | **Priority:** Medium

---

### 1.7 Shared DICOM→NIfTI Utility

**What:** Refactor the duplicated `dcm2niix` subprocess invocations (FastSurfer connector + BIDS anonymizer) into a single shared utility in `ai_analysis/connectors/utils.py`.

**Why:** Currently dcm2niix is invoked in at least two places with slightly different subprocess calls. Every new connector (nnU-Net, BrainMVP, etc.) will need the same conversion — a shared utility prevents drift.

**Technical approach:**
```python
# ai_analysis/connectors/utils.py
def dicom_series_to_nifti(series, output_dir: Path, stem: str) -> list[Path]:
    """
    DICOM series → NIfTI via dcm2niix.
    Returns list of produced .nii.gz files.
    Delegates to dicom_images.services.bids_utils.run_dcm2niix().
    """
    from dicom_images.services.bids_utils import run_dcm2niix
    dicom_dir = write_dicoms_to_tmpdir(series)
    return run_dcm2niix(dicom_dir, output_dir, stem)
```

`prepare_input()` in all connectors calls this single function.

**Effort:** S | **Priority:** Low (cleanup)

---

### 1.8 Multi-Parametric MRI Support

**What:** Extend `AnalysisTask` to accept multiple input images (e.g., T1 + T2 + FLAIR + DWI for the same study), generalizing the current PICAI `adc_image_id` hack into a first-class multi-input API.

**Why:** Multi-parametric MRI (mpMRI) is a standard clinical protocol for brain, prostate, and breast imaging. BrainMVP is pre-trained on 16,022 mpMRI scans and requires concurrent series as input.

**Technical approach:**
```python
# ai_analysis/models.py
input_images = models.ManyToManyField(
    MedicalImage, related_name='analysis_tasks', blank=True
)
input_image = models.ForeignKey(...)  # keep for backward compat (primary image)
```

The `AIModel.required_parameters` schema specifies additional modalities:
```json
{
  "t2w_image_id": { "type": "integer", "description": "T2W series", "required": true },
  "adc_image_id":  { "type": "integer", "description": "ADC map",    "required": true }
}
```

**Effort:** M | **Priority:** Medium (Future)

---

### 1.9 WSI (Whole Slide Image) Modality Support

**What:** Accept DICOM WSI SOP class uploads, store efficiently (S3 or dedicated tile store), serve tiles to OHIF, and dispatch to pathology models (PathoDuet, BROW, CITE).

**Why:** WSI pathology is the largest underserved modality in the current platform. PathoDuet achieves AUC 0.956 on Camelyon16; BROW gets 0.9511 classification accuracy on TCGA-RCC.

**Technical approach:**
1. DICOM Gateway: add WSI SOP class (`1.2.840.10008.5.1.4.1.1.77.1.6`) acceptance in C-STORE.
2. Storage: S3-compatible backend for large files (1–10 GB per slide).
3. Viewer: OHIF v3 has basic DICOM WSI support; tile-serving endpoint needed.
4. AI connector: extract `.svs`/`.tiff` from DICOM WSI using `wsidicomizer` or `openslide`.

**Effort:** L | **Priority:** Medium (Future — depends on S3 storage)

---

### 1.10 Model Benchmarking / QA Module

**What:** A `ModelBenchmark` model and associated API where users upload ground-truth masks/labels and trigger a benchmark run. Results (DSC, NSD, accuracy, BLEU) are stored and displayed on the AIModel detail page.

**Why:** Before enabling a model for research use, institutions need to verify it meets their quality bar on their own patient population. A-Eval and PULSE-EVAL define rigorous benchmarking methodologies that can be adapted here.

**Technical approach:**
```python
# ai_analysis/models.py
class ModelBenchmark(models.Model):
    ai_model       = models.ForeignKey(AIModel, on_delete=models.CASCADE)
    dataset_name   = models.CharField(max_length=100)
    metric_name    = models.CharField(max_length=50)  # 'DSC', 'NSD', 'accuracy'
    score          = models.FloatField()
    num_samples    = models.IntegerField()
    evaluated_at   = models.DateTimeField(auto_now_add=True)
    evaluated_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes          = models.TextField(blank=True)
```

Exposed at `/api/ai-analysis/models/{key}/benchmarks/`.

**Effort:** M | **Priority:** Medium

---

## Section 2 — Platform Infrastructure

### 2.1 Fine-Grained RBAC

**What:** Per-study, per-series, and per-model access controls rather than the current organization-level scope. Roles include: Viewer (read-only), Analyst (can run AI), Radiologist (can finalize reports), Admin.

**Why:** Clinical research requires that patient data access is tightly scoped. Currently any user in an organization can see all studies. HIPAA/GDPR mandates minimum-necessary access.

**Technical approach:**
- Add `StudyPermission(study, user, permission_level)` model.
- DRF permission class `HasStudyPermission` checks row-level access.
- Admin UI to assign permissions per study or bulk-assign per project.
- Migrate existing data: all current users get full access to their organization's studies.

**Effort:** L | **Priority:** High

---

### 2.2 DICOM Gateway Phase 2 — Query/Retrieve (C-FIND / C-MOVE)

**What:** Extend the DICOM Gateway from passive C-STORE receiver to an active query/retrieve node. Allow the platform to query external PACS (C-FIND) and pull specific studies (C-MOVE).

**Why:** Most clinical environments cannot push to external systems. C-FIND/C-MOVE lets the platform reach into a PACS, browse available studies, and selectively retrieve them — the standard clinical workflow.

**Technical approach:**
- Add `dicom_gateway/services/qr_service.py` implementing C-FIND SCU and C-MOVE SCU using `pynetdicom`.
- Frontend: "Import from PACS" workflow — configure AE title/host, search by patient ID/date, select studies, trigger retrieval.
- Retrieval jobs managed as Celery tasks in the `dicom_processing` queue.

**Effort:** L | **Priority:** Medium

---

### 2.3 Routing Rules Engine

**What:** Auto-forward studies to AI models (or external destinations) when they match configurable criteria (modality, body part, sending AE, patient age, etc.).

**Why:** Reduces manual intervention for routine workflows. A site receiving chest X-rays can auto-run CheXNet on every new study without user action.

**Technical approach:**
```python
# dicom_gateway/models.py
class RoutingRule(models.Model):
    name         = models.CharField(max_length=100)
    is_active    = models.BooleanField(default=True)
    priority     = models.IntegerField(default=0)
    conditions   = models.JSONField()   # {"modality": "CR", "body_part_examined": "CHEST"}
    action       = models.CharField(...)  # 'run_model', 'forward_to_pacs', 'notify'
    action_target = models.CharField(...)  # model key or AE title
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
```

Rules evaluated in `dicom_gateway/tasks.py` after every successful C-STORE.

**Effort:** M | **Priority:** Medium

---

### 2.4 S3-Compatible Object Storage

**What:** Replace local filesystem media storage with an S3-compatible backend (AWS S3, MinIO, Cloudflare R2). All `FileField` / `ImageField` paths resolve to S3 URLs.

**Why:** Current media files are stored in a Docker volume — not scalable, not backed up, not shareable across replicas. Required before horizontal scaling and WSI support.

**Technical approach:**
- Add `django-storages[s3]` to `requirements.txt`.
- Configure `DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'` in production settings.
- Add MinIO service to `docker-compose.yml` for local dev.
- Migration path: batch-copy existing media files to S3 with a management command.

**Effort:** M | **Priority:** Medium

---

### 2.5 FHIR R4 Resource Mapping

**What:** Expose platform data (studies, reports, analysis results) as FHIR R4 resources (`ImagingStudy`, `DiagnosticReport`, `Observation`) and accept FHIR-formatted payloads.

**Why:** EHR systems (Epic, Cerner) speak FHIR. Interoperability is required for integration with hospital IT infrastructure.

**Technical approach:**
- Add `fhir` app with serializers mapping `MedicalStudy → ImagingStudy`, `Report → DiagnosticReport`.
- FHIR endpoints at `/fhir/R4/ImagingStudy/`, `/fhir/R4/DiagnosticReport/`.
- Use `fhir.resources` Python package for resource validation.

**Effort:** L | **Priority:** Medium

---

### 2.6 Multi-Tenancy Improvements

**What:** Organization-level admin panels, per-org storage quotas, per-org model access controls, and organization-scoped API keys.

**Why:** Multiple institutions can share one deployment. Current organization scoping is basic — no admin dashboard, no quota enforcement, no per-org feature flags.

**Technical approach:**
- `OrganizationAdmin` role with a dedicated `/admin/org/` frontend section.
- `Organization.storage_quota_gb` field; middleware checks before each upload.
- `AIModel.organizations` M2M field to restrict model visibility.

**Effort:** M | **Priority:** Medium

---

### 2.7 Prometheus + Grafana Observability

**What:** Instrument the backend with `django-prometheus` and expose a `/metrics` endpoint. Add a Grafana service to docker-compose with a pre-built dashboard covering API latency, Celery queue depth, DB query counts, and memory usage.

**Why:** Currently there is no production observability — failures are discovered via user reports, not alerts. Prometheus + Grafana is the standard open-source stack for this.

**Technical approach:**
- Add `django-prometheus` to requirements; add `PrometheusBeforeMiddleware` / `PrometheusAfterMiddleware`.
- Add `prometheus` and `grafana` services to `docker-compose.yml`.
- Pre-provision Grafana dashboard JSON in `infra/grafana/dashboards/`.

**Effort:** M | **Priority:** Low

---

### 2.8 Horizontal Celery Scaling

**What:** Document and configure the Celery worker setup for horizontal scaling — multiple worker replicas reading from the same Redis queue, with autoscaling based on queue depth.

**Why:** AI inference tasks can take minutes per study. A single Celery worker becomes the bottleneck as usage grows.

**Technical approach:**
- Add `celery_worker_count` variable to `docker-compose.yml` (replicas field).
- Document Redis `CELERY_BROKER_TRANSPORT_OPTIONS` for high-concurrency scenarios.
- Add queue-depth alert in Prometheus.

**Effort:** S | **Priority:** Low

---

## Section 3 — Code Quality & Developer Experience

### 3.1 Backend Structured JSON Logging

**What:** Replace Django's default text formatter with `python-json-logger` for production. Every log line is a JSON object with `timestamp`, `level`, `logger`, `request_id`, `user_id`, and `message`.

**Why:** Text logs are hard to query in log aggregators (Datadog, CloudWatch, Grafana Loki). Structured logs enable filtering, alerting, and dashboarding without regex.

**Technical approach:**
```python
# backend/settings/production.py
LOGGING = {
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        }
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'json'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
```

Add `request_id` middleware that generates a UUID per request and injects it into the log context.

**Effort:** S | **Priority:** Medium

---

### 3.2 Redis Connection Pooling & Cache Strategy

**What:** Configure Redis connection pooling (`redis.ConnectionPool`) shared across Django cache backend and Celery broker. Add a cache layer for expensive read-heavy endpoints (study list, statistics).

**Why:** Each request currently opens a new Redis connection. Under load, connection exhaustion causes intermittent failures. Caching statistics endpoints (recomputed on every request) reduces DB load significantly.

**Technical approach:**
```python
# backend/settings/base.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
        },
    }
}
```

Cache `statistics/` endpoints with `cache_page(300)`. Invalidate on study/task creation.

**Effort:** S | **Priority:** Low

---

### 3.3 Dead Code & Dependency Cleanup

**What:** Audit `requirements.txt` and `package.json` for unused packages. Remove dead Django views, serializers, and React components.

**Why:** Unused dependencies increase attack surface, slow builds, and confuse new developers. Dead code creates maintenance burden.

**Technical approach:**
- Backend: `pip-check` + manual review of `requirements.txt` against actual imports.
- Frontend: `depcheck` or `knip` to find unused packages and exports.
- Remove identified dead code with targeted commits.

**Effort:** S | **Priority:** Low

---

### 3.4 API Documentation Completeness

**What:** Audit all DRF endpoints for complete `drf-spectacular` schema annotations. Ensure every endpoint has description, request/response examples, and error responses documented.

**Why:** The Swagger UI at `:3080/api/docs/` is the primary integration reference. Incomplete schemas force developers to read source code.

**Technical approach:**
- Run `./manage.py spectacular --validate` to find schema errors.
- Add `@extend_schema(...)` decorators where missing.
- Add example request/response payloads for complex endpoints (batch operations, BIDS anonymization).

**Effort:** M | **Priority:** High

---

### 3.5 Production Deployment Guide

**What:** A `docs/deployment.md` covering: Nginx reverse proxy config, SSL termination, environment variable reference, production Docker Compose overrides, database backup strategy, and log rotation.

**Why:** Currently the only deployment documentation is the Makefile. There is no guide for running this in production with real patient data.

**Technical approach:**
- Document all required environment variables with descriptions and examples.
- Provide `nginx.conf` snippet for proxy + SSL.
- Include `docker-compose.prod.yml` override with production-appropriate settings (no volume mounts for code, `DJANGO_DEBUG=False`, etc.).

**Effort:** M | **Priority:** High

---

### 3.6 Architecture Decision Records (ADRs)

**What:** Short Markdown documents in `docs/adr/` recording the reasoning behind key architectural choices: gRPC for AI orchestration, Celery queue separation, OHIF for viewing, JWT with refresh rotation.

**Why:** When team members or contributors ask "why was this done this way?", ADRs provide the answer without requiring the original author. Prevents relitigating settled decisions.

**Technical approach:**
- Use the MADR template (Markdown Architectural Decision Record).
- Start with 4–5 ADRs for the most consequential choices.
- Link ADRs from `CLAUDE.md` architecture section.

**Effort:** S | **Priority:** Medium

---

## Priority Matrix Summary

| Feature | Effort | Priority | Category |
|---------|--------|----------|----------|
| 1.1 nnU-Net Universal Connector | M | High | AI Models |
| 1.2 DICOM SEG Round-Trip | L | High | AI Models |
| 1.4 Automated Report Generation | L | High | AI Models |
| 2.1 Fine-Grained RBAC | L | High | Infrastructure |
| 3.4 API Documentation | M | High | Dev Experience |
| 3.5 Production Deployment Guide | M | High | Dev Experience |
| 1.3 Organ Label Taxonomy | S | Medium | AI Models |
| 1.6 Anonymization Gate | S | Medium | AI Models |
| 1.8 Multi-Parametric MRI | M | Medium | AI Models |
| 1.10 Model Benchmarking | M | Medium | AI Models |
| 2.2 DICOM Gateway Phase 2 | L | Medium | Infrastructure |
| 2.3 Routing Rules Engine | M | Medium | Infrastructure |
| 2.4 S3 Object Storage | M | Medium | Infrastructure |
| 2.5 FHIR R4 Mapping | L | Medium | Infrastructure |
| 2.6 Multi-Tenancy | M | Medium | Infrastructure |
| 3.1 Structured JSON Logging | S | Medium | Dev Experience |
| 3.6 Architecture ADRs | S | Medium | Dev Experience |
| 1.5 Few-Shot Fine-Tuning | L | Medium (Future) | AI Models |
| 1.7 Shared dcm2niix Utility | S | Low | AI Models |
| 1.9 WSI Modality Support | L | Medium (Future) | AI Models |
| 2.7 Prometheus + Grafana | M | Low | Infrastructure |
| 2.8 Horizontal Scaling | S | Low | Infrastructure |
| 3.2 Redis Connection Pooling | S | Low | Dev Experience |
| 3.3 Dead Code Cleanup | S | Low | Dev Experience |

# AI Analysis Workflow Guide

**Audience:** Engineering · **Scope:** how a veterinary AI analysis runs end-to-end on VetImage, from task creation to findings rendered in the viewer and a draft report.

> **Clinical framing.** Every AI result on VetImage is **decision-support, not a diagnosis**. Models are flagged experimental and human-in-the-loop: a veterinarian reviews and confirms every finding before it informs care. See `docs/VETERINARY_ALIGNMENT_REPORT.md`.

---

## 1. Overview

VetImage dispatches analysis jobs to **external model services** through a pluggable connector layer, then ingests results asynchronously. Two transport patterns are supported:

| Pattern | Models | Flow |
|---|---|---|
| **REST + webhook** | `vet-thorax-cr-v1`, `vet-hip-v1`, `vet-dental-v1`, MIRAGE, CheXNet | HTTP `POST /analyze` → service calls back to a webhook |
| **gRPC via orchestrator** | PICAI, FastSurfer | `orchestrator_client.py` → gRPC orchestrator (`USE_ORCHESTRATOR=True`) |

This guide focuses on the **REST + webhook** path used by the veterinary models.

---

## 2. Lifecycle

```
┌────────────┐  POST /api/ai-analysis/tasks/        ┌─────────────────────────┐
│  Frontend  │ ───────────────────────────────────▶ │  AnalysisTaskViewSet    │
└────────────┘                                       │  status = PENDING       │
                                                     └───────────┬─────────────┘
                                                                 │ dispatch_ai_job.delay()
                                                                 ▼
                                                     ┌─────────────────────────┐
                                                     │  Celery worker          │
                                                     │  dispatch_ai_job        │
                                                     │  → connector.dispatch_job
                                                     │  status = DISPATCHED    │
                                                     └───────────┬─────────────┘
                                          POST {endpoint_url}/analyze
                                          { task_id, callback_url, webhook_secret, … }
                                                                 ▼
                                                     ┌─────────────────────────┐
                                                     │  Model service          │
                                                     │  (e.g. vet-thorax)      │
                                                     └───────────┬─────────────┘
                       POST /api/ai-analysis/webhook/{task_id}/  │
                       { status: PROCESSING, webhook_secret }    │  (then, when done)
                       { status: COMPLETED, webhook_secret,      ▼
                         metadata: { findings: [...] } }
                                                     ┌─────────────────────────┐
                                                     │  WebhookReceiverView    │
                                                     │  → WebhookHandler       │
                                                     │  status: DISPATCHED →   │
                                                     │    PROCESSING → COMPLETED│
                                                     └───────────┬─────────────┘
                                                                 ▼
                              result_metadata.findings  ──▶ TaskMonitor (live UI)
                                                        ──▶ report_builder → report draft
```

A Celery safety net (`check_task_timeouts`, every 10 min) marks stalled `DISPATCHED`/`PROCESSING` tasks as `TIMEOUT` if the webhook never arrives.

---

## 3. The connector contract

All connectors inherit `BaseAIConnector` (`ai_analysis/connectors/base.py`) and are instantiated by `connectors/factory.py` from `AIModel.connector_class`.

A REST+webhook connector implements `dispatch_job(task)`. The dispatch payload **must** include the callback coordinates so the service can report back. Build it from `build_base_payload(task)`, which provides:

```python
{
  "task_id":          str(task.id),
  "source_file_path": "/var/www/app/backend/media/…",  # shared volume path
  "parameters":       task.parameters,
  "webhook_url":      "http://backend-vetimage:3080/api/ai-analysis/webhook/<task_id>/",
  "webhook_secret":   task.webhook_secret,              # per-task secret
}
```

The vet connectors then add `callback_url` (= `webhook_url`), `species`, `modality`, and the study/series UIDs.

> **Gotcha (regression guard).** Earlier vet connectors hand-built the payload, read a non-existent `task.webhook_url` attribute, and omitted `webhook_secret` — so the service could not authenticate its callback. Always go through `build_base_payload`. Note that `MagicMock` test tasks auto-create any attribute, so this class of bug passes unit tests but fails in production — assert on the real keys (`webhook_secret`, `callback_url`).

---

## 4. The webhook contract

The model service POSTs to `/api/ai-analysis/webhook/{task_id}/` (unauthenticated; the per-task `webhook_secret` is the credential). `WebhookHandler` (`ai_analysis/services/webhook_handler.py`):

- Validates `webhook_secret` against the task.
- Enforces transitions: `DISPATCHED → PROCESSING → COMPLETED | FAILED`. A direct `DISPATCHED → COMPLETED` is **rejected** — send `PROCESSING` first.
- Is idempotent: a duplicate delivery to a terminal task is a no-op `200`.

Payload shape:

```jsonc
// PROCESSING
{ "status": "PROCESSING", "webhook_secret": "<secret>" }

// COMPLETED
{
  "status": "COMPLETED",
  "webhook_secret": "<secret>",
  "result_file_path": "ai_results/…",      // optional; for file outputs (e.g. segmentations)
  "metadata": {                            // persisted verbatim to result_metadata
    "findings": [
      { "label": "cardiomegaly", "region": "cardiac",
        "confidence": 0.83,
        "bbox": [0.38, 0.45, 0.30, 0.35],   // optional; normalized [x,y,w,h] for viewer overlay
        "description": "Possible cardiomegaly (cardiac), confidence 83%." }
    ],
    "model_version": "…"
  }
}

// FAILED
{ "status": "FAILED", "webhook_secret": "<secret>", "error_message": "…" }
```

> **Important — there is no `result_data` column.** `AnalysisTask` stores `result_file_path` + `result_metadata` (JSON). The handler persists the webhook's `metadata` dict to `result_metadata`. **Structured findings must be sent under `metadata.findings`.** Each finding should carry a human-readable `description`, because `report_builder` and the owner/referral public views render `description`.

---

## 5. Where results surface

- **`TaskMonitor`** (`components/analysis/TaskMonitor.tsx`) renders `result_metadata.findings` as `label · region · confidence%` with a "draft findings — must be reviewed by a veterinarian" disclaimer.
- **Reports.** `POST /api/reports/` with `{ analysis_task_id }` → `ReportBuilder.build_from_task` reads `result_metadata.findings` (also accepts `results`) into a `findings` section of a draft report. The vet then edits, approves, and optionally shares it (owner share link / referral package).
- **Viewer overlay.** `GET /api/ai-analysis/tasks/study-findings/?study=<uid>` returns the user's completed-task findings for a study (each with `task_id`, `model`, and optional `bbox`). `FindingsOverlay` (`components/viewer/FindingsOverlay.tsx`) draws boxes over the Cornerstone canvas for findings that carry a normalized `bbox` ([x, y, w, h] in [0,1] image coords), recomputing on every `cornerstoneimagerendered` event via `cornerstone.pixelToCanvas` so they track zoom/pan/window-level. Toggle via the **AI findings** button in the `OHIFViewer` header. Findings without a `bbox` still appear in `TaskMonitor` and the report draft.

---

## 6. Model registration

Veterinary models are seeded by `manage.py seed_vet_models` (`update_or_create`, so re-running updates existing rows). Each `AIModel` row sets at least:

| Field | Example |
|---|---|
| `key` | `vet-thorax-cr-v1` |
| `connector_class` | `ai_analysis.connectors.vet_thorax.VetThoraxConnector` |
| `endpoint_url` | `http://vet-thorax-service:8000` |
| `supported_modalities` | `['CR', 'DX']` |
| `supported_species` | `['canine', 'feline']` |
| `use_orchestrator` | `False` (REST+webhook) |

Models also carry `limitations`, `validation_dataset`, and `metadata.experimental` / `metadata.human_in_the_loop` flags surfaced in the UI.

---

## 7. The reference service (run it locally)

`app/services/vet-thorax/` is a **CPU-only reference implementation** of the contract above. It contains **no machine learning** — it returns deterministic fixture findings derived from the task id — so the full lifecycle can be demonstrated without GPUs or proprietary weights. It implements `POST /analyze`, `GET /jobs/{id}`, `GET /health`, and posts `PROCESSING` then `COMPLETED` webhooks (with `findings` in `metadata`).

```bash
# One command: build + start the service, seed the model, drive one task E2E
make ai-demo

# Or step by step:
docker compose -f docker-compose.yml -f docker-compose.services.yml up -d --build vet-thorax-service
docker compose exec backend-vetimage python manage.py seed_vet_models
docker compose exec backend-vetimage python manage.py demo_vet_thorax --timeout 40
```

Expected tail:

```
Final status: COMPLETED
Findings (2):
  • cardiomegaly (cardiac) — confidence 0.83
  • pneumothorax (pleural_space) — confidence 0.61
AI pipeline end-to-end: OK
```

---

## 8. Building a real model service

To replace the fixture with a real model, ship a service that honours the same contract:

1. `POST /analyze` — accept `{ task_id, callback_url, webhook_secret, species, study_instance_uid, … }`, return `{ job_id, status }`, run inference asynchronously.
2. POST `PROCESSING` to `callback_url` when work starts.
3. POST `COMPLETED` with `metadata.findings` (each with a `description`) — and `result_file_path` for any file artifacts written to the shared media volume — or `FAILED` with `error_message`.
4. `GET /jobs/{id}` and `GET /health` for polling fallback and liveness.
5. Register it: add the service to `docker-compose.services.yml`, point the model's `endpoint_url` at it in `seed_vet_models.py`, re-seed.

Keep the experimental / human-in-the-loop framing intact regardless of model maturity.

---

## 9. Tests

| Test | Locks in |
|---|---|
| `ai_analysis/tests/test_pipeline_e2e.py` | webhook lifecycle, secret check, invalid transition, idempotency |
| `ai_analysis/tests/test_connectors.py::TestVetConnectorPayloads` | dispatch payload carries `webhook_url` + `webhook_secret` + `callback_url` |
| `reports/tests/test_report_builder.py` | vet finding shape → report `findings` section |

Run: `docker compose exec backend-vetimage pytest ai_analysis/ reports/ --tb=short -q`

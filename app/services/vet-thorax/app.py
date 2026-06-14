"""
Reference VetThorax model service — CPU-only, deterministic, NOT a real model.

Implements the REST + webhook contract expected by
`ai_analysis.connectors.vet_thorax.VetThoraxConnector`:

    POST /analyze        -> accepts {task_id, callback_url, webhook_secret, species, ...}
                            returns {job_id, status}, then asynchronously posts a
                            PROCESSING webhook followed by a COMPLETED webhook.
    GET  /jobs/{job_id}  -> polling fallback (returns canned findings when done).
    GET  /health         -> liveness probe.

The findings are DETERMINISTIC FIXTURES derived from the task id — there is no
machine learning here. This service exists so the full VetImage analysis
lifecycle (dispatch -> webhook -> findings -> report) can be exercised and
demonstrated end-to-end without GPUs or proprietary model weights. Every result
is flagged experimental / human-in-the-loop, exactly like the real connector.
"""
import hashlib
import logging
import os
import threading
import time
from typing import Dict

import requests
from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("vet-thorax-service")

app = FastAPI(title="VetThorax Reference Service", version="0.1.0-fixture")

# Delay (seconds) between PROCESSING and COMPLETED webhooks — small so demos are snappy.
PROCESSING_DELAY = float(os.getenv("PROCESSING_DELAY", "2"))

# Catalogue of thoracic findings the fixture can "detect".
_FINDING_CATALOGUE = [
    {"label": "cardiomegaly", "region": "cardiac"},
    {"label": "pulmonary_edema", "region": "lung"},
    {"label": "pleural_effusion", "region": "pleural_space"},
    {"label": "pneumothorax", "region": "pleural_space"},
    {"label": "bronchial_pattern", "region": "lung"},
]

# In-memory job store (single-worker reference service).
_JOBS: Dict[str, dict] = {}


class AnalyzeRequest(BaseModel):
    task_id: str
    callback_url: str | None = None
    webhook_url: str | None = None
    webhook_secret: str | None = None
    species: str | None = "canine"
    study_instance_uid: str | None = None
    # Allow any extra fields the connector sends without rejecting the request.
    class Config:
        extra = "allow"


def _deterministic_findings(task_id: str) -> list[dict]:
    """Pick 1–3 findings + pseudo-confidences deterministically from the task id."""
    digest = hashlib.sha256(task_id.encode()).hexdigest()
    seed = int(digest[:8], 16)
    count = 1 + (seed % 3)
    findings = []
    for i in range(count):
        item = _FINDING_CATALOGUE[(seed >> (i * 3)) % len(_FINDING_CATALOGUE)]
        # Confidence in [0.55, 0.95], stable per (task, finding).
        conf = 0.55 + ((int(digest[8 + i * 2: 10 + i * 2], 16) % 40) / 100.0)
        label_text = item["label"].replace("_", " ")
        findings.append({
            "label": item["label"],
            "region": item["region"],
            "confidence": round(conf, 2),
            # Human-readable line consumed by report_builder / owner + referral views.
            "description": f"Possible {label_text} ({item['region'].replace('_', ' ')}), "
                           f"confidence {round(conf * 100)}%.",
        })
    # De-duplicate by label, keep highest confidence.
    best: Dict[str, dict] = {}
    for f in findings:
        if f["label"] not in best or f["confidence"] > best[f["label"]]["confidence"]:
            best[f["label"]] = f
    return sorted(best.values(), key=lambda f: f["confidence"], reverse=True)


def _post_webhook(url: str, payload: dict) -> None:
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as exc:  # best-effort; the backend has a timeout safety net
        logger.warning("Webhook POST to %s failed: %s", url, exc)


def _run_job(job_id: str, req: AnalyzeRequest) -> None:
    callback = req.callback_url or req.webhook_url
    secret = req.webhook_secret
    findings = _deterministic_findings(req.task_id)

    # 1) PROCESSING (valid transition DISPATCHED -> PROCESSING)
    if callback and secret:
        _post_webhook(callback, {"status": "PROCESSING", "webhook_secret": secret})

    time.sleep(PROCESSING_DELAY)

    # 2) COMPLETED with findings carried in metadata.findings (the field the
    #    WebhookHandler persists to AnalysisTask.result_metadata).
    _JOBS[job_id] = {"status": "completed", "findings": findings}
    if callback and secret:
        _post_webhook(callback, {
            "status": "COMPLETED",
            "webhook_secret": secret,
            "metadata": {
                "findings": findings,
                "model_version": "vet-thorax-fixture-0.1.0",
                "experimental": True,
                "human_in_the_loop": True,
                "species": req.species,
            },
        })
    logger.info("Job %s (task %s) completed with %d finding(s)", job_id, req.task_id, len(findings))


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    job_id = f"vetthorax-{req.task_id}"
    _JOBS[job_id] = {"status": "processing", "findings": []}
    logger.info("Accepted analyze for task %s -> job %s", req.task_id, job_id)
    threading.Thread(target=_run_job, args=(job_id, req), daemon=True).start()
    return {"job_id": job_id, "id": job_id, "status": "queued"}


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = _JOBS.get(job_id)
    if job is None:
        return {"status": "unknown"}
    return {
        "status": job["status"],
        "findings": job["findings"],
        "model_version": "vet-thorax-fixture-0.1.0",
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "vet-thorax-fixture", "version": "0.1.0"}

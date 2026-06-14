# VetThorax Reference Service (CPU fixture)

A **deterministic, CPU-only reference implementation** of the VetImage AI model
service contract. It contains **no machine learning** — it returns stable,
fixture findings derived from the task id so the full analysis lifecycle
(dispatch → webhook → findings → report) can be run and demonstrated without
GPUs or proprietary model weights.

It pairs with `ai_analysis.connectors.vet_thorax.VetThoraxConnector`
(`vet-thorax-cr-v1`, `endpoint_url=http://vet-thorax-service:8000`).

## Contract

| Endpoint | Purpose |
|---|---|
| `POST /analyze` | Accepts `{task_id, callback_url, webhook_secret, species, …}`; returns `{job_id, status}`. Asynchronously POSTs a `PROCESSING` webhook, then (after `PROCESSING_DELAY`s) a `COMPLETED` webhook with findings in `metadata.findings`. |
| `GET /jobs/{job_id}` | Polling fallback; returns `{status, findings}`. |
| `GET /health` | Liveness probe. |

The `COMPLETED` webhook carries findings under `metadata.findings` because the
backend's `WebhookHandler` persists the webhook `metadata` object to
`AnalysisTask.result_metadata` (there is no separate `result_data` column).

## Run

```bash
# Built + started with the rest of the model services:
docker compose -f docker-compose.yml -f docker-compose.services.yml up -d --build vet-thorax-service

# Or via the demo target (also seeds + drives a task):
make ai-demo
```

`PROCESSING_DELAY` (default 2s) controls the gap between the PROCESSING and
COMPLETED webhooks.

## Important

Every result is flagged `experimental` / `human_in_the_loop`. This is a
demonstration/integration fixture — never present its output as a real
diagnosis or a validated model.

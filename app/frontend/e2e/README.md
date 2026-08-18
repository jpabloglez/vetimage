# E2E tests (Playwright)

Browser-driven tests against the real running stack — no mocks. They assume
the app is already up (Playwright does not start it, since it's a
multi-container Docker Compose app rather than a single dev server).

## Run locally

```bash
# 1. Bring up the stack, including the vet-thorax reference AI service used
#    by the core workflow test (CPU-only, deterministic fixture findings):
docker compose -f docker-compose.yml -f docker-compose.services.yml up -d --build vet-thorax-service
docker compose up -d

# 2. Apply migrations and seed the E2E user + AI model catalog (idempotent):
docker compose exec backend-vetimage python manage.py migrate
docker compose exec backend-vetimage python manage.py seed_e2e_data

# 3. Install Playwright browsers once (inside the frontend container, since
#    that's where the npm dependency lives):
docker compose exec frontend-vetimage npx playwright install --with-deps chromium

# 4. Run the suite:
docker compose exec frontend-vetimage npx playwright test
```

Or from the host, if you have Node installed and the frontend/backend ports
(`3001`/`3081`) are reachable at `localhost`:

```bash
cd app/frontend
npm run test:e2e
```

## What's covered

- `auth.spec.ts` — login (valid + invalid credentials), logout.
- `core-workflow.spec.ts` — the golden path: upload a DICOM study → AI model
  recommendation → dispatch analysis → wait for the (real) webhook-driven
  completion → generate a report → view it embedded (PDF iframe) from both
  the Analyze → Reports tab and the Dashboard.

## Fixtures

`e2e/fixtures/sample-cr.dcm` is a synthetic, minimal-but-valid canine
thoracic CR DICOM file (no real patient data — `PatientName: E2E^TestDog`)
generated for this suite. It carries just enough tags (StudyInstanceUID,
SeriesInstanceUID, SOPInstanceUID, Modality, 8×8 pixel data) to pass upload
validation and be recommended for `vet-thorax-cr-v1`.

## Test credentials

Seeded by `manage.py seed_e2e_data` (idempotent — safe to re-run):
`e2e@vetimage.test` / `E2ePlaywright123!`. Not a secret — it only exists in
non-production environments seeded by that command.

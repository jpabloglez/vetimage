# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VetImage is a DICOM medical imaging platform: DICOM storage, DICOMweb APIs (QIDO-RS, WADO-RS), OHIF/Cornerstone.js viewer, AI analysis orchestration, real-time monitoring, and PDF report generation.

**Stack:** Django 5 + DRF (backend) · React 18 + TypeScript + Vite (frontend) · PostgreSQL · Redis · Celery · Django Channels (WebSocket) · Docker Compose

## Build & Run

All services run inside Docker. The Makefile wraps docker-compose.

```bash
make dev               # docker-compose up -d && logs -f
make down              # stop and remove containers
docker-compose build   # rebuild images
```

Key ports: Frontend `:3001`, Backend `:3081`, Swagger `:3081/api/docs/`, PostgreSQL `:5445`, Redis `:6381`, DICOM SCP `:11113`, Orthanc `:8043`

## Testing

### Backend (pytest-django)

```bash
# All tests
docker compose exec backend-vetimage pytest --tb=short -q

# Single app
docker compose exec backend-vetimage pytest dicom_images/

# Single test
docker compose exec backend-vetimage pytest users/tests/test_views.py::TestLoginView::test_login_success

# With coverage
docker compose exec backend-vetimage pytest --cov=. --cov-report=term-missing
```

Config in `app/backend/pytest.ini`: uses `--no-migrations`, `--reuse-db`. Shared fixtures in `app/backend/conftest.py` (`user`, `auth_client`, `organization`, `owner`, `animal_patient`, `study`, `series`, `image`, `ai_model`, `analysis_task`, `completed_task`, `report`). When a model field changes, re-run with `--create-db` to rebuild the cached test schema.

## API Documentation (OpenAPI / drf-spectacular)

Interactive docs are generated from the code (drf-spectacular):

- **Swagger UI**: `:3081/api/docs/` — click **Authorize** and paste a JWT from
  `/users/auth/login/` (the `bearerAuth` scheme is defined), then **Try it out**.
- **ReDoc**: `:3081/api/redoc/` · **Raw schema**: `:3081/api/schema/`

```bash
docker compose exec backend-vetimage python manage.py spectacular --validate   # lint the schema
```

New endpoints must be documented: give `SerializerMethodField`s a return type
hint (or `@extend_schema_field`), and annotate plain `APIView`/`@action`
endpoints with `@extend_schema(responses=..., tags=[...])`. Settings live in
`SPECTACULAR_SETTINGS` (`backend/settings.py`). Contract tests in
`tests/test_openapi_schema.py` lock in schema generation, the docs endpoints,
the auth scheme, and that key veterinary paths are documented.

### Frontend (Vitest + Testing Library)

```bash
docker compose exec frontend-vetimage npx vitest run --reporter=verbose
docker compose exec frontend-vetimage npx vitest          # watch mode
docker compose exec frontend-vetimage npx vitest run --coverage
```

Shared harness: `src/test-utils.tsx` (`renderWithProviders`) and
`src/test/mockApiClient.ts` (`createApiClientMock()` — the complete apiClient
surface with safe defaults). New component tests should mock the API via
`createApiClientMock` so `AuthProvider` mounts cleanly. i18n is initialised
globally in `src/setupTests.ts`, so isolated components resolve real strings.

### Load / stress / connectivity (k6)

Dockerised k6 (no local install) against the running backend:

```bash
make loadtest-connectivity   # fast API smoke (strict thresholds)
make loadtest-load           # sustained traffic; non-zero exit on SLO breach
make loadtest-stress         # capacity / breaking-point characterisation
```

Scripts and docs in `loadtest/` — see `loadtest/README.md`.

## Linting

```bash
# Backend (CI uses ruff, Makefile uses flake8)
docker compose exec backend-vetimage ruff check .

# Frontend
docker compose exec frontend-vetimage npx eslint src/
```

## Database

```bash
make migrate           # run migrations
make makemigrations    # generate new migrations
make shell-db          # psql session
docker compose exec backend-vetimage python manage.py seed_ai_models
```

## Architecture

```
frontend (:3001) → proxy /api → backend (:3081, Daphne/ASGI)
                                    ├── PostgreSQL (:5445)
                                    ├── Redis (:6381)
                                    ├── Celery worker (queues: ai_jobs, monitoring, default)
                                    ├── Celery beat (periodic tasks)
                                    └── Django Channels (WebSocket)
DICOM Gateway (:11113 SCP, :8001 API) + gateway-celery-worker (queue: dicom_processing)
Orchestrator (:50050 gRPC) — optional, for models requiring gRPC (USE_ORCHESTRATOR=True)
Orthanc test PACS (:4242 DICOM, :8042 web)
```

Optional AI services (docker-compose.services.yml): MIRAGE `:8010`, CheXNet `:8011`, PICAI `:50051`

### Backend (`app/backend/`)

Django project root is `app/backend/`, Django package (settings/urls/asgi) is `backend/`.

| App | Purpose |
|---|---|
| `users` | Custom User model (email-based), roles, Organization, UserAPIKey |
| `dicom_images` | MedicalStudy → MedicalSeries → MedicalImage, DICOMweb, annotations |
| `ai_analysis` | AIModel registry, AnalysisTask lifecycle, Celery dispatch, WebSocket consumers |
| `credentials` | Session tracking, audit logging, API key scopes, notifications |
| `reports` | Structured reports, PDF export (ReportLab), approval workflow, owner sharing |
| `dicom_gateway` | DICOM SCP gateway, transfer monitoring |
| `patients` | Veterinary registry: Owner → AnimalPatient → VHSMeasurement |
| `files` | File upload view |
| `core` | Shared utilities |

**URL prefix pattern:** `/users/auth/` (auth), `/api/dicom/` (DICOM), `/api/ai-analysis/` (AI), `/api/credentials/` (sessions/audit), `/api/reports/` (reports), `/api/patients/` (owners, animals, VHS)

**AI connector pattern:** All connectors inherit `BaseAIConnector` (`ai_analysis/connectors/base.py`). Factory in `connectors/factory.py` instantiates by `AIModel.connector_class`. Two communication patterns:
- REST + Webhook (MIRAGE, CheXNet, vet-*): HTTP POST dispatch → webhook callback
- gRPC via Orchestrator (PICAI): `orchestrator_client.py` → gRPC orchestrator

**AI lifecycle (REST+webhook):** `dispatch_ai_job` (Celery) → `connector.dispatch_job()` POSTs `{endpoint_url}/analyze` with `callback_url` + `webhook_secret` (vet connectors build this via `build_base_payload`) → task `DISPATCHED`. Service POSTs `/api/ai-analysis/webhook/{task_id}/` with `{status, webhook_secret, metadata}`; `WebhookHandler` enforces transitions `DISPATCHED→PROCESSING→COMPLETED/FAILED` and persists the webhook `metadata` dict to `AnalysisTask.result_metadata` (**there is no `result_data` column** — findings live in `result_metadata.findings`). `report_builder.build_from_task` reads `result_metadata.findings` into a report draft; `TaskMonitor` renders them (label · region · confidence) with a vet-review disclaimer. Findings with a normalized `bbox` ([x,y,w,h] in [0,1]) overlay on the Cornerstone viewer via `FindingsOverlay` (toggle in `OHIFViewer`), fetched from `GET /api/ai-analysis/tasks/study-findings/?study=<uid>`. `make ai-demo` drives the whole loop against the in-repo CPU reference service `app/services/vet-thorax/` (deterministic fixtures, no ML) registered as `vet-thorax-cr-v1` (`endpoint_url=http://vet-thorax-service:8000`).

### Frontend (`app/frontend/src/`)

React Router v7, Tailwind CSS (class-based dark mode with `dark:` prefix), custom medical theme (`medical-card`, `medical-gradient-text`).

**Auth flow:** Access token in memory (`apiClient` singleton), refresh token in HttpOnly cookie. `AuthContext` calls `apiClient.refreshToken()` on page load to restore sessions. `api.ts` auto-refreshes on 401.

**Key directories:** `pages/` (route-level components), `components/` (feature-grouped), `hooks/` (custom hooks), `utils/api.ts` (centralized API client with all typed methods), `contexts/` (AuthContext, ThemeContext).

**Key routes:**

| Route | Component | Auth |
|---|---|---|
| `/patients` | `PatientsPage` | required |
| `/calendar` | `CalendarPage` | required |
| `/audit-log` | `AuditLogPage` | required (admin scoped) |
| `/shared/:token` | `OwnerReportPage` | **public** (no login) |
| `/referral/:token` | `ReferralPackagePage` | **public** (no login) |
| `/portal` | `OwnerPortalPage` | required (Pet Owner role only) |

## Veterinary Features

### Patient Registry (`patients` app)

**Model hierarchy:** `Owner` → `AnimalPatient` → clinical records

Per-animal record models (all org-scoped via `animal_patient__owner__organization`, all filter by `?animal=<id>`):
- `VHSMeasurement` — Vertebral Heart Score (long_axis + short_axis, vertebral units); VHS computed server-side; `interpretation` derived; human-in-the-loop.
- `ClinicalVisit` — SOAP note + vitals (weight, temperature, HR, RR), visit_type, optional `linked_study`/`linked_report`. (`/api/patients/visits/`)
- `VaccinationRecord` — vaccine_name, administered_on, next_due_on, batch. (`/api/patients/vaccinations/`)
- `WeightRecord` — time-series weight + BCS 1–9 (Purina/WSAVA). (`/api/patients/weights/`)
- `Appointment` — scheduled_at, status, `complete()` action auto-creates a `ClinicalVisit`. (`/api/patients/appointments/`)
- `Prescription` — medication, dose, route, frequency, duration. (`/api/patients/prescriptions/`)
- `AllergyRecord` — allergen, severity; `is_high_severity` (severe/life_threatening) drives the UI alert banner. (`/api/patients/allergies/`)
- `ClinicalPhoto` — non-DICOM JPEG/PNG (wounds, derm); ImageField. (`/api/patients/photos/`)
- `LabResult` — result_type, panel_name, `result_data` JSON analyte map {value, unit, ref_low, ref_high, flag}, optional pdf_file. (`/api/patients/labs/`)
- `ReproductiveEvent` — heat/mating/whelping/etc., event_date, partner_id, litter_count. (`/api/patients/reproductive/`)

Other:
- `Owner` — clinic client. Fields: first_name, last_name, **email (required)**, **phone (required)**, address, city, country, pii_anonymized. Scoped to `organization`.
- `AnimalPatient` — species (canine/feline/equine/bovine/avian/exotic/other), breed, sex, date_of_birth, weight_kg, microchip_id (ISO 15-digit or 9–20 alphanum, unique within org), `profile_photo`, insurance (provider/policy/expiry). Detail serializer embeds `weight_trend`, `vaccinations`, `upcoming_appointments`, `visits_count`.
- `MedicalStudy.animal_patient` — nullable FK linking a DICOM study to its patient.
- `BreedReference` — breed/species-specific reference ranges (currently VHS). `BreedReference.lookup(species, breed, metric)` returns the most specific match (breed substring beats species-wide); used by `VHSMeasurement.interpretation` + serializer `reference_range`. Seed: `python manage.py seed_breed_references`.

**Frontend:** `PatientsPage` → `AnimalDetailModal` is an 11-tab layout (Overview, Visits, Vaccinations, Weight, Appointments, Prescriptions, Allergies, Lab Results, Photos, Reproductive, Messages). Each panel follows the `VHSPanel` pattern (local `adding` state, `zodFieldErrors`, reload, `ConfirmDialog`). High-severity allergies render an alert banner in the modal header; insurance shows in Overview with expiry colour-coding. `/calendar` → `CalendarPage` (month/week appointment grid).

**Owner registration rule:** When creating a new owner via the UI, email and phone are **mandatory**, and at least one animal (name + species, breed optional) must be registered in the same form submission. The backend creates owner and animal sequentially; if animal creation fails, the owner is already persisted.

**VHS reference ranges:** canine 8.5–10.6 vertebrae, feline 6.7–8.1. Breed-dependent population guides only — never a diagnosis.

**GDPR anonymization:** `Owner.anonymize_pii()` blanks PII fields while keeping the record (preserves study/patient links). Anonymized owners can no longer be edited via the UI's required-email validation (by design).

**`get_or_create_organization(user)`** (`patients/views.py`) — lazily provisions an Organization + UserProfile for users who have neither. Called in every patients ViewSet before touching org-scoped data.

### Reports Approval & Sharing Workflow

- `Report.approved_by` / `Report.approved_at` — set when a vet approves the report. Only approved reports can be shared.
- `Report.share_token` (UUID) / `Report.shared_at` — set when a clinic shares with the owner.
- `GET /api/reports/shared/<uuid:token>/` — unauthenticated public endpoint serving `PublicSharedReport` (read-only, plain-language view).
- Frontend `/shared/:token` → `OwnerReportPage` — no login required; shows signalment + findings with explicit "reviewed by veterinarian" framing.
- `ReportTemplate.species_filter` / `modality_filter` (JSON lists; empty = all) + species/modality-specific `template_type` choices (thoracic_canine, dental, cardiac_vhs, …). Filter via `?species=&modality=` on `/api/reports/templates/`.

### DICOM Study Sharing (vet-to-vet)

- `StudyShareLink` (`dicom_images`) — token-gated link to a study for external vets. Serializer **writes** accept `study_uid` (the DICOMweb UID the frontend has), not the numeric PK. `is_valid()` enforces `expires_at` + `max_accesses`.
- `GET /api/dicom/shared/<uuid:token>/` — unauthenticated `PublicStudyWADOView`; increments `access_count`, returns study metadata.
- Manage links: `/api/dicom/share-links/?study=<uid>`. Frontend: `StudyShareModal` (Share button in `StudyBrowser`) — create with expiry/max-views, copy, revoke.

### Referral Network (vet-to-specialist)

- `ReferringClinic` (`patients`) — org-scoped address book of partner clinics; `ClinicalVisit.referred_by` FK attributes a case to one. (`/api/patients/referring-clinics/`)
- `ReferralPackage` (`patients`) — token-gated bundle of an animal + optional `study` + `report` + `history_summary` + `reason` + `urgency`. Serializer **writes** accept `study_uid` (DICOMweb UID), not the PK; `is_valid()` enforces `expires_at`. Manage: `/api/patients/referral-packages/?animal=<id>`.
- `GET /api/patients/referrals/<uuid:token>/` — unauthenticated `PublicReferralPackageView` serving sanitised `PublicReferralPackageSerializer` (signalment + reason + history + report findings + study UID; no internal IDs); increments `access_count`.
- Frontend: `ReferralModal` (Send icon in `StudyBrowser` card — requires `study.AnimalPatientID`); public `/referral/:token` → `ReferralPackagePage`. i18n in `viewer.referral.*` + `patients.referralPage.*`.

### Owner ↔ Clinic Messaging (`/api/patients/messages/`)

- `Message` (`patients`) — append-only thread keyed on `AnimalPatient` (audit-preserving); `from_owner` records the sending side, `is_read` tracks unread. (patients migration 0008)
- `MessageViewSet` — accessible to **both** staff (org-scoped) and the pet owner (email-scoped); `?animal=<id>` filters the thread; POST sets `sender`/`from_owner` from the caller's role and notifies the counterpart via `credentials.Notification`. `POST mark_read/` marks the *other* side's messages read. No edit/delete (append-only).
- Frontend: shared `MessageThread` component (bubbles flip via `isOwner`) — staff "Messages" tab in `AnimalDetailModal` (now 11 tabs), owner-side collapsible thread per pet on `OwnerPortalPage`. i18n `patients.messages.*`. Real-time WS delivery deferred; relies on the existing 30s `NotificationBell` poll.

### Pet-Owner Portal (`/api/portal/`)

- Owner accounts are `users.User` rows with `role == 6` (`PET_OWNER_ROLE`, in `users/models.py`), linked to their clinical `Owner` record(s) by **case-insensitive email match** (spans multiple clinics — one `Owner` row per org, same email).
- `GET /api/portal/dashboard/` — `OwnerPortalDashboardView` gated by `IsPetOwner` (`patients/views_portal.py`); returns the owner's pets (signalment + vaccination status + upcoming appointments) and their clinic-approved + shared reports (`share_path` → `/shared/<token>`).
- `POST /api/portal/owners/<id>/account/` — `OwnerAccountProvisionView`: clinic staff create an initial portal password (role=6 User with the Owner's email); 400 on duplicate email / weak password.
- Frontend: `/portal` → `OwnerPortalPage` (role-gated client-side — staff redirected to `/dashboard`). i18n in `patients.portal.*`.

### AI Model Enhancements

- `AIModel.supported_species` (JSONField) — species list for recommendation filtering (e.g., `["canine", "feline"]`).
- `AnalysisTask.priority` — `'routine'` / `'urgent'` / `'STAT'`; STAT tasks surface first in the worklist.
- Vet connectors seeded via `seed_vet_models.py`: `vet-thorax-cr-v1` → `VetThoraxConnector`, `vet-hip-v1` → `HipDysplasiaConnector` (orthopedic, canine/equine), `vet-dental-v1` → `VetDentalConnector` (canine/feline). All in `ai_analysis/connectors/`, REST+webhook MIRAGE-pattern. `vet-vhs-v1`, `vet-imgqc-v1` remain catalog stubs. All flagged experimental/human-in-the-loop.

### Notifications & Reminders

- `credentials.Notification` model + `NotificationViewSet` (`/api/credentials/notifications/`, `mark_read`/`mark_all_read` actions). Frontend `NotificationBell` in Navbar polls every 30s.
- `patients.tasks.send_vaccination_reminders` — Celery beat task (daily 08:00 UTC, `monitoring` queue). Creates a `Notification` for the administering vet when a vaccination is due in 14/7/1 days. Registered in `backend/celery.py` beat schedule + `CELERY_TASK_ROUTES`.

### Audit Log

`/audit-log` → `AuditLogPage`. Backend: `/api/credentials/` audit endpoint. Admins see full organization log; non-admins see only their own events. Filterable by event type (login_success, login_failed, suspicious_activity, etc.) and date range.

## Key Conventions

### Organization Scoping
- `UserProfile.organization` FK scopes data access — queries must filter by user's organization
- Backend views use patterns like `filter(uploaded_by__userprofile__organization=org)` or `filter(owner__organization=org)`
- `patients` views use `get_or_create_organization(user)` (auto-provisions org if missing)

### DICOM Hierarchy
`MedicalStudy` → `MedicalSeries` → `MedicalImage`, using UID natural identifiers (`study_instance_uid`, `series_instance_uid`, `sop_instance_uid`). `MedicalStudy.animal_patient` optionally links to a patient.

### Auth
- JWT: 5-min access tokens, 7-day refresh in HttpOnly cookies
- API keys for services: `oml_` prefix, SHA-256 hashed
- Custom User: email as USERNAME_FIELD, integer `role` (1=Veterinarian, 2=Guest, 3=Clinic Admin, 4=Veterinary Radiologist, 5=Superuser, 6=Pet Owner). `PET_OWNER_ROLE = 6` constant in `users/models.py` gates the owner portal.

### Code Organization
- Large Django apps split files: `views_statistics.py`, `serializers_batch.py`, `views_anonymization.py`
- Services layer in `services.py` or `services/` for business logic
- Frontend: PascalCase components, `useCamelCase` hooks, `camelCase` utils
- Validation schemas in `utils/validation.ts`: `ownerSchema` (required email + phone), `ownerAnimalSchema` (new-owner registration: name + species), `animalPatientSchema` (standalone animal), `vhsSchema`
- i18n namespace `patients` covers all of `PatientsPage`, `OwnerReportPage`, and `AuditLogPage` owner labels
- `getByLabelText` in tests must use anchored regexes (`/^Email/i` not `/Email/i`) — the search bar's aria-label contains "email" and causes false matches

### Branch & Commit Style
- Branches: `OMLAB-NNN` (e.g., `OMLAB-007`)
- Commits: `OMLAB-NNN <type>: <description>` (e.g., `OMLAB-006 Phase 3 — Tools, Reporting & AI Model Infrastructure`)

### Celery Queues
`ai_jobs` (dispatch), `monitoring` (timeouts/cleanup), `default` (general), `dicom_processing` (gateway)

## CI Pipeline (`.github/workflows/ci.yml`)

Runs on push/PR to `main`: backend lint (ruff) → backend tests (pytest + PostgreSQL + Redis) → frontend lint (eslint) → frontend tests (vitest) → Docker build validation. Also checks `makemigrations --check --dry-run` for missing migrations.

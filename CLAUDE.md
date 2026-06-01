# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenMedLab is a DICOM medical imaging platform: DICOM storage, DICOMweb APIs (QIDO-RS, WADO-RS), OHIF/Cornerstone.js viewer, AI analysis orchestration, real-time monitoring, and PDF report generation.

**Stack:** Django 5 + DRF (backend) · React 18 + TypeScript + Vite (frontend) · PostgreSQL · Redis · Celery · Django Channels (WebSocket) · Docker Compose

## Build & Run

All services run inside Docker. The Makefile wraps docker-compose.

```bash
make dev               # docker-compose up -d && logs -f
make down              # stop and remove containers
docker-compose build   # rebuild images
```

Key ports: Frontend `:3000`, Backend `:3080`, Swagger `:3080/api/docs/`, PostgreSQL `:5444`, Redis `:6379`, DICOM SCP `:11112`, Orthanc `:8042`

## Testing

### Backend (pytest-django)

```bash
# All tests
docker compose exec backend-openmedlab pytest --tb=short -q

# Single app
docker compose exec backend-openmedlab pytest dicom_images/

# Single test
docker compose exec backend-openmedlab pytest users/tests/test_views.py::TestLoginView::test_login_success

# With coverage
docker compose exec backend-openmedlab pytest --cov=. --cov-report=term-missing
```

Config in `app/backend/pytest.ini`: uses `--no-migrations`, `--reuse-db`. Shared fixtures in `app/backend/conftest.py` (`user`, `auth_client`, `study`, `series`, `image`, `ai_model`, `analysis_task`, `completed_task`, `report`).

### Frontend (Vitest + Testing Library)

```bash
docker compose exec frontend-openmedlab npx vitest run --reporter=verbose
docker compose exec frontend-openmedlab npx vitest          # watch mode
```

## Linting

```bash
# Backend (CI uses ruff, Makefile uses flake8)
docker compose exec backend-openmedlab ruff check .

# Frontend
docker compose exec frontend-openmedlab npx eslint src/
```

## Database

```bash
make migrate           # run migrations
make makemigrations    # generate new migrations
make shell-db          # psql session
docker compose exec backend-openmedlab python manage.py seed_ai_models
```

## Architecture

```
frontend (:3000) → proxy /api → backend (:3080, Daphne/ASGI)
                                    ├── PostgreSQL (:5444)
                                    ├── Redis (:6379)
                                    ├── Celery worker (queues: ai_jobs, monitoring, default)
                                    ├── Celery beat (periodic tasks)
                                    └── Django Channels (WebSocket)
DICOM Gateway (:11112 SCP, :8001 API) + gateway-celery-worker (queue: dicom_processing)
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
| `reports` | Structured reports, PDF export (ReportLab), templates |
| `dicom_gateway` | DICOM SCP gateway, transfer monitoring |
| `files` | File upload view |
| `core` | Shared utilities |

**URL prefix pattern:** `/users/auth/` (auth), `/api/dicom/` (DICOM), `/api/ai-analysis/` (AI), `/api/credentials/` (sessions/audit), `/api/reports/` (reports)

**AI connector pattern:** All connectors inherit `BaseAIConnector` (`ai_analysis/connectors/base.py`). Factory in `connectors/factory.py` instantiates by `AIModel.connector_class`. Two communication patterns:
- REST + Webhook (MIRAGE, CheXNet): HTTP POST dispatch → webhook callback
- gRPC via Orchestrator (PICAI): `orchestrator_client.py` → gRPC orchestrator

### Frontend (`app/frontend/src/`)

React Router v7, Tailwind CSS (class-based dark mode with `dark:` prefix), custom medical theme (`medical-card`, `medical-gradient-text`).

**Auth flow:** Access token in memory (`apiClient` singleton), refresh token in HttpOnly cookie. `AuthContext` calls `apiClient.refreshToken()` on page load to restore sessions. `api.ts` auto-refreshes on 401.

**Key directories:** `pages/` (route-level components), `components/` (feature-grouped), `hooks/` (custom hooks), `utils/api.ts` (centralized API client with all typed methods), `contexts/` (AuthContext, ThemeContext).

## Key Conventions

### Organization Scoping
- `UserProfile.organization` FK scopes data access — queries must filter by user's organization
- Backend views use patterns like `filter(uploaded_by__userprofile__organization=org)`

### DICOM Hierarchy
`MedicalStudy` → `MedicalSeries` → `MedicalImage`, using UID natural identifiers (`study_instance_uid`, `series_instance_uid`, `sop_instance_uid`)

### Auth
- JWT: 5-min access tokens, 7-day refresh in HttpOnly cookies
- API keys for services: `oml_` prefix, SHA-256 hashed
- Custom User: email as USERNAME_FIELD, integer `role` (1=User, 2=Guest, 3=Admin, 4=Manager, 5=Superuser)

### Code Organization
- Large Django apps split files: `views_statistics.py`, `serializers_batch.py`, `views_anonymization.py`
- Services layer in `services.py` or `services/` for business logic
- Frontend: PascalCase components, `useCamelCase` hooks, `camelCase` utils

### Branch & Commit Style
- Branches: `OMLAB-NNN` (e.g., `OMLAB-007`)
- Commits: `OMLAB-NNN <type>: <description>` (e.g., `OMLAB-006 Phase 3 — Tools, Reporting & AI Model Infrastructure`)

### Celery Queues
`ai_jobs` (dispatch), `monitoring` (timeouts/cleanup), `default` (general), `dicom_processing` (gateway)

## CI Pipeline (`.github/workflows/ci.yml`)

Runs on push/PR to `main`: backend lint (ruff) → backend tests (pytest + PostgreSQL + Redis) → frontend lint (eslint) → frontend tests (vitest) → Docker build validation. Also checks `makemigrations --check --dry-run` for missing migrations.

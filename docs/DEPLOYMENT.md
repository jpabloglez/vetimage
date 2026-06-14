# Deployment Guide

**Audience:** Engineering / ops. How to run VetImage in production. This stack
is Django + DRF + Channels (ASGI/Daphne) · PostgreSQL · Redis · Celery
(worker + beat) · a Vite/React frontend · optional AI model services.

> The repo's base `docker-compose.yml` is **development-oriented** (code-mount
> volumes, published DB/Redis ports). The `docker-compose.prod.yml` override
> applies production environment, restart policies, and a migrate +
> collectstatic startup. Read the **Caveats** section before exposing this to
> the internet.

---

## 1. Pre-flight checklist

- [ ] **`SECRET_KEY`** — strong random value (50+ chars). The app **refuses to
      boot** when `DJANGO_ENVIRONMENT=production` and the key is the insecure
      dev fallback. Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
- [ ] **`DJANGO_ENVIRONMENT=production`** and **`DEBUG=False`**.
- [ ] **`ALLOWED_HOSTS`** — comma-separated real hostnames (no `*`).
- [ ] **`CORS_ALLOWED_ORIGINS`** — explicit frontend origin(s); never allow-all
      (`CORS_ALLOW_ALL_ORIGINS` is already `False`).
- [ ] **TLS terminated** at a reverse proxy (nginx/Traefik/cloud LB). The app
      sets `SECURE_PROXY_SSL_HEADER = (HTTP_X_FORWARDED_PROTO, https)`, so the
      proxy must send `X-Forwarded-Proto: https`.
- [ ] **Database** — managed Postgres or a backed-up volume; rotate the default
      `postgres/postgres` credentials.
- [ ] **Secrets** delivered via environment / secret manager, not committed.
      `.env*` is git-ignored.

When `DEBUG=False`, settings automatically enable: `SECURE_SSL_REDIRECT`,
HSTS (1 year, subdomains, preload), `SESSION_COOKIE_SECURE`,
`CSRF_COOKIE_SECURE`, secure refresh-token cookie, `SECURE_CONTENT_TYPE_NOSNIFF`,
`SESSION_COOKIE_HTTPONLY`.

Verify with Django's own audit (expect **no `security.W*` warnings**; the
`drf_spectacular.W001/W002` lines are schema-generation noise, not deploy issues):

```bash
docker compose exec backend-vetimage python manage.py check --deploy 2>&1 | grep "security\."
```

---

## 2. Bring it up

```bash
# Provide production env (e.g. an env file consumed by your orchestrator):
export SECRET_KEY="…64+ random chars…"
export ALLOWED_HOSTS="vetimage.example.com"
export CORS_ALLOWED_ORIGINS="https://vetimage.example.com"

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The backend container runs `migrate` + `collectstatic` then serves via Daphne.
Static assets (admin / DRF / Swagger) are served by **WhiteNoise** from the ASGI
app — no separate static web server is required. The React frontend is its own
container; point your reverse proxy at the frontend for `/` and at the backend
for `/api`, `/users`, `/ws` (WebSocket upgrade).

### Static files & WhiteNoise

`whitenoise` is in `setup/requirements.txt`; the middleware is added
automatically when installed. In production (`DJANGO_ENVIRONMENT=production`)
static storage uses `CompressedManifestStaticFilesStorage` (hashed, compressed).
`collectstatic` runs on container start (also runnable via `make` / `manage.py`).

---

## 3. Data & backups

`make backup` / `make restore` wrap `pg_dump` / `pg_restore` for the Postgres
volume. Schedule `make backup` (cron) and ship dumps off-host. Persistent data
lives under `data/` (git-ignored): `data/db` (Postgres), `data/media` (uploaded
DICOM + clinical photos). Back up `data/media` alongside the database.

GDPR: schedule `manage.py purge_expired_pii` (honours `OWNER_PII_RETENTION_DAYS`)
to anonymize owner PII past the retention window.

---

## 4. Scaling & operations

- **Celery** — queues `ai_jobs`, `monitoring`, `default`, `dicom_processing`.
  Scale the worker (`docker compose up -d --scale celery-worker-vetimage=N`);
  run exactly **one** `celery-beat` instance.
- **Health** — backend `GET /api/health/` (used by the container healthcheck).
- **Logging** — structured JSON logs in production (`LOG_FORMAT=json` when
  `DJANGO_ENVIRONMENT=production`; `console` otherwise). Tune verbosity with
  `LOG_LEVEL` (default `INFO`). Every request gets an `X-Request-ID` (honouring
  an inbound header from your proxy) that is echoed on the response and stamped
  on every log line as `request_id` for correlation.
- **Error tracking** — set `SENTRY_DSN` to enable Sentry (Django + Celery
  integrations; `send_default_pii=False`). Optional `SENTRY_TRACES_SAMPLE_RATE`
  (default `0.0`) and `SENTRY_RELEASE`. With no DSN, Sentry is inert; the SDK is
  optional and the app runs fine without it installed.
- **AI model services** — see [AI-WORKFLOW.md](AI-WORKFLOW.md). The vet-thorax
  reference service is a CPU fixture (no ML); replace with real model services
  for clinical use. GPU model services need the NVIDIA container runtime.

---

## 5. Caveats (Compose override limitations)

`docker-compose.prod.yml` cannot *remove* entries the base file defines. For a
hardened deployment you should additionally:

- **Drop the code-mount volume** `./app/backend:/var/www/app/backend` so the
  container runs the baked image, not host code. (Build a prod image / use a
  base file without the mount.)
- **Stop publishing `db`/`redis` ports** (`5445`, `6381`) to the host — keep
  them on the internal Docker network only.
- Put the whole stack behind a TLS-terminating reverse proxy; do not expose
  Daphne (`:3081`) directly.

These are intentionally left as deploy-environment decisions rather than baked
into the override.

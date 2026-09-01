# Deployment Guide

**Audience:** Engineering / ops. How to run VetImage in production. This stack
is Django + DRF + Channels (ASGI/Daphne) · PostgreSQL · Redis · Celery
(worker + beat) · a Vite/React frontend · optional AI model services.

> The repo's base `docker-compose.yml` is **production-safe by default**: no
> code-mount volumes, no published DB/Redis/backend host ports. Those dev
> conveniences live in `docker-compose.override.yml`, which `docker compose`
> auto-loads only when no `-f` flag is given (plain dev runs) — an explicit
> `-f docker-compose.yml -f docker-compose.prod.yml` never loads it. The
> `docker-compose.prod.yml` override applies production environment, restart
> policies, and a migrate + collectstatic startup. Read the **Caveats**
> section before exposing this to the internet.

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
- [ ] **`NUM_PROXIES`** — set to the number of reverse proxies in front of the
      app (usually `1`). This decides which address API rate limits count
      against. Left at the default `0`, every client behind the proxy shares a
      single bucket and one busy site can throttle everyone. Your proxy must
      also append the real client IP to `X-Forwarded-For` (nginx:
      `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`).
      Do **not** set this to an empty value — DRF then trusts the raw
      client-supplied header and every throttle becomes bypassable.
- [ ] **Database** — managed Postgres or a backed-up volume; rotate the default
      `postgres/postgres` credentials.
- [ ] **Secrets** delivered via environment / secret manager, not committed.
      `.env*` is git-ignored.
- [ ] **`/media/` is NOT mapped to a public location.** Everything under
      `MEDIA_ROOT` is patient data — DICOM pixel data, clinical photographs,
      lab result PDFs. It is served *only* through the signature-checked
      `ProtectedMediaView`; pointing nginx at that directory would make every
      file world-readable to anyone who can guess a path, bypassing the app
      entirely. To let nginx push the bytes (recommended), set
      `MEDIA_ACCEL_REDIRECT_PREFIX=/internal-media/` and add an **`internal;`**
      location — the `internal` directive is what stops it being reachable
      from outside:

      ```nginx
      location /internal-media/ {
          internal;
          alias /var/www/app/backend/media/;
      }
      ```
- [ ] **Dependencies audited** — CI runs `pip-audit --strict` over all four
      Python manifests and `npm audit --audit-level=high` on every PR
      (the `Dependency Audit` job). A green build means no known CVEs in the
      pinned Python tree. Re-run locally before a release:
      `docker compose exec backend-vetimage pip-audit`.

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
- **Dependency upgrades** — Django is held on the **5.2 LTS** line. Treat the
  `Dependency Audit` CI job as the tripwire: when it goes red, upgrade rather
  than suppress. Four manifests are audited and must be upgraded together —
  `setup/requirements.txt` (backend, Celery), `app/dicom-gateway/`,
  `app/orchestrator/`, and `app/services/vet-thorax/`. Rebuild the affected
  images afterwards; the workers share the backend image.

---

## 5. Caveats (Compose override limitations)

The dev-only code-mounts and DB/Redis/backend host port publishing live in
`docker-compose.override.yml`, which `docker compose` auto-loads only for a
bare invocation (no `-f`). The `-f docker-compose.yml -f docker-compose.prod.yml`
combo from §2 never loads it — Docker Compose cannot *remove* entries an
override adds, so keeping them out of the base file (instead of trying to
un-set them in `docker-compose.prod.yml`) is what makes prod hardened by
default. Remaining deploy-environment decisions, still left to you:

- Put the whole stack behind a TLS-terminating reverse proxy; do not expose
  Daphne (`:3081`) directly.
- Exclude the bundled `orthanc-test-pacs-vetimage` service from prod — it's a
  dev/test PACS fixture with hardcoded credentials, not meant to be reachable
  from the internet. (No separate compose file for this yet; stop/remove the
  container after `up`, or split it into its own file if you need a repeatable
  prod bring-up.)
- Running the AI model services (`docker-compose.services.yml`) alongside a
  hardened prod stack: combine explicitly, e.g.
  `-f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.services.yml`.

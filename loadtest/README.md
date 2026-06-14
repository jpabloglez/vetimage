# VetImage — Load, Stress & Connectivity Testing (k6)

API performance/resilience testing for the VetImage backend using
[k6](https://k6.io/). Scripts run in the official `grafana/k6` Docker image on
the app's Docker network — **no local k6 install required**.

## Layout

```
loadtest/k6/
├── lib/common.js      # BASE_URL + shared request helpers (health, models, login)
├── connectivity.js    # fast API sanity smoke (1 VU, strict thresholds)
├── load.js            # sustained expected traffic (SLO thresholds gate exit code)
└── stress.js          # push beyond peak to find the breaking point
```

## Running

From the repo root (the stack must be up — `make up`):

```bash
make loadtest-connectivity   # ~3s  smoke test
make loadtest-load           # ~2m  sustained load, fails build if SLOs breached
make loadtest-stress         # ~2.5m capacity / breaking-point characterisation
make loadtest                # connectivity + load
```

### Overrides

| Variable | Default | Purpose |
|---|---|---|
| `K6_BASE_URL` | `http://backend-vetimage:3080` | Target API (in-network). Use `http://localhost:3081` from the host, or a deployed URL. |
| `K6_VUS` | 20 (load) / 100 (stress) | Peak virtual users. |
| `K6_EMAIL` / `K6_PASSWORD` | unset | Optional — enables the authenticated login connectivity check. |

```bash
make loadtest-load K6_VUS=50
make loadtest-stress K6_VUS=300
make loadtest-connectivity K6_EMAIL=vet@clinic.com K6_PASSWORD=secret
```

Run any script directly:

```bash
docker run --rm -i --network vetimage_app-network \
  -v "$PWD/loadtest/k6:/scripts" -e BASE_URL=http://backend-vetimage:3080 \
  grafana/k6 run /scripts/load.js
```

## Thresholds (what gates a pass)

- **connectivity.js** — 100% checks pass, 0% HTTP errors, p95 < 1000 ms.
- **load.js** — error rate < 1%, p95 < 800 ms, p99 < 1500 ms, checks > 99%.
  A breached threshold makes k6 exit non-zero → use as a CI/post-deploy gate.
- **stress.js** — lenient guard rails only (errors < 25%, p99 < 8 s). Read the
  printed p95/p99/error-rate to characterise capacity; degradation is expected.

## Endpoints exercised

Public, side-effect-free reads so the suite is safe to run against any
environment: `GET /api/health/` and `GET /api/ai-analysis/models/`. The optional
login check (`POST /users/auth/login/`) runs only when credentials are provided.
To extend coverage to authenticated/owner/VHS/report endpoints, capture a token
via `tryLogin()` and add authenticated requests in a new scenario.

## CI usage

`make loadtest-connectivity` is a fast post-deploy smoke gate. `make loadtest-load`
can run nightly or pre-release; its non-zero exit on SLO breach fails the job.

// Shared helpers for VetImage k6 test scripts.
//
// BASE_URL defaults to the in-network backend service so the grafana/k6 container
// can run on `vetimage_app-network`. Override with -e BASE_URL=... to target a
// host port (e.g. http://localhost:3081) or a deployed environment.
import http from 'k6/http';
import { check } from 'k6';

export const BASE_URL = __ENV.BASE_URL || 'http://backend-vetimage:3080';

// Public, unauthenticated endpoints that are always safe to hammer.
export const ENDPOINTS = {
  health: `${BASE_URL}/api/health/`,
  models: `${BASE_URL}/api/ai-analysis/models/`,
};

export function getHealth() {
  const res = http.get(ENDPOINTS.health, { tags: { name: 'health' } });
  check(res, { 'health 200': (r) => r.status === 200 });
  return res;
}

export function getModels() {
  const res = http.get(ENDPOINTS.models, { tags: { name: 'models' } });
  check(res, {
    'models 200': (r) => r.status === 200,
    'models is json': (r) => (r.headers['Content-Type'] || '').includes('application/json'),
  });
  return res;
}

// Optional authenticated connectivity check. Only runs when credentials are
// provided via env (K6_EMAIL / K6_PASSWORD), so the suite never hard-depends on
// seeded users.
export function tryLogin() {
  const email = __ENV.K6_EMAIL;
  const password = __ENV.K6_PASSWORD;
  if (!email || !password) return null;

  const res = http.post(
    `${BASE_URL}/users/auth/login/`,
    JSON.stringify({ email, password }),
    { headers: { 'Content-Type': 'application/json' }, tags: { name: 'login' } },
  );
  check(res, { 'login 200': (r) => r.status === 200 });
  try { return res.json('access'); } catch (_) { return null; }
}

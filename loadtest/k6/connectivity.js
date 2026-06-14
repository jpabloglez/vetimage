// Connectivity smoke test — fast sanity check that the API is reachable and
// responding correctly. Run this first (e.g. in CI / post-deploy) before any
// load test. Strict thresholds: zero failed checks, low latency, no HTTP errors.
//
//   make loadtest-connectivity
//
import { sleep } from 'k6';
import { getHealth, getModels, tryLogin, BASE_URL } from './lib/common.js';

export const options = {
  vus: 1,
  iterations: 5,
  thresholds: {
    checks: ['rate==1.0'],            // every check must pass
    http_req_failed: ['rate==0.0'],   // no transport/HTTP errors
    http_req_duration: ['p(95)<1000'], // generous for a cold smoke test
  },
};

export default function () {
  getHealth();
  getModels();
  tryLogin(); // no-op unless K6_EMAIL / K6_PASSWORD are set
  sleep(0.5);
}

export function handleSummary(data) {
  const checks = data.metrics.checks ? data.metrics.checks.values.rate : 0;
  return {
    stdout: `\nVetImage connectivity smoke @ ${BASE_URL}\n` +
      `  checks passed: ${(checks * 100).toFixed(1)}%\n` +
      `  p95 latency:   ${(data.metrics.http_req_duration?.values['p(95)'] ?? 0).toFixed(1)} ms\n`,
  };
}

// Load test — sustained, realistic traffic against read endpoints to validate
// the API holds its latency/error SLOs under expected concurrency.
//
//   make loadtest-load                  # default profile
//   make loadtest-load K6_VUS=50        # override peak VUs
//
// Profile: ramp up → hold → ramp down. Thresholds encode the SLO; a failing
// threshold makes k6 exit non-zero (CI gate).
import { sleep } from 'k6';
import { getHealth, getModels, BASE_URL } from './lib/common.js';

const PEAK = parseInt(__ENV.K6_VUS || '20', 10);

export const options = {
  scenarios: {
    steady_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: PEAK },  // ramp up
        { duration: '1m', target: PEAK },    // hold
        { duration: '20s', target: 0 },      // ramp down
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],        // < 1% errors
    http_req_duration: ['p(95)<800', 'p(99)<1500'],
    checks: ['rate>0.99'],
  },
};

export default function () {
  // Mix of the two cheapest public reads — representative of dashboard polling.
  getHealth();
  getModels();
  sleep(1);
}

export function handleSummary(data) {
  const d = data.metrics.http_req_duration?.values || {};
  return {
    stdout: `\nVetImage load test @ ${BASE_URL} (peak ${PEAK} VUs)\n` +
      `  requests:    ${data.metrics.http_reqs?.values.count ?? 0}\n` +
      `  error rate:  ${((data.metrics.http_req_failed?.values.rate ?? 0) * 100).toFixed(2)}%\n` +
      `  p95 / p99:   ${(d['p(95)'] ?? 0).toFixed(0)} / ${(d['p(99)'] ?? 0).toFixed(0)} ms\n`,
  };
}

// Stress test — push concurrency well beyond expected peak to find the breaking
// point and observe how the API degrades (latency growth, error onset).
//
//   make loadtest-stress
//   make loadtest-stress K6_VUS=200
//
// Thresholds are deliberately lenient (we EXPECT degradation here); they exist
// to flag catastrophic failure, not to gate normal SLOs. Read the p95/p99 and
// error-onset point in the summary to characterise capacity.
import { sleep } from 'k6';
import { getHealth, getModels, BASE_URL } from './lib/common.js';

const PEAK = parseInt(__ENV.K6_VUS || '100', 10);

export const options = {
  scenarios: {
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: Math.round(PEAK / 2) },
        { duration: '30s', target: PEAK },
        { duration: '1m', target: PEAK },     // sustain peak
        { duration: '30s', target: 0 },       // recovery
      ],
      gracefulRampDown: '15s',
    },
  },
  thresholds: {
    // Catastrophic-failure guard rails only.
    http_req_failed: ['rate<0.25'],
    http_req_duration: ['p(99)<8000'],
  },
};

export default function () {
  getHealth();
  getModels();
  sleep(0.5);
}

export function handleSummary(data) {
  const d = data.metrics.http_req_duration?.values || {};
  return {
    stdout: `\nVetImage STRESS test @ ${BASE_URL} (peak ${PEAK} VUs)\n` +
      `  requests:    ${data.metrics.http_reqs?.values.count ?? 0}\n` +
      `  error rate:  ${((data.metrics.http_req_failed?.values.rate ?? 0) * 100).toFixed(2)}%\n` +
      `  p95 / p99:   ${(d['p(95)'] ?? 0).toFixed(0)} / ${(d['p(99)'] ?? 0).toFixed(0)} ms\n` +
      `  max:         ${(d.max ?? 0).toFixed(0)} ms\n`,
  };
}

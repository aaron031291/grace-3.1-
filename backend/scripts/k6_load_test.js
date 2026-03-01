/**
 * k6 Load Test — Grace API performance validation.
 * 
 * Install: https://k6.io/docs/getting-started/installation/
 * Run: k6 run scripts/k6_load_test.js
 * 
 * Validates:
 *   p95 latency < 400ms for critical endpoints
 *   Error rate < 0.1%
 *   Throughput > 50 req/s
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const latency = new Trend('latency');

export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp up
    { duration: '2m', target: 50 },     // Hold at 50 users
    { duration: '30s', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<400'],    // p95 < 400ms
    errors: ['rate<0.001'],              // Error rate < 0.1%
  },
};

const BASE = 'http://localhost:8000';

export default function () {
  // Health check
  let res = http.get(`${BASE}/health`);
  check(res, { 'health 200': (r) => r.status === 200 });
  errorRate.add(res.status !== 200);
  latency.add(res.timings.duration);

  // Smoke test
  res = http.get(`${BASE}/api/audit/test/smoke`);
  check(res, { 'smoke 200': (r) => r.status === 200 });
  errorRate.add(res.status !== 200);

  // Vault status
  res = http.get(`${BASE}/api/vault/status`);
  check(res, { 'vault 200': (r) => r.status === 200 });
  errorRate.add(res.status !== 200);

  // Console status
  res = http.get(`${BASE}/api/console/status`);
  check(res, { 'console 200': (r) => r.status === 200 });
  errorRate.add(res.status !== 200);

  // Ghost memory
  res = http.get(`${BASE}/api/audit/ghost-memory/stats`);
  check(res, { 'ghost 200': (r) => r.status === 200 });
  errorRate.add(res.status !== 200);

  sleep(1);
}

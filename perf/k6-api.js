import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:3001';
const ACCESS_TOKEN = __ENV.TOKEN || '';
const TOOL_ID = __ENV.TOOL_ID || '';
const START_VUS = Number(__ENV.START_VUS || 1);
const RAMP_DURATION = __ENV.RAMP_DURATION || '30s';
const STEADY_DURATION = __ENV.STEADY_DURATION || '2m';
const RAMP_DOWN_DURATION = __ENV.RAMP_DOWN_DURATION || '30s';
const STEADY_TARGET_VUS = Number(__ENV.STEADY_TARGET_VUS || 10);

const HEADERS = ACCESS_TOKEN
  ? { Authorization: `Bearer ${ACCESS_TOKEN}` }
  : {};

export const options = {
  scenarios: {
    baseline: {
      executor: 'ramping-vus',
      startVUs: START_VUS,
      stages: [
        { duration: RAMP_DURATION, target: STEADY_TARGET_VUS },
        { duration: STEADY_DURATION, target: STEADY_TARGET_VUS },
        { duration: RAMP_DOWN_DURATION, target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.02'],
    http_req_duration: ['p(95)<1200', 'p(99)<2000'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

function hit(url, tags) {
  const res = http.get(url, { headers: HEADERS, tags });
  check(res, { 'status is 2xx/3xx': (r) => r.status >= 200 && r.status < 400 });
}

export default function () {
  hit(`${BASE_URL}/api/v1/tools/?skip=0&limit=20`, { endpoint: 'tools_list' });

  if (TOOL_ID) {
    hit(
      `${BASE_URL}/api/v1/admin/tools/${TOOL_ID}/usage-logs?skip=0&limit=20`,
      { endpoint: 'tool_usage_logs' }
    );
  }

  sleep(1);
}

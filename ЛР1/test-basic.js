import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  const response = http.get('http://127.0.0.1:8080');
  check(response, {
    'status is 200': (r) => r.status === 200,
  });
  sleep(1);
}

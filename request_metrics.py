"""Small bounded Prometheus text exporter for this standard-library lab."""
from collections import defaultdict
from threading import Lock

class RequestMetrics:
    def __init__(self):
        self._lock = Lock()
        self._counts = defaultdict(int)
        self._seconds = defaultdict(float)

    def observe(self, route, status, seconds):
        if route not in {'/', '/healthz', 'unmatched'} or status not in {200, 404} or seconds < 0:
            raise ValueError('invalid request observation')
        with self._lock:
            self._counts[(route, status)] += 1
            self._seconds[(route, status)] += seconds

    def render(self):
        with self._lock:
            rows = [(key, self._counts[key], self._seconds[key]) for key in sorted(self._counts)]
        lines = ['# HELP workplace_http_requests_total Handled application GET requests excluding scrapes.',
                 '# TYPE workplace_http_requests_total counter']
        for (route, status), count, _ in rows:
            lines.append(f'workplace_http_requests_total{{route="{route}",status="{status}"}} {count}')
        lines.extend(['# HELP workplace_http_request_duration_seconds Server handler duration in seconds excluding scrapes.',
                      '# TYPE workplace_http_request_duration_seconds summary'])
        for (route, status), count, seconds in rows:
            labels = f'{{route="{route}",status="{status}"}}'
            lines.append(f'workplace_http_request_duration_seconds_count{labels} {count}')
            lines.append(f'workplace_http_request_duration_seconds_sum{labels} {seconds:.9f}')
        return '\n'.join(lines) + '\n'

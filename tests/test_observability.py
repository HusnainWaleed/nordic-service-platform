import concurrent.futures
import contextlib
import io
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen
from app import Handler, ServiceServer
from request_metrics import RequestMetrics

class MetricsTests(unittest.TestCase):
    def test_concurrent_observations_are_not_lost(self):
        metrics = RequestMetrics()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: metrics.observe('/healthz', 200, .01), range(1000)))
        text = metrics.render()
        self.assertIn('workplace_http_requests_total{route="/healthz",status="200"} 1000\n', text)
        self.assertIn('workplace_http_request_duration_seconds_sum{route="/healthz",status="200"} 10.000000000\n', text)

    def test_unbounded_labels_are_rejected(self):
        with self.assertRaises(ValueError): RequestMetrics().observe('/private-user-path', 200, 1)

class ObservabilityHttpTests(unittest.TestCase):
    def setUp(self):
        self.server = ServiceServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=5)
    def scrape(self):
        with urlopen(self.base+'/metrics', timeout=3) as response:
            self.assertIn('version=0.0.4', response.headers['Content-Type'])
            return response.read().decode()
    def test_scrapes_are_excluded_from_application_counts(self):
        with urlopen(self.base+'/healthz', timeout=3) as response: response.read()
        first = self.scrape(); second = self.scrape()
        self.assertEqual(first, second)
        self.assertIn('workplace_http_requests_total{route="/healthz",status="200"} 1\n', second)
        self.assertNotIn('route="/metrics"', second)
    def test_raw_paths_and_query_values_are_not_exposed(self):
        log = io.StringIO()
        with contextlib.redirect_stderr(log):
            with self.assertRaises(HTTPError) as error:
                urlopen(self.base+'/synthetic-private-id?token=synthetic-secret', timeout=3)
            error.exception.close()
            text = self.scrape()
        self.assertNotIn('synthetic-private-id', text+log.getvalue())
        self.assertNotIn('synthetic-secret', text+log.getvalue())
        events = [json.loads(line) for line in log.getvalue().splitlines()]
        self.assertTrue(any(e['route']=='unmatched' and e['status']==404 for e in events))
        self.assertIn('route="unmatched",status="404"', text)

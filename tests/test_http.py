import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from app import Handler, ThreadingHTTPServer


class HttpContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_health_response(self):
        with urlopen(self.base + '/healthz', timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), 'application/json')
            self.assertEqual(json.load(response), {'status': 'ok', 'service': 'workplace-status'})

    def test_unknown_route_is_not_healthy(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base + '/missing', timeout=3)
        self.assertEqual(error.exception.code, 404)
        error.exception.close()

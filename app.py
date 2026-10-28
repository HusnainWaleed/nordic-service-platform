"""Synthetic workplace status service; no personal or employer data."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sys
import time
from request_metrics import RequestMetrics

class ServiceServer(ThreadingHTTPServer):
    def __init__(self, *args, **kwargs):
        self.metrics = RequestMetrics()
        super().__init__(*args, **kwargs)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        started = time.monotonic()
        path = self.path.split('?', 1)[0]
        route = path if path in {'/', '/healthz', '/metrics'} else 'unmatched'
        status = 404 if route == 'unmatched' else 200
        if route == '/metrics':
            body = self.server.metrics.render().encode()
            content_type = 'text/plain; version=0.0.4; charset=utf-8'
        else:
            body = json.dumps({'status': 'ok', 'service': 'workplace-status'} if status == 200 else {'error': 'not found'}).encode()
            content_type = 'application/json'
        try:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body)
        finally:
            seconds = time.monotonic() - started
            if route != '/metrics': self.server.metrics.observe(route, status, seconds)
            # Never include raw URLs, query strings, headers or client addresses.
            print(json.dumps({'event': 'http_request', 'route': route, 'status': status,
                              'duration_seconds': round(seconds, 6)}), file=sys.stderr, flush=True)

    def log_message(self, format, *args):
        # Disable BaseHTTPRequestHandler's raw request logging, including errors.
        pass

if __name__ == '__main__': ServiceServer(('0.0.0.0', 8080), Handler).serve_forever()

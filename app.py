"""Synthetic workplace status service; no personal or employer data."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/', '/healthz'):
            self.send_error(404); return
        body = json.dumps({'status': 'ok', 'service': 'workplace-status'}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)

if __name__ == '__main__': ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()

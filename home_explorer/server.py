"""Home Explorer v0.1.0: read-only Home Assistant domain inventory.

The Supervisor API token is server-side and has broad authority; source-code
read-only restrictions are not an HA API permission boundary.
"""
import json
import os
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PORT = 8099
INGRESS_GATEWAY = '172.30.32.2'
BASE = Path(__file__).resolve().parent
MAX_RESPONSE_BYTES = 12 * 1024 * 1024


def fetch_states():
    token = os.environ.get('SUPERVISOR_TOKEN', '')
    if not token:
        raise RuntimeError('Supervisor API token unavailable')
    request = Request(
        'http://supervisor/core/api/states',
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'},
        method='GET',
    )
    with urlopen(request, timeout=12) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError('Inventory exceeds response limit')
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError('Unexpected response type')
    return data


EXCLUDED = {'person', 'device_tracker', 'camera', 'image', 'calendar',
            'conversation', 'stt', 'tts', 'update', 'event'}


def inventory(states):
    """Return category totals, never entity names, attributes or addresses."""
    counts = Counter()
    for item in states:
        if not isinstance(item, dict):
            continue
        entity = item.get('entity_id', '')
        if not isinstance(entity, str) or '.' not in entity:
            continue
        domain = entity.split('.', 1)[0]
        if domain not in EXCLUDED:
            counts[domain] += 1
    return {
        'version': '0.1.0',
        'mode': 'read-only',
        'total_visible_entities': sum(counts.values()),
        'groups': [{'domain': key, 'count': value} for key, value in sorted(counts.items())],
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, body, content_type, status=200):
        self.send_response(status)
        for key, value in {
            'Content-Type': content_type,
            'Content-Length': str(len(body)),
            'Cache-Control': 'no-store',
            'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'no-referrer',
            'Content-Security-Policy':
                "default-src 'none'; style-src 'self'; script-src 'self'; "
                "connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'",
        }.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.client_address[0] != INGRESS_GATEWAY:
            return self.send(b'Forbidden', 'text/plain', 403)
        route = self.path.split('?', 1)[0].rstrip('/')
        if route.endswith('/api/inventory'):
            try:
                payload = json.dumps(inventory(fetch_states())).encode()
                return self.send(payload, 'application/json')
            except (HTTPError, URLError, ValueError, RuntimeError, TimeoutError):
                return self.send(b'{"error":"Could not fetch Home Assistant inventory"}', 'application/json', 503)
        if route.endswith('/app.js'):
            return self.send((BASE / 'web/app.js').read_bytes(), 'application/javascript')
        if route.endswith('/style.css'):
            return self.send((BASE / 'web/style.css').read_bytes(), 'text/css')
        if '/api/' in route:
            return self.send(b'Not found', 'text/plain', 404)
        return self.send((BASE / 'web/index.html').read_bytes(), 'text/html; charset=utf-8')

    def do_POST(self):
        self.send(b'Read-only prototype', 'text/plain', 405)

    do_PUT = do_PATCH = do_DELETE = do_POST


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()

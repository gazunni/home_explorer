"""Home Explorer 0.2.0. Read-only, on-demand registry discovery."""
import json
import os
import re
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from websockets.sync.client import connect

BASE = Path(__file__).resolve().parent / "web"
PORT = 8099
GATEWAY = "172.30.32.2"
MAX_DEVICES = 1000
MAX_ENTITIES = 10000
# Excluded from the browser, including names and capabilities.
SENSITIVE = {
    "person", "device_tracker", "camera", "image", "lock", "alarm_control_panel",
    "siren", "notify", "conversation", "calendar", "stt", "tts", "todo",
}
# Names alone can leak personal info; these filters are deliberately conservative.
PRIVATE_NAME = re.compile(
    r"(?:camera|door|lock|alarm|siren|presence|location|gps|person|"
    r"ipad|iphone|phone|pixel|galaxy|tablet|webhook|email|"
    r"motion|leak|moisture|security|fob|@)",
    re.IGNORECASE,
)
ALLOWED_DOMAINS = {
    "light", "switch", "sensor", "binary_sensor", "fan", "climate", "humidifier",
    "vacuum", "lawn_mower", "cover", "media_player", "number", "select",
    "button", "update", "remote",
}
EXCLUDED_DOMAINS = {"update"}  # technical update entities not meaningful features


def registry_request():
    """Read only the device and entity registries, never call services."""
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    if not token:
        raise RuntimeError("Supervisor token missing")
    with connect(
        "ws://supervisor/core/websocket",
        open_timeout=12, close_timeout=4, max_size=16 * 1024 * 1024
    ) as ws:
        greeting = json.loads(ws.recv(timeout=12))
        if greeting.get("type") != "auth_required":
            raise RuntimeError("Unexpected WebSocket greeting")
        ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(ws.recv(timeout=12)).get("type") != "auth_ok":
            raise RuntimeError("Authentication unsuccessful")
        result = []
        for req_id, kind in enumerate(
            ("config/device_registry/list", "config/entity_registry/list"), start=1
        ):
            ws.send(json.dumps({"id": req_id, "type": kind}))
            message = json.loads(ws.recv(timeout=15))
            if message.get("id") != req_id or not message.get("success"):
                raise RuntimeError("Registry query not available")
            if not isinstance(message.get("result"), list):
                raise RuntimeError("Unexpected registry result")
            result.append(message["result"])
        return result


def scan(devices, entities):
    if len(devices) > MAX_DEVICES or len(entities) > MAX_ENTITIES:
        raise RuntimeError("Registry size exceeds safety limits")
    by_device = defaultdict(list)
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        device_id = entity.get("device_id")
        entity_id = entity.get("entity_id", "")
        if not device_id or not isinstance(entity_id, str) or "." not in entity_id:
            continue
        domain = entity_id.split(".", 1)[0]
        if domain in ALLOWED_DOMAINS and domain not in EXCLUDED_DOMAINS:
            if entity.get("disabled_by") is None:
                by_device[device_id].append(domain)
    results = []
    hidden = 0
    for device in devices:
        if not isinstance(device, dict) or not isinstance(device.get("id"), str):
            continue
        # Child devices: attach features to parent only when supported by device registry.
        name = device.get("name_by_user") or device.get("name") or device.get("model") or "Unnamed device"
        manufacturer = device.get("manufacturer") or "Unknown manufacturer"
        model = device.get("model") or "Unknown model"
        if not all(isinstance(v, str) for v in (name, manufacturer, model)):
            hidden += 1
            continue
        domains = by_device.get(device["id"], [])
        if PRIVATE_NAME.search(" ".join((name, manufacturer, model))):
            hidden += 1
            continue
        # Avoid exposing sensitive-only devices, but don't claim names are verified safe.
        if not domains:
            continue
        kinds = Counter(domains)
        results.append({
            "name": name[:90],
            "manufacturer": manufacturer[:75],
            "model": model[:75],
            "capabilities": [
                {"type": kind.replace("_", " ").title(), "entities": number}
                for kind, number in sorted(kinds.items())
            ],
            "entity_count": len(domains),
            "source": "Home Assistant registry",
        })
    results.sort(key=lambda item: (item["manufacturer"].casefold(), item["name"].casefold()))
    return {
        "version": "0.2.0",
        "mode": "read-only",
        "registered_devices": len(devices),
        "registered_entities": len(entities),
        "displayed_devices": len(results),
        "hidden_private_devices": hidden,
        "devices": results[:500],
        "note": "Capabilities are inferred from registered entity types, not manufacturer documentation.",
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        return

    def reply(self, status, content, mime):
        self.send_response(status)
        headers = {
            "Content-Type": mime,
            "Content-Length": str(len(content)),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "SAMEORIGIN",
            "Content-Security-Policy": "default-src 'none'; script-src 'self'; "
              "style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'",
        }
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.client_address[0] != GATEWAY:
            return self.reply(403, b"Forbidden", "text/plain")
        # Ingress prepends a variable path: accept ONLY known suffixes.
        path = self.path.split("?", 1)[0].rstrip("/")
        if path.endswith("/api/devices"):
            try:
                devices, entities = registry_request()
                data = json.dumps(scan(devices, entities)).encode()
                return self.reply(200, data, "application/json")
            except Exception:
                return self.reply(503, b'{"error":"Registry scan unavailable. Check application logs."}', "application/json")
        for suffix, filename, mime in (
            ("/app.js", "app.js", "text/javascript"),
            ("/style.css", "style.css", "text/css"),
        ):
            if path.endswith(suffix):
                return self.reply(200, (BASE / filename).read_bytes(), mime)
        if path.endswith("/api") or "/api/" in path:
            return self.reply(404, b"Not found", "text/plain")
        if path.endswith(("/", "/home_explorer")) or path.endswith("/index.html") or path:
            return self.reply(200, (BASE / "index.html").read_bytes(), "text/html")
        return self.reply(404, b"Not found", "text/plain")

    def do_POST(self):
        self.reply(405, b"Read-only", "text/plain")

    do_PUT = do_DELETE = do_PATCH = do_POST


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

"""Home Explorer 0.4.0: on-demand, read-only registry exploration."""
import json
import os
import re
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from websockets.sync.client import connect

BASE = Path(__file__).resolve().parent / 'web'
PORT = 8099
GATEWAY = '172.30.32.2'
MAX_DEVICES = 1000
MAX_ENTITIES = 10000
PRIVATE_NAME = re.compile(
    r'(?:camera|door|lock|alarm|siren|presence|location|gps|person|'
    r'ipad|iphone|phone|pixel|galaxy|tablet|webhook|email|'
    r'motion|leak|moisture|security|fob|@|\b(?:dave|david|cindy|gazunni)\b)', re.IGNORECASE)
ALLOWED_DOMAINS = {
    'light', 'switch', 'sensor', 'binary_sensor', 'fan', 'climate',
    'humidifier', 'vacuum', 'lawn_mower', 'cover', 'media_player',
    'number', 'select', 'button', 'remote',
}

def registry_request():
    token = os.environ.get('SUPERVISOR_TOKEN', '')
    if not token:
        raise RuntimeError('Supervisor token missing')
    with connect('ws://supervisor/core/websocket', open_timeout=12,
                 close_timeout=4, max_size=16 * 1024 * 1024) as ws:
        greeting = json.loads(ws.recv(timeout=12))
        if greeting.get('type') != 'auth_required':
            raise RuntimeError('Unexpected WebSocket greeting')
        ws.send(json.dumps({'type': 'auth', 'access_token': token}))
        if json.loads(ws.recv(timeout=12)).get('type') != 'auth_ok':
            raise RuntimeError('Authentication failed')
        result = []
        for request_id, kind in enumerate(
                ('config/device_registry/list', 'config/entity_registry/list'), 1):
            ws.send(json.dumps({'id': request_id, 'type': kind}))
            message = json.loads(ws.recv(timeout=15))
            if message.get('id') != request_id or not message.get('success'):
                raise RuntimeError('Registry query unavailable')
            if not isinstance(message.get('result'), list):
                raise RuntimeError('Unexpected registry result')
            result.append(message['result'])
        return result

# Descriptions are grounded only in domain semantics, never inferred vendor commands.
CAPABILITY_GUIDE = {
    'light': ('Lighting', 'Light control may support switching, dimming or colour if available.'),
    'switch': ('Power and switches', 'Switch entities may allow power control; some are configuration settings.'),
    'sensor': ('Measurements', 'Readings may include battery, energy, temperature or operating information.'),
    'binary_sensor': ('Conditions', 'On/off conditions such as activity or connected state.'),
    'fan': ('Air movement', 'Fan speed or on/off control may be available.'),
    'climate': ('Temperature control', 'Thermostat modes or target temperature may be available.'),
    'humidifier': ('Humidity management', 'Humidity setpoint and operating mode may be available.'),
    'vacuum': ('Cleaning', 'Vacuum operation and status may be available.'),
    'lawn_mower': ('Lawn care', 'Mower operation and status may be available.'),
    'cover': ('Shades and covers', 'Open, close or position may be available.'),
    'media_player': ('Entertainment', 'Playback or volume may be available.'),
    'number': ('Adjustable settings', 'A numeric device setting is exposed.'),
    'select': ('Modes and options', 'A selectable device mode or option is exposed.'),
    'button': ('Device actions', 'A one-time device command exists; details need verification.'),
    'remote': ('Remote commands', 'A remote-control entity is exposed.'),
}

# Classification is based on domain only. It is not an authorization or proof of a service call.
OBSERVATION_DOMAINS = {'sensor', 'binary_sensor'}
POTENTIAL_CONTROL_DOMAINS = ALLOWED_DOMAINS - OBSERVATION_DOMAINS

IDEAS = {
    'light': ('Lighting schedules', 'Consider sunset or bedtime lighting after checking existing automations.'),
    'fan': ('Comfort-based fan control', 'Consider temperature-based fan operation after verifying temperature sensors.'),
    'climate': ('Comfort and electricity', 'Review temperature schedules alongside electricity rate periods.'),
    'vacuum': ('Cleaning routines', 'Consider scheduled cleaning after checking presence and quiet hours.'),
    'lawn_mower': ('Lawn care scheduling', 'Consider mowing windows once weather and safety conditions are verified.'),
    'cover': ('Shade routines', 'Consider sunrise and sunset shade positioning.'),
    'humidifier': ('Humidity monitoring', 'Consider notifications for humidity or a full water tank when supported.'),
    'media_player': ('Entertainment routines', 'Consider grouping playback or power actions after reviewing controls.'),
    'sensor': ('Device monitoring', 'Explore meaningful alerts or trends for measured conditions.'),
    'switch': ('Power schedules', 'Review off-hours schedules for nonessential loads; avoid critical equipment.'),
}

def scan(devices, entities):
    if len(devices) > MAX_DEVICES or len(entities) > MAX_ENTITIES:
        raise RuntimeError('Registry exceeds safety limit')
    by_device = defaultdict(list)
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        dev = entity.get('device_id')
        entity_id = entity.get('entity_id', '')
        if not isinstance(dev, str) or not isinstance(entity_id, str) or '.' not in entity_id:
            continue
        domain = entity_id.split('.', 1)[0]
        if domain in ALLOWED_DOMAINS and entity.get('disabled_by') is None:
            by_device[dev].append(domain)
    # Internal registry keys are used only for grouping and are NEVER returned to the browser.
    lookup = {d['id']: d for d in devices if isinstance(d, dict) and isinstance(d.get('id'), str)}
    visible = {}
    hidden = 0
    virtual_count = 0
    for device_id, device in lookup.items():
        name = device.get('name_by_user') or device.get('name') or device.get('model') or 'Unnamed device'
        manufacturer = device.get('manufacturer') or 'Unknown manufacturer'
        model = device.get('model') or 'Unknown model'
        if not all(isinstance(x, str) for x in (name, manufacturer, model)):
            hidden += 1
            continue
        if PRIVATE_NAME.search(' '.join((name, manufacturer, model))):
            hidden += 1
            continue
        domains = by_device.get(device_id, [])
        if not domains:
            continue
        counts = Counter(domains)
        # Sense virtual detection is limited to known Sense integration metadata.
        # Never merge same-name entities without parent/device evidence.
        is_virtual = manufacturer.strip().casefold() in ('sense labs, inc.', 'sense labs inc.', 'sense labs') and model.strip().casefold() == 'sense'
        if is_virtual:
            virtual_count += 1
        guide = [{
            'type': CAPABILITY_GUIDE[k][0],
            'domain': k,
            'entities': n,
            'explanation': CAPABILITY_GUIDE[k][1],
            'access': 'Information only' if k in OBSERVATION_DOMAINS else 'Potential control',
            'verification': ('Read-only state/measurement category.'
                             if k in OBSERVATION_DOMAINS else
                             'Entity category suggests a possible control. Actual services, permissions, '
                             'supported features and device state have not been checked.'),
        } for k, n in sorted(counts.items())]
        ideas = [{'title': IDEAS[k][0], 'description': IDEAS[k][1]}
                 for k in ('light','fan','climate','vacuum','lawn_mower','cover','humidifier','media_player','switch','sensor')
                 if k in counts][:2]
        visible[device_id] = {
            'name': name[:90], 'manufacturer': manufacturer[:75], 'model': model[:75],
            'capabilities': guide, 'entity_count': len(domains), 'ideas': ideas,
            'observable_categories': sum(1 for k in counts if k in OBSERVATION_DOMAINS),
            'potential_control_categories': sum(1 for k in counts if k in POTENTIAL_CONTROL_DOMAINS),
            'kind': 'Energy-monitor detection' if is_virtual else 'Registered device',
            'virtual': is_virtual,
            'parent_id': device.get('via_device_id'),
        }
    for device_id, item in visible.items():
        parent = visible.get(item['parent_id'])
        if parent and parent is not item:
            item['related_to'] = parent['name']
        else:
            item['related_to'] = None
        del item['parent_id']
    result = list(visible.values())
    result.sort(key=lambda x: (x['virtual'], x['manufacturer'].casefold(), x['name'].casefold()))
    return {
        'version': '0.4.0', 'mode': 'read-only',
        'registered_devices': len(devices), 'registered_entities': len(entities),
        'displayed_devices': len(result), 'hidden_private_devices': hidden,
        'virtual_monitor_entries': virtual_count,
        'devices': result[:500],
        'note': 'Potential control does not establish an executable command. Whether a feature requires a manufacturer app cannot be determined from registry data. Suggestions are examples only; device commands and current automations have not been verified.'
    }

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, status, content, mime):
        self.send_response(status)
        for name, value in {
            'Content-Type': mime, 'Content-Length': str(len(content)),
            'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
            'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'SAMEORIGIN',
            'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'",
        }.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.client_address[0] != GATEWAY:
            return self.reply(403, b'Forbidden', 'text/plain')
        route = self.path.split('?', 1)[0].rstrip('/')
        if route.endswith('/api/devices'):
            try:
                data = json.dumps(scan(*registry_request())).encode()
                return self.reply(200, data, 'application/json')
            except Exception:
                return self.reply(503, b'{"error":"Registry scan unavailable; see app logs."}', 'application/json')
        for suffix, filename, mime in (('/app.js', 'app.js', 'text/javascript'),
                                        ('/style.css', 'style.css', 'text/css')):
            if route.endswith(suffix):
                return self.reply(200, (BASE / filename).read_bytes(), mime)
        if route.endswith('/api') or '/api/' in route:
            return self.reply(404, b'Not found', 'text/plain')
        return self.reply(200, (BASE / 'index.html').read_bytes(), 'text/html; charset=utf-8')

    def do_POST(self):
        return self.reply(405, b'Read-only', 'text/plain')
    do_PUT = do_PATCH = do_DELETE = do_POST

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()

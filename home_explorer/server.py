"""Home Explorer 0.11.0: on-demand, read-only registry exploration."""
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
    r'motion|leak|moisture|security|secret|credential|token|password|api[_-]?key|fob|@|\b(?:dave|david|cindy|gazunni)\b)', re.IGNORECASE)
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
                ('config/device_registry/list', 'config/entity_registry/list', 'get_states'), 1):
            ws.send(json.dumps({'id': request_id, 'type': kind}))
            message = json.loads(ws.recv(timeout=15))
            if message.get('id') != request_id or not message.get('success'):
                raise RuntimeError('Registry query unavailable')
            if not isinstance(message.get('result'), list):
                raise RuntimeError('Unexpected registry result')
            result.append(message['result'])
        ws.send(json.dumps({'id': 4, 'type': 'get_services'}))
        response = json.loads(ws.recv(timeout=15))
        services = response.get('result', {}) if response.get('id') == 4 and response.get('success') else {}
        configurations = []
        candidates = [state['entity_id'] for state in result[2]
                      if isinstance(state, dict) and isinstance(state.get('entity_id'), str)
                      and state['entity_id'].startswith('automation.')]
        candidates = list(dict.fromkeys(candidates))[:100]
        for offset, entity_id in enumerate(candidates, 5):
            try:
                ws.send(json.dumps({'id': offset, 'type': 'automation/config',
                                    'entity_id': entity_id}))
                reply = json.loads(ws.recv(timeout=3))
                payload = reply.get('result')
                if (reply.get('id') == offset and reply.get('success')
                        and isinstance(payload, dict)
                        and isinstance(payload.get('config'), dict)):
                    configurations.append(payload['config'])
            except (TimeoutError, OSError, ValueError):
                break
        return (*result, services if isinstance(services, dict) else {},
                configurations, len(candidates))

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

# Compact summaries use only explicitly registered, non-private entities.
# A summary is a snapshot, never a claim that an action is executable.
SUMMARY_PRIORITY = (
    ('current_status', 'Current status'), ('operating_state', 'Operating state'),
    ('remaining_time', 'Remaining time'), ('current_temperature', 'Temperature'),
    ('temperature', 'Temperature'), ('humidity', 'Humidity'),
    ('battery', 'Battery'), ('power', 'Power'), ('energy', 'Energy'),
)
def summarize_entities(entities):
    candidates = []
    for e in entities:
        entity_id = e['entity_id']
        suffix = entity_id.split('.', 1)[1]
        label = e['label']
        if e['state'] in ('Not available', 'unknown', 'unavailable'):
            continue
        for pos, (keyword, title) in enumerate(SUMMARY_PRIORITY):
            if suffix.endswith(keyword) or suffix.endswith(keyword + '_status'):
                candidates.append((pos, title, e['state'], e['domain']))
                break
    candidates.sort(key=lambda x: x[0])
    output = []
    seen = set()
    for _, title, state, domain in candidates:
        if title in seen:
            continue
        output.append({'label': title, 'state': state, 'domain': domain})
        seen.add(title)
        if len(output) == 3:
            break
    return output

# Explicit local configuration only; never infer electrical wiring from names.
# Edit power_dependencies.json to confirm relationships before they are displayed.
DEPENDENCY_FILE = Path('/data/power_dependencies.json')

def load_power_dependencies(path=DEPENDENCY_FILE):
    try:
        raw = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict) or len(raw) > 100:
        return {}
    result = {}
    for name, entity_id in raw.items():
        if (isinstance(name, str) and isinstance(entity_id, str)
                and 0 < len(name) <= 90
                and re.fullmatch(r'switch\.[a-z0-9_]{1,100}', entity_id)
                and not PRIVATE_NAME.search(name + ' ' + entity_id)):
            result[name] = entity_id
    return result

def save_power_dependencies(mapping, path=DEPENDENCY_FILE):
    """Atomically persist confirmed wiring only in the add-on's private data."""
    if not isinstance(mapping, dict) or len(mapping) > 100:
        raise ValueError('Invalid mapping')
    for name, entity_id in mapping.items():
        if (not isinstance(name, str) or not isinstance(entity_id, str)
                or not 0 < len(name) <= 90
                or not re.fullmatch(r'switch\.[a-z0-9_]{1,100}', entity_id)
                or PRIVATE_NAME.search(name + ' ' + entity_id)):
            raise ValueError('Invalid relationship')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(mapping, sort_keys=True), encoding='utf-8')
    temp.replace(path)
    return len(mapping)

def power_dependency(name, states, dependencies=None):
    mapping = load_power_dependencies() if dependencies is None else dependencies
    entity_id = mapping.get(name)
    if not entity_id:
        return None
    state = states.get(entity_id, 'Not available')
    if state not in ('on', 'off'):
        state = 'Not available'
    return {'source': 'Explicitly configured', 'supply_state': state,
            'interpretation': (
                'Upstream outlet is off; appliance readings may be unavailable.'
                if state == 'off' else
                'Upstream outlet is on; this does not prove appliance operation.'
                if state == 'on' else
                'Upstream outlet state could not be confirmed.'
            )}

def device_diagnostics(entities):
    """Evidence summary, not an assertion of connectivity or scheduled intent."""
    if not entities:
        return {'status':'No readings','available':0,'unavailable':0,'unknown':0}
    unavailable = sum(e['state'] in ('unavailable','Not available') for e in entities)
    unknown = sum(e['state'] == 'unknown' for e in entities)
    available = len(entities) - unavailable - unknown
    if available and unavailable:
        status = 'Partially available'
    elif available:
        status = 'Readings available'
    elif unavailable:
        status = 'Readings unavailable'
    else:
        status = 'No current readings'
    return {'status':status,'available':available,'unavailable':unavailable,'unknown':unknown}

def automation_counts(states):
    """Status counts only: no automation names, rules or identifiers returned."""
    rows = [s for s in (states or []) if isinstance(s, dict)
            and isinstance(s.get('entity_id'), str)
            and s['entity_id'].startswith('automation.')]
    counts = Counter(s.get('state', 'unknown') for s in rows)
    return {'total': len(rows), 'enabled': counts.get('on', 0),
            'disabled': counts.get('off', 0),
            'other': len(rows)-counts.get('on', 0)-counts.get('off', 0)}

def referenced_devices(config, device_entities):
    """Only exact references from known structured fields; ignore templates/text."""
    matches = set()
    if not isinstance(config, dict):
        return matches
    for plural, singular, kind in (('triggers','trigger','trigger'),
                                  ('conditions','condition','condition'),
                                  ('actions','action','action')):
        roots = config.get(plural, config.get(singular))
        stack = [(roots, 0)]
        examined = 0
        while stack and examined < 600:
            node, depth = stack.pop()
            examined += 1
            if depth > 12:
                continue
            if isinstance(node, list):
                stack.extend((v,depth+1) for v in node[:100])
            elif isinstance(node, dict):
                for field, value in node.items():
                    if field in ('entity_id', 'device_id'):
                        refs = value if isinstance(value, list) else [value]
                        for ref in refs[:100]:
                            if isinstance(ref, str) and ref in device_entities:
                                matches.add((device_entities[ref], kind))
                    elif field in ('trigger','condition','action','actions','conditions',
                                   'triggers','sequence','choose','default','then',
                                   'else','repeat','parallel','target'):
                        stack.append((value,depth+1))
    return matches

def automation_links(configurations, device_entities):
    links = defaultdict(lambda: {'trigger':0,'condition':0,'action':0})
    for config in (configurations or [])[:100]:
        for device_id, relation in referenced_devices(config,device_entities):
            links[device_id][relation] += 1
    return links

def scan(devices, entities, states=None, services=None, configurations=None, attempted=0):
    if len(devices) > MAX_DEVICES or len(entities) > MAX_ENTITIES:
        raise RuntimeError('Registry exceeds safety limit')
    by_device = defaultdict(list)
    entity_devices = {}
    states = states or []
    catalog = {}
    if isinstance(services, dict):
        for domain, entries in services.items():
            if domain in ALLOWED_DOMAINS and isinstance(entries, dict):
                catalog[domain] = sorted(k for k in entries
                    if isinstance(k, str) and re.fullmatch(r'[a-z_]{1,50}', k))[:40]
    metadata = {}
    for item in states:
        if not isinstance(item, dict):
            continue
        eid = item.get('entity_id')
        attrs = item.get('attributes')
        if not isinstance(eid, str) or not isinstance(attrs, dict):
            continue
        flags = attrs.get('supported_features')
        opts = attrs.get('options')
        metadata[eid] = {
            'supported_features': flags if type(flags) is int and 0 <= flags <= 2147483647 else None,
            'options': [v for v in opts[:20]
                        if isinstance(v, str) and len(v) <= 60 and not PRIVATE_NAME.search(v)]
                       if isinstance(opts, list) else []}

    safe_states = {}
    for item in (states or []):
        if not isinstance(item, dict):
            continue
        eid, value = item.get('entity_id'), item.get('state')
        if isinstance(eid, str) and isinstance(value, str) and len(value) <= 80 and eid.split('.', 1)[0] in ALLOWED_DOMAINS:
            safe_states[eid] = value
    confirmed_dependencies = load_power_dependencies()
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        dev = entity.get('device_id')
        entity_id = entity.get('entity_id', '')
        if not isinstance(dev, str) or not isinstance(entity_id, str) or '.' not in entity_id:
            continue
        domain = entity_id.split('.', 1)[0]
        label = entity.get('name') or entity.get('original_name') or entity_id.split('.', 1)[-1].replace('_', ' ')
        if not isinstance(label, str) or PRIVATE_NAME.search(entity_id + ' ' + label):
            continue
        if domain in ALLOWED_DOMAINS and entity.get('disabled_by') is None:
            entity_devices[entity_id] = dev
            entity_devices[dev] = dev
            by_device[dev].append({'domain': domain, 'entity_id': entity_id,
                                   'label': label[:90], 'state': safe_states.get(entity_id, 'Not available'),
                                   'metadata': metadata.get(entity_id, {})})
    associations = automation_links(configurations, entity_devices)
    # Internal registry keys are used only for grouping and are NEVER returned to the browser.
    lookup = {d['id']: d for d in devices if isinstance(d, dict) and isinstance(d.get('id'), str)}
    visible = {}
    hidden = 0
    virtual_count = 0
    registry_review = []
    disabled_count = 0
    empty_count = 0
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
        disabled_by = device.get('disabled_by')
        if disabled_by is not None:
            disabled_count += 1
        if not domains:
            empty_count += 1
        if disabled_by is not None or not domains:
            registry_review.append({
                'name': name[:90], 'manufacturer': manufacturer[:75],
                'model': model[:75], 'disabled_by': str(disabled_by)[:40] if disabled_by is not None else None,
                'visible_entities': len(domains),
                'review_reason': ('Disabled registration' if disabled_by is not None else 'No eligible visible entities'),
            })
        if not domains or disabled_by is not None:
            continue
        counts = Counter(e['domain'] for e in domains)
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
            'members': [{'name': e['label'], 'entity_id': e['entity_id'], 'state': e['state'], 'domain': e['domain'],
                        'supported_features': e['metadata'].get('supported_features'),
                        'options': e['metadata'].get('options', [])}
                        for e in domains if e['domain'] == k][:100],
            'domain_services': catalog.get(k, []),
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
            'summary': summarize_entities(domains),
            'diagnostics': device_diagnostics(domains),
            'power_dependency': power_dependency(name, safe_states, confirmed_dependencies),
            'automation_links': dict(associations.get(device_id, {'trigger':0,'condition':0,'action':0})),
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
        'version': '0.13.1', 'mode': 'read-only',
        'registered_devices': len(devices), 'registered_entities': len(entities),
        'displayed_devices': len(result), 'hidden_private_devices': hidden,
        'virtual_monitor_entries': virtual_count,
        'disabled_registrations': disabled_count,
        'empty_visible_registrations': empty_count,
        'registry_review': sorted(registry_review, key=lambda x: x['name'].casefold())[:250],
        'automations': {**automation_counts(states), 'configurations_checked': len(configurations or []), 'lookup_attempted': attempted},
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
        if route.endswith('/api/relationships'):
            return self.reply(200, json.dumps(load_power_dependencies()).encode(), 'application/json')
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
        if self.client_address[0] != GATEWAY:
            return self.reply(403, b'Forbidden', 'text/plain')
        route = self.path.split('?', 1)[0].rstrip('/')
        if not route.endswith('/api/relationships'):
            return self.reply(405, b'Not allowed', 'text/plain')
        if (self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json'
                or self.headers.get('X-Home-Explorer') != 'relationship-update'):
            return self.reply(415, b'Unsupported request', 'text/plain')
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 2 <= size <= 16000:
                return self.reply(413, b'Invalid request size', 'text/plain')
            mapping = json.loads(self.rfile.read(size))
            saved = save_power_dependencies(mapping)
            return self.reply(200, json.dumps({'saved': saved}).encode(), 'application/json')
        except (ValueError, TypeError):
            return self.reply(400, b'Invalid relationship', 'text/plain')
        except OSError:
            return self.reply(503, b'Local storage unavailable', 'text/plain')
    def do_PUT(self):
        return self.reply(405, b'Not allowed', 'text/plain')
    do_PATCH = do_DELETE = do_PUT

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()

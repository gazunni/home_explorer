"""Home Explorer: constrained registry exploration and local relationship storage."""
import json
import hashlib
import logging
import os
import re
import secrets
from urllib.parse import parse_qs, urlsplit
import threading
import time
from collections import Counter, defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from websockets.sync.client import connect

LOG = logging.getLogger('home_explorer')
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
BASE = Path(__file__).resolve().parent / 'web'
PORT = 8099
GATEWAY = '172.30.32.2'
MAX_DEVICES = 1000
MAX_ENTITIES = 10000
# Generic privacy terms only; never check in homeowner identifiers.
# Letter boundaries prevent "clock" matching "lock" and "outdoor" matching "door".
PRIVATE_NAME = re.compile(
    r'(?<![A-Za-z])(?:camera|door|lock|alarm|siren|presence|location|gps|person|'
    r'ipad|iphone|phone|pixel|galaxy|tablet|webhook|email|'
    r'motion|leak|moisture|security|secret|credential|token|password|api[_-]?key|fob)(?![A-Za-z])|@',
    re.IGNORECASE)
ALLOWED_DOMAINS = {
    'light', 'switch', 'sensor', 'binary_sensor', 'fan', 'climate',
    'humidifier', 'vacuum', 'lawn_mower', 'cover', 'media_player',
    'number', 'select', 'button', 'remote',
}

# This whitelist constrains the requests emitted by this application. It does
# not reduce the Supervisor token's underlying Home Assistant permissions.
READ_QUERY_TYPES = frozenset({
    'config/device_registry/list', 'config/entity_registry/list',
    'get_states', 'get_services', 'automation/config',
})
def read_query(query_type, **parameters):
    if query_type not in READ_QUERY_TYPES:
        raise ValueError('Home Assistant operation is not an approved read query')
    if query_type == 'automation/config':
        entity_id = parameters.get('entity_id')
        if (set(parameters) != {'entity_id'} or not isinstance(entity_id, str)
                or not re.fullmatch(r'automation\.[a-z0-9_]{1,128}', entity_id)):
            raise ValueError('Invalid automation reference')
    elif parameters:
        raise ValueError('Unexpected Home Assistant query parameters')
    return {'type': query_type, **parameters}

# Serialize scans to limit expensive concurrent Supervisor WebSocket sessions.
SCAN_LOCK = threading.Lock()
# Ephemeral per-scan lookup; automation names are never in normal scan results.
AUTOMATION_REFERENCES = {}
AUTOMATION_REFERENCES_AT = 0.0
AUTOMATION_REFERENCE_TTL = 1800
# Conservative metadata-only concealment. Security context takes priority over convenience.
SECURITY_NAME_PATTERN = re.compile(r'(?:alarm|armed|disarm|security|surveillance|camera|cctv|doorbell|lock|unlock|intrud|motion detect|entry|access control|keypad|presence|occupan|away mode|vacation|garage door|gate|siren|panic|smoke alarm|carbon monoxide|co detector|safe|credential|password|pin code|geo.?fenc)', re.IGNORECASE)

def automation_name_is_sensitive(alias):
    return not isinstance(alias, str) or not alias.strip() or bool(SECURITY_NAME_PATTERN.search(alias))


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
            ws.send(json.dumps({'id': request_id, **read_query(kind)}))
            message = json.loads(ws.recv(timeout=15))
            if message.get('id') != request_id or not message.get('success'):
                raise RuntimeError('Registry query unavailable')
            if not isinstance(message.get('result'), list):
                raise RuntimeError('Unexpected registry result')
            result.append(message['result'])
        ws.send(json.dumps({'id': 4, **read_query('get_services')}))
        response = json.loads(ws.recv(timeout=15))
        services = response.get('result', {}) if response.get('id') == 4 and response.get('success') else {}
        configurations = []
        candidates = [state['entity_id'] for state in result[2]
                      if isinstance(state, dict) and isinstance(state.get('entity_id'), str)
                      and state['entity_id'].startswith('automation.')]
        candidates = list(dict.fromkeys(candidates))[:100]
        for offset, entity_id in enumerate(candidates, 5):
            try:
                ws.send(json.dumps({'id': offset, **read_query('automation/config', entity_id=entity_id)}))
                reply = json.loads(ws.recv(timeout=3))
                payload = reply.get('result')
                if (reply.get('id') == offset and reply.get('success')
                        and isinstance(payload, dict)
                        and isinstance(payload.get('config'), dict)):
                    sanitized_internal = dict(payload['config'])
                    sanitized_internal['_he_source_entity'] = entity_id
                    configurations.append(sanitized_internal)
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

def power_dependency(name, states, dependencies=None, device_key=None, name_is_unique=True):
    mapping = load_power_dependencies() if dependencies is None else dependencies
    entity_id = mapping.get(device_key) if device_key else None
    if not entity_id and name_is_unique:
        entity_id = mapping.get(name)  # Legacy name-keyed relationships
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

def automation_action_overlap(configurations, device_entities):
    """Count DISTINCT fetched configurations directly referencing device actions.

    Not a conflict detector: no directions, schedules, execution or mutual
    exclusivity inferred. Shares the exact-reference semantics of automation_links.
    """
    counts = Counter()
    for configuration in (configurations or [])[:100]:
        if not isinstance(configuration, dict):
            continue
        targets = {device_id for device_id, role in
                   referenced_devices(configuration, device_entities)
                   if role == 'action'}
        for device_id in targets:
            counts[device_id] += 1
    return dict(counts)


def automation_explanations(configurations, device_entities):
    """Privacy-limited explanation of exact structured automation references.

    Never export automation labels, identifiers, target values, times, templates,
    service names, or raw configuration. Whitelist generic operation categories.
    """
    grouped = defaultdict(lambda: defaultdict(set))
    allowed = {
        'state': 'State change', 'numeric_state': 'Numeric threshold',
        'time': 'Time', 'time_pattern': 'Time pattern',
        'sun': 'Sun event', 'zone': 'Zone', 'device': 'Device event',
        'event': 'Event', 'template': 'Template (not interpreted)',
        'and': 'All conditions', 'or': 'Any condition', 'not': 'Negated condition',
        'trigger': 'Trigger condition',
    }
    for config in (configurations or [])[:100]:
        if not isinstance(config, dict):
            continue
        for plural, singular, role in (('triggers', 'trigger', 'trigger'),
                                       ('conditions', 'condition', 'condition'),
                                       ('actions', 'action', 'action')):
            root = config.get(plural, config.get(singular))
            stack = [(root, 0)]
            examined = 0
            while stack and examined < 600:
                node, depth = stack.pop()
                examined += 1
                if depth > 12:
                    continue
                if isinstance(node, list):
                    stack.extend((x, depth + 1) for x in node[:100])
                    continue
                if not isinstance(node, dict):
                    continue
                owners = set()
                for key in ('entity_id', 'device_id'):
                    raw = node.get(key)
                    values = raw if isinstance(raw, list) else [raw]
                    for value in values[:100]:
                        if isinstance(value, str) and value in device_entities:
                            owners.add(device_entities[value])
                if role == 'action':
                    kind = 'Action target (operation not verified)'
                else:
                    raw_kind = node.get('platform') if role == 'trigger' else node.get('condition')
                    if role == 'trigger' and raw_kind is None:
                        raw_kind = node.get('trigger')
                    kind = allowed.get(raw_kind, 'Other structured reference') if isinstance(raw_kind, str) else 'Other structured reference'
                for owner in owners:
                    grouped[owner][role].add(kind)
                for key in ('trigger', 'condition', 'action', 'actions', 'conditions',
                            'triggers', 'sequence', 'choose', 'default', 'then',
                            'else', 'repeat', 'parallel', 'target'):
                    if isinstance(node.get(key), (dict, list)):
                        stack.append((node[key], depth + 1))
    return {owner: {role: sorted(values)[:6] for role, values in roles.items()}
            for owner, roles in grouped.items()}


def automation_flow_summaries(configurations, device_entities):
    """Bounded per-device flow outlines from individual configurations.

    A flow shares one source automation, but phases are not asserted to execute
    in order or cause one another. Never return names, IDs, thresholds, time
    values, services, or original configuration fragments.
    """
    results = defaultdict(list)
    categories = {
        'state': 'State', 'numeric_state': 'Numeric threshold',
        'time': 'Time', 'time_pattern': 'Time pattern', 'sun': 'Sun',
        'zone': 'Zone', 'device': 'Device', 'event': 'Event',
        'template': 'Template (not interpreted)',
    }
    for config in (configurations or [])[:100]:
        if not isinstance(config, dict):
            continue
        roots = {
            'trigger': config.get('triggers', config.get('trigger', [])),
            'condition': config.get('conditions', config.get('condition', [])),
            'action': config.get('actions', config.get('action', [])),
        }
        roles = defaultdict(set)
        # Action direction is only attached to a device when a target explicitly
        # references one of its known entities. Keep all identities server-side.
        owner_directions = defaultdict(set)
        owner_branches = defaultdict(set)
        stages = {}
        branch = False
        unsupported = False
        for role, root in roots.items():
            kinds = set()
            stack = [(root, 0)]
            seen = 0
            while stack and seen < 600:
                node, depth = stack.pop()
                seen += 1
                if depth > 12:
                    unsupported = True
                    continue
                if isinstance(node, list):
                    stack.extend((child, depth + 1) for child in node[:100])
                    if len(node) > 100:
                        unsupported = True
                    continue
                if not isinstance(node, dict):
                    continue
                for key in ('entity_id', 'device_id'):
                    values = node.get(key)
                    values = values if isinstance(values, list) else [values]
                    for value in values[:100]:
                        if isinstance(value, str) and value in device_entities:
                            roles[device_entities[value]].add(role)
                if role == 'trigger':
                    kind = node.get('platform', node.get('trigger'))
                    if isinstance(kind, str):
                        kinds.add(categories.get(kind, 'Other trigger'))
                elif role == 'condition':
                    kind = node.get('condition')
                    if isinstance(kind, str):
                        kinds.add(categories.get(kind, 'Composite/other condition'))
                elif role == 'action' and any(k in node for k in ('action', 'service', 'device_id', 'target', 'entity_id')):
                    # Closed, privacy-safe action categories; do not return services or targets.
                    service = node.get('action', node.get('service'))
                    safe_actions = {
                        'climate.set_temperature': 'Thermostat target adjustment',
                        'climate.set_hvac_mode': 'Thermostat mode selection',
                        'climate.turn_off': 'Thermostat off command',
                        'climate.turn_on': 'Thermostat on command',
                        'switch.turn_on': 'Switch on command',
                        'switch.turn_off': 'Switch off command',
                        'light.turn_on': 'Light on command',
                        'light.turn_off': 'Light off command',
                        'fan.turn_on': 'Fan on command',
                        'fan.turn_off': 'Fan off command',
                        'fan.set_percentage': 'Fan speed adjustment',
                        'input_boolean.turn_on': 'Helper on command',
                        'input_boolean.turn_off': 'Helper off command',
                        'notify.notify': 'Notification action',
                    }
                    kinds.add(safe_actions.get(service, 'Other action (not interpreted)') if isinstance(service, str)
                              else 'Action step (not executed)')
                    # A service without an explicit known entity target cannot
                    # be attributed to the enclosing device.
                    if isinstance(service, str):
                        direction = ('on' if service in ('switch.turn_on', 'light.turn_on', 'fan.turn_on', 'climate.turn_on')
                                     else 'off' if service in ('switch.turn_off', 'light.turn_off', 'fan.turn_off', 'climate.turn_off')
                                     else None)
                        if direction:
                            target = node.get('target', {})
                            values = []
                            if isinstance(target, dict):
                                values.extend(target.get('entity_id', []) if isinstance(target.get('entity_id'), list)
                                              else [target.get('entity_id')])
                            values.extend(node.get('entity_id', []) if isinstance(node.get('entity_id'), list)
                                          else [node.get('entity_id')])
                            for v in values[:100]:
                                if isinstance(v, str) and v in device_entities:
                                    owner_directions[device_entities[v]].add(direction)
                                    if branch:
                                        owner_branches[device_entities[v]].add('branch_context_present')
                if 'value_template' in node or 'data_template' in node or 'template' in node:
                    unsupported = True
                if any(k in node for k in ('choose', 'repeat', 'parallel', 'if', 'then', 'else')):
                    branch = True
                if 'variables' in node or 'wait_template' in node:
                    unsupported = True
                for field in ('trigger','condition','action','actions','conditions','triggers',
                              'sequence','choose','default','then','else','repeat','parallel',
                              'target','if'):
                    child = node.get(field)
                    if isinstance(child, (dict, list)):
                        stack.append((child, depth + 1))
            if stack:
                unsupported = True
            stages[role] = sorted(kinds)[:5]
        if not any(roles.values()):
            continue
        phase = {
            'trigger': bool(roots['trigger']),
            'condition': bool(roots['condition']),
            'action': bool(roots['action']),
        }
        for owner, referenced_roles in roles.items():
            if len(results[owner]) >= 12:
                continue
            results[owner].append({
                'roles': [role for role in ('trigger','condition','action') if role in referenced_roles],
                'review_token': config.get('_he_review_token') if isinstance(config.get('_he_review_token'), str) else None,
                'automation_name': config.get('_he_display_name') if isinstance(config.get('_he_display_name'), str) else None,
                'name_concealed': bool(config.get('_he_name_concealed')),
                'phases': phase,
                'trigger_types': stages['trigger'],
                'condition_types': stages['condition'],
                'action_types': stages['action'],
                'branching': branch,
                'targeted_directions': sorted(owner_directions.get(owner, set())),
                'opposing_targeted_actions': len(owner_directions.get(owner, set())) > 1,
                'action_path_uncertain': branch,
                'needs_review': unsupported,
                'description': 'These phases are present in one automation configuration; their runtime sequence and outcomes are not verified.',
            })
    return dict(results)


def registry_classification(name, manufacturer, model, disabled_by, entity_total, eligible):
    """Conservative, metadata-only review; never assert a cloud scene was deleted."""
    vendor = manufacturer.casefold().strip()
    label = name.casefold()
    if disabled_by is not None:
        return 'Disabled registration', 'Disabled in Home Assistant; not evidence of deletion.'
    if (vendor in ('tuya', 'smart life', 'smartlife') and
            ('wind speed level' in label or 'tap-to-run' in label or 'scene' in label)):
        return 'Possible Tuya virtual scene', 'Name and integration suggest a scene/preset; verify in Smart Life. Not a physical-device fault.'
    if 'coordinator' in label or 'bridge' in label or 'hub' in label:
        return 'Possible infrastructure', 'May be a legitimate integration or network registration.'
    if entity_total == 0:
        return 'No registered entities', 'No entity-registry entries linked; this alone does not establish obsolescence.'
    if eligible == 0:
        return 'Entities excluded from display', 'Registered entities exist but none qualify for normal display.'
    return 'Review', 'Inspect this registration in Home Assistant.'


def outlet_meter_candidates(switches, entities):
    """Offer only uniquely matched same-device meter candidates; never certify wiring.

    Require the *entire* switch entity suffix plus a measurement suffix, rather than
    vague name similarity. Each sensor must belong to exactly one outlet candidate.
    """
    meters = []
    for e in entities:
        if e.get('domain') != 'sensor':
            continue
        meta = e.get('metadata', {})
        kind, unit = meta.get('device_class'), meta.get('unit')
        if (kind, unit) not in (('power', 'W'), ('power', 'kW'),
                                ('current', 'A'), ('current', 'mA'),
                                ('voltage', 'V')):
            continue
        try:
            value = float(e['state'])
            if not -1000000 < value < 1000000:
                continue
        except (ValueError, TypeError, KeyError):
            continue
        meters.append((e, kind, unit, value))
    matched = defaultdict(list)
    for meter, kind, unit, value in meters:
        suffix = meter['entity_id'].split('.', 1)[-1]
        owners = []
        for switch in switches:
            stem = switch['entity_id'].split('.', 1)[-1]
            if suffix.startswith(stem + '_') and suffix[len(stem)+1:] in (
                    'power', 'current_consumption', 'active_power', 'current',
                    'voltage', 'power_consumption'):
                owners.append(switch['entity_id'])
        if len(owners) == 1:
            matched[owners[0]].append({
                'kind': kind, 'value': value, 'unit': unit,
                'last_updated': meter.get('metadata', {}).get('last_updated')})
    return {key: values[:3] for key, values in matched.items()}


def meter_readings(entries):
    """Return bounded fresh/state numeric meter observations from one registry device."""
    observations = []
    seen = set()
    for entry in entries:
        if entry.get('domain') != 'sensor':
            continue
        props = entry.get('metadata') or {}
        kind, unit = props.get('device_class'), props.get('unit')
        if (kind, unit) not in (('power', 'W'), ('power', 'kW'),
                               ('current', 'A'), ('current', 'mA'),
                               ('voltage', 'V')):
            continue
        try:
            measurement = float(entry['state'])
            if not -1000000 < measurement < 1000000 or kind in seen:
                continue
        except (ValueError, TypeError, KeyError):
            continue
        seen.add(kind)
        observations.append({'kind': kind, 'value': measurement,
                             'unit': unit, 'last_updated': props.get('last_updated')})
        if len(observations) == 3:
            break
    return observations


def socket_child_candidates(lookup, by_device):
    """Correlate child socket sensors with switches on their actual parent device.

    A device-registry via_device_id relationship is necessary but not enough:
    require the *full* normalized child device name to match the terminal
    component of a unique parent switch ID. Never infer based on mere 'Sony'
    or similar fuzzy matches.
    """
    proposed = defaultdict(list)
    for child_id, child in lookup.items():
        parent_id = child.get('via_device_id')
        if not isinstance(parent_id, str) or parent_id not in lookup:
            continue
        if (child.get('disabled_by') is not None or
                (child.get('manufacturer') or '').casefold().strip() != 'tp-link'):
            continue
        child_name = child.get('name_by_user') or child.get('name')
        if not isinstance(child_name, str) or PRIVATE_NAME.search(child_name):
            continue
        suffix = re.sub(r'[^a-z0-9]+', '_', child_name.casefold()).strip('_')
        if len(suffix) < 8:
            continue
        observations = meter_readings(by_device.get(child_id, []))
        if not observations:
            continue
        parents = [e for e in by_device.get(parent_id, [])
                   if e.get('domain') == 'switch' and
                   e.get('entity_category') not in ('config', 'diagnostic')]
        matches = [e['entity_id'] for e in parents
                   if e['entity_id'].split('.', 1)[-1].endswith('_' + suffix)]
        if len(matches) == 1:
            proposed[(parent_id, matches[0])].append(observations)
    # Enforce uniqueness: a single switch cannot inherit two different sockets.
    return {key: groups[0] for key, groups in proposed.items() if len(groups) == 1}


def scan(devices, entities, states=None, services=None, configurations=None, attempted=0):
    global AUTOMATION_REFERENCES, AUTOMATION_REFERENCES_AT
    # Public scan shows ordinary names; sensitive aliases use opt-in opaque lookup.
    prepared = []
    new_references = {}
    for original in (configurations or [])[:100]:
        if not isinstance(original, dict):
            prepared.append(original)
            continue
        config = dict(original)
        alias = config.get('alias')
        if isinstance(alias, str) and 0 < len(alias) <= 255:
            key = secrets.token_urlsafe(18)
            if automation_name_is_sensitive(alias):
                config['_he_review_token'] = key
                config['_he_name_concealed'] = True
                new_references[key] = alias
            else:
                config['_he_display_name'] = alias
        prepared.append(config)
    configurations = prepared
    AUTOMATION_REFERENCES = new_references
    AUTOMATION_REFERENCES_AT = time.monotonic()
    if len(devices) > MAX_DEVICES or len(entities) > MAX_ENTITIES:
        raise RuntimeError('Registry exceeds safety limit')
    by_device = defaultdict(list)
    registry_entities = defaultdict(list)
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
            'friendly_name': attrs.get('friendly_name')[:90] if isinstance(attrs.get('friendly_name'), str) and not PRIVATE_NAME.search(attrs.get('friendly_name')) else None,
            'supported_features': flags if type(flags) is int and 0 <= flags <= 2147483647 else None,
            'device_class': attrs.get('device_class') if attrs.get('device_class') in ('power', 'current', 'voltage') else None,
            'entity_category': attrs.get('entity_category') if attrs.get('entity_category') in ('config', 'diagnostic') else None,
            'unit': attrs.get('unit_of_measurement') if attrs.get('unit_of_measurement') in ('W', 'kW', 'A', 'mA', 'V') else None,
            'last_updated': item.get('last_updated') if isinstance(item.get('last_updated'), str) else None,
            'last_changed': item.get('last_changed') if isinstance(item.get('last_changed'), str) else None,
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
        registry_entities[dev].append(entity)
        domain = entity_id.split('.', 1)[0]
        label = entity.get('name') or metadata.get(entity_id, {}).get('friendly_name') or entity.get('original_name') or entity_id.split('.', 1)[-1].replace('_', ' ')
        if not isinstance(label, str) or PRIVATE_NAME.search(entity_id + ' ' + label):
            continue
        if domain in ALLOWED_DOMAINS and entity.get('disabled_by') is None:
            entity_devices[entity_id] = dev
            entity_devices[dev] = dev
            by_device[dev].append({'domain': domain, 'entity_id': entity_id,
                                   'label': label[:90], 'state': safe_states.get(entity_id, 'Not available'),
                                   'metadata': metadata.get(entity_id, {}),
                                   'entity_category': (entity.get('entity_category')
                                                       or metadata.get(entity_id, {}).get('entity_category'))})
    socket_candidates = socket_child_candidates(
        {d['id']: d for d in devices if isinstance(d, dict) and isinstance(d.get('id'), str)},
        by_device)
    associations = automation_links(configurations, entity_devices)
    explanations = automation_explanations(configurations, entity_devices)
    flow_outlines = automation_flow_summaries(configurations, entity_devices)
    action_overlap = automation_action_overlap(configurations, entity_devices)
    # Raw registry keys remain internal; only one-way opaque lookup keys reach the browser.
    lookup = {d['id']: d for d in devices if isinstance(d, dict) and isinstance(d.get('id'), str)}
    visible = {}
    hidden = 0
    virtual_count = 0
    registry_review = []
    disabled_count = 0
    empty_count = 0
    name_counts = Counter((d.get('name_by_user') or d.get('name') or d.get('model') or 'Unnamed device') for d in lookup.values())
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
            all_entities = registry_entities.get(device_id, [])
            registered_total = len(all_entities)
            disabled_entities = sum(e.get('disabled_by') is not None for e in all_entities)
            private_entities = 0
            unsupported_entities = 0
            for e in all_entities:
                eid = e.get('entity_id', '')
                label = e.get('name') or e.get('original_name') or eid.split('.', 1)[-1].replace('_', ' ')
                if isinstance(eid, str) and isinstance(label, str):
                    if PRIVATE_NAME.search(eid + ' ' + label):
                        private_entities += 1
                    elif eid.split('.', 1)[0] not in ALLOWED_DOMAINS:
                        unsupported_entities += 1
            category, explanation = registry_classification(
                name, manufacturer, model, disabled_by, registered_total, len(domains))
            registry_review.append({
                'name': name[:90], 'manufacturer': manufacturer[:75],
                'model': model[:75], 'disabled_by': str(disabled_by)[:40] if disabled_by is not None else None,
                'visible_entities': len(domains), 'registered_entity_count': registered_total,
                'disabled_entity_count': disabled_entities,
                'privacy_excluded_count': private_entities,
                'unsupported_domain_count': unsupported_entities,
                'category': category, 'explanation': explanation,
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
                        'last_changed': e['metadata'].get('last_changed'),
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
        public_key = 'device:' + hashlib.sha256(device_id.encode('utf-8')).hexdigest()[:24]
        electrical = []
        outlet_candidates = {}
        # Only the owning device can report these measurements. For multi-outlet
        # strips, these cannot safely be attributed to any particular outlet.
        # Ignore configuration and diagnostic switches (e.g. EP25 LED).
        # They are not independently switched mains outlets.
        outlet_switches = [e for e in domains if e['domain'] == 'switch'
                           and e.get('entity_category') not in ('config', 'diagnostic')]
        switch_count = len(outlet_switches)
        electrical_note = ('Electrical readings belong to the single normal switch on this device.'
                           if switch_count == 1 else
                           'Electrical readings not attributed: ' + str(switch_count) +
                           ' normal switches share this registry device.'
                           if switch_count > 1 else
                           'No normal outlet switch identified on this registry device.')
        if switch_count > 1:
            outlet_candidates = outlet_meter_candidates(outlet_switches, domains)
            for switch in outlet_switches:
                sid = switch['entity_id']
                registry_match = socket_candidates.get((device_id, sid))
                if registry_match:
                    # Registry-linked socket match takes precedence over name
                    # matching of measurements on the parent strip.
                    outlet_candidates[sid] = registry_match
        if switch_count == 1:
            for entry in domains:
                if entry['domain'] != 'sensor':
                    continue
                props = entry.get('metadata', {})
                kind = props.get('device_class')
                unit = props.get('unit')
                if ((kind, unit) not in (('power', 'W'), ('power', 'kW'),
                                         ('current', 'A'), ('current', 'mA'),
                                         ('voltage', 'V'))):
                    continue
                value = entry['state']
                try:
                    measurement = float(value)
                    if not -1000000 < measurement < 1000000:
                        continue
                except (ValueError, TypeError):
                    continue
                electrical.append({'kind': kind, 'value': measurement,
                                   'unit': unit, 'last_updated': props.get('last_updated')})
                if len(electrical) >= 3:
                    break
        visible[device_id] = {
            'device_key': public_key,
            'electrical': electrical,
            'outlet_meter_candidates': outlet_candidates,
            'socket_meter_candidate_ids': [sid for sid in outlet_candidates if (device_id, sid) in socket_candidates],
            'electrical_note': electrical_note,
            'name': name[:90], 'manufacturer': manufacturer[:75], 'model': model[:75],
            'capabilities': guide, 'entity_count': len(domains), 'ideas': ideas,
            'summary': summarize_entities(domains),
            'diagnostics': device_diagnostics(domains),
            'power_dependency': power_dependency(name, safe_states, confirmed_dependencies, public_key, name_counts[name] == 1),
            'automation_links': dict(associations.get(device_id, {'trigger':0,'condition':0,'action':0})),
            'automation_explanations': explanations.get(device_id, {}),
            'automation_flows': flow_outlines.get(device_id, []),
            'action_overlap': {'configuration_count': action_overlap.get(device_id, 0),
                               'potential_overlap': action_overlap.get(device_id, 0) >= 2},
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
    observed = [x for x in result if not x['virtual']]
    def roles(item):
        refs = item['automation_links']
        return [role for role in ('trigger', 'condition', 'action') if refs.get(role, 0) > 0]
    for item in result:
        item['automation_insight'] = {
            'roles': roles(item),
            'review': ('Multiple roles observed' if len(roles(item)) >= 2
                       else 'Used as ' + roles(item)[0] if roles(item)
                       else 'No exact reference found'),
            'limits': 'Only exact structured references in accessible automation configurations are counted.',
        }
    referenced = [item for item in observed if roles(item)]
    intelligence = {
        'devices_examined': len(observed),
        'devices_with_exact_references': len(referenced),
        'devices_without_exact_references': len(observed) - len(referenced),
        'devices_used_in_triggers': sum('trigger' in roles(item) for item in observed),
        'devices_used_in_conditions': sum('condition' in roles(item) for item in observed),
        'devices_used_in_actions': sum('action' in roles(item) for item in observed),
        'devices_with_multiple_roles': sum(len(roles(item)) >= 2 for item in observed),
        'devices_with_action_overlap': sum(item['action_overlap']['potential_overlap'] for item in observed),
        'configurations_checked': len(configurations or []),
        'configurations_attempted': attempted,
        'coverage_is_partial': attempted != len(configurations or []),
        'scope_note': 'Exact structured references only. Templates, indirect scripts, dynamically addressed entities, and manufacturer-app automations are not resolved. A zero count does not establish that a device is unused.'
    }
    return {
        'version': '0.29.0', 'mode': 'read-only',
        'registered_devices': len(devices), 'registered_entities': len(entities),
        'displayed_devices': len(result), 'hidden_private_devices': hidden,
        'virtual_monitor_entries': virtual_count,
        'disabled_registrations': disabled_count,
        'empty_visible_registrations': empty_count,
        'registry_review': sorted(registry_review, key=lambda x: x['name'].casefold())[:250],
        'automations': {**automation_counts(states), 'configurations_checked': len(configurations or []), 'lookup_attempted': attempted},
        'devices': result[:500],
        'automation_intelligence': intelligence,
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

    def allowed_gateway(self):
        return self.client_address[0] == GATEWAY

    def request_route(self):
        # Home Assistant ingress prefixes the route; check suffixes at
        # slash boundaries, not arbitrary string endings.
        return self.path.split('?', 1)[0].rstrip('/')

    def do_GET(self):
        if not self.allowed_gateway():
            return self.reply(403, b'Forbidden', 'text/plain')
        route = self.request_route()
        if route.endswith('/api/automation-reference') and route.count('/api/') == 1:
            tokens = parse_qs(urlsplit(self.path).query, keep_blank_values=True).get('token', [])
            if len(tokens) != 1 or not re.fullmatch(r'[A-Za-z0-9_-]{16,64}', tokens[0]):
                return self.reply(400, b'{"error":"Invalid reference"}', 'application/json')
            if time.monotonic() - AUTOMATION_REFERENCES_AT > AUTOMATION_REFERENCE_TTL:
                return self.reply(404, b'{"error":"Reference expired; refresh devices"}', 'application/json')
            name = AUTOMATION_REFERENCES.get(tokens[0])
            if name is None:
                return self.reply(404, b'{"error":"Reference unavailable; refresh devices"}', 'application/json')
            return self.reply(200, json.dumps({'automation_name': name}).encode(), 'application/json')
        if route.endswith('/api/relationships') and route.count('/api/') == 1:
            return self.reply(200, json.dumps(load_power_dependencies()).encode(), 'application/json')
        if route.endswith('/api/devices') and route.count('/api/') == 1:
            try:
                if not SCAN_LOCK.acquire(blocking=False):
                    return self.reply(429, b'{"error":"A discovery scan is already running."}', 'application/json')
                try:
                    data = json.dumps(scan(*registry_request())).encode()
                finally:
                    SCAN_LOCK.release()
                return self.reply(200, data, 'application/json')
            except Exception as exc:
                # Exception messages can include device identifiers: log class only.
                LOG.warning('Registry scan unavailable (%s)', type(exc).__name__)
                return self.reply(503, b'{"error":"Registry scan unavailable; see app logs."}', 'application/json')
        for suffix, filename, mime in (('/app.js', 'app.js', 'text/javascript'),
                                        ('/style.css', 'style.css', 'text/css')):
            if route.endswith(suffix) and route.count(suffix) == 1:
                return self.reply(200, (BASE / filename).read_bytes(), mime)
        if route.endswith('/api') or '/api/' in route:
            return self.reply(404, b'Not found', 'text/plain')
        return self.reply(200, (BASE / 'index.html').read_bytes(), 'text/html; charset=utf-8')

    def do_POST(self):
        if not self.allowed_gateway():
            return self.reply(403, b'Forbidden', 'text/plain')
        route = self.request_route()
        if not route.endswith('/api/relationships') or route.count('/api/') != 1:
            return self.reply(405, b'Not allowed', 'text/plain')
        if (self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json'
                or self.headers.get('X-Home-Explorer') != 'relationship-update'):
            return self.reply(415, b'Unsupported request', 'text/plain')
        if self.headers.get('Transfer-Encoding'):
            return self.reply(400, b'Transfer encoding not supported', 'text/plain')
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

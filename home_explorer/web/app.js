"use strict";
const get = id => document.getElementById(id);
let devices = [];
const openRows = new Set();
function elem(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

/* Display-only interpretations; do not infer verified capabilities or commands. */
function readableState(raw, domain) {
  if (raw === null || raw === undefined || raw === '') return 'No reading';
  const value = String(raw).trim();
  if (value === 'unknown') return 'Unknown (Home Assistant has no current reading)';
  if (value === 'unavailable') return 'Unavailable (Home Assistant cannot currently report it)';
  if (value === 'Not available') return 'No current reading';
  if (value === 'power_off') return 'Powered off';
  if (value === 'idle') return 'Idle';
  if (value === 'paused') return 'Paused';
  if (value === 'playing') return 'Playing';
  if (value === 'standby') return 'Standby';
  if (value === 'heating') return 'Heating';
  if (value === 'cooling') return 'Cooling';
  if (value === 'cleaning') return 'Cleaning';
  if (value === 'docked') return 'Docked';
  if (value === 'on') {
    if (domain === 'binary_sensor') return 'Detected / active';
    return 'On';
  }
  if (value === 'off') {
    if (domain === 'binary_sensor') return 'Clear / inactive';
    return 'Off';
  }
  // Never interpret numeric values without units, or arbitrary vendor states.
  return value.replace(/_/g, ' ');
}
function capabilityNote(domain) {
  const descriptions = {
    light: 'A light entity may support on/off, brightness, or colour depending on integration support.',
    switch: 'A switch entity may expose on/off services; it may represent a setting rather than physical power.',
    select: 'A select entity may expose available options and selection services.',
    number: 'A number entity may expose a numeric setting with configured bounds.',
    fan: 'A fan entity may expose on/off and supported speed settings.',
    climate: 'A climate entity may expose modes, setpoints and HVAC services.',
    humidifier: 'A humidifier entity may expose humidity targets and on/off services.',
    cover: 'A cover entity may expose open/close or position controls.',
    media_player: 'A media player may expose playback or volume services.',
    vacuum: 'A vacuum entity may expose cleaning or return-to-base services.',
    lawn_mower: 'A lawn mower entity may expose mowing actions.',
    remote: 'A remote entity may expose a command service.',
    button: 'A button entity may expose a press service.',
    sensor: 'An observation only; no control service is implied.',
    binary_sensor: 'An observation only; on/off indicates a reported condition, not a control.'
  };
  return descriptions[domain] || 'Available commands for this entity have not been verified.';
}

function render() {
  const term = get('search').value.trim().toLocaleLowerCase();
  const kind = get('kind').value;
  const matches = devices.map((d, index) => ({d, index})).filter(({d}) =>
    (kind === 'all' || (kind === 'virtual' ? d.virtual : !d.virtual)) &&
    [d.name, d.manufacturer, d.model, d.related_to || '',
     ...d.capabilities.flatMap(c => [c.type, ...(c.members || []).flatMap(m => [m.name, m.entity_id])])].join(' ').toLocaleLowerCase().includes(term));
  const fragment = document.createDocumentFragment();
  for (const {d, index} of matches) {
    const row = elem('details', undefined, 'device-row');
    row.open = openRows.has(index);
    row.addEventListener('toggle', () => {
      if (row.open) openRows.add(index);
      else openRows.delete(index);
    });
    const summary = elem('summary', undefined, 'device-summary');
    const heading = elem('span', undefined, 'device-title');
    heading.append(elem('strong', d.name));
    const sub = elem('span', d.manufacturer + ' · ' + d.model, 'row-meta');
    heading.append(sub);
    summary.append(heading);
    const counts = elem('span', undefined, 'row-counts');
    if (d.observable_categories) counts.append(elem('span', d.observable_categories + ' info', 'access-info'));
    if (d.potential_control_categories) counts.append(elem('span', d.potential_control_categories + ' possible controls', 'access-possible'));
    summary.append(counts);
    summary.append(elem('span', undefined, 'chevron'));
    row.append(summary);
    const body = elem('div', undefined, 'device-body');
    body.append(elem('p', d.kind, 'kind'));
    if (Array.isArray(d.summary) && d.summary.length) {
      const glance = elem('div', undefined, 'at-a-glance');
      glance.append(elem('h4', 'At a glance'));
      for (const point of d.summary) {
        const line = elem('div', undefined, 'glance-line');
        line.append(elem('span', point.label));
        line.append(elem('strong', readableState(point.state, point.domain)));
        glance.append(line);
      }
      body.append(glance);
    }
    if (d.related_to) body.append(elem('p', 'Part of: ' + d.related_to, 'related'));
    body.append(elem('h4', 'What Home Assistant exposes (' + d.entity_count + ')'));
    const list = elem('div', undefined, 'guide');
    for (const cap of d.capabilities) {
      const section = elem('section', undefined, 'capability-group');
      section.append(elem('h4', cap.type + ' · ' + cap.entities + ' · ' + cap.access));
      const members = elem('div', undefined, 'entity-members');
      for (const member of (cap.members || [])) {
        const entry = elem('div', undefined, 'entity-member');
        const identity = elem('span', undefined, 'entity-identity');
        identity.append(elem('strong', member.name));
        identity.append(elem('span', readableState(member.state, member.domain || cap.domain), 'friendly-state'));
        entry.append(identity);
        const detail = elem('details', undefined, 'technical-details');
        detail.append(elem('summary', 'Technical details'));
        detail.append(elem('code', member.entity_id, 'entity-id'));
        detail.append(elem('p', 'Raw state: ' + String(member.state), 'raw-state'));
        if (Number.isInteger(member.supported_features))
          detail.append(elem('p', 'Reported supported-features bitmask: ' + member.supported_features + ' (not service-tested)', 'feature-flags'));
        if (Array.isArray(member.options) && member.options.length)
          detail.append(elem('p', 'Reported options: ' + member.options.join(', '), 'reported-options'));
        if (Array.isArray(cap.domain_services) && cap.domain_services.length)
          detail.append(elem('p', 'Domain-wide service catalogue: ' + cap.domain_services.join(', ') + '. These are not verified for this specific entity.', 'listed-services'));
        detail.append(elem('p', capabilityNote(member.domain || cap.domain), 'service-note'));
        detail.append(elem('p', 'No services have been invoked or tested. Actual control availability depends on the integration, entity and permissions.', 'service-warning'));
        entry.append(detail);
        members.append(entry);
      }
      section.append(members);
      list.append(section);
    }
    body.append(list);
    if (d.virtual) {
      body.append(elem('p', 'This is a Sense energy-monitor detection, not necessarily a separate controllable appliance.', 'hint'));
    } else if (d.ideas.length) {
      body.append(elem('h4', 'Ideas to explore'));
      for (const idea of d.ideas) {
        const item = elem('p', undefined, 'idea');
        item.append(elem('strong', idea.title + ': '));
        item.append(document.createTextNode(idea.description));
        body.append(item);
      }
    }
    row.append(body);
    fragment.append(row);
  }
  get('devices').replaceChildren(fragment);
  get('count').textContent = matches.length + ' shown';
  if (!matches.length) get('devices').append(elem('p', 'No matching entries in this view.', 'empty'));
}
get('search').addEventListener('input', render);
get('kind').addEventListener('change', render);
get('scan').addEventListener('click', async () => {
  get('scan').disabled = true;
  get('status').textContent = 'Reading device and entity registries locally…';
  try {
    const root = location.href.split('?')[0].replace(/\/?$/, '/');
    const response = await fetch(new URL('api/devices', root), {credentials:'same-origin',cache:'no-store'});
    if (!response.ok) throw new Error('Registry request failed (HTTP ' + response.status + ')');
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    if (!Array.isArray(data.devices)) throw new Error('Invalid response');
    devices = data.devices;
    if (data.automations && get('automation-status')) {
      const a = data.automations;
      get('automation-status').textContent = 'Existing automations: ' + a.total + ' detected · ' + a.enabled +
        ' enabled · ' + a.disabled + ' disabled · ' + a.other +
        ' other. Names, rules and device relationships were not examined.';
    }
    openRows.clear();
    get('registered').textContent = String(data.registered_devices);
    get('shown').textContent = String(data.displayed_devices);
    get('energy').textContent = String(data.virtual_monitor_entries);
    get('stats').hidden = false;
    get('toolbar').hidden = false;
    get('status').textContent = 'Discovery complete. ' + data.hidden_private_devices +
      ' sensitive-name entries filtered. No devices or automations were changed.';
    render();
  } catch (error) {get('status').textContent = 'Scan unavailable: ' + error.message;}
  finally {get('scan').disabled = false;}
});

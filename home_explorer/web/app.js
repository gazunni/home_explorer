"use strict";
const get = id => document.getElementById(id);
let devices = [];
let mappings = {};
let selectedSource = '';
let proposedTarget = '';

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
    if (d.power_dependency) {
      const supply = d.power_dependency;
      const panel = elem('div', undefined, 'at-a-glance');
      panel.append(elem('h4', 'Confirmed upstream power supply'));
      panel.append(elem('p', 'Outlet: ' + readableState(supply.supply_state, 'switch')));
      panel.append(elem('p', supply.interpretation));
      panel.append(elem('small', 'Relationship confirmed by homeowner. This does not verify an automation schedule or device health.'));
      body.append(panel);
    }
    if (d.diagnostics) {
      const diag = d.diagnostics;
      const summary = elem('p', 'Reading health: ' + diag.status + ' · ' +
        diag.available + ' reporting · ' + diag.unavailable + ' unavailable · ' +
        diag.unknown + ' unknown. This does not establish physical power or connectivity.', 'diagnostics');
      body.append(summary);
    }
    if (d.automation_links) {
      const refs = d.automation_links;
      const sum = refs.trigger + refs.condition + refs.action;
      if (sum) body.append(elem('p', 'Existing automation references: ' + refs.trigger +
        ' trigger · ' + refs.condition + ' condition · ' + refs.action +
        ' action. Counts reflect exact references in checked configurations only.', 'automation-links'));
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
    try {
      const mapResponse = await fetch(new URL('api/relationships', root), {credentials:'same-origin',cache:'no-store'});
      mappings = mapResponse.ok ? await mapResponse.json() : {};
    } catch (_) { mappings = {}; }
    renderMapper();
    if (data.automations && get('automation-status')) {
      const a = data.automations;
      const incomplete = a.configurations_checked < a.lookup_attempted;
      get('automation-status').textContent = 'Existing automations: ' + a.total + ' detected · ' + a.enabled +
        ' enabled · ' + a.disabled + ' disabled · ' + a.other +
        ' other · ' + a.configurations_checked + ' of ' + a.lookup_attempted +
        ' eligible configurations checked.' + (incomplete ? ' Partial analysis: some automation definitions were unavailable.' : '') +
        ' Relationships require exact structured references; automation names are hidden.';
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

/* Drag-and-drop and tap-to-connect use the same explicit confirmation flow. */
function renderMapper() {
  const root = get('mapper');
  const sources = get('map-source');
  if (!root || !sources) return;
  const sourceChoices = [];
  for (const d of devices) {
    if (d.virtual) continue;
    for (const cap of d.capabilities)
      if (cap.domain === 'switch') for (const m of cap.members)
        sourceChoices.push({id:m.entity_id, label:d.name + ' · ' + m.name});
  }
  sources.replaceChildren(new Option('Choose smart outlet…', ''));
  for (const src of sourceChoices) sources.append(new Option(src.label, src.id));
  sources.value = selectedSource;
  const list = elem('div', undefined, 'mapper-list');
  const names = devices.filter(d => !d.virtual).map(d => d.name);
  for (const d of devices.filter(d => !d.virtual)) {
    const item = elem('button', d.name, 'mapper-device');
    item.type = 'button';
    item.title = 'Select as target appliance';
    item.addEventListener('click', () => proposeRelationship(d.name));
    item.addEventListener('dragover', event => event.preventDefault());
    item.addEventListener('drop', event => {
      event.preventDefault();
      const dragged = event.dataTransfer.getData('text/plain');
      if (sourceChoices.some(s => s.id === dragged)) {
        selectedSource = dragged;
        sources.value = dragged;
        proposeRelationship(d.name);
      }
    });
    list.append(item);
  }
  const draggable = elem('div', undefined, 'mapper-sources');
  for (const src of sourceChoices) {
    const chip = elem('button', '↗ ' + src.label, 'mapper-source');
    chip.type = 'button';
    chip.draggable = true;
    chip.addEventListener('dragstart', event => {
      selectedSource = src.id;
      event.dataTransfer.setData('text/plain', src.id);
    });
    chip.addEventListener('click', () => {
      selectedSource = src.id;
      sources.value = src.id;
      get('map-status').textContent = 'Tap a target appliance below, or drag this outlet onto it.';
    });
    draggable.append(chip);
  }
  root.replaceChildren(draggable, list);
  const existing = get('map-existing');
  existing.replaceChildren();
  for (const [target, source] of Object.entries(mappings)) {
    const line = elem('div', undefined, 'mapped-pair');
    line.append(elem('span', target + ' ← ' + source));
    const remove = elem('button', 'Remove');
    remove.type = 'button';
    remove.addEventListener('click', () => {
      const next = {...mappings};
      delete next[target];
      persistMappings(next);
    });
    line.append(remove);
    existing.append(line);
  }
}
function proposeRelationship(target) {
  if (!selectedSource) {
    get('map-status').textContent = 'Choose a source outlet first.';
    return;
  }
  if (devices.filter(d => d.name === target).length !== 1) {
    get('map-status').textContent = 'Target name is ambiguous; cannot map safely.';
    return;
  }
  const sourceDevice = devices.find(d => d.capabilities.some(c =>
    c.members.some(m => m.entity_id === selectedSource)));
  if (sourceDevice && sourceDevice.name === target) {
    get('map-status').textContent = 'Choose a different appliance from the source outlet device.';
    return;
  }
  proposedTarget = target;
  get('map-target').textContent = target;
  get('map-proposal').hidden = false;
  get('map-status').textContent = 'Confirm the actual electrical wiring before saving.';
}
async function persistMappings(next) {
  const root = location.href.split('?')[0].replace(/\/?$/, '/');
  try {
    const response = await fetch(new URL('api/relationships', root), {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json', 'X-Home-Explorer':'relationship-update'},
      body:JSON.stringify(next)
    });
    if (!response.ok) throw new Error('Save failed (HTTP ' + response.status + ')');
    mappings = next;
    proposedTarget = '';
    selectedSource = '';
    get('map-proposal').hidden = true;
    get('map-status').textContent = 'Saved locally. Scan again to refresh diagnostics.';
    renderMapper();
  } catch (error) { get('map-status').textContent = error.message; }
}
get('map-source').addEventListener('change', value => {
  selectedSource = value.target.value;
  get('map-status').textContent = selectedSource ?
    'Tap the appliance below, or drag an outlet onto it.' : 'Choose a source outlet.';
});
get('map-confirm').addEventListener('click', () => {
  if (selectedSource && proposedTarget)
    persistMappings({...mappings, [proposedTarget]:selectedSource});
});
get('map-cancel').addEventListener('click', () => {
  proposedTarget = '';
  get('map-proposal').hidden = true;
});

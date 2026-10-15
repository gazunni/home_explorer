"use strict";
const get = id => document.getElementById(id);
let devices = [];
let mappings = {};
let selectedSource = '';
let proposedTarget = '';

const openRows = new Set();
const alpha = (a,b) => a.localeCompare(b, undefined, {numeric:true,sensitivity:'base'});
let scanInProgress = false;
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

/* Health classifications describe HA readings, not physical device faults. */
function deviceHealth(d) {
  const diag = d.diagnostics;
  if (!diag || !Number.isFinite(diag.available) || !Number.isFinite(diag.unavailable) || !Number.isFinite(diag.unknown))
    return {label:'Not assessed',kind:'neutral',detail:'No reliable entity-reading summary is available.'};
  const total = diag.available + diag.unavailable + diag.unknown;
  if (!total) return {label:'No readings',kind:'neutral',detail:'No current entity readings are available for assessment.'};
  const power = d.power_dependency && d.power_dependency.supply_state;
  if (power === 'off') return {label:'Upstream off',kind:'power',detail:'The confirmed power source reports off. Unavailable readings may be expected; this does not establish a device fault.'};
  if (diag.unavailable > 0 && power === 'on') return {label:'Check readings',kind:'attention',detail:'The confirmed power source reports on, but ' + diag.unavailable + ' entity readings are unavailable. Investigate integration or connectivity before assuming a device fault.'};
  if (diag.unavailable > 0) return {label:'Check readings',kind:'attention',detail:diag.unavailable + ' entity readings are unavailable. The cause is unknown; this is not proof of a connectivity or hardware fault.'};
  if (diag.unknown > 0) return {label:'Unknown readings',kind:'neutral',detail:diag.unknown + ' readings are unknown. Home Assistant has not reported their current values.'};
  return {label:'Reporting',kind:'good',detail:'All ' + diag.available + ' assessed entity readings are reporting. This does not confirm physical operation or device health.'};
}

function render() {
  const term = get('search').value.trim().toLocaleLowerCase();
  const kind = get('kind').value;
  const matches = devices.map((d, index) => ({d, index})).filter(({d}) =>
    (kind === 'all' || (kind === 'virtual' ? d.virtual : !d.virtual)) &&
    [d.name, d.manufacturer, d.model, d.related_to || '',
     ...d.capabilities.flatMap(c => [c.type, ...(c.members || []).flatMap(m => [m.name, m.entity_id])])].join(' ').toLocaleLowerCase().includes(term));
  matches.sort((a,b) => alpha(a.d.name,b.d.name));
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
    if (!d.virtual) { const health = deviceHealth(d); counts.append(elem('span', health.label, 'health-pill health-' + health.kind)); }
    if (d.observable_categories) counts.append(elem('span', d.observable_categories + ' info', 'access-info'));
    if (d.potential_control_categories) counts.append(elem('span', d.potential_control_categories + ' possible controls', 'access-possible'));
    if (d.power_dependency) {
      const power = d.power_dependency.supply_state;
      const label = power === 'off' ? 'Upstream off' : power === 'on' ? 'Upstream on' : 'Power unknown';
      counts.append(elem('span', label, 'access-info'));
    }
    summary.append(counts);
    summary.append(elem('span', undefined, 'chevron'));
    row.append(summary);
    const body = elem('div', undefined, 'device-body');
    body.append(elem('p', d.kind, 'kind'));
    if (!d.virtual) {
      const health = deviceHealth(d);
      const panel = elem('section', undefined, 'health-panel');
      panel.append(elem('strong', 'Device readings · ' + health.label));
      panel.append(elem('p', health.detail));
      if (d.diagnostics) panel.append(elem('small', d.diagnostics.available + ' reporting · ' + d.diagnostics.unavailable + ' unavailable · ' + d.diagnostics.unknown + ' unknown'));
      body.append(panel);
    }
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
      if (d.diagnostics) {
        const readings = d.diagnostics;
        let assessment = 'Power source state and device readings are separate observations.';
        if (supply.supply_state === 'off' && readings.unavailable)
          assessment = 'Upstream power is off and some appliance readings are unavailable. This is consistent with lost power, but is not proof of the cause.';
        else if (supply.supply_state === 'on' && readings.available)
          assessment = 'Upstream power is on and the appliance reports readings. This does not confirm that the appliance is actively operating.';
        else if (supply.supply_state === 'on' && readings.unavailable)
          assessment = 'Upstream power is on but some appliance readings are unavailable. Check connectivity and integration status before diagnosing a fault.';
        panel.append(elem('p', assessment, 'diagnostics'));
      }
      panel.append(elem('small', 'Relationship confirmed by homeowner. This does not verify an automation schedule or device health.'));
      body.append(panel);
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
    const compactOff = d.power_dependency && d.power_dependency.supply_state === 'off';
    let hiddenUnavailable = 0;
    const hiddenEntries = elem('div', undefined, 'entity-members');
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
        if (compactOff && member.state === 'unavailable') {
          hiddenEntries.append(entry);
          hiddenUnavailable++;
        } else {
          members.append(entry);
        }
      }
      if (members.childElementCount) {
        section.append(members);
        list.append(section);
      }
    }
    if (hiddenUnavailable) {
      const folded = elem('details', undefined, 'technical-details');
      folded.append(elem('summary', hiddenUnavailable + ' unavailable readings — expand for individual entities and technical details'));
      folded.append(hiddenEntries);
      list.append(folded);
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
async function refreshDevices() {
  if (scanInProgress) return;
  scanInProgress = true;
  get('scan').disabled = true;
  get('scan-notice').hidden = true;
  get('scan-state').textContent = 'Scanning…';
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
    const automation = data.automations || {};
    get('automation-total').textContent = automation.total ?? '—';
    get('automation-enabled').textContent = automation.enabled ?? '—';
    get('automation-disabled').textContent = automation.disabled ?? '—';
    get('automation-checked').textContent = automation.lookup_attempted != null ? String(automation.configurations_checked ?? 0) + '/' + String(automation.lookup_attempted) : '—';
    get('privacy-count').textContent = String(data.hidden_private_devices ?? 0);
    get('scan-state').textContent = 'Scan complete';
    if (data.automations && automation.configurations_checked < automation.lookup_attempted) {
      const a = data.automations;
      const incomplete = a.configurations_checked < a.lookup_attempted;
      get('scan-notice').hidden = false;
      get('scan-notice').textContent = 'Existing automations: ' + a.total + ' detected · ' + a.enabled +
        ' enabled · ' + a.disabled + ' disabled · ' + a.other +
        ' other · ' + a.configurations_checked + ' of ' + a.lookup_attempted +
        ' eligible configurations checked.' + (incomplete ? ' Partial analysis: some automation definitions were unavailable.' : '') +
        ' Relationships require exact structured references; automation names are hidden.';
    }
    openRows.clear();
    get('registered').textContent = String(data.registered_devices);
    get('shown').textContent = String(data.displayed_devices);
    get('energy').textContent = String(data.virtual_monitor_entries);
    get('disabled-reg').textContent = String(data.disabled_registrations ?? 0);
    get('empty-reg').textContent = String(data.empty_visible_registrations ?? 0);
    registryReview = Array.isArray(data.registry_review) ? data.registry_review : [];
    renderRegistryReview();
    get('stats').hidden = false;
    get('toolbar').hidden = false;

    render();
  } catch (error) {get('scan-notice').textContent = 'Scan unavailable: ' + error.message; get('scan-state').textContent = 'Scan failed'; get('scan-notice').hidden = false;}
  finally {get('scan').disabled = false; scanInProgress = false;}
}
let registryReview = [];
function renderRegistryReview() {
  const filter = get('review-filter').value;
  const visible = registryReview.filter(item => {
    if (filter === 'all') return true;
    if (filter === 'disabled') return item.disabled_by != null;
    if (filter === 'virtual') return item.category === 'Possible Tuya virtual scene';
    if (filter === 'infrastructure') return item.category === 'Possible infrastructure';
    if (filter === 'no-entities') return item.registered_entity_count === 0;
    if (filter === 'excluded') return item.category === 'Entities excluded from display';
    return true;
  });
  get('review-count').textContent = registryReview.length + ' to review';
  const list = get('review-items');
  list.replaceChildren();
  if (!visible.length) list.append(elem('p', 'No entries match this filter.', 'hint'));
  for (const item of visible) {
    const line = elem('div', undefined, 'review-item');
    line.append(elem('strong', item.name));
    line.append(elem('span', item.category || 'Review', 'review-category'));
    line.append(elem('span', item.explanation || 'Inspect in Home Assistant.', 'row-meta'));
    const details = [String(item.registered_entity_count ?? 0) + ' registered entities',
      String(item.visible_entities ?? 0) + ' eligible visible',
      String(item.disabled_entity_count ?? 0) + ' entity-disabled',
      String(item.unsupported_domain_count ?? 0) + ' unsupported domains'];
    if (item.privacy_excluded_count) details.push('Privacy exclusions present');
    line.append(elem('span', details.join(' · '), 'row-meta'));
    list.append(line);
  }
}
get('review-filter').addEventListener('change', renderRegistryReview);
get('scan').addEventListener('click', refreshDevices);
refreshDevices();


/* The mapping is saved by exact switch entity ID and opaque device key, not labels. */
function shortOutlet(source) {
  const d = source.device;
  const original = source.memberName || d.name;
  const stripped = original.startsWith(d.name + ' ') ? original.slice(d.name.length + 1) : original;
  const name = stripped || d.name;
  return name + ' (' + d.manufacturer + (d.model && !d.model.startsWith('Unknown') ? ' ' + d.model : '') + ')';
}
function sourceSnapshot(source) {
  const owner = source.device;
  const matches = owner.capabilities.flatMap(c => c.members || []).filter(m => m.entity_id === source.id);
  const current = matches.length ? matches[0].state : 'Not available';
  const sw = current === 'on' ? 'On (reported)' : current === 'off' ? 'Off (reported)' : 'Unknown';
  const observations = ['Switch: ' + sw];
  for (const reading of owner.electrical || []) {
    const time = Date.parse(reading.last_updated || '');
    const age = Number.isFinite(time) ? Math.max(0, Math.round((Date.now() - time) / 60000)) + ' min ago' : 'update time unknown';
    observations.push(reading.kind + ': ' + reading.value + ' ' + reading.unit + ' (reported ' + age + ')');
  }
  if ((owner.electrical || []).length)
    observations.push('Electrical readings are observations, not proof of appliance operation. They may lag the switch state.');
  else
    observations.push((owner.electrical_note || 'Electrical measurements were not attributed.') + ' No supported current measurement is available for this source.');
  return observations;
}
/* Compact touch-first relationship editor. No nested scrolling or drag requirement. */
function mapperChoices() {
  const sources = [];
  for (const d of devices) {
    if (d.virtual) continue;
    for (const cap of d.capabilities) {
      if (cap.domain !== 'switch') continue;
      for (const m of cap.members || []) {
        if (m.entity_id.startsWith('switch.'))
          sources.push({id:m.entity_id, label:(m.name && m.name !== d.name ? m.name + ' · ' + d.name : d.name) + ' · ' + m.entity_id + ' · ' + d.manufacturer, memberName:m.name, owner:d.device_key, device:d});
      }
    }
  }
  return sources.sort((a,b) => alpha(a.label,b.label));
}
function renderMapper() {
  const sourceSelect = get('map-source');
  const targetSelect = get('map-target-select');
  const query = get('map-search').value.trim().toLocaleLowerCase();
  const sourceQuery = get('map-source-search').value.trim().toLocaleLowerCase();
  const oldTarget = targetSelect.value;
  const sources = mapperChoices();
  sourceSelect.replaceChildren(new Option('Choose a smart outlet…', ''));
  for (const source of sources.filter(x => (x.label + ' ' + x.id).toLocaleLowerCase().includes(sourceQuery)))
    sourceSelect.append(new Option(source.label, source.id));
  sourceSelect.value = [...sourceSelect.options].some(o => o.value === selectedSource) ? selectedSource : '';
  targetSelect.replaceChildren(new Option('Choose an appliance…', ''));
  const names = devices.filter(d => !d.virtual &&
    [d.name,d.manufacturer,d.model,...d.capabilities.flatMap(c => (c.members || []).map(m => m.name))]
      .join(' ').toLocaleLowerCase().includes(query))
    .sort((a,b) => alpha(a.name,b.name));
  for (const d of names) {
    const duplicate = devices.some(x => x !== d && x.name === d.name);
    const label = d.name + ' · ' + [d.manufacturer,d.model].filter(Boolean).join(' · ') +
      (duplicate ? ' · distinct registration' : '');
    targetSelect.append(new Option(label, d.device_key));
  }
  if ([...targetSelect.options].some(o => o.value === oldTarget))
    targetSelect.value = oldTarget;
  updateMapperPreview();
  const existing = get('map-existing');
  existing.replaceChildren();
  const entries = Object.entries(mappings);
  get('map-count').textContent = entries.length + ' saved';
  for (const [target, source] of entries) {
    const line = elem('div', undefined, 'mapped-pair');
    const displaySource = sources.find(x => x.id === source);
    const targetDevice = devices.find(d => d.device_key === target) || devices.find(d => d.name === target);
    const left = elem('div', undefined, 'mapped-description');
    const sourceText = displaySource ? shortOutlet(displaySource) : 'Unresolved outlet';
    const targetText = targetDevice ? targetDevice.name + ' (' + targetDevice.manufacturer + ')' : 'Previously saved appliance';
    left.append(elem('strong', sourceText + ' → ' + targetText));
    const detail = document.createElement('details');
    detail.className = 'mapped-technical';
    detail.append(elem('summary', 'Electrical observations & IDs'));
    if (displaySource) {
      for (const observation of sourceSnapshot(displaySource))
        detail.append(elem('p', observation));
    }
    detail.append(elem('p', 'Switch entity: ' + source));
    if (targetDevice) detail.append(elem('p', 'Appliance: ' + targetDevice.name + ' · ' + targetDevice.model));
    left.append(detail);
    line.append(left);
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
  get('map-empty').hidden = entries.length > 0;
}
async function persistMappings(next) {
  const root = location.href.split('?')[0].replace(/\/?$/, '/');
  try {
    const response = await fetch(new URL('api/relationships', root), {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-Home-Explorer':'relationship-update'},
      body:JSON.stringify(next)
    });
    if (!response.ok) throw new Error('Save failed (HTTP ' + response.status + ')');
    mappings = next;
    get('map-proposal').hidden = true;
    get('map-status').textContent = 'Relationship saved locally. Rescan to update device diagnostics.';
    renderMapper();
  } catch (error) {
    get('map-status').textContent = error.message;
  }
}
function updateMapperPreview() {
  const source = mapperChoices().find(x => x.id === get('map-source').value);
  const target = devices.find(x => !x.virtual && x.device_key === get('map-target-select').value);
  const sourceDevice = source && source.device;
  const sourceMeta = sourceDevice ? [sourceDevice.manufacturer,sourceDevice.model].filter(Boolean).join(' · ') : '';
  const targetMeta = target ? [target.manufacturer,target.model].filter(Boolean).join(' · ') : '';
  get('map-source-info').textContent = source ? source.label + (sourceMeta ? ' — ' + sourceMeta : '') : 'Select a power source to see its details.';
  get('map-target-info').textContent = target ? target.name + (targetMeta ? ' — ' + targetMeta : '') : 'Select an appliance to see its details.';
}
get('map-source').addEventListener('change', event => {
  selectedSource = event.target.value;
  get('map-proposal').hidden = true;
  updateMapperPreview();
});
get('map-target-select').addEventListener('change', () => {
  get('map-proposal').hidden = true;
  updateMapperPreview();
});
get('map-search').addEventListener('input', renderMapper);
get('map-source-search').addEventListener('input', renderMapper);
get('map-add').addEventListener('click', () => {
  const target = get('map-target-select').value;
  const source = get('map-source').value;
  const choices = mapperChoices();
  if (!source || !target) {
    get('map-status').textContent = 'Choose both a smart outlet and an appliance.';
    return;
  }
  const owner = choices.find(x => x.id === source);
  if (!owner || owner.owner === target) {
    get('map-status').textContent = 'Select a valid outlet and a different target appliance.';
    return;
  }
  proposedTarget = target;
  const targetDevice = devices.find(d => d.device_key === target);
   get('map-target').textContent = targetDevice ? targetDevice.name + ' · ' + targetDevice.manufacturer : target;
  get('map-source-label').textContent = owner.label;
  get('map-proposal').hidden = false;
});
get('map-confirm').addEventListener('click', () => {
  if (proposedTarget && selectedSource &&
      get('map-target-select').value === proposedTarget &&
      get('map-source').value === selectedSource)
    persistMappings({...mappings,[proposedTarget]:selectedSource});
});
get('map-cancel').addEventListener('click', () => {
  proposedTarget = '';
  get('map-proposal').hidden = true;
});

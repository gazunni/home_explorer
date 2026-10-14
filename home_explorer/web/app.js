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
function render() {
  const term = get('search').value.trim().toLocaleLowerCase();
  const kind = get('kind').value;
  const matches = devices.map((d, index) => ({d, index})).filter(({d}) =>
    (kind === 'all' || (kind === 'virtual' ? d.virtual : !d.virtual)) &&
    [d.name, d.manufacturer, d.model, d.related_to || '',
     ...d.capabilities.map(c => c.type)].join(' ').toLocaleLowerCase().includes(term));
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
    if (d.related_to) body.append(elem('p', 'Part of: ' + d.related_to, 'related'));
    body.append(elem('h4', 'What Home Assistant exposes (' + d.entity_count + ')'));
    const list = elem('div', undefined, 'guide');
    for (const cap of d.capabilities) {
      const item = elem('div', undefined, 'feature');
      item.append(elem('strong', cap.type + ' · ' + cap.entities + ' · ' + cap.access));
      item.append(elem('p', cap.explanation));
      item.append(elem('p', cap.verification, 'verification'));
      list.append(item);
    }
    body.append(list);
    body.append(elem('p', 'Manufacturer-app-only features: unknown. Registry data cannot establish manufacturer-only functionality.', 'unknown'));
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

"use strict";
const get = id => document.getElementById(id);
let devices = [];
function elem(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function render() {
  const term = get('search').value.trim().toLocaleLowerCase();
  const kind = get('kind').value;
  const matches = devices.filter(d =>
    (kind === 'all' || (kind === 'virtual' ? d.virtual : !d.virtual)) &&
    [d.name, d.manufacturer, d.model, d.related_to || '',
     ...d.capabilities.map(c => c.type)].join(' ').toLocaleLowerCase().includes(term));
  const fragment = document.createDocumentFragment();
  for (const d of matches) {
    const card = elem('article', undefined, 'device');
    const heading = elem('div', undefined, 'heading');
    heading.append(elem('h3', d.name));
    heading.append(elem('span', d.kind, 'kind'));
    card.append(heading);
    card.append(elem('p', d.manufacturer + ' · ' + d.model, 'meta'));
    const access = elem('div', undefined, 'access');
    if (d.observable_categories) access.append(elem('span', d.observable_categories + ' information group(s)', 'access-info'));
    if (d.potential_control_categories) access.append(elem('span', d.potential_control_categories + ' possible control group(s)', 'access-possible'));
    card.append(access);
    if (d.related_to) card.append(elem('p', 'Part of: ' + d.related_to, 'related'));
    const detail = elem('details');
    const summary = elem('summary', 'What Home Assistant exposes (' + d.entity_count + ')');
    detail.append(summary);
    const list = elem('div', undefined, 'guide');
    for (const cap of d.capabilities) {
      const item = elem('div', undefined, 'feature');
      item.append(elem('strong', cap.type + ' · ' + cap.entities + ' · ' + cap.access));
      item.append(elem('p', cap.explanation));
      item.append(elem('p', cap.verification, 'verification'));
      list.append(item);
    }
    detail.append(list);
    detail.append(elem('p', 'Manufacturer-app-only features: unknown. This scan does not query the manufacturer or enumerate live service commands.', 'unknown'));
    card.append(detail);
    if (d.virtual) {
      card.append(elem('p', 'This is a detection made by your Sense energy monitor, not necessarily another controllable appliance.', 'hint'));
    } else if (d.ideas.length) {
      card.append(elem('h4', 'Ideas to explore'));
      for (const idea of d.ideas) {
        const item = elem('p', undefined, 'idea');
        item.append(elem('strong', idea.title + ': '));
        item.append(document.createTextNode(idea.description));
        card.append(item);
      }
    }
    fragment.append(card);
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

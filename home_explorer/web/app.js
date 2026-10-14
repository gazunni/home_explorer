'use strict';
const get = id => document.getElementById(id);
let devices = [];
function elem(tag, value, className) {
  const e = document.createElement(tag);
  if (value !== undefined) e.textContent = value;
  if (className) e.className = className;
  return e;
}
function render() {
  const term = get('search').value.trim().toLowerCase();
  const matched = devices.filter(d =>
    (d.name + ' ' + d.manufacturer + ' ' + d.model).toLowerCase().includes(term));
  get('devices').replaceChildren();
  get('count').textContent = matched.length + ' devices shown';
  for (const d of matched) {
    const card = elem('article', undefined, 'device');
    card.append(elem('h3', d.name));
    card.append(elem('p', d.manufacturer + ' · ' + d.model, 'meta'));
    const caps = elem('div', undefined, 'caps');
    for (const c of d.capabilities) {
      caps.append(elem('span', c.type + ' (' + c.entities + ')', 'cap'));
    }
    card.append(caps);
    card.append(elem('p', 'Exposed entity categories; detailed actions require verification.', 'fine'));
    get('devices').append(card);
  }
}
get('search').addEventListener('input', render);
get('scan').addEventListener('click', async () => {
  get('scan').disabled = true;
  get('status').textContent = 'Reading registries through the local Home Assistant connection…';
  try {
    const root = location.href.split('?')[0].replace(/\/?$/, '/');
    const response = await fetch(new URL('api/devices', root), {
      credentials: 'same-origin', cache: 'no-store'
    });
    if (!response.ok) throw new Error('Registry request failed (HTTP ' + response.status + ')');
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    devices = data.devices;
    get('registered').textContent = String(data.registered_devices);
    get('shown').textContent = String(data.displayed_devices);
    get('stats').hidden = false;
    get('search').disabled = false;
    get('status').textContent = 'Discovery completed. ' + data.hidden_private_devices +
      ' private-name devices filtered. No devices or automations were changed.';
    render();
  } catch (error) {
    get('status').textContent = 'Scan not available: ' + error.message;
  } finally {
    get('scan').disabled = false;
  }
});
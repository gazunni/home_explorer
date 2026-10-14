'use strict';
const $ = id => document.getElementById(id);
function el(tag, content, className) {
  const node = document.createElement(tag);
  if (content !== undefined) node.textContent = content;
  if (className) node.className = className;
  return node;
}
$('scan').addEventListener('click', async () => {
  $('scan').disabled = true;
  $('status').textContent = 'Reading Home Assistant entity categories locally…';
  $('result').replaceChildren();
  $('stats').hidden = true;
  try {
    const base = location.href.split('?')[0].replace(/\/?$/, '/');
    const response = await fetch(new URL('api/inventory', base), {
      credentials: 'same-origin', cache: 'no-store'
    });
    if (!response.ok) throw new Error('Inventory unavailable (HTTP ' + response.status + ')');
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    $('entities').textContent = String(data.total_visible_entities);
    $('groups').textContent = String(data.groups.length);
    $('stats').hidden = false;
    for (const group of data.groups) {
      const card = el('article', undefined, 'card');
      card.append(el('h3', group.domain), el('div', group.count + ' entities', 'count'));
      card.append(el('p', 'Available entity category; device-level capabilities need verification.'));
      $('result').append(card);
    }
    $('status').textContent = 'Inventory loaded. No devices or automations were changed.';
  } catch (err) {
    $('status').textContent = 'Scan failed: ' + err.message;
  } finally {
    $('scan').disabled = false;
  }
});

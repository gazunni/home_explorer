// Synthetic UI contract test; no homeowner data or HA access.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('home_explorer/web/app.js', 'utf8');
function take(start, end) {
  const a = src.indexOf(start), b = src.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a);
  return src.slice(a, b);
}
const fn = take('function shortOutlet(', 'function readingsForSource(') +
  '\n' + take('function renderDependencies()', 'function renderMapper(');
const makeNode = (tag, text) => ({
  tag, textContent: text || '', children: [],
  append(child) { this.children.push(child); },
  replaceChildren() { this.children = []; }
});
const byId = { 'dependency-items': makeNode('div'), 'dependency-count': makeNode('span') };
const ctx = {
  devices: [
    { device_key:'parent', name:'Generic Strip', manufacturer:'TP-Link', model:'HS300',
      capabilities:[], automation_insight:{roles:['action']}, outlet_meter_candidates:{} },
    { device_key:'unique', name:'Washer', manufacturer:'Example', automation_insight:{roles:['trigger']},
      power_dependency:{supply_state:'on'}, capabilities:[] },
    { device_key:'a1', name:'Sony TV', manufacturer:'Example', capabilities:[] },
    { device_key:'a2', name:'Sony TV', manufacturer:'Example', capabilities:[] }
  ],
  mappings:{ unique:'switch.roku', 'Sony TV':'switch.sony' },
  get: id => byId[id],
  elem: (tag,text) => makeNode(tag,text),
  mapperChoices: () => [
    {id:'switch.roku', memberName:'Generic Strip Roku', device:ctx.devices[0]},
    {id:'switch.sony', memberName:'Generic Strip Sony', device:ctx.devices[0]}
  ]
};
vm.createContext(ctx);
vm.runInContext(fn + '\nrenderDependencies();', ctx);
assert.equal(byId['dependency-count'].textContent, '2 confirmed links');
const entries = byId['dependency-items'].children;
assert.match(entries[0].children[0].textContent,/Roku.*Washer/);
assert.match(entries[1].children[0].textContent,/Sony.*Sony TV/);
assert.ok(entries[1].children.some(n => /Several registered devices share/.test(n.textContent)));
assert.ok(!entries[1].children.some(n => /Appliance has exact automation references/.test(n.textContent)));
assert.ok(!entries[1].children.some(n => /Outlet reported on/.test(n.textContent)));
console.log('Dependency labeling regression tests passed');

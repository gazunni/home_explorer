// Synthetic opportunity intelligence regression tests (no homeowner data).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('home_explorer/web/app.js','utf8');
const a = src.indexOf('function opportunityFindings(');
const b = src.indexOf('function renderOpportunities()',a);
assert.ok(a >= 0 && b > a);
const ctx = {automationIntelligence:{coverage_is_partial:false}};
vm.createContext(ctx);
vm.runInContext(src.slice(a,b),ctx);
const items = [
 {device_key:'one',name:'TV',virtual:false, action_overlap:{potential_overlap:true},power_dependency:{supply_state:'Not available'}},
 {device_key:'two',name:'TV',virtual:false},
 {device_key:'out',name:'Outlet',virtual:false}
];
let findings = ctx.opportunityFindings(items,{'TV':'switch.plug','one':'switch.other'});
assert.ok(findings.some(f => f.type === 'Ambiguous saved relationship'));
assert.ok(findings.some(f => f.type === 'Automation target review'));
assert.ok(findings.some(f => f.label.includes('TV — confirm intended registration')));
assert.ok(findings.some(f => f.type === 'Power evidence review'));
assert.ok(findings.every(f => f.next && f.evidence && f.label));
assert.ok(!JSON.stringify(findings).toLowerCase().includes('delete'));
ctx.automationIntelligence.coverage_is_partial = true;
findings = ctx.opportunityFindings([], {});
assert.equal(findings.length,1);
assert.equal(findings[0].type,'Coverage review');
ctx.automationIntelligence.coverage_is_partial = false;
assert.equal(ctx.opportunityFindings([],{}).length,0);
console.log('Opportunity Intelligence regression tests passed');

// v0.21.0 sanitized modernization evidence regression tests.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const src = fs.readFileSync('home_explorer/web/app.js','utf8');
const start = src.indexOf('function modernizationCandidates(');
const end = src.indexOf('function renderModernizationReview()',start);
assert.ok(start >= 0 && end > start);
const ctx = {alpha:(a,b)=>a.localeCompare(b)};
vm.createContext(ctx);
vm.runInContext(src.slice(start,end),ctx);
const items = [
 {name:'Ceiling fan', action_overlap:{potential_overlap:true,configuration_count:3},automation_flows:[{branching:true,needs_review:true}]},
 {name:'Idle light',action_overlap:{potential_overlap:false,configuration_count:1}},
 {name:'Hidden virtual',virtual:true,action_overlap:{potential_overlap:true,configuration_count:12}},
 {name:'Ecobee', action_overlap:{potential_overlap:true,configuration_count:2},automation_flows:[]}
];
const out=ctx.modernizationCandidates(items,true);
assert.equal(out.total,2);
assert.equal(out.cases.length,2);
assert.equal(out.cases[0].name,'Ceiling fan');
assert.equal(out.cases[0].branching,1);
assert.equal(out.cases[0].limited,true);
assert.equal(out.coveragePartial,true);
assert.ok(out.cases.every(c => c.check.includes('Home Assistant')));
assert.ok(!JSON.stringify(out).includes('80°F'));
assert.equal(ctx.modernizationCandidates([],false).total,0);
const app=fs.readFileSync('home_explorer/web/app.js','utf8');
const html=fs.readFileSync('home_explorer/web/index.html','utf8');
const pStart=app.indexOf('function modernizationPageSlice(');
const pEnd=app.indexOf('function renderModernizationReview()',pStart);
assert.ok(pStart>=0 && pEnd>pStart);
vm.runInContext(app.slice(pStart,pEnd),ctx);
const twenty=Array.from({length:20},(_,i)=>i);
const page=ctx.modernizationPageSlice(twenty,0);
assert.equal(page.items.length,5); assert.equal(page.pages,4);
assert.equal(ctx.modernizationPageSlice(twenty,3).items[0],15);
assert.equal(ctx.modernizationPageSlice(twenty,99).index,3);
assert.equal(ctx.modernizationPageSlice(twenty,-1).index,0);
assert.equal(ctx.modernizationPageSlice([],0).items.length,0);
assert.ok(html.includes('id="modernization-prev"') && html.includes('id="modernization-next"'));
console.log('Modernization Review regression tests passed');

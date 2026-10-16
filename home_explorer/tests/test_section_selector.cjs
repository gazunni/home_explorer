// Static DOM wiring regression: all eight existing panel IDs remain in place.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const html=fs.readFileSync('home_explorer/web/index.html','utf8');
const js=fs.readFileSync('home_explorer/web/app.js','utf8');
const ids=['equipment-review','automation-review','overlap-review','opportunity-review','modernization-review','registry-review','dependency-review','map-editor'];
assert.equal((html.match(/<select id="section-select"/g)||[]).length,1);
for(const id of ids){
 assert.ok(html.includes('value="'+id+'"'),'missing selector choice '+id);
 assert.ok(html.includes('id="'+id+'"'),'missing original panel '+id);
 assert.ok(js.includes("'"+id+"'"),'missing navigator binding '+id);
}
assert.ok(html.includes('id="toolbar"'));
assert.ok(html.includes('id="devices"'));
assert.ok(js.includes("showExplorerSection('equipment-review')"));
assert.ok(js.includes("section.hidden = key !== chosen"));
assert.ok(js.includes("detail.open = key === chosen"));
const getDeclaration=js.indexOf("const get = id => document.getElementById(id);");
const firstUse=js.indexOf("get('section-select').addEventListener");
assert.ok(getDeclaration >= 0 && getDeclaration < firstUse,'element lookup must initialize before section setup');
assert.equal((js.match(/const get = id => document.getElementById\(id\);/g)||[]).length,1);
console.log('Section navigator regression tests passed');

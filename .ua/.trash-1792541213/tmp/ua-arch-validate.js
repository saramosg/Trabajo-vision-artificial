const fs = require('fs');
const [,, layersPath, inputPath] = process.argv;
const layers = JSON.parse(fs.readFileSync(layersPath, 'utf8'));
const input = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
const expected = new Set(input.fileNodes.map(n => n.id));

let ok = true;
const seen = new Map();
for (const l of layers) {
  if (!Array.isArray(l.nodeIds) || l.nodeIds.length === 0) { console.error('EMPTY LAYER: ' + l.id); ok = false; }
  for (const id of l.nodeIds) {
    if (!expected.has(id)) { console.error('INVENTED ID: ' + id + ' in ' + l.id); ok = false; }
    if (seen.has(id)) { console.error('DUPLICATE: ' + id + ' in ' + l.id + ' and ' + seen.get(id)); ok = false; }
    seen.set(id, l.id);
  }
  if (!/^layer:[a-z0-9]+(-[a-z0-9]+)*$/.test(l.id)) { console.error('BAD LAYER ID: ' + l.id); ok = false; }
  for (const f of ['id', 'name', 'description', 'nodeIds']) {
    if (!(f in l)) { console.error('MISSING FIELD ' + f + ' in ' + l.id); ok = false; }
  }
}
const missing = [...expected].filter(id => !seen.has(id));
if (missing.length) { console.error('UNASSIGNED: ' + missing.join(', ')); ok = false; }

const total = layers.reduce((a, l) => a + l.nodeIds.length, 0);
console.log('layers=' + layers.length + ' (3-10 required)');
console.log('assigned=' + total + ' expected=' + expected.size + ' -> ' + (total === expected.size ? 'MATCH' : 'MISMATCH'));
if (layers.length < 3 || layers.length > 10) { console.error('LAYER COUNT OUT OF RANGE'); ok = false; }
if (total !== expected.size) ok = false;
console.log(ok ? 'VALIDATION OK' : 'VALIDATION FAILED');
process.exit(ok ? 0 : 1);

#!/usr/bin/env node
// Phase 6 step 1-2: assemble the full KnowledgeGraph with layers/tour normalization.
const fs = require('fs');
const path = require('path');

const repo = process.argv[2];
const uaDir = path.join(repo, '.ua');
const inter = path.join(uaDir, 'intermediate');

const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const assembled = readJson(path.join(inter, 'assembled-graph.json'));
const scan = readJson(path.join(inter, 'scan-result.json'));

const FILE_LEVEL_TYPES = new Set(['file', 'config', 'document', 'service', 'pipeline', 'table', 'schema', 'resource', 'endpoint']);
const PREFIXES = ['file:', 'config:', 'document:', 'service:', 'pipeline:', 'table:', 'schema:', 'resource:', 'endpoint:'];

const nodes = Array.isArray(assembled.nodes) ? assembled.nodes : [];
const edges = Array.isArray(assembled.edges) ? assembled.edges : [];
const nodeIds = new Set(nodes.map((n) => n.id));

const kebab = (s) => String(s).trim().toLowerCase()
  .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');

// --- layers normalization ---
let rawLayers = readJson(path.join(inter, 'layers.json'));
if (!Array.isArray(rawLayers)) rawLayers = rawLayers.layers || [];
const layers = [];
for (const [i, raw] of rawLayers.entries()) {
  const l = { ...raw };
  if (!l.id) l.id = 'layer:' + (kebab(l.name || ('layer-' + (i + 1))) || ('layer-' + (i + 1)));
  if (!l.name) l.name = l.id;
  if (!l.description) l.description = 'Capa del proyecto';
  let ids = l.nodeIds || l.nodes || [];
  if (ids.length && typeof ids[0] === 'object') ids = ids.map((n) => n.id);
  l.nodeIds = ids.map((id) => {
    if (nodeIds.has(id)) return id;
    const asFile = 'file:' + String(id).replace(/\\/g, '/');
    if (nodeIds.has(asFile)) return asFile;
    for (const p of PREFIXES) {
      if (nodeIds.has(p + id)) return p + id;
    }
    return id;
  }).filter((id) => nodeIds.has(id));
  layers.push(l);
}

// --- tour normalization ---
let rawTour = readJson(path.join(inter, 'tour.json'));
if (!Array.isArray(rawTour)) rawTour = rawTour.steps || rawTour.tour || [];
const tour = rawTour.map((raw, i) => {
  const s = { ...raw };
  s.order = typeof s.order === 'number' ? s.order : i + 1;
  if (!s.title) s.title = 'Paso ' + s.order;
  if (!s.description) s.description = s.whyItMatters || '';
  let ids = s.nodeIds || s.nodesToInspect || [];
  if (ids.length && typeof ids[0] === 'object') ids = ids.map((n) => n.id);
  s.nodeIds = ids.map((id) => {
    if (nodeIds.has(id)) return id;
    const asFile = 'file:' + String(id).replace(/\\/g, '/');
    if (nodeIds.has(asFile)) return asFile;
    for (const p of PREFIXES) {
      if (nodeIds.has(p + id)) return p + id;
    }
    return id;
  }).filter((id) => nodeIds.has(id));
  if (s.whyItMatters && !s.description) s.description = s.whyItMatters;
  delete s.nodesToInspect;
  delete s.whyItMatters;
  return s;
}).sort((a, b) => a.order - b.order);

// --- node field hygiene (auto-fix) ---
const VALID_TYPES = new Set(['file', 'function', 'class', 'config', 'document', 'service', 'table', 'endpoint', 'pipeline', 'schema', 'resource', 'concept', 'pattern']);
const keptNodes = [];
for (const n of nodes) {
  if (!n.id || !VALID_TYPES.has(n.type)) continue;
  if (!n.name) n.name = n.id;
  if (!n.summary) n.summary = 'Sin resumen disponible';
  if (!Array.isArray(n.tags) || !n.tags.length) n.tags = ['untagged'];
  keptNodes.push(n);
}
const keptIds = new Set(keptNodes.map((n) => n.id));
const keptEdges = edges.filter((e) => keptIds.has(e.source) && keptIds.has(e.target));

const graph = {
  version: '1.0.0',
  project: {
    name: scan.name || 'Trabajo-vision-artificial',
    languages: scan.languages || [],
    frameworks: scan.frameworks || [],
    description: scan.description || '',
    analyzedAt: new Date().toISOString(),
    gitCommitHash: process.argv[3] || 'sin-git',
  },
  nodes: keptNodes,
  edges: keptEdges,
  layers,
  tour,
};

fs.writeFileSync(path.join(inter, 'assembled-graph.json'), JSON.stringify(graph, null, 2));
const fileNodes = keptNodes.filter((n) => FILE_LEVEL_TYPES.has(n.type));
const covered = new Set(layers.flatMap((l) => l.nodeIds));
console.log(JSON.stringify({
  nodes: keptNodes.length,
  edges: keptEdges.length,
  layers: layers.length,
  tour: tour.length,
  fileNodes: fileNodes.length,
  fileNodesInLayers: fileNodes.filter((n) => covered.has(n.id)).length,
}, null, 2));

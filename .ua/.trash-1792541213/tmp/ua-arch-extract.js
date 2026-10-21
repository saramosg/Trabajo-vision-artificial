const fs = require('fs');

const [,, graphPath, outPath] = process.argv;
if (!graphPath || !outPath) {
  process.stderr.write('usage: node ua-arch-extract.js <assembled-graph.json> <out.json>\n');
  process.exit(1);
}

let graph;
try {
  graph = JSON.parse(fs.readFileSync(graphPath, 'utf8'));
} catch (e) {
  process.stderr.write('error: cannot read graph "' + graphPath + '": ' + e.message + '\n');
  process.exit(1);
}

const FILE_LEVEL_TYPES = new Set([
  'file', 'config', 'document', 'service', 'pipeline', 'table', 'schema', 'resource', 'endpoint'
]);

const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
const edges = Array.isArray(graph.edges) ? graph.edges : [];

const fileNodes = nodes
  .filter(n => FILE_LEVEL_TYPES.has(n.type))
  .map(n => ({
    id: n.id,
    type: n.type,
    name: n.name,
    filePath: n.filePath,
    summary: n.summary || '',
    tags: Array.isArray(n.tags) ? n.tags : []
  }));

const fileIds = new Set(fileNodes.map(n => n.id));

const allEdges = edges
  .filter(e => fileIds.has(e.source) && fileIds.has(e.target))
  .map(e => ({ source: e.source, target: e.target, type: e.type }));

const importEdges = allEdges.filter(e => e.type === 'imports');

const droppedImports = edges.filter(e => e.type === 'imports' && !(fileIds.has(e.source) && fileIds.has(e.target)));

fs.writeFileSync(outPath, JSON.stringify({ fileNodes, importEdges, allEdges }, null, 2));

process.stdout.write(
  'fileNodes=' + fileNodes.length +
  ' importEdges=' + importEdges.length +
  ' allEdges=' + allEdges.length +
  ' droppedNonFileLevelImports=' + droppedImports.length + '\n'
);

#!/usr/bin/env node
/**
 * ua-tour-analyze.js
 * Analiza la topologia del grafo de un proyecto para senalar senales estructurales
 * utiles al diseno de un tour pedagogico.
 *
 * Uso: node ua-tour-analyze.js <input.json> <output.json>
 *
 * Entrada: { nodes: [...], edges: [...], layers: [...] }
 * Salida:  { scriptCompleted, entryPointCandidates, fanInRanking, fanOutRanking,
 *            bfsTraversal, nonCodeFiles, clusters, layers, nodeSummaryIndex,
 *            totalNodes, totalEdges }
 */

const fs = require('fs');

const ENTRY_FILENAMES = [
  'index.ts', 'index.js', 'main.ts', 'main.js', 'app.ts', 'app.js',
  'server.ts', 'server.js', 'mod.rs', 'main.go', 'main.py', 'main.rs',
  'manage.py', 'app.py', 'wsgi.py', 'asgi.py', 'run.py', '__main__.py',
  'Application.java', 'Main.java', 'Program.cs', 'config.ru', 'index.php',
  'App.swift', 'Application.kt', 'main.cpp', 'main.c'
];

const CODE_TYPES = new Set(['file', 'config', 'service', 'pipeline', 'table', 'schema', 'resource', 'endpoint']);
const DOC_TYPES = new Set(['document']);
const INFRA_TYPES = new Set(['service', 'pipeline', 'resource']);
const DATA_TYPES = new Set(['table', 'schema', 'endpoint']);
// Aristas estructurales de pertenencia: no son dependencias reales entre archivos.
const STRUCTURAL_EDGES = new Set(['contains', 'exports']);

function fail(message) {
  process.stderr.write('ERROR: ' + message + '\n');
  process.exit(1);
}

function main() {
  const inputPath = process.argv[2];
  const outputPath = process.argv[3];
  if (!inputPath || !outputPath) {
    fail('Uso: node ua-tour-analyze.js <input.json> <output.json>');
  }

  let data;
  try {
    data = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  } catch (err) {
    fail('No se pudo leer/parsear la entrada: ' + err.message);
  }

  const nodes = Array.isArray(data.nodes) ? data.nodes : [];
  const edges = Array.isArray(data.edges) ? data.edges : [];
  const layers = Array.isArray(data.layers) ? data.layers : [];

  const nodeById = new Map();
  for (const n of nodes) {
    if (n && n.id) nodeById.set(n.id, n);
  }

  /**
   * Resuelve cualquier id de nodo (incluidos function: y class:) al nodo de
   * nivel archivo al que pertenece, para poder trabajar sobre la proyeccion
   * archivo-a-archivo de las aristas.
   */
  function resolveToFile(id) {
    if (!id) return null;
    if (nodeById.has(id)) return id;
    const m = /^(function|class):(.+):[^:]+$/.exec(id);
    if (m) {
      const candidate = 'file:' + m[2];
      if (nodeById.has(candidate)) return candidate;
    }
    return null;
  }

  // ---- Aristas proyectadas a nivel archivo (sin auto-loops) ----
  const projected = [];
  const seenPair = new Set();
  for (const e of edges) {
    if (!e || !e.source || !e.target) continue;
    const s = resolveToFile(e.source);
    const t = resolveToFile(e.target);
    if (!s || !t || s === t) continue;
    const key = s + '\u0000' + t;
    if (seenPair.has(key)) continue;
    seenPair.add(key);
    projected.push({ source: s, target: t, type: e.type, weight: e.weight });
  }

  // ---- A/B. Fan-in y fan-out ----
  const fanInMap = new Map();
  const fanOutMap = new Map();
  for (const e of projected) {
    if (STRUCTURAL_EDGES.has(e.type)) continue;
    if (!fanInMap.has(e.target)) fanInMap.set(e.target, new Set());
    if (!fanOutMap.has(e.source)) fanOutMap.set(e.source, new Set());
    fanInMap.get(e.target).add(e.source);
    fanOutMap.get(e.source).add(e.target);
  }
  const fanIn = nodes.map((n) => ({ id: n.id, fanIn: (fanInMap.get(n.id) || new Set()).size, name: n.name }));
  const fanOut = nodes.map((n) => ({ id: n.id, fanOut: (fanOutMap.get(n.id) || new Set()).size, name: n.name }));
  fanIn.sort((a, b) => b.fanIn - a.fanIn || a.id.localeCompare(b.id));
  fanOut.sort((a, b) => b.fanOut - a.fanOut || a.id.localeCompare(b.id));
  const fanInRanking = fanIn.slice(0, 20);
  const fanOutRanking = fanOut.slice(0, 20);

  // ---- C. Candidatos a punto de entrada ----
  const fanInValues = fanIn.map((f) => f.fanIn);
  const fanOutValues = fanOut.map((f) => f.fanOut);
  const top10FanOut = percentileThreshold(fanOutValues, 0.9, true);
  const bottom25FanIn = percentileThreshold(fanInValues, 0.25, false);

  const candidates = [];
  for (const n of nodes) {
    let score = 0;
    const filePath = n.filePath || n.name || '';
    const baseName = filePath.split('/').pop();
    const segments = filePath.split('/').filter(Boolean).length;
    const isDoc = DOC_TYPES.has(n.type);
    const isCode = CODE_TYPES.has(n.type);

    if (isCode) {
      if (ENTRY_FILENAMES.includes(baseName)) score += 3;
      if (segments <= 2) score += 1;
      if ((fanOutMap.get(n.id) || new Set()).size >= top10FanOut) score += 1;
      if ((fanInMap.get(n.id) || new Set()).size <= bottom25FanIn) score += 1;
    }
    if (isDoc) {
      const rootDoc = segments === 1;
      if (rootDoc && baseName.toLowerCase() === 'readme.md') score += 5;
      else if (rootDoc && baseName.toLowerCase().endsWith('.md')) score += 2;
    }
    if (score > 0) {
      candidates.push({ id: n.id, score, name: n.name, type: n.type, summary: n.summary, filePath });
    }
  }
  candidates.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
  const entryPointCandidates = candidates.slice(0, 5);

  // ---- D. Cadenas de dependencia (BFS desde el entry point de codigo) ----
  const codeEntry = candidates.find((c) => CODE_TYPES.has(c.type)) || null;
  const adjacency = new Map();
  for (const e of projected) {
    if (e.type !== 'imports' && e.type !== 'calls') continue;
    if (!adjacency.has(e.source)) adjacency.set(e.source, []);
    adjacency.get(e.source).push(e.target);
  }

  const bfsTraversal = { startNode: null, order: [], depthMap: {}, byDepth: {} };
  if (codeEntry) {
    const order = [];
    const depthMap = {};
    const byDepth = {};
    const queue = [codeEntry.id];
    depthMap[codeEntry.id] = 0;
    while (queue.length) {
      const current = queue.shift();
      order.push(current);
      const d = depthMap[current];
      (byDepth[d] = byDepth[d] || []).push(current);
      for (const next of adjacency.get(current) || []) {
        if (!(next in depthMap)) {
          depthMap[next] = d + 1;
          queue.push(next);
        }
      }
    }
    bfsTraversal.startNode = codeEntry.id;
    bfsTraversal.order = order;
    bfsTraversal.depthMap = depthMap;
    bfsTraversal.byDepth = byDepth;
  }

  // ---- E. Inventario de archivos no-codigo ----
  const pick = (types) =>
    nodes
      .filter((n) => types.has(n.type))
      .map((n) => ({ id: n.id, name: n.name, type: n.type, summary: n.summary, filePath: n.filePath }));
  const nonCodeFiles = {
    documentation: pick(DOC_TYPES),
    infrastructure: pick(INFRA_TYPES),
    data: pick(DATA_TYPES),
    config: pick(new Set(['config']))
  };

  // ---- F. Clusters altamente acoplados ----
  const outAdj = new Map();
  const inAdj = new Map();
  for (const e of projected) {
    if (STRUCTURAL_EDGES.has(e.type)) continue;
    if (!outAdj.has(e.source)) outAdj.set(e.source, new Set());
    if (!inAdj.has(e.target)) inAdj.set(e.target, new Set());
    outAdj.get(e.source).add(e.target);
    inAdj.get(e.target).add(e.source);
  }
  const clusters = [];
  const usedMembers = new Set();
  const pairKey = (a, b) => (a < b ? a + '|' + b : b + '|' + a);
  const pairSeen = new Set();
  for (const [src, targets] of outAdj) {
    for (const dst of targets) {
      if (!outAdj.has(dst)) continue;
      if (!outAdj.get(dst).has(src)) continue;
      const key = pairKey(src, dst);
      if (pairSeen.has(key)) continue;
      pairSeen.add(key);
      const members = new Set([src, dst]);
      // Expansion: nodos conectados a 2+ miembros del cluster.
      let changed = true;
      while (changed && members.size < 5) {
        changed = false;
        const candidates = new Map();
        for (const m of members) {
          for (const n of outAdj.get(m) || []) if (!members.has(n)) candidates.set(n, (candidates.get(n) || 0) + 1);
          for (const n of inAdj.get(m) || []) if (!members.has(n)) candidates.set(n, (candidates.get(n) || 0) + 1);
        }
        for (const [n, count] of candidates) {
          if (count >= 2 && members.size < 5) {
            members.add(n);
            changed = true;
          }
        }
      }
      let edgeCount = 0;
      for (const a of members) {
        for (const b of members) {
          if (a !== b && (outAdj.get(a) || new Set()).has(b)) edgeCount++;
        }
      }
      const memberList = Array.from(members).sort();
      clusters.push({ nodes: memberList, edgeCount });
      memberList.forEach((m) => usedMembers.add(m));
    }
  }
  clusters.sort((a, b) => b.edgeCount - a.edgeCount || b.nodes.length - a.nodes.length || a.nodes[0].localeCompare(b.nodes[0]));
  const topClusters = clusters.slice(0, 10);

  // ---- G. Capas ----
  const layersOut = {
    count: layers.length,
    list: layers.map((l) => ({ id: l.id, name: l.name, description: l.description }))
  };

  // ---- H. Indice de resumenes ----
  const nodeSummaryIndex = {};
  for (const n of nodes) {
    nodeSummaryIndex[n.id] = { name: n.name, type: n.type, summary: n.summary, filePath: n.filePath };
  }

  const results = {
    scriptCompleted: true,
    entryPointCandidates,
    fanInRanking,
    fanOutRanking,
    bfsTraversal,
    nonCodeFiles,
    clusters: topClusters,
    layers: layersOut,
    nodeSummaryIndex,
    totalNodes: nodes.length,
    totalEdges: edges.length
  };

  try {
    fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
  } catch (err) {
    fail('No se pudo escribir la salida: ' + err.message);
  }
  process.exit(0);
}

function percentileThreshold(values, p, high) {
  if (!values.length) return high ? 0 : 0;
  const sorted = values.slice().sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.floor((high ? p : 1 - p) * sorted.length)));
  return sorted[idx];
}

main();

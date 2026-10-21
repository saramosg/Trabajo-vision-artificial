const fs = require('fs');

const [,, inPath, outPath] = process.argv;
if (!inPath || !outPath) {
  process.stderr.write('usage: node ua-arch-analyze.js <input.json> <output.json>\n');
  process.exit(1);
}

let input;
try {
  input = JSON.parse(fs.readFileSync(inPath, 'utf8'));
} catch (e) {
  process.stderr.write('error: cannot read input "' + inPath + '": ' + e.message + '\n');
  process.exit(1);
}

const fileNodes = Array.isArray(input.fileNodes) ? input.fileNodes : [];
const importEdges = Array.isArray(input.importEdges) ? input.importEdges : [];
const allEdges = Array.isArray(input.allEdges) ? input.allEdges : [];

const byId = new Map();
for (const n of fileNodes) byId.set(n.id, n);

const pathOf = id => (byId.get(id) || {}).filePath || '';
const dirOf = p => { const i = p.lastIndexOf('/'); return i === -1 ? '' : p.slice(0, i); };

/* ------------------------------------------------------------------ */
/* A. Directory Grouping                                               */
/* ------------------------------------------------------------------ */

function computeCommonPrefix(paths) {
  if (!paths.length) return '';
  const dirs = paths.map(dirOf);
  if (dirs.some(d => d === '')) return '';
  const segLists = dirs.map(d => d.split('/'));
  const prefix = [];
  for (let i = 0; ; i++) {
    const seg = segLists[0][i];
    if (seg === undefined) break;
    if (!segLists.every(sl => sl[i] === seg)) break;
    prefix.push(seg);
  }
  return prefix.length ? prefix.join('/') + '/' : '';
}

const paths = fileNodes.map(n => n.filePath || '');
const commonPrefix = computeCommonPrefix(paths);

function groupOf(id) {
  const p = pathOf(id);
  let rel = p;
  if (commonPrefix && rel.startsWith(commonPrefix)) rel = rel.slice(commonPrefix.length);
  const segs = rel.split('/');
  return segs.length > 1 ? segs[0] : 'root';
}

const directoryGroups = {};
for (const n of fileNodes) {
  const g = groupOf(n.id);
  if (!directoryGroups[g]) directoryGroups[g] = [];
  directoryGroups[g].push(n.id);
}

const groupMembers = {};
for (const g of Object.keys(directoryGroups)) {
  groupMembers[g] = new Set(directoryGroups[g]);
}
const groupOfNode = {};
for (const n of fileNodes) groupOfNode[n.id] = groupOf(n.id);

/* ------------------------------------------------------------------ */
/* B. Node Type Grouping                                               */
/* ------------------------------------------------------------------ */

const nodeTypeGroups = {};
for (const n of fileNodes) {
  if (!nodeTypeGroups[n.type]) nodeTypeGroups[n.type] = [];
  nodeTypeGroups[n.type].push(n.id);
}

/* ------------------------------------------------------------------ */
/* C. Import Adjacency Matrix                                           */
/* ------------------------------------------------------------------ */

const fileFanOut = {};
const fileFanIn = {};
for (const n of fileNodes) { fileFanOut[n.id] = 0; fileFanIn[n.id] = 0; }

const groupImports = {}; // group -> { importedBy:Set, imports:Set }
for (const g of Object.keys(directoryGroups)) {
  groupImports[g] = { imports: new Set(), importedBy: new Set() };
}

for (const e of importEdges) {
  if (fileFanOut[e.source] === undefined) fileFanOut[e.source] = 0;
  if (fileFanIn[e.target] === undefined) fileFanIn[e.target] = 0;
  fileFanOut[e.source]++;
  fileFanIn[e.target]++;
  const gs = groupOfNode[e.source];
  const gt = groupOfNode[e.target];
  if (gs !== undefined && gt !== undefined && gs !== gt) {
    groupImports[gs].imports.add(gt);
    groupImports[gt].importedBy.add(gs);
  }
}

/* ------------------------------------------------------------------ */
/* D. Cross-Category Dependency Analysis                               */
/* ------------------------------------------------------------------ */

const ccMap = new Map();
for (const e of allEdges) {
  const st = (byId.get(e.source) || {}).type || 'unknown';
  const tt = (byId.get(e.target) || {}).type || 'unknown';
  const key = st + '|' + tt + '|' + e.type;
  ccMap.set(key, (ccMap.get(key) || 0) + 1);
}
const crossCategoryEdges = [];
for (const [key, count] of ccMap) {
  const [fromType, toType, edgeType] = key.split('|');
  crossCategoryEdges.push({ fromType, toType, edgeType, count });
}
crossCategoryEdges.sort((a, b) => b.count - a.count || a.fromType.localeCompare(b.fromType));

const nonCodeToCode = {};
for (const e of allEdges) {
  const st = (byId.get(e.source) || {}).type;
  const tt = (byId.get(e.target) || {}).type;
  const codeTypes = new Set(['file']);
  if (st && st !== 'file' && tt && codeTypes.has(tt)) {
    if (!nonCodeToCode[st]) nonCodeToCode[st] = [];
    nonCodeToCode[st].push({ source: e.source, target: e.target, type: e.type });
  }
  if (tt && tt !== 'file' && st && codeTypes.has(st)) {
    if (!nonCodeToCode[tt]) nonCodeToCode[tt] = [];
    nonCodeToCode[tt].push({ source: e.source, target: e.target, type: e.type });
  }
}

/* ------------------------------------------------------------------ */
/* E. Inter-Group Import Frequency                                     */
/* ------------------------------------------------------------------ */

const igMap = new Map();
for (const e of importEdges) {
  const gs = groupOfNode[e.source];
  const gt = groupOfNode[e.target];
  if (!gs || !gt || gs === gt) continue;
  const key = gs + '->' + gt;
  igMap.set(key, (igMap.get(key) || 0) + 1);
}
const interGroupImports = [];
for (const [key, count] of igMap) {
  const [from, to] = key.split('->');
  interGroupImports.push({ from, to, count });
}
interGroupImports.sort((a, b) => b.count - a.count);

/* ------------------------------------------------------------------ */
/* F. Intra-Group Import Density                                       */
/* ------------------------------------------------------------------ */

const intraGroupDensity = {};
for (const g of Object.keys(directoryGroups)) {
  let internalEdges = 0;
  let totalEdges = 0;
  for (const e of importEdges) {
    const gs = groupOfNode[e.source];
    const gt = groupOfNode[e.target];
    if (gs === g && gt === g) { internalEdges++; totalEdges++; }
    else if (gs === g || gt === g) { totalEdges++; }
  }
  intraGroupDensity[g] = {
    internalEdges,
    totalEdges,
    density: totalEdges ? Math.round((internalEdges / totalEdges) * 1000) / 1000 : 0
  };
}

/* ------------------------------------------------------------------ */
/* G. Directory / File Pattern Matching                                */
/* ------------------------------------------------------------------ */

const DIR_PATTERNS = {
  routes: 'api', api: 'api', controllers: 'api', endpoints: 'api', handlers: 'api',
  services: 'service', core: 'service', lib: 'service', domain: 'service', logic: 'service',
  models: 'data', db: 'data', data: 'data', persistence: 'data', repository: 'data', entities: 'data',
  components: 'ui', views: 'ui', pages: 'ui', ui: 'ui', layouts: 'ui', screens: 'ui',
  middleware: 'middleware', plugins: 'middleware', interceptors: 'middleware', guards: 'middleware',
  utils: 'utility', helpers: 'utility', common: 'utility', shared: 'utility', tools: 'utility',
  config: 'config', constants: 'config', env: 'config', settings: 'config',
  __tests__: 'test', test: 'test', tests: 'test', spec: 'test', specs: 'test',
  types: 'types', interfaces: 'types', schemas: 'types', contracts: 'types', dtos: 'types',
  hooks: 'hooks',
  store: 'state', state: 'state', reducers: 'state', actions: 'state', slices: 'state',
  assets: 'assets', static: 'assets', public: 'assets',
  migrations: 'data',
  management: 'config', commands: 'config',
  templatetags: 'utility',
  signals: 'service',
  serializers: 'api',
  cmd: 'entry',
  internal: 'service',
  pkg: 'utility',
  dto: 'types', request: 'types', response: 'types',
  entity: 'data',
  controller: 'api',
  routers: 'api',
  composables: 'service',
  blueprints: 'api',
  mailers: 'service', jobs: 'service', channels: 'service',
  bin: 'entry',
  docs: 'documentation', documentation: 'documentation', wiki: 'documentation',
  deploy: 'infrastructure', deployment: 'infrastructure', infra: 'infrastructure', infrastructure: 'infrastructure',
  '.github': 'ci-cd', '.gitlab': 'ci-cd', '.circleci': 'ci-cd',
  k8s: 'infrastructure', kubernetes: 'infrastructure', helm: 'infrastructure', charts: 'infrastructure',
  terraform: 'infrastructure', tf: 'infrastructure',
  docker: 'infrastructure',
  sql: 'data', database: 'data', schema: 'data'
};

const patternMatches = {};
for (const g of Object.keys(directoryGroups)) {
  patternMatches[g] = DIR_PATTERNS[g] || null;
}

const filePatternMatches = {};
for (const n of fileNodes) {
  const p = n.filePath || '';
  const base = p.slice(p.lastIndexOf('/') + 1);
  let label = null;
  if (/^test_.*\.py$/.test(base) || /.*_test\.go$/.test(base) || /.*Test\.java$/.test(base) ||
      /.*_spec\.rb$/.test(base) || /.*Test\.php$/.test(base) || /.*Tests\.cs$/.test(base) ||
      /\.(test|spec)\.[jt]sx?$/.test(base)) {
    label = 'test';
  } else if (/\.d\.ts$/.test(base)) {
    label = 'types';
  } else if (base === '__init__.py' || base === 'index.ts' || base === 'index.js') {
    label = 'entry';
  } else if (base === 'manage.py') {
    label = 'entry';
  } else if (base === 'wsgi.py' || base === 'asgi.py') {
    label = 'config';
  } else if (base === 'main.py') {
    label = 'entry';
  } else if (base === 'main.rs' || base === 'lib.rs') {
    label = 'entry';
  } else if (base === 'Application.java' || base === 'Program.cs') {
    label = 'entry';
  } else if (base === 'config.ru') {
    label = 'entry';
  } else if (['Cargo.toml', 'go.mod', 'Gemfile', 'pom.xml', 'build.gradle', 'composer.json'].includes(base)) {
    label = 'config';
  } else if (base === 'Dockerfile' || /^docker-compose\./.test(base)) {
    label = 'infrastructure';
  } else if (/\.(tf|tfvars)$/.test(base)) {
    label = 'infrastructure';
  } else if (/\.github\/workflows\//.test(p) || base === '.gitlab-ci.yml' || base === 'Jenkinsfile') {
    label = 'ci-cd';
  } else if (/\.sql$/.test(base)) {
    label = 'data';
  } else if (/\.(graphql|gql|proto)$/.test(base)) {
    label = 'types';
  } else if (/\.(md|rst)$/.test(base)) {
    label = 'documentation';
  } else if (base === 'Makefile') {
    label = 'infrastructure';
  } else if (/\.spec$/.test(base)) {
    label = 'config';
  } else if (/\.qss$/.test(base)) {
    label = 'ui';
  } else if (base === 'requirements.txt' || /\.(txt|toml|yaml|yml|ini|cfg)$/.test(base)) {
    label = 'config';
  } else if (/\.(webp|png|jpe?g|gif|bmp|svg|ico)$/.test(base)) {
    label = 'assets';
  }
  filePatternMatches[n.id] = label;
}

/* ------------------------------------------------------------------ */
/* H. Deployment Topology Detection                                    */
/* ------------------------------------------------------------------ */

const allPaths = fileNodes.map(n => n.filePath || '');
const infraFiles = [];
let hasDockerfile = false, hasCompose = false, hasK8s = false, hasTerraform = false, hasCI = false;
for (const n of fileNodes) {
  const p = n.filePath || '';
  const base = p.slice(p.lastIndexOf('/') + 1);
  if (base === 'Dockerfile' || /^Dockerfile\./.test(base)) { hasDockerfile = true; infraFiles.push(p); }
  else if (/^docker-compose\./.test(base)) { hasCompose = true; infraFiles.push(p); }
  else if (/\.(tf|tfvars)$/.test(base) || /(^|\/)(k8s|kubernetes|helm|charts)\//.test(p)) {
    hasTerraform = hasTerraform || /\.tf/.test(base); hasK8s = hasK8s || !/\.tf/.test(base); infraFiles.push(p);
  }
  else if (/\.github\/workflows\//.test(p) || base === '.gitlab-ci.yml' || base === 'Jenkinsfile') { hasCI = true; infraFiles.push(p); }
  else if (base === 'Makefile') { infraFiles.push(p); }
  else if (base === 'main.spec') { infraFiles.push(p); }
}
const deploymentTopology = { hasDockerfile, hasCompose, hasK8s, hasTerraform, hasCI, infraFiles };

/* ------------------------------------------------------------------ */
/* I. Data Pipeline Detection                                          */
/* ------------------------------------------------------------------ */

const schemaFiles = [], migrationFiles = [], dataModelFiles = [], apiHandlerFiles = [];
for (const n of fileNodes) {
  const p = n.filePath || '';
  const base = p.slice(p.lastIndexOf('/') + 1);
  if (/\.(sql|graphql|gql|proto|prisma)$/.test(base)) schemaFiles.push(p);
  if (/migrations?\//.test(p)) migrationFiles.push(p);
  if (/(^|\/)(models?|db|data|persistence|repository|entities)\//.test(p)) dataModelFiles.push(p);
  if (/(^|\/)(routes?|api|controllers?|endpoints?|blueprints?)\//.test(p)) apiHandlerFiles.push(p);
}
const dataPipeline = { schemaFiles, migrationFiles, dataModelFiles, apiHandlerFiles };

/* ------------------------------------------------------------------ */
/* J. Documentation Coverage                                            */
/* ------------------------------------------------------------------ */

const docIds = new Set(nodeTypeGroups['document'] || []);
const groupsWithDocsSet = new Set();
const undocumentedGroups = [];
for (const g of Object.keys(directoryGroups)) {
  let has = false;
  for (const id of directoryGroups[g]) {
    if (docIds.has(id) && /\.(md|rst)$/i.test(pathOf(id))) has = true;
    for (const e of allEdges) {
      if (e.type === 'documents' && e.target === id && docIds.has(e.source)) has = true;
    }
  }
  if (has) groupsWithDocsSet.add(g); else undocumentedGroups.push(g);
}
const docCoverage = {
  groupsWithDocs: groupsWithDocsSet.size,
  totalGroups: Object.keys(directoryGroups).length,
  coverageRatio: Object.keys(directoryGroups).length
    ? Math.round((groupsWithDocsSet.size / Object.keys(directoryGroups).length) * 100) / 100
    : 0,
  undocumentedGroups
};

/* ------------------------------------------------------------------ */
/* K. Dependency Direction                                             */
/* ------------------------------------------------------------------ */

const pairCounts = new Map();
for (const e of importEdges) {
  const gs = groupOfNode[e.source], gt = groupOfNode[e.target];
  if (!gs || !gt || gs === gt) continue;
  pairCounts.set(gs + '|' + gt, (pairCounts.get(gs + '|' + gt) || 0) + 1);
}
const dependencyDirection = [];
for (const g of Object.keys(directoryGroups)) {
  for (const other of Object.keys(directoryGroups)) {
    if (g === other) continue;
    const forward = pairCounts.get(g + '|' + other) || 0;
    const backward = pairCounts.get(other + '|' + g) || 0;
    if (forward === 0 && backward === 0) continue;
    if (forward > backward) dependencyDirection.push({ dependent: g, dependsOn: other });
    else if (backward > forward) dependencyDirection.push({ dependent: other, dependsOn: g });
    else dependencyDirection.push({ dependent: g, dependsOn: other, mutual: true });
  }
}

/* ------------------------------------------------------------------ */

const results = {
  scriptCompleted: true,
  commonPrefix,
  directoryGroups,
  nodeTypeGroups,
  crossCategoryEdges,
  nonCodeToCode,
  interGroupImports,
  intraGroupDensity,
  patternMatches,
  filePatternMatches,
  deploymentTopology,
  dataPipeline,
  docCoverage,
  dependencyDirection,
  fileStats: {
    totalFileNodes: fileNodes.length,
    filesPerGroup: Object.fromEntries(Object.entries(directoryGroups).map(([k, v]) => [k, v.length])),
    nodeTypeCounts: Object.fromEntries(Object.entries(nodeTypeGroups).map(([k, v]) => [k, v.length]))
  },
  fileFanIn,
  fileFanOut
};

try {
  fs.writeFileSync(outPath, JSON.stringify(results, null, 2));
} catch (e) {
  process.stderr.write('error: cannot write output "' + outPath + '": ' + e.message + '\n');
  process.exit(1);
}

process.stdout.write('OK: wrote ' + outPath + '\n');

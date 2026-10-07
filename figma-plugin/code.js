// Plugin de desarrollo: sincroniza los 5 frames con la app local.
// Importar: Figma > Plugins > Development > Import plugin from manifest.
// Uso: Plugins > Development > Sync UNAL tokens > Run.
// Crea la pagina "Sync UNAL v2" (borra la anterior si existe: es generada).
// PASADA 1: medidas, radios, rellenos, fuentes (detecta la del archivo).
// PASADA 2: layout como la app. Cada movimiento se VERIFICA releyendo x/y
// y el notify reporta sin aplicar.
const TOK = {
  BTN_W: 200, BTN_H: 60, RADIO_BOTON: 30,
  NAV_W: 160, NAV_H: 48, RADIO_NAV: 24,
  SUPERFICIE: '#D9D9D9', BORDE: '#9E9E9E', ACENTO: '#2F6FED',
  TEXTO: '#000000',
  TITULO: 28, ETIQUETA: 16, BOTON: 14,
  COLOR_CANAL: {
    r: '#C62828', g: '#2E7D32', b: '#1565C0',
    y: '#8D6E00', c: '#00838F', m: '#AD1457',
  },
  ESPACIO_ITEM: 24,
};

const FRAMES = ['1:2382', '1:2387', '1:2406', '11:6', '23:38'];
const PAGINA = 'Sync UNAL v2';

const BOTONES_STD = {
  '1:2382': ['elegir modelo', 'quitar fondo', 'recortar imagen', 'rectangle 3'],
  '1:2387': ['rectangle 3', 'regresar'],
  '1:2406': ['rectangle 3', 'regresar'],
  '11:6': ['gardar imagen', 'guardar mascara de imagen', 'quitar fondo'],
  '23:38': ['guardar copia', 'sobreescribir'],
};
const BOTONES_PRIM = { '1:2382': ['canales'], '23:38': ['rectangle 2'] };
const BOTONES_NAV = { '1:2387': ['regresar'], '1:2406': ['regresar'] };
const TITULOS = ['analizador de imagenes', 'rgb', 'ycm'];

const norm = (s) => (s || '').trim().toLowerCase();
function hex(h) {
  const n = parseInt(h.slice(1), 16);
  return { r: ((n >> 16) & 255) / 255, g: ((n >> 8) & 255) / 255, b: (n & 255) / 255 };
}
function solido(h) { return [{ type: 'SOLID', color: hex(h) }]; }
function caminar(nodo, fn) {
  fn(nodo);
  if ('children' in nodo) for (const c of nodo.children) caminar(c, fn);
}
function hijo(frame, pred) {
  let out = null;
  caminar(frame, (x) => { if (!out && pred(x)) out = x; });
  return out;
}
function hijos(frame, pred) {
  const out = [];
  caminar(frame, (x) => { if (pred(x)) out.push(x); });
  return out;
}
function rectPorNombre(frame, nombre) {
  return hijo(frame, (x) => x.type === 'RECTANGLE' && norm(x.name) === norm(nombre));
}
function boton(rect, w, h, radio, primario) {
  rect.resize(w, h);
  if ('cornerRadius' in rect) rect.cornerRadius = radio;
  rect.fills = solido(primario ? TOK.ACENTO : TOK.SUPERFICIE);
  rect.strokes = solido(primario ? TOK.ACENTO : TOK.BORDE);
  rect.strokeWeight = 1;
}

// Fuente real del archivo (el boceto usa Inter, no Segoe UI).
let FUENTE = 'Inter';
function detectarFuente(frame) {
  const t = hijo(frame, (x) => x.type === 'TEXT' && x.fontName && x.fontName.family);
  if (t) FUENTE = t.fontName.family;
}
async function estiloTexto(nodo, size, estilo, fill) {
  try { await figma.loadFontAsync({ family: FUENTE, style: estilo }); } catch (e) { return false; }
  try {
    nodo.fontSize = size;
    if (fill) nodo.fills = solido(fill);
    return true;
  } catch (e) { return false; }
}
async function ponerTexto(nodo, chars, size, estilo, fill) {
  try { await figma.loadFontAsync({ family: FUENTE, style: estilo }); } catch (e) { return false; }
  try {
    nodo.characters = chars;
    nodo.fontSize = size;
    if (fill) nodo.fills = solido(fill);
    return true;
  } catch (e) { return false; }
}
function centrar(txt, rect) {
  txt.x = rect.x + (rect.width - txt.width) / 2;
  txt.y = rect.y + (rect.height - txt.height) / 2;
}
// Mueve el grupo para que su rect quede en (tx,ty). Devuelve true si la
// posicion final coincide (verificacion leida, no supuesta).
function llevarRect(grupo, rect, tx, ty) {
  grupo.x += tx - (grupo.x + rect.x);
  grupo.y += ty - (grupo.y + rect.y);
  return Math.abs((grupo.x + rect.x) - tx) < 0.6 && Math.abs((grupo.y + rect.y) - ty) < 0.6;
}
function grupoDe(frame, rect) {
  return hijo(frame, (x) => x.children && x.children.includes(rect));
}
async function tituloNuevo(frame, chars, y, cuenta) {
  try { await figma.loadFontAsync({ family: FUENTE, style: 'Bold' }); } catch (e) { cuenta.fallo++; return; }
  try {
    const t = figma.createText();
    t.fontName = { family: FUENTE, style: 'Bold' };
    t.characters = chars;
    t.fontSize = TOK.TITULO;
    t.fills = solido(TOK.TEXTO);
    frame.appendChild(t);
    t.x = (1280 - t.width) / 2;
    t.y = y;
    cuenta.ok++;
  } catch (e) { cuenta.fallo++; }
}

// ---------- PASADA 1 ----------
async function pasada1(frame, id, cuenta) {
  detectarFuente(frame);
  for (const nombre of (BOTONES_STD[id] || [])) {
    let n = 0;
    caminar(frame, (x) => {
      if (x.type === 'RECTANGLE' && norm(x.name) === norm(nombre)) {
        try { boton(x, TOK.BTN_W, TOK.BTN_H, TOK.RADIO_BOTON, false); n++; } catch (e) {}
      }
    });
    n > 0 ? cuenta.ok++ : cuenta.fallo++;
    if (norm(nombre) === 'gardar imagen') {
      caminar(frame, (x) => { if (norm(x.name) === 'gardar imagen') x.name = 'Guardar imagen'; });
    }
  }
  for (const nombre of (BOTONES_PRIM[id] || [])) {
    let n = 0;
    caminar(frame, (x) => {
      if (x.type === 'RECTANGLE' && norm(x.name) === norm(nombre)) {
        try { boton(x, TOK.BTN_W, TOK.BTN_H, TOK.RADIO_BOTON, true); n++; } catch (e) {}
      }
    });
    n > 0 ? cuenta.ok++ : cuenta.fallo++;
  }
  for (const nombre of (BOTONES_NAV[id] || [])) {
    let n = 0;
    caminar(frame, (x) => {
      if (x.type === 'RECTANGLE' && norm(x.name) === norm(nombre)) {
        try { boton(x, TOK.NAV_W, TOK.NAV_H, TOK.RADIO_NAV, false); n++; } catch (e) {}
      }
    });
    n > 0 ? cuenta.ok++ : cuenta.fallo++;
  }
  const jobs = [];
  caminar(frame, (x) => {
    if (x.type !== 'TEXT') return;
    const c = norm(x.characters);
    if (TOK.COLOR_CANAL[c]) jobs.push(estiloTexto(x, TOK.BOTON, 'Semi Bold', TOK.COLOR_CANAL[c]));
    else if (TITULOS.includes(c)) jobs.push(estiloTexto(x, TOK.TITULO, 'Bold', TOK.TEXTO));
    else if (c === 'modelo:') jobs.push(estiloTexto(x, TOK.ETIQUETA, 'Regular', TOK.TEXTO));
  });
  for (const j of jobs) (await j) ? cuenta.ok++ : cuenta.fallo++;
}

// ---------- PASADA 2 ----------
async function botonesDeGrupo(frame, cuenta) {
  const grupos = hijos(frame, (x) =>
    x.children && x.children.some((c) => c.type === 'RECTANGLE' && c.width === 200));
  for (const g of grupos) {
    const r = g.children.find((c) => c.type === 'RECTANGLE' && c.width === 200);
    for (const t of g.children.filter((c) => c.type === 'TEXT')) {
      if (await estiloTexto(t, TOK.BOTON, 'Semi Bold', TOK.TEXTO)) cuenta.ok++;
      else cuenta.fallo++;
      try { centrar(t, r); cuenta.ok++; } catch (e) { cuenta.fallo++; }
    }
  }
}

async function layoutPrincipal(frame, cuenta) {
  const t = hijo(frame, (x) => x.type === 'TEXT' && norm(x.characters) === 'analizador de imagenes');
  if (t) {
    t.x = (1280 - t.width) / 2; t.y = 61;
    (Math.abs(t.x - (1280 - t.width) / 2) < 0.6) ? cuenta.ok++ : cuenta.fallo++;
  } else cuenta.fallo++;
  const zona = hijo(frame, (x) => x.name === 'Group 1');
  if (zona) {
    zona.x += 370 - zona.x; zona.y += 200 - zona.y;
    (zona.x === 370 && zona.y === 200) ? cuenta.ok++ : cuenta.fallo++;
  } else cuenta.fallo++;
  const COL = 710;
  const modelo = rectPorNombre(frame, 'Elegir modelo');
  const lblModelo = hijo(frame, (x) => x.type === 'TEXT' && norm(x.characters) === 'modelo:');
  if (modelo) {
    modelo.x = COL; modelo.y = 200;
    (modelo.x === COL && modelo.y === 200) ? cuenta.ok++ : cuenta.fallo++;
  } else cuenta.fallo++;
  if (modelo && lblModelo) {
    lblModelo.x = COL - 24 - lblModelo.width;
    lblModelo.y = 200 + (60 - lblModelo.height) / 2;
    cuenta.ok++;
  }
  for (const [nombre, y] of [['quitar fondo', 284], ['canales', 368], ['recortar imagen', 452]]) {
    const r = rectPorNombre(frame, nombre);
    if (!r) { cuenta.fallo++; continue; }
    const g = grupoDe(frame, r);
    if (g) {
      llevarRect(g, r, COL, y) ? cuenta.ok++ : cuenta.fallo++;
      const txt = g.children.find((c) => c.type === 'TEXT');
      if (txt) { try { centrar(txt, r); cuenta.ok++; } catch (e) { cuenta.fallo++; } }
    } else {
      r.x = COL; r.y = y;
      (r.x === COL && r.y === y) ? cuenta.ok++ : cuenta.fallo++;
    }
  }
}

async function layoutCanales(frame, cuenta) {
  const titulo = hijo(frame, (x) => x.type === 'TEXT' && ['rgb', 'ycm'].includes(norm(x.characters)));
  if (titulo) { titulo.x = (1280 - titulo.width) / 2; titulo.y = 110; cuenta.ok++; } else cuenta.fallo++;
  const letras = ['r', 'g', 'b', 'y', 'c', 'm'];
  const xs = [60, 490, 920];
  const presentes = letras.map((l) => hijo(frame,
    (x) => x.type === 'RECTANGLE' && norm(x.name) === l)).filter(Boolean).slice(0, 3);
  const letrasT = letras.map((l) => hijo(frame,
    (x) => x.type === 'TEXT' && norm(x.characters) === l)).filter(Boolean).slice(0, 3);
  presentes.forEach((r, i) => {
    r.x = xs[i]; r.y = 260;
    (r.x === xs[i] && r.y === 260) ? cuenta.ok++ : cuenta.fallo++;
    const t = letrasT[i];
    if (t) { t.x = r.x + (300 - t.width) / 2; t.y = 260 - 10 - t.height; cuenta.ok++; }
  });
  const img = hijo(frame, (x) => x.type === 'TEXT' && norm(x.characters) === 'imagen:');
  if (img) { img.x = 60; img.y = 15; cuenta.ok++; }
  const dir = hijo(frame, (x) => x.type === 'TEXT' && norm(x.characters).startsWith('directorio'));
  if (dir) { dir.x = 60; dir.y = 55; cuenta.ok++; }
  const reg = hijo(frame, (x) => x.type === 'RECTANGLE' && norm(x.name) === 'regresar');
  if (reg) {
    const g = grupoDe(frame, reg);
    if (g) {
      llevarRect(g, reg, 1060, 29) ? cuenta.ok++ : cuenta.fallo++;
      const tr = g.children.find((c) => c.type === 'TEXT');
      if (tr) { try { centrar(tr, reg); cuenta.ok++; } catch (e) { cuenta.fallo++; } }
    } else {
      reg.x = 1060; reg.y = 29;
      (reg.x === 1060 && reg.y === 29) ? cuenta.ok++ : cuenta.fallo++;
    }
  } else cuenta.fallo++;
  const modoR = hijo(frame, (x) => x.type === 'RECTANGLE' && norm(x.name) === 'rectangle 3');
  if (modoR) {
    const g = grupoDe(frame, modoR);
    if (g) {
      llevarRect(g, modoR, 612, 29) ? cuenta.ok++ : cuenta.fallo++;
      const lbl = g.children.find((c) => c.type === 'TEXT');
      if (lbl) {
        if (await estiloTexto(lbl, TOK.ETIQUETA, 'Regular', TOK.TEXTO)) cuenta.ok++; else cuenta.fallo++;
        lbl.x = modoR.x - 12 - lbl.width;
        lbl.y = modoR.y + (60 - lbl.height) / 2;
        cuenta.ok++;
      }
      try {
        const gh = g.clone();
        frame.appendChild(gh);
        const rt = gh.children.find((c) => c.type === 'RECTANGLE');
        const tt = gh.children.find((c) => c.type === 'TEXT');
        if (tt) { (await ponerTexto(tt, 'Histograma de color', TOK.BOTON, 'Semi Bold', TOK.TEXTO)) ? cuenta.ok++ : cuenta.fallo++; }
        if (rt) {
          llevarRect(gh, rt, 836, 29) ? cuenta.ok++ : cuenta.fallo++;
          if (tt) { try { centrar(tt, rt); cuenta.ok++; } catch (e) { cuenta.fallo++; } }
        }
      } catch (e) { cuenta.fallo++; }
    }
  } else cuenta.fallo++;
}

async function layoutHistograma(frame, cuenta) {
  await tituloNuevo(frame, 'Histograma de color', 16, cuenta);
  const orig = hijo(frame, (x) => x.type === 'RECTANGLE' && norm(x.name) === 'imagen normal');
  if (orig) {
    orig.x = 60; orig.y = 200;
    (orig.x === 60 && orig.y === 200) ? cuenta.ok++ : cuenta.fallo++;
  } else cuenta.fallo++;
  const canales = hijos(frame, (x) => x.type === 'RECTANGLE' && norm(x.name) === 'imagen con canal');
  if (canales[0]) {
    canales[0].x = 334; canales[0].y = 200;
    (canales[0].x === 334 && canales[0].y === 200) ? cuenta.ok++ : cuenta.fallo++;
  } else cuenta.fallo++;
  for (let i = 1; i < canales.length; i++) {
    try { canales[i].remove(); cuenta.ok++; } catch (e) { cuenta.fallo++; }
  }
  if (orig) {
    try {
      const cont = orig.clone();
      frame.appendChild(cont);
      cont.name = 'Contorno binario';
      cont.x = 60; cont.y = 462;
      (cont.x === 60 && cont.y === 462) ? cuenta.ok++ : cuenta.fallo++;
    } catch (e) { cuenta.fallo++; }
  }
  const lbl = (chars, x, y) => {
    const t = hijo(frame, (t2) => t2.type === 'TEXT' && norm(t2.characters) === chars);
    if (t) { t.x = x + (250 - t.width) / 2; t.y = y; cuenta.ok++; } else cuenta.fallo++;
  };
  lbl('imagen original', 60, 172);
  lbl('imagen por canales', 334, 172);
  lbl('canal de contorno binario', 60, 434);
  const graf = hijo(frame, (x) => x.type === 'RECTANGLE' && norm(x.name) === 'histograma de color por canal');
  if (graf) {
    graf.x = 648; graf.y = 200;
    (graf.x === 648 && graf.y === 200) ? cuenta.ok++ : cuenta.fallo++;
  } else cuenta.fallo++;
  for (const [nombre, y] of [['slider inferior histograma', 545], ['slider superior histograma', 585]]) {
    const s = hijo(frame, (x) => norm(x.name) === nombre);
    if (s) { s.x = 648; s.y = y; cuenta.ok++; } else cuenta.fallo++;
  }
  const gardar = hijo(frame, (x) => x.type === 'RECTANGLE' && norm(x.name) === 'guardar imagen');
  if (gardar) {
    gardar.x = 648; gardar.y = 625;
    (gardar.x === 648 && gardar.y === 625) ? cuenta.ok++ : cuenta.fallo++;
  } else cuenta.fallo++;
  const gm = hijo(frame, (x) => x.type === 'RECTANGLE' && norm(x.name) === 'guardar mascara de imagen');
  if (gm) {
    gm.x = 872; gm.y = 625;
    (gm.x === 872 && gm.y === 625) ? cuenta.ok++ : cuenta.fallo++;
  } else cuenta.fallo++;
  const qf = hijo(frame, (x) => x.type === 'RECTANGLE' && norm(x.name) === 'quitar fondo');
  if (qf) {
    qf.x = 648; qf.y = 140;
    const okQ = (qf.x === 648 && qf.y === 140);
    okQ ? cuenta.ok++ : cuenta.fallo++;
    const t = hijo(frame, (x) => x.type === 'TEXT' && norm(x.characters) === 'quitar fondo de color');
    if (t) { try { centrar(t, qf); cuenta.ok++; } catch (e) { cuenta.fallo++; } }
    try {
      const gl = qf.clone();
      frame.appendChild(gl);
      gl.name = 'Limpiar mascara';
      gl.x = 872; gl.y = 140;
      (gl.x === 872 && gl.y === 140) ? cuenta.ok++ : cuenta.fallo++;
      const gt = hijo(frame, (x) => x.type === 'TEXT' && norm(x.characters) === 'quitar fondo de color');
      if (gt) {
        const g2 = gt.clone();
        frame.appendChild(g2);
        if (await ponerTexto(g2, 'Limpiar mascara', TOK.BOTON, 'Semi Bold', TOK.TEXTO)) cuenta.ok++;
        else cuenta.fallo++;
        try { centrar(g2, gl); cuenta.ok++; } catch (e) { cuenta.fallo++; }
      }
    } catch (e) { cuenta.fallo++; }
  } else cuenta.fallo++;
  const modo = hijo(frame, (x) => x.type === 'TEXT' && norm(x.characters) === 'modo actual:');
  if (modo && gardar) {
    try {
      const gr = gardar.clone();
      frame.appendChild(gr);
      gr.name = 'Selector canal';
      gr.x = 900; gr.y = 60;
      (gr.x === 900 && gr.y === 60) ? cuenta.ok++ : cuenta.fallo++;
      const tr = modo.clone();
      frame.appendChild(tr);
      if (await ponerTexto(tr, 'R', TOK.BOTON, 'Semi Bold', TOK.COLOR_CANAL.r)) cuenta.ok++;
      else cuenta.fallo++;
      try { centrar(tr, gr); cuenta.ok++; } catch (e) { cuenta.fallo++; }
    } catch (e) { cuenta.fallo++; }
    if (await ponerTexto(modo, 'Canal actual:', TOK.ETIQUETA, 'Regular', TOK.TEXTO)) cuenta.ok++;
    else cuenta.fallo++;
    modo.x = 648; modo.y = 60 + (60 - modo.height) / 2;
    cuenta.ok++;
  } else cuenta.fallo++;
}

async function layoutRecorte(frame, cuenta) {
  await tituloNuevo(frame, 'Recortar imagen', 40, cuenta);
  const img = hijo(frame, (x) => x.type === 'RECTANGLE' && norm(x.name) === 'imagen');
  if (img) {
    try { img.resize(613, 613); } catch (e) {}
    img.x = 60; img.y = 60;
    (img.x === 60 && img.y === 60) ? cuenta.ok++ : cuenta.fallo++;
  } else cuenta.fallo++;
  for (const [nombre, chars, y] of [['rectangle 2', 'Redimensionar', 200], ['guardar copia', 'Guardar copia', 284], ['sobreescribir', 'Sobreescribir', 368]]) {
    const r = hijo(frame, (x) => x.type === 'RECTANGLE' && norm(x.name) === nombre);
    if (!r) { cuenta.fallo++; continue; }
    r.x = 713; r.y = y;
    (r.x === 713 && r.y === y) ? cuenta.ok++ : cuenta.fallo++;
    const t = hijo(frame, (x) => x.type === 'TEXT' && norm(x.characters) === chars);
    if (t) { try { centrar(t, r); cuenta.ok++; } catch (e) { cuenta.fallo++; } }
  }
}

async function main() {
  const cuenta = { ok: 0, fallo: 0 };
  for (const p of figma.root.children) {
    if (p.type === 'PAGE' && p.name === 'Sync UNAL v2') { p.remove(); break; }
  }
  const pagina = figma.createPage();
  pagina.name = 'Sync UNAL v2';
  const marcos = {};
  for (const id of FRAMES) {
    const f = figma.getNodeById(id);
    if (!f || f.type !== 'FRAME') { cuenta.fallo++; continue; }
    const dup = f.clone();
    pagina.appendChild(dup);
    marcos[id] = dup;
  }
  for (const id of FRAMES) {
    if (marcos[id]) await pasada1(marcos[id], id, cuenta);
  }
  if (marcos['1:2382']) await botonesDeGrupo(marcos['1:2382'], cuenta);
  if (marcos['1:2387']) await botonesDeGrupo(marcos['1:2387'], cuenta);
  if (marcos['1:2406']) await botonesDeGrupo(marcos['1:2406'], cuenta);
  if (marcos['1:2382']) await layoutPrincipal(marcos['1:2382'], cuenta);
  if (marcos['1:2387']) await layoutCanales(marcos['1:2387'], cuenta);
  if (marcos['1:2406']) await layoutCanales(marcos['1:2406'], cuenta);
  if (marcos['11:6']) await layoutHistograma(marcos['11:6'], cuenta);
  if (marcos['23:38']) await layoutRecorte(marcos['23:38'], cuenta);
  try { figma.currentPage = pagina; } catch (e) {}
  figma.notify(`Sync UNAL v2: ${cuenta.ok} ok, ${cuenta.fallo} sin aplicar (verificados). Pagina regenerada.`);
  figma.closePlugin();
}

main();

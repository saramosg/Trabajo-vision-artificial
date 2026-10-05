import re, sys, io, ast, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RUTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "requisitos.md")
doc = open(RUTA, encoding="utf-8").read()
lineas = doc.splitlines()

fallos = []

def check(nombre, ok, detalle=""):
    print(("   OK   " if ok else "   FALLA") + f" {nombre}" + (f"  -> {detalle}" if detalle and not ok else ""))
    if not ok:
        fallos.append(nombre)

# --- A) tokens.py se importa sin NameError y todas las constantes se usan ---
print("=== A) ui/tokens.py ===")
src = re.search(r"### 5\.1 Tokens.*?```python\n(.*?)```", doc, re.S).group(1)
try:
    ns = {}
    exec(compile(src, "tokens.py", "exec"), ns)
    check("tokens.py importa sin NameError", True)
    check("ANCHO_CONTENIDO == 1160", ns.get("ANCHO_CONTENIDO") == 1160, str(ns.get("ANCHO_CONTENIDO")))
except Exception as e:
    check("tokens.py importa sin NameError", False, f"{type(e).__name__}: {e}")
    ns = {}
# Una constante está "usada" si aparece con prefijo `tokens.` o `ui.tokens.`
# en el doc. Solo se marcan huérfanas las que no aparecen de ninguna forma.
consts = set(re.findall(r"^([A-Z][A-Z0-9_]*)\s*=", src, re.M))
# Se acepta como "usada" la mención por su NOMBRE desnudo en el doc (tablas,
# comentarios) o con prefijo tokens. Se ignoran las menciones dentro del propio
# bloque de tokens.py y las claves de diccionarios (COLOR_CANAL: "R": ...).
cuerpo = re.sub(r"### 5\.1 Tokens.*?```python\n.*?```", "", doc, flags=re.S)
huerfanas = []
for c in sorted(consts):
    if re.search(rf"\b{re.escape(c)}\b", cuerpo):
        continue
    huerfanas.append(c)
check("sin constantes huerfanas", not huerfanas, ", ".join(huerfanas))

# Y al reves: ningun token citado como tokens.X debe faltar en tokens.py
# `tokens.MARCADOR_INFERIOR` se escribe a veces como `tokens.MARCADOR_*` (plural):
# se acepta ese prefijo si al menos un token que lo empieza existe.
citadas = set(re.findall(r"tokens\.([A-Z][A-Z0-9_]*)", doc))
faltan = sorted(c for c in citadas
                if c not in consts and not any(k.startswith(c) for k in consts))
check("todo token citado existe en tokens.py", not faltan, ", ".join(faltan))

# --- B) todos los bloques python del doc compilan ---
print("\n=== B) Sintaxis de todos los bloques python ===")
import textwrap
bloques = re.findall(r"```python\n(.*?)```", doc, re.S)
malos, fragmentos = [], 0
for i, b in enumerate(bloques):
    b = b.rstrip()
    if not b:
        continue
    # Un bloque que empieza indentado es un fragmento de continuación (la
    # segunda línea de un cálculo), no un módulo: se deduenta y se intenta.
    codigo = textwrap.dedent(b)
    try:
        ast.parse(codigo)
    except SyntaxError as e:
        if b[:1].isspace():
            fragmentos += 1          # fragmento legible, no un error
            continue
        malos.append(f"bloque {i+1}: linea {e.lineno} {e.msg}")
check(f"{len(bloques)} bloques python parsean", not malos, "; ".join(malos))

# El widget SIEMPRE tiene una zona valida (613x613), asi que _a_widget_rect no
# necesita dealear el borde del widget. Pero un QRect VACIO en el modo B sin
# ampliar es un caso real, y si se "arregla" con max(1, ...) sale un punto de
# 1x1 que paintEvent toma por seleccion: se vela toda la imagen y se dibuja un
# pixel de acento en vez del marco. Se comprueba en el codigo porque es una
# excepcion que debe existir explicitamente.
bloque_sel = next((b for b in bloques if "class SelectorCuadrado" in b), None)
if bloque_sel:
    src_sel = textwrap.dedent(bloque_sel)
    cuerpo_ar = src_sel[src_sel.index("def _a_widget_rect"):]
    cuerpo_ar = cuerpo_ar[:cuerpo_ar.index("\n    def ")] if "\n    def " in cuerpo_ar else cuerpo_ar
    check("_a_widget_rect propaga el QRect vacio en vez de inventar un 1x1",
          "if rect.isEmpty():" in cuerpo_ar and "return QRect()" in cuerpo_ar,
          "falta el caso vacio: el velo se pintaria sobre toda la imagen")

# --- C) core/recorte.py: escalar() conserva proporcion, aplicar_recorte() ---
print("\n=== C) core/recorte.py escalar() / aplicar_recorte() ===")
import numpy as np
import cv2
nsr = {"np": np, "cv2": cv2}
for fn in ("recortar", "escalar", "lienzo_blanco", "aplicar_recorte"):
    m = re.search(rf"(?m)^def {fn}\(.*?(?=\n(?:def |class |#|\w+:)|\Z)", doc, re.S)
    if m:
        # El doc cierra el bloque con ``` : cortar ahí para no execuar markdown.
        cuerpo = re.split(r"(?m)^```", m.group(0))[0].rstrip()
        exec(compile(cuerpo, "x", "exec"), nsr)
check("define recortar/escalar/lienzo_blanco/aplicar_recorte",
      all(f in nsr for f in ("recortar", "escalar", "lienzo_blanco", "aplicar_recorte")),
      ", ".join(k for k in ("recortar", "escalar", "lienzo_blanco", "aplicar_recorte")
                if k not in nsr))
check("NO quedan redimensionar() ni centralizar()",
      "redimensionar" not in nsr and "centralizar" not in nsr)
escalar, aplicar = nsr.get("escalar"), nsr.get("aplicar_recorte")
lienzo = nsr.get("lienzo_blanco")
if lienzo:
    # Lo que falta se rellena de BLANCO, no se estira. 300x400 -> 512x512 con
    # la foto en (106, 56) y el resto en 255.
    peq = np.random.default_rng(7).integers(0, 255, (300, 400, 3), dtype=np.uint8)
    li = lienzo(peq, 512)
    check("lienzo_blanco() lleva un 300x400 a 512x512", li.shape == (512, 512, 3),
          str(li.shape))
    check("lienzo_blanco() centra la foto SIN estirarla",
          np.array_equal(li[106:406, 56:456], peq))
    check("lienzo_blanco() rellena de BLANCO (255), no de negro ni transparente",
          np.array_equal(li[0, 0], [255, 255, 255])
          and np.array_equal(li[105, :], np.full((512, 3), 255, np.uint8)),
          str(li[0, 0]))
    check("lienzo_blanco() no toca una imagen que ya cabe",
          lienzo(np.zeros((600, 600, 3), np.uint8), 512).shape == (600, 600, 3))
if escalar:
    # REGLA 4: conserva la proporcion -> los DOS lados se escalan igual
    out = escalar(np.zeros((10, 20, 3), np.uint8), 2.0)
    check("escalar() conserva la proporcion (10x20 x2 -> 20x40)",
          out.shape == (20, 40, 3), str(out.shape))
    out = escalar(np.zeros((300, 400, 3), np.uint8), 2.0)
    check("escalar() por encima de 1 cubre los dos lados a la vez",
          min(out.shape[:2]) == 600, str(out.shape))
    # REGLA 5: factor 1.0 NO pasa por cv2 (si hiciera resize, 400x300 -> 400x300
    # pero con interpolacion, y el array ya no seria identico byte a byte)
    src = np.random.default_rng(0).integers(0, 255, (40, 60, 3), dtype=np.uint8)
    copia = escalar(src, 1.0)
    check("escalar(factor=1.0) sale BIT A BIT igual",
          np.array_equal(copia, src))
    check("escalar(factor=1.0) devuelve copia, no la misma referencia",
          copia is not src)
    try:
        escalar(src, 0.0)
        check("escalar() con factor 0 lanza ValueError", False, "no lanzo")
    except ValueError:
        check("escalar() con factor 0 lanza ValueError", True)
if aplicar:
    LADO = 512
    # MODO A: factor 1.0 -> recorte puro, sin remuestrear. Esta es la garantia
    # central del modo A: el resultado debe ser identico al corte directo.
    grande = np.random.default_rng(1).integers(0, 255, (900, 1200, 3), dtype=np.uint8)
    r = aplicar(grande, 100, 200, LADO, 1.0)
    ref = grande[200:200 + LADO, 100:100 + LADO]
    check("modo A: resultado de 512x512", r.shape == (LADO, LADO, 3), str(r.shape))
    check("modo A: BIT A BIT igual a original[y:y+512, x:x+512]",
          np.array_equal(r, ref))
    # MODO B con factor 1.0 (el default): la foto NO se amplía, se centra sobre
    # el lienzo blanco. 300x400 -> bandas de 106 arriba/abajo y 56 a los lados.
    chica = np.random.default_rng(2).integers(0, 255, (300, 400, 3), dtype=np.uint8)
    r2 = aplicar(chica, 0, 0, LADO, 1.0)
    check("modo B factor 1.0: resultado de 512x512", r2.shape == (LADO, LADO, 3),
          str(r2.shape))
    check("modo B factor 1.0: la foto sale SIN TOCAR, centrada en el lienzo",
          np.array_equal(r2[106:406, 56:456], chica))
    check("modo B factor 1.0: lo que falta es BLANCO",
          np.array_equal(r2[0, :], np.full((LADO, 3), 255, np.uint8)),
          str(r2[0, 0]))
    check("modo B factor 1.0: NO se estira para quadrarla (300x400 sigue 300x400)",
          r2[106:406, 56:456].shape == (300, 400, 3))
    # Con zoom suficiente para tapar el lienzo, el blanco desaparece y el
    # recorte sale de la imagen YA ampliada.
    r3 = aplicar(chica, 0, 0, LADO, 2.0)
    completa = cv2.resize(chica, (800, 600), interpolation=cv2.INTER_LINEAR)
    check("modo B con zoom que tapa el lienzo: sale 512, no la imagen entera",
          r3.shape == (LADO, LADO, 3) and completa.shape != (LADO, LADO, 3),
          f"salida {r3.shape}, escalada completa {completa.shape}")
    check("modo B con zoom: sale el recorte de la imagen YA ampliada",
          np.array_equal(r3, completa[0:LADO, 0:LADO]))
    check("modo B con zoom que tapa: NO queda relleno blanco en el frame",
          not (r3 == 255).all(axis=2).all())

# --- D) recorte sin Qt (regla §8.4) ---
print("\n=== D) core/ no importa Qt ===")
bloque_recorte = re.search(r"### 7\.7 Recorte.*?```python\n(.*?)```", doc, re.S).group(1)
arbol = ast.parse(textwrap.dedent(bloque_recorte))
lineas_b = textwrap.dedent(bloque_recorte).splitlines()
nombres = [n.name for n in arbol.body if isinstance(n, ast.FunctionDef)]
check("core/recorte.py define recortar/escalar/lienzo_blanco/aplicar_recorte",
      set(nombres) == {"recortar", "escalar", "lienzo_blanco", "aplicar_recorte"},
      ", ".join(nombres))
check("core/recorte.py ya NO define redimensionar ni centralizar",
      not ({"redimensionar", "centralizar"} & set(nombres)))
for nodo in arbol.body:
    if not isinstance(nodo, ast.FunctionDef):
        continue
    # Firma + cuerpo SIN el docstring (el docstring sí puede mencionar QRect).
    cuerpo = [l for i, l in enumerate(lineas_b[nodo.lineno - 1:nodo.end_lineno])
              if not (nodo.body and i == 0)]
    cuerpo = [l for l in cuerpo if not l.lstrip().startswith("#")]
    texto = "\n".join(cuerpo)
    # Los argumentos anotados como QRect también cuentan.
    usa_qt = re.search(r"QRect|QPoint|QSize|Qt\.|Signal", texto)
    check(f"{nodo.name}() sin Qt", not usa_qt, usa_qt.group(0) if usa_qt else "")

# --- E) QSS: focus y disabled coherentes con §5.1 ---
print("\n=== E) QSS estados ===")
qss = re.search(r"### 5\.6 Estilos.*?```css\n(.*?)```", doc, re.S).group(1)
for sel, nec in [("QPushButton:focus", "anillo ACENTO"), ("QPushButton#navegacion:focus", "anillo"),
                 ("QPushButton#primario:focus", "anillo")]:
    bloque = re.search(rf"{re.escape(sel)}\s*\{{([^}}]*)\}}", qss)
    check(f"{sel} existe", bool(bloque))
    if bloque:
        # #primario usa anillo NEGRO a propósito (sobre fondo ACENTO el azul sería
        # invisible); el resto usa ACENTO. Los dos deben ser un anillo de 2 px.
        anillo = "2px solid #2F6FED" in bloque.group(1) or "2px solid #000000" in bloque.group(1)
        check(f"{sel} con anillo de foco de 2px", anillo, bloque.group(1).strip()[:70])
# disabled debe usar SOLO los tres tokens de §5.1
for sel in ("QPushButton:disabled", "QPushButton#primario:disabled"):
    bloque = re.search(rf"{re.escape(sel)}\s*\{{([^}}]*)\}}", qss)
    if bloque:
        cuerpo = bloque.group(1)
        usa_tokens = all(t in cuerpo for t in ("#EFEFEF", "#9E9E9E", "#DCDCDC"))
        check(f"{sel} usa los 3 tokens disabled", usa_tokens, cuerpo.strip().replace("\n", " ")[:80])
# ningun :focus debe reutilizar el fondo del hover
for sel in ("QPushButton:focus", "QPushButton#primario:focus"):
    bloque = re.search(rf"{re.escape(sel)}\s*\{{([^}}]*)\}}", qss)
    if bloque:
        check(f"{sel} NO copia el fondo del hover", "background-color" not in bloque.group(1),
              bloque.group(1).strip())

# --- F) marcadores: misma funcion de mapeo que el handle ---
print("\n=== F) Marcadores de sliders ===")
check("existe helper x_de_marcador", "def x_de_marcador(" in doc)
check("dibujar_marcadores usa x_de_marcador", re.search(r"def dibujar_marcadores.*?x_de_marcador\(", doc, re.S) is not None)
check("el mapeo ya no usa area_grafico.width()",
      re.search(r"def dibujar_marcadores.*?area_grafico\.width\(\)", doc, re.S) is None)
# El marcador debe PREGUNTARLE a Qt la posicion del handle, no calcularla.
check("x_de_marcador consulta el handle real de Qt (subControlRect)",
      "SC_SliderHandle" in doc and "initStyleOption" in doc)
# Y no debe mutar el slider: se usa dentro de paintEvent.
# El docstring MENCIONA setValue() para explicar que no se usa: hay que mirar
# solo el codigo real, no los comentarios.
_fn = re.search(r"(?ms)^def x_de_marcador\(.*?\n(?=\S)", doc)
if _fn:
    _txt = _fn.group(0)
    if '"""' in _txt:                       # quitar el docstring: explica, no ejecuta
        _txt = _txt.split('"""', 2)[0] + _txt.rsplit('"""', 1)[-1]
check("x_de_marcador NO muta el slider (se usa en paintEvent)",
      _fn is not None and "setValue" not in _txt,
      "llama a slider.setValue() en el codigo de x_de_marcador")
check("x_de_marcador sobreescribe sliderValue en la copia",
      re.search(r"def x_de_marcador\(.*?opcion\.sliderValue = valor", doc, re.S) is not None)
check("el marcador recibe los DOS sliders (inf y sup), no uno",
      re.search(r"def dibujar_marcadores\(p: QPainter, area_grafico: QRect,\s*slider_inf: QSlider,\s*slider_sup: QSlider", doc) is not None,
      "la firma no declara slider_inf y slider_sup")

# --- G) la salida 512 es fija y no hay forma de cambiarla ---
print("\n=== G) Salida fija de 512 ===")
check("existe el token LADO_SALIDA = 512", re.search(r"LADO_SALIDA\s*=\s*512", doc) is not None)
check("512 solo aparece en el token LADO_SALIDA",
      len(re.findall(r"(?<![\w.])512(?![\w])", cuerpo)) == 0,
      "revisar: hay un 512 escrito fuera del token")
check("ya no existe LADO_ZONA_RECORTE_MIN", "LADO_ZONA_RECORTE_MIN" not in doc)
check("ya no existe LADO_MINIMO = 50", not re.search(r"LADO_MINIMO\s*=\s*50", doc))
# Acotar a la seccion 6.5: con DOTALL "### 6.5.*QSpinBox" encontraria tambien
# cualquier QSpinBox de §5.3 o §6.1, que si son validos (estan reservados).
sec65 = re.search(r"### 6\.5 .*?(?=\n## |\Z)", doc, re.S)
sec65 = sec65.group(0) if sec65 else ""
check("la pantalla de recorte NO tiene QSpinBox", "QSpinBox" not in sec65,
      "aparece en §6.5: " + ", ".join(
          l.strip()[:60] for l in sec65.splitlines() if "QSpinBox" in l))
check("la pantalla de recorte NO tiene campo numerico",
      "Lado del recorte" not in sec65)
check("el marco del widget usa el token, no un numero fijo",
      re.search(r"LADO_MARCO\s*=\s*tokens\.LADO_SALIDA", doc) is not None)
check("el widget NO tiene wheelEvent (la rueda no redimensiona)",
      re.search(r"class SelectorCuadrado.*?def wheelEvent", doc, re.S) is None)
check("SelectorCuadrado.LADO_MINIMO ya no existe",
      "LADO_MINIMO" not in doc)
check("'Redimensionar' genera la vista previa, no escribe el archivo",
      re.search(r"\*\*Redimensionar:\*\*.*?No escribe\s+ningún archivo", doc, re.S) is not None)
check("guardar escribe la vista previa tal cual",
      re.search(r"\*\*Guardar copia:\*\*.*?escribe `EstadoImagen\.vista_previa` tal cual", doc, re.S) is not None)
check("EstadoImagen tiene factor y vista_previa",
      re.search(r"factor:\s*float", doc) is not None
      and re.search(r"vista_previa:\s*np\.ndarray", doc) is not None)
check("EstadoImagen ya NO tiene lado_destino",
      not re.search(r"^\s+lado_destino:", doc, re.M))
# El doc llama a este metodo desde la ventana: si no existe en el dataclass, el
# codigo del documento no corre. Un metodo citado y no definido es un NameError
# esperando a que alguien implemente la pantalla.
check("EstadoImagen define invalidar_vista_previa() (se llama desde la ventana)",
      re.search(r"class EstadoImagen:.*?def invalidar_vista_previa\(", doc, re.S) is not None)
check("invalidar_vista_previa() limpia la vista previa y NO el recorte",
      re.search(r"def invalidar_vista_previa\(.*?self\.vista_previa = None", doc, re.S) is not None
      and re.search(r"def invalidar_vista_previa.*?self\.recorte = ", doc, re.S) is None)
# EstadoImagen.recorte guarda coordenadas del LIENZO, no de la foto escalada
check("EstadoImagen.recorte esta en pixeles del LIENZO, no de la imagen escalada",
      re.search(r"recorte: tuple\[int, int\].*?LIENZO", doc) is not None
      and "YA ESCALADA" not in doc)

# La vista previa no puede quedarse obsoleta en pantalla: la regla 9 promete que
# lo que se ve es lo que se guarda, y permitir guardar un render viejo tras mover
# el marco rompe exactamente esa promesa en silencio.
check("mover el marco o tocar el zoom INVALIDA la vista previa",
      re.search(r"\*\*Cualquier cambio invalida la vista previa\.\*\*", sec65) is not None,
      "§6.5 no dice qué pasa con la vista previa al cambiar el encuadre")
check("invalidar la vista previa vuelve a deshabilitar el guardado",
      re.search(r"vuelven a deshabilitar", sec65) is not None)

# El rango del zoom tiene que estar calculado, no implementado "a ojo": sin el,
# 4x una imagen panoramica pide cientos de MB al abrir la pantalla.
check("el rango del zoom esta calculado en el documento",
      "factor_min = 1.0" in doc
      and "LADO_AMPLIADO_MAX / max(alto, ancho)" in doc)
# --- Z) Lo que una suite de TEXTO no puede dejar pasar --------------------
# Estas comprobaciones nacen de una auditoria manual del documento. Sin ellas,
# un FAILO de redaccion puede llevar varias revisiones sin que nada se entere.

# 1) Texto que describes el diseño ANTERIOR (obligar a ampliar) contradice el
#    diseño actual (zoom opcional desde 1.0 + relleno blanco).
obsoleto = []
for patron in (r"obliga a ampliar antes de recortar",
               r"el fallo del modo B sin ampliar",
               r"aún hay que ampliar",
               r"hasta que la foto (?:tape|cubra) el marco",
               r"el factor nunca baja de"):
    if re.search(patron, doc):
        obsoleto.append(patron)
check("no queda texto del diseño viejo (obligar a ampliar)", not obsoleto,
      "; ".join(obsoleto))

# 2) Todo simbolo que el codigo del doc LLAMA tiene que estar DEFINIDO en el doc.
#    _zoom_a_factor() se uso sin definir durante dos revisiones.
llamadas = set(re.findall(r"self\.(_[a-z_]+)\(", doc))
definidas = set(re.findall(r"def (_[a-z_]+)\(", doc))
metodos = set(re.findall(r"estado\.([a-z_]+)\(", doc))
metodos_def = set(re.findall(r"def ([a-z_]+)\(", doc))
sin_definir = {m for m in metodos if m not in metodos_def
               and m not in ("original", "preprocesada", "mascara", "recorte")}
check("todo metodo llamado sobre `estado` esta definido en el doc",
      not sin_definir, ", ".join(sorted(sin_definir)))
check("no hay factor_maximo() definido y nunca invocado",
      "_factor_maximo" in llamadas or doc.count("_factor_maximo") >= 2,
      f"apariciones: {doc.count('_factor_maximo')}")

# 3) Qt Style Sheets tiene una lista CERRADA de propiedades. `opacity` NO esta:
#    una regla con opacity no falla, se ignora en silencio, y el control queda
#    con el mismo aspecto que el activo.
qss_todo = re.findall(r"```css\n(.*?)```", doc, re.S)
props_qt = []
for css in qss_todo:
    for bloque in re.findall(r"\{([^}]*)\}", css):      # solo DENTRO de las llaves
        props_qt += [p.lower() for p in re.findall(r"([-a-z]+)\s*:", bloque)]
soportadas = {
    "color", "background", "background-color", "background-image", "border",
    "border-top", "border-right", "border-bottom", "border-left", "border-color",
    "border-style", "border-width", "border-radius", "border-top-left-radius",
    "font", "font-family", "font-size", "font-weight", "font-style", "padding",
    "margin", "width", "height", "min-width", "max-width", "min-height",
    "max-height", "text-align", "text-decoration", "subcontrol-origin",
    "subcontrol-position", "left", "top", "right", "bottom", "image", "spacing",
    "outline", "qproperty", "qlineargradient", "qradialgradient", "content",
}
# Qt acepta sufijos de unidades y subcontrol: se normalizan antes de comparar.
def _norm(p):
    return re.sub(r"-(top|right|bottom|left)-(color|style|width|radius)$", "", p)

desconocidas = sorted({p for p in props_qt
                       if _norm(p) not in soportadas})
check("el QSS no usa propiedades que Qt Style Sheets NO soporta", not desconocidas,
      ", ".join(desconocidas))

# 5) Todo token DEFINIDO tiene que ser USADO, y todo token usado, definido.
#    ALTO_GRAFICO_MIN se invento al escribir GraficoHistograma y no existia;
#    RAZON_RECORTE estaba definido y nadie lo usaba. Los dos se colaron en
#    silencio. Solo se miran los tokens de DISEÑO (el bloque de §5.1): un
#    `BASE = Path(...)` dentro de main.py o un `NOMBRES_CANAL = {...}` dentro
#    de colores.py son constantes de codigo, no tokens, y no se cuentan.
#    Uso = la palabra aparece en cualquier parte del doc (codigo, tabla QSS o
#    prosa), porque un token se referencia de las tres formas.
sec51 = re.search(r"### 5\.1 Tokens.*?```python\n(.*?)```", doc, re.S)
tokens_def = set(re.findall(r"(?m)^([A-Z][A-Z0-9_]+)\s*=", sec51.group(1))) if sec51 else set()
usados = set(re.findall(r"tokens\.([A-Z][A-Z0-9_]+)", doc))
sin_usar = {t for t in tokens_def
            if len(re.findall(r"(?<![A-Z0-9_])" + t + r"(?![A-Z0-9_])", doc)) < 2}
check("todo token de §5.1 se usa ademas de definirse", not sin_usar,
      ", ".join(sorted(sin_usar)))
# MARCADOR_INFERIOR / MARCADOR_SUPERIOR existen como prefijo, no como token
check("todo token usado esta definido (o es un prefijo conocido)",
      not ({u for u in usados - tokens_def} - {"MARCADOR_"}),
      ", ".join(sorted(usados - tokens_def)))

# 6) Las reglas de §6.5 se referencian por numero: si insertas una regla, todos
#    los punteros se desplazan. Se comprueba que el 13 y el 14 son las suyas.
check("la lista de reglas de §6.5 no tiene numeros duplicados",
      (lambda ns: len(ns) == len(set(ns)))(
          [int(n) for n in re.findall(r"(?m)^(\d+)\. \*\*", sec65)]))
check("la regla 13 es la del arrastre y la 14 la del QRect vacío",
      re.search(r"(?m)^13\. \*\*Mover el marco NO reconstruye", sec65) is not None
      and re.search(r"(?m)^14\. \*\*Un `QRect` vacío", sec65) is not None)
check("no queda el '12.bis' de una numeracion provisional",
      "12.bis" not in doc)

# 7) Simbolos que §0 exige poder instanciar, y que §7 llama: tienen que existir.
for simbolo, bloque in (("GraficoHistograma", "class GraficoHistograma"),
                        ("segmentar", "def segmentar("),
                        ("_zoom_a_factor", "def _zoom_a_factor(")):
    check(f"{simbolo} esta definido en el documento (no solo citado)",
          re.search(re.escape(bloque), doc) is not None)

# 8) Si widgets.py gana una clase, el plan de §0 tiene que mencionarla: es lo
#    que dice que hay que instanciarla. Un widget implementado y no planificado
#    no se prueba. Con limites de PALABRA: "Histograma" como subcadena ya sale
#    dentro de "GraficoHistograma" y el check no morderia.
plan = doc.split("### 5.2")[0]
# \s* delante: un bloque de codigo anidado en una lista numerada va indentado
# (el de ProporcionImagen, dentro del punto 3 de §5.5). Con ^class se pasaba
# por alto esa clase y luego §4.1 parecia citar un widget inexistente.
clases_widgets = sorted(set(re.findall(r"(?m)^\s*class (\w+)\(", doc)))
no_planificadas = [c for c in clases_widgets
                   if not re.search(r"(?<![A-Za-z])" + c + r"(?![A-Za-z])", plan)]
check("§0 planifica todas las clases que se declaran en el documento",
      not no_planificadas, ", ".join(no_planificadas))

# 4) Aritmetica: los Mpx citados tienen que cuadrar con los lados citados.
for ancho, alto, factor, mpx in re.findall(
        r"(\d+)x(\d+) (?:dar[ií]a|daria)\s+(\d+) px de lado y (\d+) del otro,\s*"
        r"([\d,]+) Mpx", doc):
    lado_a, lado_b = int(ancho) * int(factor), int(alto) * int(factor)
    real = lado_a * lado_b / 1e6
    check(f"la cuenta de {ancho}x{alto} a {factor}x esta bien",
          abs(real - float(mpx.replace(",", "."))) < 0.2,
          f"-> {lado_a}x{lado_b} = {real:.1f} Mpx, el doc dice {mpx}")
check("el rango del zoom nunca queda invertido (max(1.0, ...))",
      "max(1.0, min(4.0, LADO_AMPLIADO_MAX / max(alto, ancho)))" in doc)
check("el documento explica por que 1.0 sigue siendo valido por encima de 4096",
      re.search(r"1\.0 sigue\s+siendo un factor v", doc) is not None)
check("el zoom arranca en 1.0 (ampliar es opcion del usuario, no obligatorio)",
      re.search(r"\*\*1\.0\*\*, no el factor de llenado", sec65) is not None)
check("existe el token LADO_AMPLIADO_MAX",
      re.search(r"LADO_AMPLIADO_MAX\s*=\s*\d+", doc) is not None)

# Lo que falta se rellena de BLANCO, no se estira ni se amplia solo.
check("existe lienzo_blanco() en core/recorte.py",
      re.search(r"def lienzo_blanco\(", doc) is not None)
check("el relleno es BLANCO (255), no transparente ni negro",
      re.search(r"def lienzo_blanco.*?np\.full\(.*?255", doc, re.S) is not None)
check("se explica por que el relleno es blanco y no alfa 0",
      "transparente" in doc and "255" in doc)
check("aplicar_recorte rellena ANTES de recortar (regla 3 de 7.7)",
      re.search(r"def aplicar_recorte.*?lienzo_blanco\(imagen, lado\).*?recortar\(",
                doc, re.S) is not None)
check("la regla 'lienzo_blanco va antes del recorte' esta escrita",
      "va antes del recorte" in doc or "va ANTES del recorte" in doc)
check("ya no se obliga a llenar el marco (el texto viejo se elimino)",
      "el factor nunca baja de" not in doc
      and "512 / min(alto, ancho), así que no se ven huecos" not in doc)
check("centralizar() vuelve como lienzo_blanco() y el doc explica el cambio",
      re.search(r"`centralizar\(imagen, lado_destino\)`.*?\*\*Reescrita\*\*", doc, re.S) is not None)

# La ventana es quien arma el lienzo. Si el doc no lo muestra, el contrato mas
# importante del modo B queda solo en prosa: nadie puede implementarlo sin
# inventarse el reparto entre ventana y widget.
vent = re.search(r"class VentanaRecorte:.*?(?=\n```)", doc, re.S)
check("el doc implementa ui/ventana_recorte.py (quien arma el lienzo)", bool(vent))
if vent:
    cuerpo = vent.group(0)
    check("la ventana escala con escalar() y lienza con lienzo_blanco()",
          "escalar(imagen, factor)" in cuerpo and "lienzo_blanco(imagen, tokens.LADO_SALIDA)" in cuerpo)
    check("la ventana NUNCA le pasa original al widget (lo que se ve es el lienzo)",
          re.search(r"set_imagen\(self\.original\)", cuerpo) is None
          and "self._pixmap_lienzo()" in cuerpo)
    check("la ventana calcula el tope del zoom con max(1.0, ...) (nunca invertido)",
          re.search(r"max\(1\.0, min\(4\.0, tokens\.LADO_AMPLIADO_MAX", cuerpo) is not None)
    check("mover el marco o cambiar el zoom invalida la vista previa (regla 12)",
          re.search(r"def _al_mover_marco.*?invalidar_vista_previa", cuerpo, re.S) is not None)
    # El lienzo depende SOLO del factor. Rehacerlo en cada arrastre llama a
    # escalar() sobre la imagen entera por pixel de raton: un arrastre lento.
    check("mover el marco NO reconstruye el lienzo (solo el zoom lo hace)",
          re.search(r"def _al_mover_marco.*?(?=\n    def )", cuerpo, re.S) is not None
          and "set_imagen" not in re.search(r"def _al_mover_marco.*?(?=\n    def )",
                                            cuerpo, re.S).group(0))
    check("cambiar el zoom SI reconstruye el lienzo y recentra el marco",
          re.search(r"def _al_cambiar_zoom.*?set_imagen\(self\._pixmap_lienzo\(\)\)",
                    cuerpo, re.S) is not None)
    check("la ventana trata el QRect vacio como None, no como (0,0) (regla 14)",
          re.search(r"def _al_recibir_recorte.*?if rect is None or rect\.isEmpty\(\):.*?"
                    r"self\.estado\.recorte = None", cuerpo, re.S) is not None)
    check("la ventana no recalcula el relleno a mano (delega en lienzo_blanco)",
          "np.full" not in cuerpo)

# El porque de la regla 13 vive en §6.5, no en el codigo: se comprueba aparte.
check("el doc explica por que arrastrar no reconstruye el lienzo (regla 13)",
      re.search(r"13\. \*\*Mover el marco NO reconstruye el lienzo", doc) is not None)

# aplicar_recorte promete 512 o error; con el relleno casi nunca se dispara, pero
# un 450x450 colado en un dataset de 512 es justo lo que el modulo evita.
check("aplicar_recorte lanza si el recorte no sale de `lado`",
      re.search(r"def aplicar_recorte.*?raise ValueError", doc, re.S) is not None)
check("la regla de no acortar en silencio esta escrita en §7.7",
      "no acorta en silencio" in doc)
# set_imagen() emite un QRect VACIO cuando la imagen sigue siendo menor que 512.
# Si quien lo recibe no lo distingue de un (0,0) real, mete estado.recorte=(0,0)
# y "Redimensionar" llama a aplicar_recorte(0,0) -> ValueError del guard de §7.7.
check("un QRect vacio significa 'sin seleccion' (regla 12)",
      re.search(r"\*\*Un `QRect` vacío significa", sec65) is not None)
check("con QRect vacio NO se pone estado.recorte = (0,0)",
      re.search(r"dejar `EstadoImagen\.recorte` en `None`", sec65) is not None)
check("con QRect vacio se DESHABILITA 'Redimensionar'",
      re.search(r"\*\*deshabilitar\*\* \"Redimensionar\"", sec65) is not None
      or re.search(r'"Redimensionar" se habilita solo cuando hay marco', sec65) is not None)

# --- H) numeracion de listas md ---
print("\n=== H) Listas Markdown ===")
dups = []
for i in range(len(lineas) - 1):
    m1 = re.match(r"^(\d+)\.\s", lineas[i])
    m2 = re.match(r"^(\d+)\.\s", lineas[i + 1])
    if m1 and m2 and m1.group(1) == m2.group(1) and "```" not in lineas[i]:
        dups.append(f"L{i+1}/{i+2} ambos '{m1.group(1)}.'")
check("sin numeracion duplicada", not dups, "; ".join(dups))

# 9) Lo que §10 empaqueta tiene que existir en el arbol de §4.1. §10.3 marca
#    main.spec como "recomendado": si el arbol no lo lista, quien implementa
#    sigue §4.1, llega a §10 y descubre un archivo que nunca creaste.
#    Todo con limites de PALABRA: "main.spec" como subcadena sigue apareciendo
#    dentro de "main.specX", y un check que no puede fallar no verifica nada.
def en_arbol(nombre, texto):
    return re.search(r"(?<![A-Za-z0-9_.])" + re.escape(nombre) + r"(?![A-Za-z0-9_])",
                     texto) is not None

arbol = re.search(r"### 4\.1 Archivos.*?```\n(.*?)```", doc, re.S).group(1)
empaquetados = {f.split("/")[0] for f in re.findall(r"--add-data \"([^;\"]+)", doc)}
empaquetados |= set(re.findall(r"\('([^']+)',\s*'[^']+'\)", doc))
for f in sorted(empaquetados):
    check(f"§10 empaqueta '{f}' y §4.1 lo declara", en_arbol(f, arbol))
check("main.spec está en el árbol de §4.1 (es la vía recomendada de §10.3)",
      en_arbol("main.spec", arbol))
faltan = [c for c in clases_widgets if not en_arbol(c, arbol)]
check("§4.1 lista los widgets que §0 declara", not faltan, ", ".join(faltan))
# Y al reves: si §4.1 nombra un widget, tiene que existir en el documento.
nombrados = set(re.findall(r"(?<![A-Za-z])(ProporcionImagen|SelectorCuadrado|"
                           r"GraficoHistograma|OverlayMarcadores|Histograma)"
                           r"(?![A-Za-z])", arbol))
check("§4.1 no nombra widgets que el documento no define",
      not (nombrados - set(clases_widgets)),
      ", ".join(sorted(nombrados - set(clases_widgets))))

print("\n" + "=" * 62)
print(f"RESULTADO: {len(fallos)} fallo(s)" + (": " + ", ".join(fallos) if fallos else " - todo verificado"))
print("=" * 62)

# Sin esto el script miente: imprimir "1 fallo" y salir con 0 hace que un
# pipeline (o el propio suite.py) lo tome por bueno. Un verificador que no
# puede fallar no verifica nada.
sys.exit(1 if fallos else 0)

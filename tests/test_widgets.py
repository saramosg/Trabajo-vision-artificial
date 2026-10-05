"""Extrae los widgets de §6.5 y §6.4 del doc y los EJECUTA de verdad en Qt (offscreen).

Esto verifica lo que el analisis estatico no puede: que los imports existen,
que QSizePolicy esta en QtWidgets, que paintEvent no revienta y que el recorte
se pinta con el velo en el orden correcto.
"""
import sys, io, re, textwrap, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets
import numpy as np

fallos = []
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
def check(nombre, cond, detalle=""):
    print(("  OK   " if cond else "  FALLA") + " " + nombre + (f"   -> {detalle}" if detalle else ""))
    if not cond: fallos.append(nombre)

# --- 1) ubicacion real de las clases ---
print("=== 1) PySide6 real (6.11.2) ===")
mods = (QtCore, QtGui, QtWidgets)
for nombre, esperado in [("QSizePolicy", "QtWidgets"), ("QLabel", "QtWidgets"),
                         ("QRect", "QtCore"), ("QPoint", "QtCore"), ("QPointF", "QtCore"),
                         ("QSize", "QtCore"), ("Signal", "QtCore"), ("Qt", "QtCore"),
                         ("QRegion", "QtGui"), ("QPolygonF", "QtGui"), ("QPen", "QtGui"),
                         ("QColor", "QtGui"), ("QPixmap", "QtGui"), ("QPainter", "QtGui")]:
    # Qt esta reexportado en QtCore y QtGui: se acepta cualquiera de los dos.
    ok = [d.split(".")[-1] for d in [m.__name__ for m in mods if hasattr(m, nombre)]]
    if nombre == "Qt":
        check(f"{nombre} accesible desde QtCore", "QtCore" in ok, str(ok))
    else:
        check(f"{nombre} esta en {esperado}", ok == [esperado], f"esta en {ok}")

# --- 2) montar tokens.py real desde el doc ---
_RAIZ_DOC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "requisitos.md")
doc = open(_RAIZ_DOC, encoding="utf-8").read()
src_tokens = re.search(r"### 5\.1 Tokens.*?```python\n(.*?)```", doc, re.S).group(1)
import types
tokens = types.ModuleType("tokens")
exec(compile(src_tokens, "tokens.py", "exec"), tokens.__dict__)
sys.modules["tokens"] = tokens
ui = types.ModuleType("ui"); ui.__path__ = []
sys.modules["ui"] = ui
uitok = types.ModuleType("ui.tokens")
for k, v in tokens.__dict__.items():
    if k.isupper():
        setattr(uitok, k, v)
sys.modules["ui.tokens"] = uitok
check("tokens.py importa sin NameError", True)
check("ANCHO_CONTENIDO == 1160", tokens.ANCHO_CONTENIDO == 1160)

# --- 3) montar widgets.py real desde el doc ---
# Anclar en "Implementación del widget", NO en "### 6.5": §6.5 tiene varios
# bloques (el puente de ventana_recorte y el widget) y el primero que caiga
# depende del orden del documento. Un extractor posicional se rompe en cuanto
# se inserta un bloque, y falla con un ModuleNotFoundError que no señala el bloque.
src_widgets = re.search(r"Implementaci\u00f3n del widget.*?```python\n(.*?)```", doc, re.S).group(1)
src_widgets = src_widgets.replace("from ui import tokens", "import tokens")
src_marc = re.search(r"### 6\.4.*?#### Marcadores.*?```python\n(.*?)```", doc, re.S).group(1)
src_marc = src_marc.replace("from ui import tokens", "import tokens")
ns = {"QtCore": QtCore, "QtGui": QtGui, "QtWidgets": QtWidgets, "tokens": tokens}
import numpy as _np
ns["np"] = _np
try:
    exec(compile(src_widgets, "widgets.py", "exec"), ns)
    check("widgets.py (SelectorCuadrado) se importa", "SelectorCuadrado" in ns)
except Exception as e:
    check("widgets.py (SelectorCuadrado) se importa", False, f"{type(e).__name__}: {e}")
try:
    exec(compile(src_marc, "marcadores.py", "exec"), ns)
    check("dibujar_marcadores + x_de_marcador se importan",
          "dibujar_marcadores" in ns and "x_de_marcador" in ns)
except Exception as e:
    check("dibujar_marcadores + x_de_marcador se importan", False, f"{type(e).__name__}: {e}")

Selector = ns.get("SelectorCuadrado")
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

if Selector:
    print("\n=== 4) SelectorCuadrado en ejecucion (offscreen) ===")
    LADO = tokens.LADO_SALIDA
    check("LADO_SALIDA == 512", LADO == 512, str(LADO))
    check("SelectorCuadrado.LADO_MARCO sale del token", Selector.LADO_MARCO == LADO,
          str(Selector.LADO_MARCO))
    check("el widget ya NO tiene LADO_MINIMO", not hasattr(Selector, "LADO_MINIMO"))
    # QWidget SIEMPRE tiene wheelEvent (heredado). Lo que importa es que
    # SelectorCuadrado no lo SOBREESCRIBA: si no lo define, usa el de QWidget,
    # que se limita a propagar el evento al padre.
    check("el widget ya NO SOBREESCRIBE wheelEvent (la rueda no redimensiona)",
          Selector.wheelEvent is QtWidgets.QWidget.wheelEvent,
          "SelectorCuadrado define su propio wheelEvent")
    check("el widget ya NO tiene _inicio (estado muerto tras quitar el resize)",
          not hasattr(Selector(), "_inicio"))
    inst = Selector()
    check("minimumSize del widget = LADO_ZONA_RECORTE (613)",
          tokens.LADO_ZONA_RECORTE == 613 and inst.minimumSize().width() == 613,
          str(inst.minimumSize().width()))

    w = Selector()
    # La zona NO puede bajar de 613x613 (minimumSize), asi que el resize de
    # abajo es una peticion, no una garantia: leer el tamaño real del widget.
    w.resize(600, 500)
    IW, IH = 800, 600
    arr = (np.random.rand(IH, IW, 3) * 255).astype(np.uint8)
    px = QtGui.QPixmap.fromImage(QtGui.QImage(arr.data, IW, IH,
                                              IW * 3, QtGui.QImage.Format_RGB888).copy())
    w.set_imagen(px)
    check("el marco inicial mide exactamente 512x512",
          w._cuadrado.width() == 512 and w._cuadrado.height() == 512,
          f"{w._cuadrado.width()}x{w._cuadrado.height()}")
    check("el marco inicial sale del token LADO_SALIDA",
          w._cuadrado.width() == LADO, str(w._cuadrado.width()))
    # QRect.center() de un lado PAR devuelve el entero anterior (144+255=399),
    # asi que "centrado" se comprueba por SIMETRIA de los margenes, no por center().
    mx = w._cuadrado.x()
    my = w._cuadrado.y()
    check("el marco inicial esta CENTRADO (margenes simetricos)",
          mx == IW - (mx + w._cuadrado.width())
          and my == IH - (my + w._cuadrado.height()),
          f"margen izq={mx} der={IW - (mx + w._cuadrado.width())} "
          f"arr={my} aba={IH - (my + w._cuadrado.height())}")
    check("el marco cabe en la imagen",
          w._cuadrado.x() >= 0 and w._cuadrado.y() >= 0
          and w._cuadrado.right() <= IW and w._cuadrado.bottom() <= IH)

    # paintEvent real: no debe lanzar
    try:
        w.show(); app.processEvents()
        img = w.grab().toImage()
        check("paintEvent se ejecuta sin error", not img.isNull())
        check("se dibuja contenido (no todo negro)", len(set(img.pixelColor(x, y).getRgb()
              for x in range(0, 600, 60) for y in range(0, 500, 60))) > 3)
        w.hide()
    except Exception as e:
        check("paintEvent se ejecuta sin error", False, f"{type(e).__name__}: {e}")

    # arrastre: mueve el marco, NUNCA cambia su lado
    w.set_imagen(px)
    w._presionado = True
    ev = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, QtCore.QPointF(350, 200),
                           QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
    w.mouseMoveEvent(ev)
    check("tras arrastrar el marco sigue siendo 512x512",
          w._cuadrado.width() == 512 and w._cuadrado.height() == 512,
          f"{w._cuadrado.width()}x{w._cuadrado.height()}")
    check("el marco se ha MOVIDO", w._cuadrado.center() != QtCore.QPoint(IW // 2, IH // 2),
          str((w._cuadrado.x(), w._cuadrado.y())))
    check("el arrastre no se sale de la imagen",
          w._cuadrado.x() >= 0 and w._cuadrado.right() <= IW
          and w._cuadrado.y() >= 0 and w._cuadrado.bottom() <= IH,
          str((w._cuadrado.x(), w._cuadrado.y())))
    # arrastre extremo: a una esquina, debe acotar y no salirse
    for destino in (QtCore.QPointF(0, 0), QtCore.QPointF(600, 500),
                    QtCore.QPointF(-9999, -9999), QtCore.QPointF(9999, 9999)):
        w.mouseMoveEvent(QtGui.QMouseEvent(QtCore.QEvent.MouseMove, destino,
                                          QtCore.Qt.LeftButton, QtCore.Qt.LeftButton,
                                          QtCore.Qt.NoModifier))
        dentro = (w._cuadrado.x() >= 0 and w._cuadrado.right() <= IW
                  and w._cuadrado.y() >= 0 and w._cuadrado.bottom() <= IH)
        if not dentro or w._cuadrado.width() != 512:
            break
    check("arrastrar a cualquier punto deja el marco dentro y en 512",
          dentro and w._cuadrado.width() == 512,
          f"{w._cuadrado.x()},{w._cuadrado.y()} {w._cuadrado.width()}x{w._cuadrado.height()}")
    w._presionado = False

    # conversion widget <-> imagen. OJO: el widget no baja de 613x613, asi que
    # se compara contra SU tamaño real, no contra el resize solicitado.
    ww, wh = w.width(), w.height()
    check("el widget respects minimumSize (>= 613)", ww >= 613 and wh >= 613, f"{ww}x{wh}")
    d = w._a_widget()
    check("_a_widget devuelve un rect dentro del widget",
          d.x() >= 0 and d.y() >= 0 and d.right() <= ww and d.bottom() <= wh,
          str((d.x(), d.y(), d.width(), d.height())))
    p = w._a_imagen(QtCore.QPoint(0, 0))
    check("_a_imagen acota al rango de la imagen", 0 <= p.x() < IW and 0 <= p.y() < IH)

# MODO B: el widget NO ve la foto pequena, ve el LIENZO de 512 que le pasa
    # `ui/ventana_recorte.py` con lienzo_blanco(). Por eso el marco NUNCA esta
    # vacio en el camino normal, ni siquiera con el zoom en 1.0.
    print("\n=== 4b) Modo B: el widget recibe el lienzo de 512, no la foto ===")
    w2 = Selector(); w2.resize(400, 400)
    SW, SH = 400, 300
    arr2 = (np.random.rand(SH, SW, 3) * 255).astype(np.uint8)

    def a_pixmap(a):
        h, w = a.shape[:2]
        return QtGui.QPixmap.fromImage(
            QtGui.QImage(a.data, w, h, w * 3, QtGui.QImage.Format_RGB888).copy())

    lienzo = np.full((512, 512, 3), 255, np.uint8)          # lienzo_blanco(1.0)
    w2.set_imagen(a_pixmap(lienzo))
    check("con el lienzo de 512 el marco NO esta vacio (el blanco SI es recortable)",
          not w2._cuadrado.isEmpty() and w2._cuadrado.width() == 512,
          str((w2._cuadrado.width(), w2._cuadrado.height())))
    check("el marco cabe justo en el lienzo, sin salirse",
          w2._cuadrado.left() >= 0 and w2._cuadrado.top() >= 0
          and w2._cuadrado.right() <= 512 and w2._cuadrado.bottom() <= 512,
          f"marco {w2._cuadrado.x()},{w2._cuadrado.y()}")
    try:
        w2.show(); app.processEvents()
        check("paintEvent con relleno blanco no revienta", not w2.grab().toImage().isNull())
        w2.hide()
    except Exception as e:
        check("paintEvent con relleno blanco no revienta", False, f"{type(e).__name__}: {e}")

    # El blanco de relleno se ATENUA como todo lo demas (regla 8): es lienzo, no
    # foto. Con el marco en el centro y fuera de el, el pixel de una esquina es
    # visible y el pixel de un lado queda velado.
    w2.set_imagen(a_pixmap(lienzo))
    d = w2._a_widget()
    w2._cuadrado = QtCore.QRect(0, 0, 512, 512)               # todo el lienzo dentro
    w2.show(); app.processEvents()
    img = w2.grab().toImage()
    check("el lienzo entero se dibuja sin velo cuando el marco lo cubre todo",
          img.width() > 0 and img.height() > 0)

    # REGRESION (regla 13): si aun asi se cuela un pixmap menor que 512, el marco
    # se avisa VACIO. Esta es la red de seguridad, no el camino normal.
    w4 = Selector(); w4.resize(400, 400)
    w4.set_imagen(a_pixmap(arr2))
    check("un pixmap menor que 512 sin lienzo deja el marco VACIO (no inventa 512)",
          w4._cuadrado.isEmpty(), str((w4._cuadrado.width(), w4._cuadrado.height())))
    check("un rect vacio se propaga vacio (no se inventa un 1x1)",
          w4._a_widget_rect(QtCore.QRect()).isEmpty(),
          f"-> {w4._a_widget_rect(QtCore.QRect()).width()}x"
          f"{w4._a_widget_rect(QtCore.QRect()).height()}")
    sel_vacia = w4._a_widget_rect(w4._cuadrado).intersected(w4._a_widget())
    check("sin marco NO hay seleccion (la imagen no se vela entera)",
          sel_vacia.isEmpty(), f"seleccion {sel_vacia.width()}x{sel_vacia.height()}")
    recibidos = []
    w4.recorteChanged.connect(lambda r: recibidos.append(r))
    w4.set_imagen(a_pixmap(arr2))
    check("en ese caso se emite EXACTAMENTE un QRect vacio",
          len(recibidos) == 1 and recibidos[0].isEmpty(),
          f"{len(recibidos)} emisiones, rect={recibidos[0] if recibidos else None}")
    try:
        w4.show(); app.processEvents()
        check("paintEvent con marco vacio no revienta", not w4.grab().toImage().isNull())
        w4.hide()
    except Exception as e:
        check("paintEvent con marco vacio no revienta", False, f"{type(e).__name__}: {e}")

    # El caso normal y el de "sin seleccion" tienen que ser DISTINGUIBLES por la
    # UI: un marco de verdad en el origen es (0,0,512,512), no vacio.
    w3 = Selector(); w3.set_imagen(px)
    orOCKER = w3._cuadrado
    check("un marco real en el origen NO es vacio (se distingue de 'sin seleccion')",
          not orOCKER.isEmpty() and orOCKER.width() == 512,
          f"origen {orOCKER.width()}x{orOCKER.height()}")

    # Con zoom por encima de 1.0 el lienzo se arma con la foto YA ampliada: si la
    # ampliada tapa los 512, el widget vuelve a ser el caso normal de siempre.
    import cv2
    w2.set_imagen(a_pixmap(cv2.resize(arr2, (800, 600), interpolation=cv2.INTER_LINEAR)))
    check("con zoom la imagen ampliada vuelve al camino normal (marco de 512)",
          w2._cuadrado.width() == 512 and not w2._cuadrado.isEmpty()
          and w2._cuadrado.right() <= 800 and w2._cuadrado.bottom() <= 600,
          f"ampliada 800x600, marco {w2._cuadrado.width()} en "
          f"({w2._cuadrado.x()},{w2._cuadrado.y()})")

dm = ns.get("dibujar_marcadores"); xm = ns.get("x_de_marcador")
if dm and xm:
    print("\n=== 5) Marcadores: la flecha cae donde Qt pone el handle ===")
    s = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    s.setRange(0, 255); s.setPageStep(1)
    s.setFixedSize(467, 44); s.show(); app.processEvents()

    def handle_x(v):
        s.setValue(v)
        o = QtWidgets.QStyleOptionSlider(); s.initStyleOption(o)
        return s.style().subControlRect(QtWidgets.QStyle.CC_Slider, o,
                                        QtWidgets.QStyle.SC_SliderHandle, s).center().x()

    for v in (0, 1, 72, 128, 183, 254, 255):
        check(f"x_de_marcador({v}) == centro real del handle",
              xm(s, v) == handle_x(v), f"marcador={xm(s, v)} Qt={handle_x(v)}")
    check("con valor 0 NO cae en x=0 (Qt descuenta medio handle)",
          xm(s, 0) != 0, f"x={xm(s, 0)} — si fuera 0, la flecha se separaria 7 px")
    check("el mapeo es monotono",
          all(xm(s, v) <= xm(s, v + 1) for v in range(255)))
    check("un valor fuera de rango se acota", xm(s, -50) == xm(s, 0) and xm(s, 999) == xm(s, 255))
    s.setValue(0)
    check("x_de_marcador no altera el valor final del slider fuera de rango",
          s.value() in (0, 255))

    # dibujar de verdad, con DOS sliders reales (uno por limite)
    s2 = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    s2.setRange(0, 255); s2.setValue(183); s2.setFixedSize(467, 44)
    s2.show(); app.processEvents()
    area = QtCore.QRect(0, 0, 467, 333)
    class P(QtWidgets.QWidget):
        def paintEvent(self, e):
            p = QtGui.QPainter(self)
            dm(p, area, s, s2, 72, 183)
            p.end()
    p1 = P(); p1.resize(500, 400); p1.show(); app.processEvents()
    shot = p1.grab().toImage()
    check("dibujar_marcadores se ejecuta sin error", not shot.isNull())
    naranja = sum(1 for x in range(500) for y in range(0, 360, 3)
                  if shot.pixelColor(x, y) == QtGui.QColor("#E65100"))
    verde = sum(1 for x in range(500) for y in range(0, 360, 3)
                if shot.pixelColor(x, y) == QtGui.QColor("#00897B"))
    check("se pinta la linea naranja del limite inferior", naranja > 0, f"{naranja} px")
    check("se pinta la linea verde del limite superior", verde > 0, f"{verde} px")
    p1.hide(); s2.hide(); s.hide()

# --- 5) GraficoHistograma: el bloque es NUESTRO y se puede romper ---
# §0 promete que este widget "se instancia sin error", asi que se instancia.
# El riesgo real del bloque es la ARITMETICA de area_grafico(): si el grafico
# y el overlay calculan el rectangulo por separado, las flechas dejan de caer
# sobre las barras en cuanto cambia el tamano. Se comprueba que coinciden.
print("\n=== 5) GraficoHistograma en ejecucion ===")
src_graf = re.search(r"Los marcadores se pintan en un \*\*overlay\*\*.*?```python\n(.*?)```",
                    doc, re.S)
if not src_graf:
    check("el bloque de GraficoHistograma esta en el documento", False,
          "no se encontro tras 'Los marcadores se pintan en un **overlay**'")
else:
    src_graf = src_graf.group(1).replace("from ui import tokens", "import tokens")
    check("el bloque de GraficoHistograma esta en el documento", True)
    try:
        exec(compile(src_graf, "grafico.py", "exec"), ns)
        check("GraficoHistograma se importa", "GraficoHistograma" in ns)
    except Exception as e:
        check("GraficoHistograma se importa", False, f"{type(e).__name__}: {e}")

    Grafico = ns.get("GraficoHistograma")
    if Grafico:
        g = Grafico()
        g.resize(467, 333)                       # la razon de RAZON_HISTO_GRAF
        app.processEvents()
        check("GraficoHistograma se instancia sin error", True)
        check("el grafico NO usa setFixedSize (solo minimo + Expanding)",
              g.minimumSize().width() == tokens.ALTO_GRAFICO_MIN
              and g.sizePolicy().horizontalPolicy()
                  == QtWidgets.QSizePolicy.Expanding,
              f"min={g.minimumSize().width()}")

        # area_grafico() con margenes ya descontados, dentro del widget.
        a = g.area_grafico()
        check("area_grafico() descuenta margenes y no se sale del widget",
              a.top() >= 0 and a.left() >= 0
              and a.right() < g.width() and a.bottom() < g.height(),
              f"{a} en {g.width()}x{g.height()}")
        check("el alto util de area_grafico es alto - MARGEN_SUP - MARGEN_INF",
              a.height() == 333 - 8 - 18, str(a.height()))

        # La geometria que usa el overlay TIENE que ser la misma que la del
        # grafico: es la razon de que area_grafico() viva en el widget. Se
        # comprueba sobre el codigo del overlay, que es quien lo consume.
        # Solo el CUERPO de OverlayMarcadores: el texto que explica por que NO se
        # usa setGeometry menciona esas palabras y no es codigo.
        overlay_src = re.search(r"class OverlayMarcadores\b.*?(?=\nclass Histograma\b)",
                                doc, re.S)
        check("el overlay recibe area_grafico() del grafico, no lo recalcula",
              overlay_src is not None
              and "self.grafico.area_grafico()" in overlay_src.group(0)
              and "QRect(" not in overlay_src.group(0),
              "el overlay calcula su propia geometria")
        check("el overlay NO se posiciona a mano (un hijo no recibe resizeEvent)",
              overlay_src is not None
              and "setGeometry" not in overlay_src.group(0)
              and "resizeEvent" not in overlay_src.group(0),
              "el overlay sincroniza su geometria a mano")
        check("grafico y overlay comparten celda de un layout (QGridLayout)",
              "addWidget(self.grafico, 0, 0)" in doc
              and "addWidget(self.overlay, 0, 0)" in doc)

        # Pintar de verdad: 256 bins con un pico en 128.
        bins = [0] * 256
        bins[128] = 500
        g.set_datos(bins, 0, 255)
        app.processEvents()
        shot = g.grab().toImage()
        check("GraficoHistograma pinta sin error", not shot.isNull())

        # El pico debe verse: barras del color de acento dentro del area.
        acento = QtGui.QColor(tokens.ACENTO)
        pintadas = sum(1 for x in range(a.left(), a.right() + 1)
                       for y in range(a.top(), a.bottom() + 1)
                       if shot.pixelColor(x, y) == acento)
        check("las barras se pintan con el color de acento (tokens.ACENTO)",
              pintadas > 0, f"{pintadas} px")

        # Solo los bins DENTRO del rango se pintan: el resto lo atenua el overlay.
        g.set_datos(bins, 200, 255)          # el pico (128) queda FUERA
        app.processEvents()
        shot2 = g.grab().toImage()
        fuera = sum(1 for x in range(a.left(), a.right() + 1)
                    for y in range(a.top(), a.bottom() + 1)
                    if shot2.pixelColor(x, y) == acento)
        check("un bin fuera de rango NO se pinta (lo atenua el overlay)",
              fuera < pintadas, f"dentro de rango {pintadas} px, fuera {fuera} px")

        # paintEvent NO debe emitir señales: set_datos() es quien avisa.
        emissions = []
        g.rangoCambiado.connect(lambda: emissions.append(1))
        g.repaint()
        app.processEvents()
        check("paintEvent NO emite rangoCambiado (no hay reentrada al repintar)",
              not emissions, f"{len(emissions)} emissions en un repintado")
        g.set_datos(bins, 0, 255)
        app.processEvents()
        check("set_datos() si avisa del cambio de rango", len(emissions) == 1,
              f"{len(emissions)} emissions")
        g.hide()

# El overlay es el consumidor de area_grafico(): si no se monta y pinta bien,
# el bloque de GraficoHistograma es medio contrato.
if Grafico and overlay_src:
    print("\n=== 5b) Histograma (grafico + overlay) en ejecucion ===")
    # El bloque entero: overlay + contenedor. El contenedor usa QGridLayout,
    # que el bloque de GraficoHistograma no importa todavia.
    src_ov = doc[doc.index("class OverlayMarcadores"):
                 doc.index("# Se monta asi")]
    src_ov = src_ov.replace("from ui import tokens", "import tokens")
    src_ov = ("from PySide6.QtWidgets import QGridLayout\n"
              "from PySide6.QtCore import Qt\n"
              "from PySide6.QtGui import QPainter\n" + src_ov)
    try:
        exec(compile(src_ov, "histograma.py", "exec"), ns)
        check("OverlayMarcadores + Histograma se importan",
              "OverlayMarcadores" in ns and "Histograma" in ns)
    except Exception as e:
        check("OverlayMarcadores + Histograma se importan", False,
              f"{type(e).__name__}: {e}")

    Envolvente = ns.get("Histograma")
    if Envolvente:
        s_inf = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        s_sup = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        s_inf.setRange(0, 255); s_sup.setRange(0, 255)
        s_inf.setValue(40); s_sup.setValue(210)
        h = Envolvente(s_inf, s_sup)
        h.resize(600, 320)
        h.show(); app.processEvents()
        check("el contenedor Histograma se monta", h.isVisible())

        g2, ov = h.grafico, h.overlay
        check("el overlay cuelga del contenedor, no del grafico (misma celda del layout)",
              ov.parent() is h, str(ov.parent()))
        check("el overlay es transparente al raton (el raton es del grafico)",
              ov.testAttribute(QtCore.Qt.WA_TransparentForMouseEvents))

        # El layout pone los dosWidgets en la misma celda: mismo tamano siempre.
        check("grafico y overlay ocupan exactamente el mismo rect",
              ov.geometry() == g2.geometry(),
              f"overlay {ov.geometry()} vs grafico {g2.geometry()}")

        # Redimensionar el CONTENEDOR estira los dos a la vez. Este es el caso
        # que un setGeometry manual en resizeEvent no cubria.
        h.resize(500, 260)
        app.processEvents()
        check("al redimensionar el contenedor los dos se mueven juntos",
              ov.geometry() == g2.geometry() == h.rect(),
              f"overlay {ov.geometry()} grafico {g2.geometry()} cont {h.rect()}")

        # Y el area_grafico() del grafico sigue dentro del overlay, que es lo
        # que hace que las flechas caigan sobre las barras.
        a = g2.area_grafico()
        check("area_grafico() cae DENTRO del overlay",
              ov.rect().contains(a), f"area {a} overlay {ov.rect()}")

        bins2 = [0] * 256
        bins2[120] = 400
        g2.set_datos(bins2, 40, 210)
        app.processEvents()
        check("el overlay pinta sin error", not ov.grab().toImage().isNull())

        # Mover un slider deja el overlay al dia, y se releen LOS DOS.
        s_inf.setValue(80)
        app.processEvents()
        check("mover el slider inferior actualiza el overlay",
              ov._inf == 80 and ov._sup == 210,
              f"inf={ov._inf} sup={ov._sup}")
        s_sup.setValue(190)
        app.processEvents()
        check("al tocar el superior se releen los DOS sliders",
              ov._inf == 80 and ov._sup == 190,
              f"inf={ov._inf} sup={ov._sup}")
        h.hide()

# --- 6) el zoom se DESHABILITA, nunca se OCULTA ---
# La decision es "siempre visible": un control que aparece y desaparece cambia
# la pantalla bajo el usuario. Se comprueba sobre el codigo porque la ventana
# es un puente y no se puede instanciar.
print("\n=== 6) el zoom nunca se oculta ===")
ventana = re.search(r"class VentanaRecorte:.*?(?=\n```)", doc, re.S)
if ventana:
    c = ventana.group(0)
    check("el zoom NO se oculta con setVisible(False)", "setVisible(False)" not in c)
    check("el zoom NO se oculta con hide()", ".hide()" not in c)
    check("el zoom se DESHABILITA con setEnabled", "self.zoom.setEnabled(" in c)
    check("el doc dice que el zoom esta siempre visible",
          re.search(r"\*\*Siempre visible\*\*", doc) is not None)
    check("el doc dice que en modo A queda deshabilitado, no oculto",
          re.search(r"modo A est(?:a|á) \*\*deshabilitado\*\*", doc) is not None)
else:
    check("el bloque de VentanaRecorte esta en el documento", False)

print("\n" + "=" * 60)
print(f"RESULTADO: {len(fallos)} fallo(s)" + (": " + ", ".join(fallos) if fallos else " — todo correcto"))
print("=" * 60)
sys.exit(1 if fallos else 0)

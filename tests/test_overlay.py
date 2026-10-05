import sys, io, os, re, types
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt
_RAIZ_OV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
doc = open(os.path.join(_RAIZ_OV, "requisitos.md"), encoding="utf-8").read()
src_tok = re.search(r"### 5\.1 Tokens.*?```python\n(.*?)```", doc, re.S).group(1)
tokens = types.ModuleType("tokens"); exec(compile(src_tok, "t", "exec"), tokens.__dict__)
sys.modules["tokens"] = tokens
ui = types.ModuleType("ui"); ui.__path__ = []; sys.modules["ui"] = ui
uitok = types.ModuleType("ui.tokens")
for k, v in tokens.__dict__.items():
    if k.isupper(): setattr(uitok, k, v)
sys.modules["ui.tokens"] = uitok
ns = {"tokens": tokens}
exec(compile(re.search(r"### 6\.4.*?#### Marcadores.*?```python\n(.*?)```", doc, re.S)
             .group(1).replace("from ui import tokens", "import tokens"), "m", "exec"), ns)
xm, dm = ns["x_de_marcador"], ns["dibujar_marcadores"]
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

fallos = []
def check(n, c, d=""):
    print(("  OK   " if c else "  FALLA") + " " + n + (f"   -> {d}" if d else ""), flush=True)
    if not c: fallos.append(n)

W, H = 800, 400
NARANJA, VERDE = "#E65100", "#00897B"

# sliders top-level (evita el crash de render() del plugin offscreen con hijos)
sl_a = QtWidgets.QSlider(QtCore.Qt.Horizontal); sl_a.setRange(0, 255); sl_a.resize(W, 44)
sl_b = QtWidgets.QSlider(QtCore.Qt.Horizontal); sl_b.setRange(0, 255); sl_b.resize(W, 44)
sl_a.setValue(72); sl_b.setValue(183)
sl_a.show(); sl_b.show(); app.processEvents()

print("=== 1) el marcador cae donde Qt pondria el handle ===", flush=True)
for v in (0, 1, 50, 72, 128, 183, 254, 255):
    sl_a.setValue(v)
    o = QtWidgets.QStyleOptionSlider(); sl_a.initStyleOption(o)
    real = sl_a.style().subControlRect(QtWidgets.QStyle.CC_Slider, o,
                                        QtWidgets.QStyle.SC_SliderHandle, sl_a).center().x()
    check(f"x_de_marcador({v}) == Qt", xm(sl_a, v) == real, f"marca={xm(sl_a, v)} Qt={real}")
check("x_de_marcador no muta el slider", sl_a.value() == v, f"quedo en {sl_a.value()}")
sl_a.setValue(72); sl_b.setValue(183); app.processEvents()

print("\n=== 2) pintar el overlay de verdad ===", flush=True)
class Overlay(QtWidgets.QWidget):
    def __init__(self, area, a, b):
        super().__init__(None); self.area, self.a, self.b = area, a, b
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        dm(p, self.area, self.a, self.b, self.a.value(), self.b.value())
        p.end()

ov = Overlay(QtCore.QRect(0, 0, W, H), sl_a, sl_b)
ov.resize(W, H); ov.show(); app.processEvents()
img = ov.grab().toImage()
check("el overlay se pinta sin error", not img.isNull())
check("captura del tamaño del area", img.width() == W and img.height() == H,
      f"{img.width()}x{img.height()}")

def cuenta(im, x, color, ys=(40, 120, 200, 280, 360)):
    c = QtGui.QColor(color)
    return sum(1 for y in ys if im.pixelColor(x, y) == c)

xa, xb = xm(sl_a, 72), xm(sl_b, 183)
check("linea naranja centrada en la x del handle inferior", cuenta(img, xa, NARANJA) == 5,
      f"{cuenta(img, xa, NARANJA)}/5 en x={xa}")
check("linea verde centrada en la x del handle superior", cuenta(img, xb, VERDE) == 5,
      f"{cuenta(img, xb, VERDE)}/5 en x={xb}")
check("las dos lineas NO estan intercambiadas",
      cuenta(img, xa, VERDE) == 0 and cuenta(img, xb, NARANJA) == 0)
for nombre, x in (("inferior", xa), ("superior", xb)):
    check(f"la flecha de {nombre} no se desplaza 7 px del handle",
          img.pixelColor(x + 7, H - 20) == img.pixelColor(x, H - 20)
          or img.pixelColor(x + 7, H - 20) != QtGui.QColor(NARANJA if nombre == "inferior" else VERDE))

print("\n=== 3) siguen al slider en vivo (regla 5) ===", flush=True)
sl_a.setValue(20); app.processEvents()
img2 = ov.grab().toImage()
x20, x72 = xm(sl_a, 20), xm(sl_a, 72)
check("la linea naranja va a la nueva x", cuenta(img2, x20, NARANJA) == 5,
      f"{cuenta(img2, x20, NARANJA)}/5 en x={x20}")
check("desaparece de la x anterior", cuenta(img2, x72, NARANJA) == 0,
      f"{cuenta(img2, x72, NARANJA)}/5 quedan en x={x72}")
check("la linea verde no se movio", cuenta(img2, xb, VERDE) == 5)

print("\n=== 4) los extremos ===", flush=True)
sl_a.setValue(0); sl_b.setValue(255); app.processEvents()
img3 = ov.grab().toImage()
x0, x255 = xm(sl_a, 0), xm(sl_b, 255)
check("con inf=0 la flecha NO cae en x=0 (Qt descuenta medio handle)", x0 != 0, f"x={x0}")
check("la linea naranja se pinta en el extremo", cuenta(img3, x0, NARANJA) == 5, f"x={x0}")
check("la linea verde se pinta en el otro extremo", cuenta(img3, x255, VERDE) == 5, f"x={x255}")
check("las dos lineas quedan separadas y dentro del grafico",
      0 < x0 < x255 < W, f"{x0} < {x255} < {W}")
ov.hide(); sl_a.hide(); sl_b.hide()
print("\n" + "=" * 60, flush=True)
print(f"RESULTADO: {len(fallos)} fallo(s)" + (": " + ", ".join(fallos) if fallos else " — todo correcto"), flush=True)
print("=" * 60, flush=True)

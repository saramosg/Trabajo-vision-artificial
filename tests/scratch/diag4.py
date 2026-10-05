import sys, io, os, re, types
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt
doc = open(r"C:\Users\santiago\Desktop\unal\vision artificial\trabajo\requisitos.md", encoding="utf-8").read()
src_tok = re.search(r"### 5\.1 Tokens.*?```python\n(.*?)```", doc, re.S).group(1)
tokens = types.ModuleType("tokens"); exec(compile(src_tok, "t", "exec"), tokens.__dict__)
sys.modules["tokens"] = tokens
ui = types.ModuleType("ui"); ui.__path__ = []; sys.modules["ui"] = ui
uitok = types.ModuleType("ui.tokens")
for k, v in tokens.__dict__.items():
    if k.isupper(): setattr(uitok, k, v)
sys.modules["ui.tokens"] = uitok
src = re.search(r"### 6\.4.*?#### Marcadores.*?```python\n(.*?)```", doc, re.S).group(1)
ns = {"tokens": tokens}
exec(compile(src.replace("from ui import tokens", "import tokens"), "m", "exec"), ns)
xm, dm = ns["x_de_marcador"], ns["dibujar_marcadores"]
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
W, H = 800, 400

host = QtWidgets.QWidget(); host.resize(900, 600); host.show(); app.processEvents()
sl_a = QtWidgets.QSlider(QtCore.Qt.Horizontal, host)
sl_b = QtWidgets.QSlider(QtCore.Qt.Horizontal, host)
sl_a.setGeometry(0, 410, W, 44); sl_b.setGeometry(0, 456, W, 44)
sl_a.setRange(0, 255); sl_b.setRange(0, 255)
sl_a.setValue(72); sl_b.setValue(183)
app.processEvents()

class Overlay(QtWidgets.QWidget):
    def __init__(self, area, a, b, parent):
        super().__init__(parent); self.area, self.a, self.b = area, a, b
        self.setGeometry(area)
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        dm(p, self.area, self.a, self.b, self.a.value(), self.b.value())
        p.end()

area = QtCore.QRect(0, 0, W, H)
print("a) crear overlay y mostrarlo", flush=True)
ov = Overlay(area, sl_a, sl_b, host)
ov.show(); app.processEvents()
print("   mostrado OK", flush=True)
print("b) llamar a x_de_marcador FUERA del paint", flush=True)
x1 = xm(sl_a, 72); x2 = xm(sl_b, 183)
print(f"   x1={x1} x2={x2} (sin crash)", flush=True)
print("c) render() en vez de grab()", flush=True)
try:
    pm = ov.render(QtGui.QPixmap(W, H))
    print(f"   OK {pm.width()}x{pm.height()}", flush=True)
except Exception as e:
    print(f"   FALLA {type(e).__name__}: {e}", flush=True)
print("d) grab()", flush=True)
img = ov.grab().toImage()
print(f"   OK {img.width()}x{img.height()}", flush=True)
ov.hide(); host.hide()
print("FIN", flush=True)

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

print("1) dm() con slider HIJO de otro widget (como en test_overlay)", flush=True)
host = QtWidgets.QWidget(); host.resize(900, 600); host.show(); app.processEvents()
sl = QtWidgets.QSlider(QtCore.Qt.Horizontal, host)
sl.setGeometry(0, 420, W, 44); sl.setRange(0, 255); sl.show(); app.processEvents()

class Ov(QtWidgets.QWidget):
    def __init__(self, s, parent=None):
        super().__init__(parent); self.s = s
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        dm(p, QtCore.QRect(0, 0, W, H), self.s, 72, 183)
        p.end()
o = Ov(sl, host); o.setGeometry(0, 0, W, H); o.show(); app.processEvents()
print("   grab()...", flush=True)
img = o.grab().toImage()
print(f"   OK {img.width()}x{img.height()}", flush=True)
o.hide()

print("\n2) mismo pero con drawText (¿es drawText el que rompe?)", flush=True)
class Solo(QtWidgets.QWidget):
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setPen(QtGui.QPen(QtGui.QColor("#E65100"), 1))
        p.drawText(QtCore.QRect(100, 390, 80, 16), Qt.AlignCenter, "inf 72")
        p.end()
s2 = Solo(); s2.resize(W, H); s2.show(); app.processEvents()
print("   grab()...", flush=True)
i2 = s2.grab().toImage(); print(f"   OK {i2.width()}x{i2.height()}", flush=True)
s2.hide()

print("\n3) drawText FUERA del widget (base = H-18, texto en y=H+2)", flush=True)
class Fuera(QtWidgets.QWidget):
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setPen(QtGui.QPen(QtGui.QColor("#E65100"), 1))
        p.drawText(QtCore.QRect(100, H + 2, 80, 16), Qt.AlignCenter, "inf 72")
        p.end()
f = Fuera(); f.resize(W, H); f.show(); app.processEvents()
print("   grab()...", flush=True)
i3 = f.grab().toImage(); print(f"   OK {i3.width()}x{i3.height()}", flush=True)
f.hide()

print("\n4) drawPolygon con QPointF fuera de rango", flush=True)
class Pol(QtWidgets.QWidget):
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setPen(QtGui.QPen(QtGui.QColor("#E65100"), 1))
        p.setBrush(QtGui.QColor("#E65100"))
        base = H - 1 + 18
        p.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(100, base), QtCore.QPointF(114, base),
                                       QtCore.QPointF(107.0, float(H - 1))]))
        p.end()
pl = Pol(); pl.resize(W, H); pl.show(); app.processEvents()
print("   grab()...", flush=True)
i4 = pl.grab().toImage(); print(f"   OK {i4.width()}x{i4.height()}", flush=True)
pl.hide()
host.hide()
print("FIN SIN CRASH", flush=True)

import sys, io, os, re, types
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt
import numpy as np

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
print("A) overlay SIN sliders, solo pintar rectangulos", flush=True)
class Solo(QtWidgets.QWidget):
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setPen(Qt.NoPen)
        p.fillRect(QtCore.QRect(100, 10, 3, 300), QtGui.QColor("#E65100"))
        p.fillRect(QtCore.QRect(400, 10, 3, 300), QtGui.QColor("#00897B"))
        p.end()
a = Solo(); a.resize(W, H); a.show(); app.processEvents()
i1 = a.grab().toImage(); print(f"   OK {i1.width()}x{i1.height()}", flush=True)
a.hide()

print("B) overlay CON setGeometry y sin sliders", flush=True)
host = QtWidgets.QWidget(); host.resize(900, 600); host.show(); app.processEvents()
b = Solo(host); b.setGeometry(QtCore.QRect(0, 0, W, H)); b.show(); app.processEvents()
i2 = b.grab().toImage(); print(f"   OK {i2.width()}x{i2.height()}", flush=True)
b.hide()

print("C) sliders solos, grab del host", flush=True)
sl = QtWidgets.QSlider(QtCore.Qt.Horizontal, host)
sl.setGeometry(0, 420, W, 44); sl.setRange(0, 255); sl.show(); app.processEvents()
i3 = sl.grab().toImage(); print(f"   OK {i3.width()}x{i3.height()}", flush=True)
i4 = host.grab().toImage(); print(f"   OK host {i4.width()}x{i4.height()}", flush=True)

print("D) overlay HIJO de host, con un slider hermano", flush=True)
class ConSlider(QtWidgets.QWidget):
    def __init__(self, s, parent=None):
        super().__init__(parent); self.s = s
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        x = xm(self.s, 72)
        p.setPen(QtGui.QPen(QtGui.QColor("#E65100"), 3))
        p.drawLine(QtCore.QPoint(x, 0), QtCore.QPoint(x, H - 1))
        p.end()
c = ConSlider(sl, host); c.setGeometry(0, 0, W, H); c.show(); app.processEvents()
print("   sobre grab()...", flush=True)
i5 = c.grab().toImage(); print(f"   OK {i5.width()}x{i5.height()}", flush=True)
c.hide()

print("E) overlay TOP-LEVEL con slider externo (como en test_widgets)", flush=True)
s2 = QtWidgets.QSlider(QtCore.Qt.Horizontal)
s2.setRange(0, 255); s2.resize(W, 44); s2.show(); app.processEvents()
e_ = ConSlider(s2); e_.resize(W, H); e_.show(); app.processEvents()
print("   sobre grab()...", flush=True)
i6 = e_.grab().toImage(); print(f"   OK {i6.width()}x{i6.height()}", flush=True)
e_.hide(); s2.hide()

print("F) pixelColor sobre imagen capturada de widget con slider", flush=True)
n = sum(1 for y in (50, 150, 250) if i6.pixelColor(229, y) == QtGui.QColor("#E65100"))
print(f"   pixeles naranja: {n}/3", flush=True)
e_.hide()
print("FIN", flush=True)


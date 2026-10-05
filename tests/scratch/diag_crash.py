import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication([])

def center_mutando(s, v):
    s.setValue(v)                       # MUTA el slider
    o = QtWidgets.QStyleOptionSlider(); s.initStyleOption(o)
    return s.style().subControlRect(QtWidgets.QStyle.CC_Slider, o,
                                    QtWidgets.QStyle.SC_SliderHandle, s).center().x()

def center_sin_mutar(s, v):
    o = QtWidgets.QStyleOptionSlider()
    s.initStyleOption(o)
    o.sliderValue = v                  # NO muta el slider
    o.sliderPosition = v - s.minimum()
    return s.style().subControlRect(QtWidgets.QStyle.CC_Slider, o,
                                    QtWidgets.QStyle.SC_SliderHandle, s).center().x()

print("1) comparar las dos formas (fuera de paintEvent)", flush=True)
s = QtWidgets.QSlider(QtCore.Qt.Horizontal)
s.setRange(0, 255); s.resize(800, 44); s.show(); app.processEvents()
ok = True
for v in (0, 72, 128, 183, 255):
    a, b = center_mutando(s, v), center_sin_mutar(s, v)
    print(f"   v={v:3} mutando={a:3} sin_mutar={b:3} {'OK' if a==b else 'DIFIERE'}", flush=True)
    ok &= (a == b)
print(f"   -> {'identicas' if ok else 'NO identicas'}", flush=True)
print(f"   valor del slider tras preguntar sin mutar: {s.value()} (debe seguir en 0)", flush=True)

print("\n2) DENTRO de paintEvent, con la version que MUTA", flush=True)
class Mala(QtWidgets.QWidget):
    def __init__(self, sl, parent=None):
        super().__init__(parent); self.sl = sl; self.setGeometry(0, 0, 800, 400)
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        x = center_mutando(self.sl, 72)
        p.setPen(QtGui.QPen(QtGui.QColor("#E65100"), 3))
        p.drawLine(QtCore.QPoint(x, 0), QtCore.QPoint(x, 399))
        p.end()

host = QtWidgets.QWidget(); host.resize(900, 600)
sl1 = QtWidgets.QSlider(QtCore.Qt.Horizontal, host)
sl2 = QtWidgets.QSlider(QtCore.Qt.Horizontal, host)
sl1.setGeometry(0, 410, 800, 44); sl2.setGeometry(0, 456, 800, 44)
sl1.setRange(0, 255); sl2.setRange(0, 255)
host.show(); app.processEvents()
m = Mala(sl1, host); m.show(); app.processEvents()
print("  sobre grab()...", flush=True)
img = m.grab().toImage()
print(f"   OK, captura {img.width()}x{img.height()}", flush=True)
m.hide(); host.hide()

print("\n3) DENTRO de paintEvent, SIN mutar", flush=True)
class Buena(QtWidgets.QWidget):
    def __init__(self, sl, parent=None):
        super().__init__(parent); self.sl = sl; self.setGeometry(0, 0, 800, 400)
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        x = center_sin_mutar(self.sl, 72)
        p.setPen(QtGui.QPen(QtGui.QColor("#E65100"), 3))
        p.drawLine(QtCore.QPoint(x, 0), QtCore.QPoint(x, 399))
        p.end()

host2 = QtWidgets.QWidget(); host2.resize(900, 600)
s3 = QtWidgets.QSlider(QtCore.Qt.Horizontal, host2); s3.setRange(0, 255)
host2.show(); app.processEvents()
g = Buena(s3, host2); g.show(); app.processEvents()
print("   sobre grab()...", flush=True)
img2 = g.grab().toImage()
print(f"   OK, captura {img2.width()}x{img2.height()}", flush=True)
# verificar que el pixel naranja cae donde toca
x = center_sin_mutar(s3, 72)
n = sum(1 for y in (50, 150, 250, 350) if img2.pixelColor(x, y) == QtGui.QColor("#E65100"))
print(f"   pixeles naranja en x={x}: {n}/4", flush=True)
print(f"   valor del slider tras pintar: {s3.value()} (debe seguir en 0)", flush=True)
g.hide(); host2.hide()
print("\nFIN SIN CRASH", flush=True)

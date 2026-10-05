import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt
app = QtWidgets.QApplication([])
W, H = 800, 400
host = QtWidgets.QWidget(); host.resize(900, 600); host.show(); app.processEvents()

def mk(y, v):
    s = QtWidgets.QSlider(QtCore.Qt.Horizontal, host)
    s.setGeometry(0, y, W, 44); s.setRange(0, 255); s.setValue(v); s.show()
    return s

a, b = mk(410, 72), mk(456, 183)
app.processEvents()

def xm(s, v):
    o = QtWidgets.QStyleOptionSlider(); s.initStyleOption(o)
    o.sliderValue = v; o.sliderPosition = v - s.minimum()
    return s.style().subControlRect(QtWidgets.QStyle.CC_Slider, o,
                                    QtWidgets.QStyle.SC_SliderHandle, s).center().x()

print("1) xm sobre DOS sliders, con painter activo", flush=True)
class Dos(QtWidgets.QWidget):
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        x1, x2 = xm(a, 72), xm(b, 183)
        p.setPen(QtGui.QPen(QtGui.QColor("#E65100"), 3))
        p.drawLine(QtCore.QPoint(x1, 0), QtCore.QPoint(x1, H - 1))
        p.setPen(QtGui.QPen(QtGui.QColor("#00897B"), 3))
        p.drawLine(QtCore.QPoint(x2, 0), QtCore.QPoint(x2, H - 1))
        p.end()
d = Dos(host); d.setGeometry(0, 0, W, H); d.show(); app.processEvents()
try:
    im = d.grab().toImage()
    n1 = sum(1 for y in (50, 150, 250) if im.pixelColor(xm(a, 72), y) == QtGui.QColor("#E65100"))
    n2 = sum(1 for y in (50, 150, 250) if im.pixelColor(xm(b, 183), y) == QtGui.QColor("#00897B"))
    print(f"   OK {im.width()}x{im.height()}  naranja={n1}/3 verde={n2}/3", flush=True)
except Exception as ex:
    print(f"   FALLA {type(ex).__name__}: {ex}", flush=True)
d.hide()

print("\n2) los sliders FUERA del host (top-level)", flush=True)
t1 = QtWidgets.QSlider(QtCore.Qt.Horizontal); t1.setRange(0, 255); t1.resize(W, 44)
t2 = QtWidgets.QSlider(QtCore.Qt.Horizontal); t2.setRange(0, 255); t2.resize(W, 44)
t1.setValue(72); t2.setValue(183); t1.show(); t2.show(); app.processEvents()
class Dos2(QtWidgets.QWidget):
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        x1, x2 = xm(t1, 72), xm(t2, 183)
        p.setPen(QtGui.QPen(QtGui.QColor("#E65100"), 3))
        p.drawLine(QtCore.QPoint(x1, 0), QtCore.QPoint(x1, H - 1))
        p.setPen(QtGui.QPen(QtGui.QColor("#00897B"), 3))
        p.drawLine(QtCore.QPoint(x2, 0), QtCore.QPoint(x2, H - 1))
        p.end()
d2 = Dos2(); d2.resize(W, H); d2.show(); app.processEvents()
try:
    im2 = d2.grab().toImage()
    n1 = sum(1 for y in (50, 150, 250) if im2.pixelColor(xm(t1, 72), y) == QtGui.QColor("#E65100"))
    n2 = sum(1 for y in (50, 150, 250) if im2.pixelColor(xm(t2, 183), y) == QtGui.QColor("#00897B"))
    print(f"   OK {im2.width()}x{im2.height()}  naranja={n1}/3 verde={n2}/3", flush=True)
except Exception as ex:
    print(f"   FALLA {type(ex).__name__}: {ex}", flush=True)
d2.hide(); t1.hide(); t2.hide(); host.hide()
print("FIN", flush=True)

import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6 import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt
app = QtWidgets.QApplication([])
W, H = 800, 400

class Solo(QtWidgets.QWidget):
    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setPen(Qt.NoPen)
        p.fillRect(QtCore.QRect(100, 10, 3, 300), QtGui.QColor("#E65100"))
        p.end()

host = QtWidgets.QWidget(); host.resize(900, 600); host.show(); app.processEvents()
w = Solo(host); w.setGeometry(0, 0, W, H); w.show(); app.processEvents()

print("1) render() con pintado simple, SIN sliders", flush=True)
try:
    pm = w.render(QtGui.QPixmap(W, H)); print(f"   OK {pm.width()}", flush=True)
except Exception as e:
    print(f"   FALLA {type(e).__name__}: {e}", flush=True)
print("   (si esto falla, el crash es de render() en offscreen, no del doc)", flush=True)

print("\n2) grab() con pintado simple", flush=True)
try:
    im = w.grab().toImage(); print(f"   OK {im.width()}", flush=True)
except Exception as e:
    print(f"   FALLA {type(e).__name__}: {e}", flush=True)

print("\n3) consultar el estilo de un slider con QPainter activo", flush=True)
sl = QtWidgets.QSlider(QtCore.Qt.Horizontal, host)
sl.setGeometry(0, 420, W, 44); sl.setRange(0, 255); sl.show(); app.processEvents()
class ConSlider(QtWidgets.QWidget):
    def paintEvent(self, e):
        p = QtGui.QPainter(self)              # painter ACTIVO
        o = QtWidgets.QStyleOptionSlider()
        sl.initStyleOption(o)                # consultar el slider con painter vivo
        r = sl.style().subControlRect(QtWidgets.QStyle.CC_Slider, o,
                                      QtWidgets.QStyle.SC_SliderHandle, sl)
        p.setPen(QtGui.QPen(QtGui.QColor("#E65100"), 3))
        p.drawLine(QtCore.QPoint(r.center().x(), 0), QtCore.QPoint(r.center().x(), H - 1))
        p.end()
c = ConSlider(host); c.setGeometry(0, 0, W, H); c.show(); app.processEvents()
print("   grab()...", flush=True)
try:
    im2 = c.grab().toImage(); print(f"   OK {im2.width()}", flush=True)
except Exception as e:
    print(f"   FALLA {type(e).__name__}: {e}", flush=True)
c.hide(); w.hide(); host.hide()
print("FIN", flush=True)

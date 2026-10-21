"""Suite de la pantalla de recorte (6.5): scroll, atajos de teclado.

La pantalla de recorte es la mas alta de la app (la zona de la vista son
613 px). Se monta sin foto: lo que se comprueba es la estructura de la
pantalla, no el recorte en si (eso lo cubre test_recorte.py con el
codigo del doc).

Qt offscreen.
"""

import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import QApplication, QScrollArea, QWidget

from core.imagen import EstadoImagen
from ui.ventana_recorte import VentanaRecorte

fallos = []


def check(nombre, cond, detalle=""):
    print(
        ("  OK   " if cond else "  FALLA")
        + " "
        + nombre
        + (f"   -> {detalle}" if detalle and not cond else "")
    )
    if not cond:
        fallos.append(nombre)


class _VentanaFalsa(QWidget):
    def __init__(self):
        super().__init__()
        self.estado = EstadoImagen()

    def mostrar(self, nombre):
        pass


app = QApplication.instance() or QApplication([])
falsa = _VentanaFalsa()
falsa.show()
p = VentanaRecorte(falsa)
p.resize(1280, 720)
p.show()
app.processEvents()

print("=== pantalla de recorte: estructura ===")

# 1) SCROLL: la pagina mas alta va dentro de un QScrollArea (§5.3 regla 8)
scrolls = p.findChildren(QScrollArea)
check(
    "la pantalla de recorte tiene QScrollArea", len(scrolls) >= 1, f"n={len(scrolls)}"
)
minimo = p.minimumSizeHint()
check(
    "el scroll evita que la ventana minima se vaya de la pantalla",
    minimo.height() <= 700,
    f"minimumSizeHint={minimo.height()}px",
)

# 2) ATAJOS: + / - para el zoom y NINGUNA flecha (§6.0: "las pantallas de
#    histograma y recorte NO tienen flechas de teclado"). Con flechas
#    ademas colisionaban con las de la ventana principal.
teclas = set()
for atajo in p.findChildren(QShortcut):
    for parte in atajo.key().toString().split("+"):
        teclas.add(parte.strip().upper())
flechas = {"LEFT", "RIGHT", "UP", "DOWN"}
check(
    "sin atajos de flechas (§6.0)",
    not (teclas & flechas),
    str(sorted(teclas & flechas)),
)
check(
    "si atajos de zoom (+ / -)",
    bool(teclas & {"+", "-", "PLUS", "MINUS"}),
    str(sorted(teclas)),
)

# 3) el zoom responde
antes = p.zoom.value()
p.zoom.setValue(p.zoom.value() + 10)
check("el zoom se mueve", p.zoom.value() == antes + 10, f"{antes} -> {p.zoom.value()}")

print("\n" + "=" * 60)
print(
    f"RESULTADO: {len(fallos)} fallo(s)"
    + (": " + ", ".join(fallos) if fallos else " — todo correcto")
)
print("=" * 60)
sys.exit(1 if fallos else 0)

"""Suite de modos de la pantalla de histograma (6.4).

El boton de la cabecera alterna el modo ACTIVO: "Detección de umbral"
(pantalla actual: histograma, barras, fila canal, fila fondo, sliders =
rango) y "Detección de bordes" (metodo + t1/t2, controles de bordes,
miniaturas afectadas). Al entrar siempre arranca en umbral. Se ejecuta
contra ui/ventana_histograma.py REAL, en Qt offscreen.
"""

import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

import numpy as np
from PySide6.QtWidgets import QApplication, QWidget

from core.imagen import EstadoImagen
from ui.ventana_histograma import VentanaHistograma

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
    """Minimal: QWidget (VentanaHistograma lo usa de parent) + estado."""

    def __init__(self):
        super().__init__()
        self.estado = EstadoImagen()

    def mostrar(self, nombre):
        pass


app = QApplication.instance() or QApplication([])
falsa = _VentanaFalsa()
# Imagen sintetica: fondo 128, cuadro 220 (dentro del rango 40-200).
falsa.estado.original = np.full((64, 64, 3), 128, np.uint8)
falsa.estado.original[20:44, 20:44] = 220
falsa.estado.inf, falsa.estado.sup = 40, 200
falsa.show()  # sin esto isVisible() es False en toda la cadena (QParent oculto)
p = VentanaHistograma(falsa)
p.resize(1280, 720)
p.show()
app.processEvents()

print("=== boton de modo junto a REGRESAR ===")
modo = getattr(p, "boton_modo", None)
regresar = getattr(p, "boton_regresar", None)
check(
    "la pantalla tiene boton_modo", modo is not None, "no existe el atributo boton_modo"
)
check("la pantalla tiene boton_regresar", regresar is not None)

if modo is not None and regresar is not None:
    check(
        "usa el estilo de navegacion (objectName navegacion)",
        modo.objectName() == "navegacion",
        f"objectName={modo.objectName()!r}",
    )
    check("altura fija = BTN_NAV_ALTO (48)", modo.height() == 48, str(modo.height()))
    check(
        "ancho minimo = BTN_NAV_ANCHO (160)",
        modo.minimumWidth() == 160,
        str(modo.minimumWidth()),
    )
    check(
        "misma fila que REGRESAR",
        abs(modo.y() - regresar.y()) <= 2,
        f"y_modo={modo.y()} y_regresar={regresar.y()}",
    )
    check(
        "queda a la izquierda de REGRESAR",
        modo.x() + modo.width() <= regresar.x() + 1,
        f"modo_derecha={modo.x() + modo.width()} regresar_izq={regresar.x()}",
    )

    print("\n=== modos: umbral <-> bordes ===")
    check(
        "texto inicial 'Detección de umbral'",
        modo.text() == "Detección de umbral",
        f"texto={modo.text()!r}",
    )
    check("umbral: vista_histograma visible", p.vista_histograma.isVisible())
    check("umbral: fila canal visible", p.lbl_canal.isVisible())
    check("umbral: fila fondo visible", p.boton_fondo.isVisible())
    check(
        "umbral: el boton 'Quitar fondo' esta en la fila derecha",
        p._fila_fondo.indexOf(p.boton_fondo) >= 0,
    )
    check("umbral: boton_metodo oculto", not p.boton_metodo.isVisible())
    check("umbral: vaciar oculto", not p.boton_vaciar.isVisible())
    check(
        "umbral: etiquetas umbral ocultas",
        not p.lbl_inf.isVisible() and not p.lbl_sup.isVisible(),
    )

    antes = (falsa.estado.inf, falsa.estado.sup, falsa.estado.modo)
    modo.click()
    check(
        "clic -> texto 'Detección de bordes'",
        modo.text() == "Detección de bordes",
        f"texto={modo.text()!r}",
    )
    check(
        "clic NO escribe inf/sup/modo",
        (falsa.estado.inf, falsa.estado.sup, falsa.estado.modo) == antes,
        str((falsa.estado.inf, falsa.estado.sup, falsa.estado.modo)),
    )
    check(
        "bordes: vista_histograma visible (mapa de bordes)",
        p.vista_histograma.isVisible(),
    )
    check(
        "bordes: fila canal oculta",
        not p.lbl_canal.isVisible() and not p.boton_canal.isVisible(),
    )
    check(
        "bordes: 'Limpiar máscara' oculta",
        not p.boton_limpiar.isVisible(),
    )
    check(
        "bordes: el boton 'Quitar fondo' sigue visible",
        p.boton_fondo.isVisible(),
    )
    check(
        "bordes: el boton 'Quitar fondo' esta en la rejilla",
        p._rejilla.indexOf(p.boton_fondo) >= 0,
    )
    check(
        "bordes: el boton ya no esta en la fila derecha",
        p._fila_fondo.indexOf(p.boton_fondo) < 0,
    )
    check("bordes: boton_metodo visible", p.boton_metodo.isVisible())
    check("bordes: vaciar visible", p.boton_vaciar.isVisible())
    check(
        "bordes: etiquetas umbral visibles",
        p.lbl_inf.isVisible() and p.lbl_sup.isVisible(),
    )
    check(
        "bordes: sliders no tocan estado",
        (falsa.estado.inf, falsa.estado.sup) == (40, 200),
        str((falsa.estado.inf, falsa.estado.sup)),
    )
    check(
        "bordes: sliders recargados con _t1/_t2",
        (p._t1, p._t2) == (100, 200)
        and (p.slider_inf.value(), p.slider_sup.value()) == (100, 200),
        str((p._t1, p._t2, p.slider_inf.value(), p.slider_sup.value())),
    )

    # sliders: en bordes escriben _t1, no estado
    p.slider_inf.setValue(33)
    check(
        "slider inf en bordes escribe _t1",
        p._t1 == 33 and falsa.estado.inf == 40,
        str((p._t1, falsa.estado.inf)),
    )

    # ciclo de metodos
    texts = [p.boton_metodo.text()]
    p.boton_metodo.click()
    texts.append(p.boton_metodo.text())
    p.boton_metodo.click()
    texts.append(p.boton_metodo.text())
    p.boton_metodo.click()
    texts.append(p.boton_metodo.text())
    check(
        "metodo cicla canny->sobel->laplaciano->canny",
        texts == ["Canny", "Sobel", "Laplaciano", "Canny"],
        str(texts),
    )

    # ida y vuelta conserva el rango de umbral (guarda del pise de sliders)
    modo.click()  # vuelta a umbral
    check(
        "vuelta a umbral: texto",
        modo.text() == "Detección de umbral",
        f"texto={modo.text()!r}",
    )
    check("vuelta a umbral: vista visible", p.vista_histograma.isVisible())
    check(
        "vuelta a umbral: el boton 'Quitar fondo' vuelve a la fila derecha",
        p._fila_fondo.indexOf(p.boton_fondo) >= 0
        and p._rejilla.indexOf(p.boton_fondo) < 0,
    )
    check(
        "vuelta a umbral: estado.inf/sup intactos",
        (falsa.estado.inf, falsa.estado.sup) == (40, 200),
        str((falsa.estado.inf, falsa.estado.sup)),
    )
    p.slider_inf.setValue(50)
    check("umbral: slider escribe estado.inf", falsa.estado.inf == 50)

    # al_entrar siempre restaura umbral
    modo.click()  # a bordes
    p.al_entrar()
    check(
        "al_entrar restaura modo umbral",
        modo.text() == "Detección de umbral" and p.vista_histograma.isVisible(),
    )
    check("al_entrar conserva estado.mascara", falsa.estado.mascara is None)

    # refrescar en bordes sin imagen: no crashea
    salv = falsa.estado.original
    falsa.estado.original = None
    p._modo = "bordes"
    p._aplicar_modo()
    check("bordes sin imagen: no crashea", True)
    falsa.estado.original = salv
    p.al_entrar()

print("\n" + "=" * 60)
print(
    f"RESULTADO: {len(fallos)} fallo(s)"
    + (": " + ", ".join(fallos) if fallos else " — todo correcto")
)
print("=" * 60)
sys.exit(1 if fallos else 0)

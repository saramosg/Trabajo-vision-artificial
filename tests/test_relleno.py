"""Suite del relleno por clics sobre el mapa de bordes (6.4, modo bordes).

Cada clic en el contorno binario (o en el area grande) rellena la region
cerrada por los bordes y acumula con OR en estado.mascara. Se ejecuta
contra ui/ventana_histograma.py REAL, en Qt offscreen.
"""

import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

import numpy as np
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from core.imagen import EstadoImagen
from ui.ventana_histograma import VentanaHistograma, ZonaBordes

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
# 96x96: fondo 30, dos cuadros claros 230 de 24x24 en (12,12) y (60,60).
img = np.full((96, 96, 3), 30, np.uint8)
img[12:36, 12:36] = 230
img[60:84, 60:84] = 230
falsa.estado.original = img
falsa.show()
p = VentanaHistograma(falsa)
p.resize(1280, 720)
p.show()
app.processEvents()
modo = p.boton_modo
modo.click()  # a bordes
app.processEvents()

print("=== relleno por clics ===")
check(
    "mapa de bordes calculado en modo bordes",
    p._mapa_bordes is not None and np.any(p._mapa_bordes > 0),
)

# clic en el fondo abierto (region que toca el borde): no llena nada y
# lo avisa — nada falla en silencio.
p.al_rellenar(1, 1)
check("fondo abierto: no crea mascara", falsa.estado.mascara is None)
check(
    "fondo abierto: aviso en pantalla",
    p.lbl_aviso.text() != "",
    repr(p.lbl_aviso.text()),
)

p.al_rellenar(24, 24)
m = falsa.estado.mascara
check("1er clic: mascara creada", m is not None)
check(
    "1er clic: region A llena", m is not None and m[24, 24] == 255 and m[16, 16] == 255
)
check("1er clic: region B vacia", m is not None and m[72, 72] == 0)

p.al_rellenar(72, 72)
check(
    "2do clic: acumula OR (A y B)",
    falsa.estado.mascara[24, 24] == 255 and falsa.estado.mascara[72, 72] == 255,
)

copia = falsa.estado.mascara.copy()
p.al_rellenar(24, 24)
check("clic repetido: mascara sin cambios", np.array_equal(copia, falsa.estado.mascara))

p.boton_vaciar.click()
check("vaciar relleno pone estado.mascara None", falsa.estado.mascara is None)

# volver a umbral: el relleno (si lo hay) sigue ahi y no se rompe nada
p.al_rellenar(24, 24)
modo.click()
check(
    "vuelta a umbral conserva el relleno",
    falsa.estado.mascara is not None and falsa.estado.mascara[24, 24] == 255,
)
check(
    "_mascara_a_guardar en umbral intersecta con rango",
    p._mascara_a_guardar() is not None,
)
modo.click()
check(
    "_mascara_a_guardar en bordes devuelve el relleno puro",
    falsa.estado.mascara is not None
    and np.array_equal(p._mascara_a_guardar(), falsa.estado.mascara),
)

print("=== aviso del relleno ===")
# Un objeto que NO toca el borde: no hay aviso (nada que contar).
p.boton_vaciar.click()
p.al_rellenar(24, 24)
check(
    "objeto central: sin aviso",
    p.lbl_aviso.text() == "",
    repr(p.lbl_aviso.text()),
)

# Un objeto CORTADO por el cuadro: el contorno no cierra, el marco de
# la imagen lo cierra y el aviso lo dice.
img_cortado = np.full((96, 96, 3), 30, np.uint8)
img_cortado[0:60, 40:96] = 230  # objeto pegado arriba y a la derecha
falsa_c = _VentanaFalsa()
falsa_c.estado.original = img_cortado
falsa_c.show()
pc = VentanaHistograma(falsa_c)
pc.resize(1280, 720)
pc.show()
app.processEvents()
pc.boton_modo.click()  # a bordes
app.processEvents()
pc.al_rellenar(70, 20)
check(
    "objeto cortado: se rellena",
    falsa_c.estado.mascara is not None and np.count_nonzero(falsa_c.estado.mascara) > 0,
)
check(
    "objeto cortado: el aviso dice que se cerro con el borde",
    "borde de la imagen" in pc.lbl_aviso.text(),
    repr(pc.lbl_aviso.text()),
)
check(
    "objeto cortado: la region llega al borde del cuadro",
    falsa_c.estado.mascara is not None and falsa_c.estado.mascara[0, 70] == 255,
)
check(
    "objeto cortado: el fondo de la izquierda sigue vacio",
    falsa_c.estado.mascara is not None and falsa_c.estado.mascara[80, 10] == 0,
)

print("=== 'Quitar fondo' en modo bordes ===")
# Sin relleno no hay nada que quitar: el boton avisa y no activa el preview.
p.boton_vaciar.click()
p.al_rellenar(24, 24)  # rellena la region A
p.boton_vaciar.click()  # vacia el relleno otra vez
p.al_rellenar(24, 24)
m = falsa.estado.mascara
check("relleno previo para el preview", m is not None and np.count_nonzero(m) > 0)

p.boton_fondo.click()
check("boton: preview activado", p._fondo_activo is True)
check(
    "boton: el texto alterna a 'Restaurar original'",
    p.boton_fondo.text() == "Restaurar original",
    p.boton_fondo.text(),
)
check("boton: el preview no escribe estado", falsa.estado.mascara is not None)
p.boton_fondo.click()
check("boton: preview desactivado", p._fondo_activo is False)
check(
    "boton: el texto vuelve a 'Quitar fondo'",
    p.boton_fondo.text() == "Quitar fondo",
    p.boton_fondo.text(),
)

# Sin relleno: avisa y no deja la imagen en negro.
p.boton_vaciar.click()
p.boton_fondo.click()
check("sin relleno: el preview no se activa", p._fondo_activo is False)
check(
    "sin relleno: el aviso lo dice",
    "relleno" in p.lbl_aviso.text(),
    repr(p.lbl_aviso.text()),
)

print("\n=== mapeo widget -> imagen ===")
z = p.mini_contorno
z.resize(250, 250)
app.processEvents()
ancho_img = 96
centro = z._a_imagen(z.width() // 2, z.height() // 2)
check(
    "centro del widget -> centro aproximado de la imagen",
    centro is not None and abs(centro[0] - 48) <= 3 and abs(centro[1] - 48) <= 3,
    str(centro),
)
punto = z._a_imagen(z.width() - 1, z.height() - 1)
check(
    "esquina inferior valida y dentro de rango",
    punto is not None and 0 <= punto[0] < ancho_img and 0 <= punto[1] < ancho_img,
    str(punto),
)
# sin pixmap no hay letterbox que mapear: devuelve None en vez de crashear
z2 = p.vista_histograma
z2.set_imagen(QPixmap())
check("sin pixmap _a_imagen devuelve None", z2._a_imagen(10, 10) is None)

# imagen NO cuadrada (96x128) en lienzo 250x250: hay barras de letterbox
# a izquierda/derecha; ahi el clic no debe mapear, y los bordes internos
# deben caer en el primer/ultimo px de la imagen (sin off-by-one).
zq = ZonaBordes((250, 250), (10, 10))
zq.resize(250, 250)
zq.set_imagen(QPixmap(96, 128))
app.processEvents()
check("no cuadrado: barra izquierda -> None", zq._a_imagen(5, 10) is None)
check("no cuadrado: barra derecha -> None", zq._a_imagen(245, 10) is None)
izq = zq._a_imagen(31, 0)  # borde interior izquierdo superior (x0 = (250-187)//2)
check("no cuadrado: interior -> (0, 0)", izq == (0, 0), str(izq))
der = zq._a_imagen(217, 249)  # borde interior derecho inferior
check("no cuadrado: esquina inf-der -> (95, 127)", der == (95, 127), str(der))

print("\n" + "=" * 60)
print(
    f"RESULTADO: {len(fallos)} fallo(s)"
    + (": " + ", ".join(fallos) if fallos else " — todo correcto")
)
print("=" * 60)
sys.exit(1 if fallos else 0)

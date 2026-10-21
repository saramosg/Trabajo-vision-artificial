"""Suite de core/bordes.py: deteccion (canny/sobel/laplaciano) y relleno.

Sin Qt: solo NumPy + OpenCV. Se ejecuta contra core/bordes.py REAL.
"""

import sys, io, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

import cv2
import numpy as np

from core.bordes import detectar_bordes

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


print("=== detectar_bordes ===")
# cuadrado blanco (200) 24x24 centrado en fondo negro, 64x64
img = np.zeros((64, 64), np.uint8)
img[20:44, 20:44] = 200
# La frontera real es el anillo de 1 px que rodea el cuadrado. Tras el
# blur 5x5 el borde cae a 1-2 px de esa linea (y las esquinas se curvan
# en diagonal), asi que el criterio es: >=90 % de los px del anillo tiene
# un borde detectado a <=2 px de distancia. Umbrales por escala propias
# de cada metodo (canny: low/high; sobel/lap: magnitud y |lap|).
_UMBRAL = {"canny": (50, 150), "sobel": (0, 100), "laplaciano": (0, 30)}
for metodo in ("canny", "sobel", "laplaciano"):
    t1, t2 = _UMBRAL[metodo]
    out = detectar_bordes(img, metodo, t1, t2)
    check(f"{metodo}: dtype uint8", out.dtype == np.uint8)
    check(f"{metodo}: misma forma", out.shape == img.shape)
    check(f"{metodo}: valores 0/255", set(np.unique(out)) <= {0, 255})
    check(f"{metodo}: detecta algo", np.any(out > 0))
    anillo = np.zeros_like(img)
    anillo[19, 19:45] = 255
    anillo[44, 19:45] = 255
    anillo[19:45, 19] = 255
    anillo[19:45, 44] = 255
    cercano = cv2.dilate((out > 0).astype(np.uint8), np.ones((5, 5), np.uint8))
    fraccion = np.count_nonzero(cercano[anillo > 0]) / np.count_nonzero(anillo)
    check(
        f"{metodo}: >=90% de la frontera (+-2 px)",
        fraccion >= 0.9,
        f"fraccion={fraccion:.2f}",
    )
try:
    detectar_bordes(img, "noexiste", 0, 255)
    check("metodo desconocido lanza ValueError", False)
except ValueError:
    check("metodo desconocido lanza ValueError", True)

print("=== rellenar_bordes ===")
from core.bordes import rellenar_bordes


def _cuadro(anillo: bool = True, hueco: bool = False):
    """32x32: anillo blanco 0/255 de pared en [10..21]x[10..21]."""
    m = np.zeros((32, 32), np.uint8)
    if anillo:
        m[10, 10:22] = 255
        m[21, 10:22] = 255
        m[10:22, 10] = 255
        m[10:22, 21] = 255
        if hueco:
            m[10, 15:17] = 0  # hueco de 2 px en la pared superior
    return m


# 1) llena el interior y no se sale
m, hubo = rellenar_bordes(_cuadro(), None, (15, 15))
check("interior relleno", m[15, 15] == 255 and m[12, 12] == 255)
check("exterior intacto", m[1, 1] == 0 and m[30, 30] == 0 and m[15, 25] == 0)
check("hubo_cambio True en el 1er clic", hubo is True)
check("mascara uint8 0/255", set(np.unique(m)) <= {0, 255} and m.dtype == np.uint8)

# 2) hueco de 2 px: la dilatacion lo sella, no se escapa
m, hubo = rellenar_bordes(_cuadro(hueco=True), None, (15, 15))
check("hueco sellado: interior lleno", m[15, 15] == 255)
check("hueco sellado: exterior intacto", m[1, 1] == 0)

# 3) acumulable: dos ANILLOS disjuntos se llenan con OR (cada clic llena
#    el interior de su anillo; un bloque solido no encierra region)
m2 = np.zeros((32, 32), np.uint8)


def _anillo(dst, y0, x0, lado):
    y1, x1 = y0 + lado, x0 + lado
    dst[y0, x0 : x1 + 1] = 255
    dst[y1, x0 : x1 + 1] = 255
    dst[y0 : y1 + 1, x0] = 255
    dst[y0 : y1 + 1, x1] = 255


_anillo(m2, 3, 3, 8)
_anillo(m2, 18, 18, 8)
m, _ = rellenar_bordes(m2, None, (7, 7))
m, _ = rellenar_bordes(m2, m, (22, 22))
check("acumula ambas regiones", m[7, 7] == 255 and m[22, 22] == 255)

# 4) clic repetido: no cambia nada
m1, hubo1 = rellenar_bordes(_cuadro(), None, (15, 15))
m1b, hubo2 = rellenar_bordes(_cuadro(), m1, (16, 16))
check("clic repetido hubo_cambio False", hubo1 is True and hubo2 is False)
check("clic repetido mascara identica", np.array_equal(m1, m1b))

# 5) seed sobre la pared: snap al libre mas cercano (radio 3) y llena
m, hubo = rellenar_bordes(_cuadro(), None, (10, 15))  # (10,15) es pared
check("seed en pared: aun llena el interior", m[15, 15] == 255 and hubo is True)

# 6) mascara existente no reemplaza: OR preserva pixeles previos
previa = np.zeros((32, 32), np.uint8)
previa[30, 30] = 255
m, _ = rellenar_bordes(_cuadro(), previa, (15, 15))
check("preserva px previo ajeno", m[30, 30] == 255)

# 7) fondo abierto: la region libre toca el borde de la imagen -> no es
#    una region cerrada, no se llena (un clic en el fondo no puede
#    seleccionar la imagen entera)
m0, hubo0 = rellenar_bordes(_cuadro(), None, (1, 1))
check("fondo abierto: no llena nada", hubo0 is False and not np.any(m0))

print("=== rellenar_bordes sin bordes internos ===")


def _cuadro_partido():
    """40x40: cuadrado [10..29] con dos lineas internas que se cruzan.

    Las lineas internas parten el interior en 4 bolsillos. Con el
    relleno de barrera cada clic llenaba UN bolsillo (y las lineas
    quedaban como huecos); el relleno por objeto llena los cuatro de
    una vez y sin huecos.
    """
    m = np.zeros((40, 40), np.uint8)
    m[10, 10:30] = 255
    m[29, 10:30] = 255
    m[10:30, 10] = 255
    m[10:30, 29] = 255
    m[20, 12:28] = 255  # horizontal
    m[12:28, 20] = 255  # vertical
    return m


_cuadro_p = _cuadro_partido()
_mp, hubo_p = rellenar_bordes(_cuadro_p, None, (14, 14))

# 1) un solo clic llena los 4 bolsillos: las lineas internas no son barreras
check(
    "1 clic llena los 4 bolsillos",
    _mp[14, 14] == 255
    and _mp[14, 25] == 255
    and _mp[25, 14] == 255
    and _mp[25, 25] == 255,
)

# 2) los bordes internos quedan rellenos: no quedan espacios
_interior = np.zeros((40, 40), np.uint8)
_interior[12:28, 12:28] = 255
check("la linea horizontal interna queda rellena", _mp[20, 15] == 255)
check("la linea vertical interna queda rellena", _mp[15, 20] == 255)
check("el cruce de las lineas queda relleno", _mp[20, 20] == 255)
_faltan = int(np.count_nonzero(_interior & (255 - _mp)))
check("sin huecos en todo el interior", _faltan == 0, f"faltan={_faltan}")

# 3) la silueta es el contorno detectado y no se sale de el
check("la silueta incluye el borde detectado", _mp[10, 20] == 255)
check("no se sale del contorno", _mp[9, 20] == 0 and _mp[30, 20] == 0)
check(
    "el exterior sigue vacio",
    _mp[1, 1] == 0 and _mp[35, 35] == 0 and _mp[20, 36] == 0,
)

# 4) el resultado no depende del bolsillo donde se clique
_mp2, _ = rellenar_bordes(_cuadro_p, None, (25, 25))
check("el relleno es el mismo desde cualquier bolsillo", np.array_equal(_mp, _mp2))

# 5) dos objetos separados: cada clic llena solo el suyo
_m3 = np.zeros((40, 40), np.uint8)
_anillo(_m3, 3, 3, 8)  # anillo en [3..11]
_anillo(_m3, 22, 22, 8)  # anillo en [22..30]
_m3a, _ = rellenar_bordes(_m3, None, (7, 7))
_m3a, _ = rellenar_bordes(_m3, _m3a, (26, 26))
check("dos objetos: ambos rellenos", _m3a[7, 7] == 255 and _m3a[26, 26] == 255)
check("dos objetos: el exterior intacto", _m3a[1, 1] == 0 and _m3a[15, 15] == 0)

# 6) arista suelta del fondo: no encierra nada, no rellena
_suelto = np.zeros((40, 40), np.uint8)
_suelto[10, 10:20] = 255  # linea abierta que no cierra region
_ms, hubo_s = rellenar_bordes(_suelto, None, (10, 15))
check("arista suelta: no rellena", hubo_s is False and not np.any(_ms))

# 7) el fondo abierto: no rellena
_mf, hubo_f = rellenar_bordes(_cuadro_p, None, (2, 2))
check("fondo abierto (objeto): no rellena", hubo_f is False and not np.any(_mf))

print("=== rellenar_bordes: el marco como pared ===")


def _objeto_cortado(interno: bool = False):
    """40x40: objeto cortado por el cuadro.

    El objeto es el rectangulo [20..39] x [0..35]: su contorno es una
    "L" (muro vertical en x=20 y muro horizontal en y=35) y se escapa
    por arriba y por la derecha. Fuera del objeto queda el fondo.
    Con `interno` se anade un borde interno en x=30 que parte el
    interior en dos.
    """
    m = np.zeros((40, 40), np.uint8)
    m[0:36, 20] = 255  # muro vertical
    m[35, 20:40] = 255  # muro horizontal
    if interno:
        m[0:31, 30] = 255  # borde interno
    return m


# 1) objeto cortado por el cuadro: se rellena su parte visible
_mc, hubo_c = rellenar_bordes(_objeto_cortado(), None, (30, 10))
check("objeto cortado: el interior se rellena", _mc[10, 30] == 255)
check("objeto cortado: hubo_cambio True", hubo_c is True)
check(
    "objeto cortado: llega al borde del cuadro",
    _mc[0, 30] == 255 and _mc[30, 39] == 255,
)
check("objeto cortado: el fondo de la izquierda sigue vacio", _mc[10, 10] == 0)
check("objeto cortado: el fondo de abajo sigue vacio", _mc[38, 30] == 0)
check("objeto cortado: la esquina del fondo sigue vacia", _mc[39, 3] == 0)

# 2) el borde interno NO parte el objeto: el relleno es solido
_mi, hubo_i = rellenar_bordes(_objeto_cortado(interno=True), None, (25, 10))
check("con borde interno: la parte izquierda se rellena", _mi[10, 25] == 255)
check("con borde interno: la parte derecha se rellena", _mi[10, 35] == 255)
check("con borde interno: el borde interno queda relleno", _mi[10, 30] == 255)
check("con borde interno: no sale del objeto", _mi[38, 30] == 0 and _mi[10, 10] == 0)

# 3) un objeto CERRADO sigue sin llenarse desde el fondo (no cambia)
_mf2, hubo_f2 = rellenar_bordes(_cuadro(), None, (1, 1))
check(
    "objeto cerrado: el fondo sigue sin rellenarse",
    hubo_f2 is False and not np.any(_mf2),
)

# 4) contorno roto por el medio que NO sale del cuadro: el relleno no
#    puede llevarse el fondo (seria la imagen entera). Con el hueco
#    abierto, el interior se une con el fondo: no hay region cerrable.
_roto = np.zeros((60, 60), np.uint8)
_roto[10, 10:50] = 255
_roto[49, 10:50] = 255
_roto[10:50, 10] = 255
_roto[10:50, 49] = 255
_roto[10, 27:33] = 0  # hueco de 6 px: la dilatacion no lo sella
_mr, hubo_r = rellenar_bordes(_roto, None, (30, 30))
check(
    "contorno roto sin salir del cuadro: no rellena el fondo",
    hubo_r is False and not np.any(_mr),
    f"pixeles={int(np.count_nonzero(_mr))}",
)

# 5) UMBRALES BAJOS: los bordes forman una malla conectada que cubre la
#    foto entera. El "objeto" no puede ser la imagen completa: al
#    seleccionar una parte se rellena SOLO esa parte.
_ruido = np.zeros((120, 120), np.uint8)
_aleatorio = np.random.default_rng(7)
_ruido[:] = (_aleatorio.random((120, 120)) * 255).astype(np.uint8)
_ruido[40:80, 40:80] = 255
_mapa_ruido = detectar_bordes(_ruido, "canny", 10, 30)
_mx, hubo_x = rellenar_bordes(_mapa_ruido, None, (60, 60))
check(
    "umbrales bajos: hay relleno",
    hubo_x is True,
)
check(
    "umbrales bajos: no se rellena la foto entera",
    np.count_nonzero(_mx) < 0.5 * _mx.size,
    f"pixeles={int(np.count_nonzero(_mx))} de {_mx.size}",
)

print("=== deteccion: histeresis en sobel/laplaciano ===")
# t1 = umbral bajo, t2 = umbral alto. Un pixel "debil" (entre t1 y t2)
# se conserva solo si esta conectado a uno fuerte (>= t2), como en Canny.
_fuerte = np.zeros((60, 60), np.uint8)
_fuerte[:, 20:22] = 200  # borde fuerte (magnitud ~255)
_fuerte[:, 27:29] = 30  # borde debil pegado (magnitud ~40)
_mh = detectar_bordes(_fuerte, "sobel", 10, 100)
check("histeresis: el borde fuerte se conserva", _mh[30, 20] > 0)
check("histeresis: el borde debil pegado al fuerte se conserva", _mh[30, 27] > 0)

# el mismo borde debil, pero separado del fuerte
_sep = np.zeros((60, 60), np.uint8)
_sep[:, 20:22] = 200
_sep[:, 40:42] = 30
_mh2 = detectar_bordes(_sep, "sobel", 10, 100)
check("histeresis: el borde debil separado no se conserva", _mh2[30, 41] == 0)

# sin ningun pixel fuerte no hay borde
_solo_debil = np.zeros((60, 60), np.uint8)
_solo_debil[:, 20:22] = 30
_mh3 = detectar_bordes(_solo_debil, "sobel", 10, 200)
check("histeresis: sin pixel fuerte no hay borde", not np.any(_mh3 > 0))

# con t1 = t2 el borde debil se pierde aunque este pegado al fuerte
_mh4 = detectar_bordes(_fuerte, "sobel", 100, 100)
check(
    "histeresis: con t1 = t2 solo queda el fuerte",
    _mh4[30, 20] > 0 and _mh4[30, 27] == 0,
)

print("=== deteccion: cierre del contorno al rellenar ===")
# Contorno en banda de 3 px (como el borde real de un objeto, que sale
# con varios px de grosor) y un hueco de 6 px: la dilatacion 3x3 no lo
# sella, pero el cierre morfologico si -> el objeto se rellena entero.
_mapa_c = np.zeros((60, 60), np.uint8)
_mapa_c[10:13, 10:50] = 255
_mapa_c[47:50, 10:50] = 255
_mapa_c[10:50, 10:13] = 255
_mapa_c[10:50, 47:50] = 255
_mapa_c[10:13, 27:33] = 0  # hueco de 6 px
_mc2, hubo_c2 = rellenar_bordes(_mapa_c, None, (30, 30))
check(
    "el cierre une el hueco del contorno y el objeto se rellena",
    hubo_c2 and np.count_nonzero(_mc2) > 1200,
    f"pixeles={int(np.count_nonzero(_mc2))}",
)

print("\n" + "=" * 60)
print(
    f"RESULTADO: {len(fallos)} fallo(s)"
    + (": " + ", ".join(fallos) if fallos else " — todo correcto")
)
print("=" * 60)
sys.exit(1 if fallos else 0)

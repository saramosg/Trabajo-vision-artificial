"""Deteccion de bordes del canal activo y relleno por objeto y clics.

`detectar_bordes` aplica uno de tres metodos (canny, sobel, laplaciano)
sobre un componente 2D uint8 y devuelve el mapa binario 0/255. Los tres
comparten blur gaussiano 5x5 previo (mismo enfoque que los notebooks del
proyecto: Canny con umbrales t1/t2; sobel/laplaciano con magnitud y
umbral fijo en t2).

`rellenar_bordes` es el relleno POR OBJETO: desde un clic llena la
region completa que encierran los bordes, solida y sin huecos. Los
bordes INTERNOS (textura, manchas, vetas) dejan de ser paredes: pasan a
ser relleno, asi que no quedan espacios dentro del objeto. El recorte
se hace por connectivity: el FONDO son las componentes libres que
tocan el borde de la imagen y todo lo demas (paredes + bolsillos) es
un objeto. La region se acumula con OR sobre la mascara existente
(nunca borra).

Cuando el contorno se ESCAPA del cuadro (el objeto esta cortado por la
imagen) el MARCO DE LA IMAGEN hace de pared: el contorno queda cerrado
por el borde de la imagen y el objeto se rellena igual. Si el contorno
ademas esta roto por el medio, se dilata un poco (radio proporcional a
la imagen) para cerrar ese hueco. Un clic en el fondo abierto o sobre
una arista suelta no hace nada y avisa con False.

Este modulo es NumPy/OpenCV puro: no conoce Qt ni tokens de interfaz.
"""

import cv2
import numpy as np

METODOS = ("canny", "sobel", "laplaciano")


def detectar_bordes(imagen: np.ndarray, metodo: str, t1: int, t2: int) -> np.ndarray:
    """Mapa de bordes uint8 0/255 con la forma de `imagen` (2D uint8).

    - `canny`: cv2.Canny con (t1, t2) como (low, high).
    - `sobel`: magnitud sqrt(Gx^2+Gy^2) y umbral en t2.
    - `laplaciano`: |Laplace| y umbral en t2.
    """
    if metodo not in METODOS:
        raise ValueError(f"metodo de bordes desconocido: {metodo!r}")
    blur = cv2.GaussianBlur(imagen, (5, 5), 0)
    if metodo == "canny":
        return cv2.Canny(blur, t1, t2)
    if metodo == "sobel":
        gx = cv2.Sobel(blur, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(blur, cv2.CV_64F, 0, 1, ksize=3)
        mag = cv2.convertScaleAbs(cv2.magnitude(gx, gy))
        return np.where(mag >= t2, 255, 0).astype(np.uint8)
    lap = cv2.convertScaleAbs(cv2.Laplacian(blur, cv2.CV_64F, ksize=3))
    return np.where(lap >= t2, 255, 0).astype(np.uint8)


def _etiquetas_del_borde(etiquetas: np.ndarray) -> set:
    """Etiquetas de componentes que tocan el borde de la imagen.

    La etiqueta 0 (las paredes) se descarta: no es fondo alcanzable.
    """
    ids = set(
        etiquetas[0, :].tolist()
        + etiquetas[-1, :].tolist()
        + etiquetas[:, 0].tolist()
        + etiquetas[:, -1].tolist()
    )
    ids.discard(0)
    return ids


def _bolsillo_cerca(
    etq_libre: np.ndarray, fondo_ids: set, x: int, y: int, ancho: int, alto: int
) -> tuple[int | None, int | None]:
    """Pixel libre mas cercano (radio 3) que NO sea fondo abierto.

    Se usa cuando el clic cae sobre una pared: el bolsillo cerrado mas
    cercano es la pista de en que objeto se hizo clic.
    """
    for radio in range(1, 4):
        for dy in range(-radio, radio + 1):
            for dx in range(-radio, radio + 1):
                if max(abs(dx), abs(dy)) != radio:
                    continue  # solo el anillo exterior de cada radio
                nx, ny = x + dx, y + dy
                if not (0 <= nx < ancho and 0 <= ny < alto):
                    continue
                etiqueta = int(etq_libre[ny, nx])
                if etiqueta != 0 and etiqueta not in fondo_ids:
                    return nx, ny
    return None, None


def _contorno_sale_del_cuadro(
    mapa_bordes: np.ndarray, etq_paredes: np.ndarray, muro: int
) -> bool:
    """True si el contorno de este muro SALE del cuadro.

    El MARCO DE LA IMAGEN solo puede cerrar un contorno que llega al
    borde: sus extremos estan en el borde de la imagen (el objeto esta
    cortado). Un contorno cerrado (o roto por el medio) NO sale del
    cuadro: rellenar con el marco se llevaria el fondo entero.
    """
    crudo = (mapa_bordes > 0) & (etq_paredes == muro)
    if not np.any(crudo):
        return False
    alto, ancho = crudo.shape[:2]
    kernel = np.ones((3, 3), np.uint8)
    kernel[1, 1] = 0
    vecinos = cv2.filter2D(
        crudo.astype(np.uint8), -1, kernel, borderType=cv2.BORDER_CONSTANT
    )
    extremos = crudo & (vecinos == 1)  # pixeles con un solo vecino
    ys, xs = np.where(extremos)
    if len(xs) == 0:
        return False  # contorno cerrado: no sale del cuadro
    en_borde = (ys == 0) | (ys == alto - 1) | (xs == 0) | (xs == ancho - 1)
    return bool(en_borde.any())


def _region_con_muro(
    etq_paredes: np.ndarray,
    muro: int,
    sx: int,
    sy: int,
    con_marco: bool,
    radio: int = 0,
) -> tuple[np.ndarray, int, np.ndarray]:
    """Componentes libres usando SOLO el componente de pared `muro`.

    Con `con_marco` el marco de la imagen tambien hace de pared: el
    contorno que se escapa del cuadro queda cerrado por el borde. La
    region devuelta es la que contiene la semilla.

    `radio` dilata el muro (para cerrar un hueco del contorno) y
    devuelve el grosor a la region con la misma dilatacion.
    """
    pixeles = (etq_paredes == muro).astype(np.uint8) * 255
    if radio > 0:
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (2 * radio + 1, 2 * radio + 1)
        )
        pixeles = cv2.dilate(pixeles, kernel)
    if con_marco:
        lienzo = cv2.copyMakeBorder(pixeles, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=255)
        libre = (lienzo == 0).astype(np.uint8)
        _n, etiquetas = cv2.connectedComponents(libre, connectivity=4)
        etiqueta = int(etiquetas[sy + 2, sx + 2])
        region = (etiquetas == etiqueta)[2:-2, 2:-2]
        if radio > 0:
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (2 * radio + 1, 2 * radio + 1)
            )
            region = cv2.dilate(region.astype(np.uint8), kernel)
        return etiquetas, etiqueta, region
    libre = (pixeles == 0).astype(np.uint8)
    _n, etiquetas = cv2.connectedComponents(libre, connectivity=4)
    etiqueta = int(etiquetas[sy, sx])
    return etiquetas, etiqueta, etiquetas == etiqueta


def _objeto_con_marco(
    paredes: np.ndarray,
    etq_paredes: np.ndarray,
    etq_libre: np.ndarray,
    mapa_bordes: np.ndarray,
    sx: int,
    sy: int,
) -> np.ndarray | None:
    """Region del objeto cuando el contorno NO cierra dentro del cuadro.

    El MARCO DE LA IMAGEN hace de pared. El muro del objeto es su
    contorno PRINCIPAL: el componente de pared que, con el marco,
    enclose la region mas grande. Los bordes INTERNOS no son muros: se
    rellenan, y por eso el objeto queda SOLIDO (sin huecos).

    Si el contorno esta roto por el medio, se dilata un poco (radio
    proporcional a la imagen) para cerrar el hueco y se devuelve el
    grosor a la region.

    Devuelve None si el clic no esta en un objeto (p. ej. esta en el
    fondo de un objeto cerrado, o el contorno no cierra de ninguna
    forma y el relleno se llevaria el fondo entero).
    """
    # Las paredes que tocan el bolsillo de la semilla
    bolsillo = (etq_libre == int(etq_libre[sy, sx])).astype(np.uint8)
    vecinos = (cv2.dilate(bolsillo, np.ones((3, 3), np.uint8)) > 0) & (paredes > 0)
    muros = [int(m) for m in np.unique(etq_paredes[vecinos]) if m != 0]
    if not muros:
        return None

    alto, ancho = mapa_bordes.shape[:2]
    radio = max(3, int(round(min(alto, ancho) * 0.02)))

    elegido = None
    for paso in (0, radio):
        # Solo se aceptan muros que SEPARAN: el objeto y el fondo quedan
        # en dos partes. Un borde interno suelto no separa nada.
        separadores = []
        for muro in muros:
            # El MARCO DE LA IMAGEN solo puede cerrar un contorno que SALE
            # del cuadro (el objeto esta cortado por el borde de la
            # imagen). Un contorno cerrado lo cierra el propio borde
            # dibujado; uno roto por el medio no se puede cerrar de
            # ninguna forma: rellenar con el marco se llevaria el fondo
            # entero (o dejaria el objeto partido).
            if not _contorno_sale_del_cuadro(mapa_bordes, etq_paredes, muro):
                continue
            etq, etiqueta, region = _region_con_muro(
                etq_paredes, muro, sx, sy, True, paso
            )
            if etiqueta == 0:
                continue
            if len(set(np.unique(etq).tolist()) - {0}) < 2:
                continue
            area = int(np.count_nonzero(region))
            separadores.append((area, muro))
        if separadores:
            elegido = max(separadores)[1]
            break
    if elegido is None:
        return None

    # Si al otro lado del muro hay una region CERRADA, el objeto es un
    # agujero dentro del fondo: el clic esta en el fondo, no en el
    # objeto, y no se rellena.
    etq_sin, etiqueta_sin, _r = _region_con_muro(
        etq_paredes, elegido, sx, sy, False, radio
    )
    if etiqueta_sin != 0:
        otros = set(np.unique(etq_sin).tolist()) - {0, etiqueta_sin}
        cerrados = otros - _etiquetas_del_borde(etq_sin)
        if cerrados:
            return None

    _etq, etiqueta, region = _region_con_muro(etq_paredes, elegido, sx, sy, True, radio)
    if etiqueta == 0:
        return None
    salida = region.astype(np.uint8) * 255
    # El contorno detectado tambien es parte de la silueta.
    salida = cv2.bitwise_or(
        salida, ((mapa_bordes > 0) & (etq_paredes == elegido)).astype(np.uint8) * 255
    )
    return salida


def rellenar_bordes(
    mapa_bordes: np.ndarray, mascara: np.ndarray | None, punto: tuple[int, int]
) -> tuple[np.ndarray, bool]:
    """Rellena el objeto que encierran los bordes y lo acumula con OR.

    Devuelve `(mascara_acumulada, hubo_cambio)`. `hubo_cambio` es False
    si el clic no agrego pixeles: la semilla caia en el fondo abierto, o
    sobre una arista suelta que no encierra region, o la region ya
    estaba llena. `mascara=None` arranca en ceros. La mascara de entrada
    nunca se muta in-place.

    El relleno es POR OBJETO, no por bolsillo: los bordes internos no
    son paredes, son relleno. Por eso un solo clic deja el objeto
    entero y sin espacios.

    Si el contorno se escapa del cuadro, el MARCO DE LA IMAGEN hace de
    pared y el objeto se cierra con el borde de la imagen.
    """
    alto, ancho = mapa_bordes.shape[:2]
    base = (
        np.zeros((alto, ancho), np.uint8)
        if mascara is None
        else mascara.astype(np.uint8, copy=True)
    )
    x, y = int(punto[0]), int(punto[1])
    if not (0 <= x < ancho and 0 <= y < alto):
        return base, False

    # Paredes: los bordes detectados dilatados 3x3 para sellar huecos
    # de 1-2 px (una linea de borde casi nunca es continua).
    paredes = cv2.dilate((mapa_bordes > 0).astype(np.uint8), np.ones((3, 3), np.uint8))
    libre = (paredes == 0).astype(np.uint8)
    _n, etq_libre = cv2.connectedComponents(libre, connectivity=4)
    _n2, etq_paredes = cv2.connectedComponents(paredes, connectivity=8)

    # FONDO: componentes libres que tocan el borde de la imagen. Son el
    # fondo abierto: un clic ahi no puede seleccionar el objeto.
    fondo_ids = _etiquetas_del_borde(etq_libre)

    # La semilla: el bolsillo libre donde cae el clic. Si el clic cae
    # sobre una pared, se usa el bolsillo CERRADO mas cercano.
    if int(etq_libre[y, x]) != 0:
        sx, sy = x, y
    else:
        sx, sy = _bolsillo_cerca(etq_libre, fondo_ids, x, y, ancho, alto)
        if sx is None:
            return base, False

    if int(etq_libre[sy, sx]) not in fondo_ids:
        # CASO CERRADO: el objeto no toca el borde de la imagen.
        # OBJETOS: todo lo que no es fondo (paredes + bolsillos). Con
        # conectividad 8 los bolsillos de un mismo objeto quedan en un
        # solo componente: los une la pared que los encierra. Asi los
        # bordes internos dejan de partir el interior en regiones.
        objetos = np.where(np.isin(etq_libre, list(fondo_ids)), 0, 255).astype(np.uint8)
        _n3, etq_obj = cv2.connectedComponents(objetos, connectivity=8)
        componente = int(etq_obj[sy, sx])
        if componente == 0:
            return base, False
        # REGION: el componente del objeto menos el anillo exterior (las
        # paredes pegadas al fondo). Los bordes internos se quedan: son
        # relleno, no huecos.
        fondo = np.isin(etq_libre, list(fondo_ids)) & (libre > 0)
        anillo = (paredes > 0) & (
            cv2.dilate(fondo.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        )
        region = ((etq_obj == componente) & ~anillo).astype(np.uint8) * 255
        if not np.any((region > 0) & (libre > 0)):
            # Solo es una arista suelta del fondo: no encierra region.
            return base, False
        # GUARDA DE DENSIDAD: con los umbrales bajos los bordes forman
        # una malla conectada que cubre la foto entera y el "objeto"
        # seria la imagen completa. Cuando pasa eso, el mapa no delima
        # ningun objeto: se rellena SOLO la parte que hay bajo el clic
        # (el bolsillo local), que es lo que el usuario quiere al
        # "seleccionar una parte".
        if np.count_nonzero(region) > 0.85 * region.size:
            local = (etq_libre == int(etq_libre[sy, sx])).astype(np.uint8) * 255
            if np.any((local > 0) & (libre > 0)):
                region = local
    else:
        # CASO ABIERTO: el contorno se escapa del cuadro. El marco de la
        # imagen hace de pared y el objeto se cierra con el borde.
        region = _objeto_con_marco(paredes, etq_paredes, etq_libre, mapa_bordes, sx, sy)
        if region is None:
            return base, False

    nueva = cv2.bitwise_or(base, region)
    hubo_cambio = not np.array_equal(nueva, base)
    return nueva, hubo_cambio

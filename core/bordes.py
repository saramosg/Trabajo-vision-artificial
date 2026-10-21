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


def radio_cierre(alto: int, ancho: int) -> int:
    """Radio del cierre morfologico del mapa de bordes.

    Proporcional al lado menor (5 %) para cerrar los huecos del
    contorno, con TOPE de 45 px: en una foto de 4000 px un radio
    proporcional (200 px) fundiria la textura de la piel en una sola
    mancha y el mapa dejaria de servir. Medido sobre las fotos del
    proyecto: con radio 5 % (tope 45) los rellenos que se comian la
    foto entera pasan a ser 0.
    """
    return min(45, max(2, int(round(min(alto, ancho) * 0.05))))


def cerrar_mapa(mapa: np.ndarray, radio: int) -> np.ndarray:
    """Cierre morfologico del mapa de bordes (dilata y luego erosiona).

    Une los extremos de la linea que estaban separados: el contorno de
    un objeto sale con huecos de varios pixeles y, sin cerrarlos, el
    interior se une con el fondo y el relleno se lleva la foto entera.
    No engrosa la linea (por eso es cierre y no solo dilatacion).

    El kernel es una ELIPSE y no un rectangulo: el rectangular es mas
    agresivo (convierte en puente un hueco de 5 px entre un borde
    interno y el exterior del objeto, y el objeto deja de quedar
    solido). Se paga con el tiempo: 0,96 s en una foto de 45 MP.
    """
    if radio <= 0:
        return mapa
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * radio + 1, 2 * radio + 1)
    )
    return cv2.morphologyEx(mapa, cv2.MORPH_CLOSE, kernel)


def _histeresis(magnitud: np.ndarray, t1: int, t2: int) -> np.ndarray:
    """Umbral con histeresis para Sobel y Laplaciano (como el de Canny).

    Un pixel "debil" (entre t1 y t2) se conserva solo si esta conectado
    a uno fuerte (>= t2). Con un solo umbral el contorno sale partido en
    tropezones sueltos y t1 no hacia nada: con la histeresis los dos
    sliders tienen sentido en los tres metodos.
    """
    bajo, fuerte = (t1, t2) if t1 <= t2 else (t2, t1)
    if bajo <= 0:
        return (magnitud >= fuerte).astype(np.uint8) * 255
    mascara = (magnitud >= bajo).astype(np.uint8)
    n, etiquetas = cv2.connectedComponents(mascara, connectivity=8)
    Mask_ = magnitud >= fuerte
    if not Mask_.any():
        return np.zeros_like(magnitud, np.uint8)
    etq_fuerte = etiquetas[Mask_]
    etq_fuerte = etq_fuerte[etq_fuerte > 0]
    if etq_fuerte.size == 0:
        return np.zeros_like(magnitud, np.uint8)
    conservar = np.zeros(n, bool)
    conservar[etq_fuerte] = True
    return np.where(conservar[etiquetas], 255, 0).astype(np.uint8)


def detectar_bordes(imagen: np.ndarray, metodo: str, t1: int, t2: int) -> np.ndarray:
    """Mapa de bordes uint8 0/255 con la forma de `imagen` (2D uint8).

    - `canny`: cv2.Canny con (t1, t2) como (low, high).
    - `sobel`: magnitud sqrt(Gx^2+Gy^2) con histéresis (t1 bajo, t2 alto).
    - `laplaciano`: |Laplace| con histéresis (t1 bajo, t2 alto).

    El mapa sale CRUDO (sin cerrar): el cierre morfologico se hace en
    `rellenar_bordes`, que es donde importa (el usuario ve el mapa tal
    como lo detecta el metodo, y en fotos grandes cerrarlo aqui
    fundiria la textura de la piel en una sola mancha).
    """
    if metodo not in METODOS:
        raise ValueError(f"metodo de bordes desconocido: {metodo!r}")
    blur = cv2.GaussianBlur(imagen, (5, 5), 0)
    if metodo == "canny":
        return cv2.Canny(blur, int(t1), int(t2))
    if metodo == "sobel":
        gx = cv2.Sobel(blur, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(blur, cv2.CV_64F, 0, 1, ksize=3)
        mag = cv2.convertScaleAbs(cv2.magnitude(gx, gy))
        return _histeresis(mag, int(t1), int(t2))
    lap = cv2.convertScaleAbs(cv2.Laplacian(blur, cv2.CV_64F, ksize=3))
    return _histeresis(lap, int(t1), int(t2))


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
    metodo: str = "canny",
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
            # El MARCO DE LA IMAGEN solo cuenta si el contorno SALE del
            # cuadro: entonces el objeto esta cortado por la imagen y el
            # marco lo cierra. Si el contorno no sale, la region la acota
            # el propio contorno (sin marco): si no, el marco cerraria
            # cualquier region y el relleno se extenderia mas alla del
            # objeto (se comeria el fondo de alrededor).
            sale = _contorno_sale_del_cuadro(mapa_bordes, etq_paredes, muro)
            etq, etiqueta, region = _region_con_muro(
                etq_paredes, muro, sx, sy, sale, paso
            )
            if etiqueta == 0:
                continue
            if len(set(np.unique(etq).tolist()) - {0}) < 2:
                continue
            area = int(np.count_nonzero(region))
            # Una region que se come casi todo el cuadro no es de fiar:
            # el contorno esta roto por el medio y el relleno se llevaria
            # el fondo entero.
            if area > 0.85 * region.size and not sale:
                continue
            separadores.append((area, muro))
        if separadores:
            elegido = max(separadores)[1]
            break
    if elegido is None:
        return None

    # Si al otro lado del muro hay una region CERRADA, puede ser el
    # objeto (el clic esta en el fondo) o un bolsillo interno (el clic
    # esta en el objeto).
    #   - Con un mapa limpio (canny) el hueco es el objeto: se descarta.
    #   - Con sobel/laplaciano el objeto sale partido en bolsillos
    #     pequenos y el hueco puede ser cualquiera de ellos: solo se
    #     descarta si el hueco es GRANDE (aun asi seria el objeto).
    etq_sin, etiqueta_sin, _r = _region_con_muro(
        etq_paredes, elegido, sx, sy, False, radio
    )
    if etiqueta_sin != 0:
        otros = set(np.unique(etq_sin).tolist()) - {0, etiqueta_sin}
        cerrados = otros - _etiquetas_del_borde(etq_sin)
        if cerrados:
            if metodo == "canny":
                return None
            lado = int(np.count_nonzero(etq_sin == etiqueta_sin))
            mayor = max(int(np.count_nonzero(etq_sin == e)) for e in cerrados)
            # El hueco del otro lado es el OBJETO (el clic esta en el
            # fondo) solo si es grande; un bolsillo interno del objeto es
            # pequeno y no puede ser el objeto.
            if mayor > 0.20 * lado:
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
    mapa_bordes: np.ndarray,
    mascara: np.ndarray | None,
    punto: tuple[int, int],
    metodo: str = "canny",
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

    # Paredes: el mapa de bordes CERRADO (une los huecos del contorno)
    # y luego dilatado 3x3 para sellar los huecos de 1-2 px que quedan.
    # El cierre va aqui y no en `detectar_bordes` a proposito: el mapa
    # que ve el usuario sigue siendo el crudo y en fotos grandes
    # cerrarlo ahi fundiria la textura de la piel en una sola mancha.
    # El cierre morfologico solo se aplica a CANNY: su mapa es una linea
    # de 1 px, y cerrarla solo tapa los huecos del contorno (sin el, el
    # interior se une con el fondo y el relleno se lleva la foto entera).
    # En sobel/laplaciano el mapa es una banda de 3-4 px con ruido:
    # cerrarlo fusiona la textura con el contorno y el relleno se
    # extiende mas alla del objeto (medido: la sobreextension sube del
    # 8 % al 11 % y el maximo del 25 % al 49 %).
    if metodo == "canny":
        mapa = cerrar_mapa(mapa_bordes, radio_cierre(alto, ancho))
    else:
        mapa = mapa_bordes
    paredes = cv2.dilate((mapa > 0).astype(np.uint8), np.ones((3, 3), np.uint8))
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
        region = _objeto_con_marco(
            paredes, etq_paredes, etq_libre, mapa_bordes, sx, sy, metodo
        )
        if region is None:
            return base, False

    nueva = cv2.bitwise_or(base, region)
    hubo_cambio = not np.array_equal(nueva, base)
    return nueva, hubo_cambio

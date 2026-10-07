"""Segmentacion del objeto y utilidades de mascara binaria.

Modelos disponibles (`segmentar`):
- `grabcut` (predeterminado): recorta al 10 % de los bordes y segmenta
  sobre una copia reducida (lado mayor 500 px) por velocidad; la mascara
  se devuelve al tamano original con vecino mas cercano.
- `otsu`: umbral de Otsu por canal RGB unidos con OR; si el blanco es
  mayoria se invierte (el objeto es la region minoritaria).

Ambos pasan la misma limpieza: cierre morfologico y conservar solo el
componente conexo mayor.

Utilidades derivadas:
- `limpiar_mascara`: rellena huecos internos (flood fill desde el fondo
  exterior) y elimina islas flotantes (componente mayor).
- `contorno`: perimetro de 1 px del objeto, sin relleno.
"""
import cv2
import numpy as np


def _a_escala(imagen: np.ndarray, lado: int = 500):
    """Copia reducida SOLO para segmentar. Devuelve (imagen, escala)."""
    alto, ancho = imagen.shape[:2]
    escala = min(1.0, lado / max(alto, ancho))
    if escala == 1.0:
        return np.ascontiguousarray(imagen), 1.0
    return (np.ascontiguousarray(
                cv2.resize(imagen, (max(1, int(round(ancho * escala))),
                                    max(1, int(round(alto * escala)))),
                           interpolation=cv2.INTER_AREA)),
            escala)


def _devolver_a_escala(mascara: np.ndarray, escala: float,
                       forma_original: tuple[int, int]) -> np.ndarray:
    """Reescala la mascara al tamano original. INTER_NEAREST, no bilineal."""
    if escala == 1.0:
        return mascara
    return cv2.resize(mascara, (forma_original[1], forma_original[0]),
                      interpolation=cv2.INTER_NEAREST)


def _grabcut(imagen: np.ndarray) -> np.ndarray:
    """GrabCut con rect al 10 % de los bordes (GC_INIT_WITH_RECT)."""
    alto, ancho = imagen.shape[:2]
    margen = max(1, int(round(min(alto, ancho) * 0.10)))
    rect = (margen, margen, ancho - 2 * margen, alto - 2 * margen)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    mascara = np.zeros((alto, ancho), np.uint8)
    cv2.grabCut(imagen, mascara, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
    return np.where((mascara == cv2.GC_FGD) | (mascara == cv2.GC_PR_FGD),
                    255, 0).astype(np.uint8)


def _otsu(imagen: np.ndarray) -> np.ndarray:
    """OTSU por canal, unidos con bitwise_or. Si el blanco es mayoria, se invierte."""
    binaria = None
    for c in range(imagen.shape[2]):
        _, canal = cv2.threshold(imagen[:, :, c], 0, 255,
                                 cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        binaria = canal if binaria is None else cv2.bitwise_or(binaria, canal)
    if np.count_nonzero(binaria) > binaria.size // 2:
        binaria = cv2.bitwise_not(binaria)
    return binaria


def segmentar(imagen: np.ndarray, modelo: str = "grabcut") -> np.ndarray:
    """Mascara binaria del objeto: uint8 0/255, con la forma de `imagen`."""
    if modelo not in ("grabcut", "otsu"):
        raise ValueError(f"modelo de segmentacion desconocido: {modelo!r}")
    forma_original = imagen.shape[:2]
    pequena, escala = _a_escala(imagen)
    if modelo == "grabcut":
        binaria = _grabcut(pequena)
    else:
        binaria = _otsu(pequena)
    binaria = _devolver_a_escala(binaria, escala, forma_original)

    # Limpieza comun: cierre morfologico y quedarse con el componente mayor.
    kernel = np.ones((3, 3), np.uint8)
    binaria = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, kernel, iterations=2)
    numero, marcada = cv2.connectedComponents((binaria > 0).astype(np.uint8))
    if numero > 1:
        mayor = int(np.argmax(np.bincount(marcada.ravel())[1:]) + 1)
        binaria = np.where(marcada == mayor, 255, 0).astype(np.uint8)
    return binaria


def limpiar_mascara(mascara: np.ndarray,
                    area_minima: float = 0.01) -> np.ndarray:
    """Rellena huecos internos y elimina islas flotantes (uint8 0/255).

    1. Huecos: floodFill desde el fondo exterior (region growing del
       fondo, Tarea 6/7); lo no alcanzado dentro del objeto son huecos y
       se encienden. Equivale al cierre morfologico (dilatar x3 +
       erosionar x3) de la Tarea 6, pero exacto.
    2. Islas: se conservan los componentes con area >= `area_minima`
       (fraccion del total, 1 % por defecto) en vez del ganador unico:
       con fondos en rango todo conectaba en un ~100 % blanco.
    Vacia o llena entra igual y sale igual (la pantalla decide avisar).
    """
    binaria = (mascara > 0).astype(np.uint8) * 255
    if not np.any(binaria):
        return binaria
    alto, ancho = binaria.shape[:2]
    total = alto * ancho
    # Semilla en un pixel de FONDO del borde: si (0,0) cae sobre el objeto
    # (p. ej. isla en la esquina) el floodFill marcaria el objeto como
    # exterior y el relleno fallaria.
    ys, xs = np.where(binaria == 0)
    if len(xs) == 0:
        rellena = binaria  # todo blanco: no hay fondo ni huecos
    else:
        # La semilla tiene que estar en el FONDO EXTERIOR: un hueco tambien
        # es negro, pero sembrar ahi convertiria el fondo en objeto. Por
        # eso se busca primero en el borde; si el objeto toca todo el
        # borde no hay exterior distinguible y se omite el relleno.
        borde_negro = np.concatenate([binaria[0, :], binaria[-1, :],
                                      binaria[:, 0], binaria[:, -1]])
        if not np.any(borde_negro == 0):
            rellena = binaria
        else:
            dist = np.minimum(np.minimum(xs, ancho - 1 - xs),
                              np.minimum(ys, alto - 1 - ys))
            i = int(np.argmin(dist))
            exterior = binaria.copy()
            cv2.floodFill(exterior, np.zeros((alto + 2, ancho + 2), np.uint8),
                          (int(xs[i]), int(ys[i])), 255)
            rellena = cv2.bitwise_or(binaria, cv2.bitwise_not(exterior))
    numero, marcada = cv2.connectedComponents(
        (rellena > 0).astype(np.uint8))
    if numero > 2:  # fondo + 2 o mas regiones: solo las de area suficiente
        tamanos = np.bincount(marcada.ravel())
        validas = [e for e in range(1, numero)
                   if tamanos[e] >= area_minima * total]
        if validas:
            rellena = np.where(np.isin(marcada, validas), 255, 0).astype(np.uint8)
    return rellena


def contorno(mascara: np.ndarray) -> np.ndarray:
    """Borde externo del objeto en blanco sobre negro (uint8 0/255).

    Solo el perimetro, nunca relleno: `findContours` + `drawContours` con
    grosor 1 (Tarea 1: `findContours(img_bin, RETR_TREE, CHAIN_APPROX_SIMPLE)`
    + `drawContours`; Tarea 7: Canny da "linea continua de ancho unitario").
    Un grosor mayor se ve macizo al reducir a la miniatura de 250x250.
    """
    binaria = (mascara > 0).astype(np.uint8) * 255
    contornos, _ = cv2.findContours(binaria, cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)
    salida = np.zeros_like(binaria)
    cv2.drawContours(salida, contornos, -1, 255, 1)
    return salida

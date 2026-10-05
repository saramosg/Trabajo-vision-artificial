"""Extraccion de canales RGB / YCM y modos de visualizacion.

Canales:
- RGB: cada letra es un canal directo (R=0, G=1, B=2).
- YCM: promedios en float32 para no desbordar (Y=(R+G)/2, C=(G+B)/2,
  M=(R+B)/2) convertidos a uint8.

Modos (solo `color` y `blanco y negro`):
- `color`: el canal activo conserva sus componentes y el resto va a 0.
- `blanco y negro`: el componente 2D tal cual.

`etiqueta_canal` da el texto en espanol del campo "Canal actual"
(p. ej. "RGB - Azul"). Este modulo no conoce colores de interfaz: solo
devuelve arrays y texto.
"""
import numpy as np

NOMBRES_CANAL = {
    "R": "Rojo", "G": "Verde", "B": "Azul",
    "Y": "Amarillo", "C": "Cian", "M": "Magenta",
}

_INDICE_RGB = {"R": 0, "G": 1, "B": 2}


def canal_rgb(imagen: np.ndarray, letra: str) -> np.ndarray:
    """Componente 2D del canal R/G/B."""
    return imagen[:, :, _INDICE_RGB[letra]]


def componente_ycm(imagen: np.ndarray, letra: str) -> np.ndarray:
    """Componente 2D de Y/C/M como promedio en float32 -> uint8 (sin desbordar).

    Y = (R + G) / 2 ; C = (G + B) / 2 ; M = (R + B) / 2
    """
    r = imagen[:, :, 0].astype(np.float32)
    g = imagen[:, :, 1].astype(np.float32)
    b = imagen[:, :, 2].astype(np.float32)
    if letra == "Y":
        valor = (r + g) / 2.0
    elif letra == "C":
        valor = (g + b) / 2.0
    elif letra == "M":
        valor = (r + b) / 2.0
    else:
        raise ValueError(f"canal YCM invalido: {letra!r}")
    return valor.astype(np.uint8)


def componente(imagen: np.ndarray, espacio: str, letra: str) -> np.ndarray:
    """Componente 2D (uint8) del canal, en el espacio RGB o YCM."""
    if espacio not in ("RGB", "YCM"):
        raise ValueError(f"espacio de color invalido: {espacio}")
    if espacio == "RGB":
        return canal_rgb(imagen, letra)
    return componente_ycm(imagen, letra)


def modo_color(imagen: np.ndarray, letra: str) -> np.ndarray:
    """Array 3D con la representacion en color del canal.

    R = (R,0,0)  G = (0,G,0)  B = (0,0,B)  (otros componentes en 0)
    Y = (R,G,0)  C = (0,G,B)  M = (R,0,B)
    """
    r = imagen[:, :, 0]
    g = imagen[:, :, 1]
    b = imagen[:, :, 2]
    cero = np.zeros_like(r)
    if letra == "R":
        return np.dstack([r, cero, cero])
    if letra == "G":
        return np.dstack([cero, g, cero])
    if letra == "B":
        return np.dstack([cero, cero, b])
    if letra == "Y":
        return np.dstack([r, g, cero])
    if letra == "C":
        return np.dstack([cero, g, b])
    if letra == "M":
        return np.dstack([r, cero, b])
    raise ValueError(f"canal invalido: {letra!r}")


def modo_blanco_y_negro(componente_canal: np.ndarray) -> np.ndarray:
    """El canal en 2D (ya es monocromatico)."""
    return componente_canal


def aplicar_modo(imagen: np.ndarray, espacio: str, letra: str, modo: str) -> np.ndarray:
    """Devuelve el array del canal segun el modo `color` | `blanco y negro`."""
    if modo == "color":
        return modo_color(imagen, letra)
    if modo == "blanco y negro":
        return modo_blanco_y_negro(componente(imagen, espacio, letra))
    raise ValueError(f"modo invalido: {modo!r}")


def etiqueta_canal(espacio: str, letra: str) -> str:
    """'RGB' o 'YCM' + el nombre del canal en espanol. Ej.: 'RGB - Azul'."""
    if espacio not in ("RGB", "YCM"):
        raise ValueError(f"espacio de color invalido: {espacio}")
    return f"{espacio} - {NOMBRES_CANAL[letra]}"

"""Carga/guardado de imagenes y estado compartido de la app.

Este modulo es la unica via de entrada/salida de archivos de imagen y el
hogar del `EstadoImagen`, el objeto que comparten por referencia las cinco
pantallas (principal, RGB, YCM, histograma y recorte).

Convenciones que el resto del codigo da por supuestas:
- `original` es siempre RGB uint8 de 3 canales, forma (alto, ancho, 3).
- `original` nunca se modifica: el preprocesado escribe copias.
- La mascara es uint8 con 255 = objeto, 0 = fondo.

Regla de dependencias: `core/` nunca importa de `ui/`.
"""
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass
class EstadoImagen:
    ruta: str | None = None
    original: np.ndarray | None = None   # RGB, nunca se modifica
    preprocesada: np.ndarray | None = None
    mascara: np.ndarray | None = None    # uint8, 255 = objeto
    modelo: str = "grabcut"              # "grabcut" | "otsu"
    modo: str = "color"                  # "color" | "blanco y negro"
    espacio: str = "RGB"                 # "RGB" | "YCM"
    canal_actual: str = "R"              # "R".."M"
    inf: int = 0                         # limite inferior del histograma (0-255)
    sup: int = 255                       # limite superior del histograma (0-255)
    recorte: tuple[int, int, int, int] | None = None   # (x, y, ancho, alto) del marco FIJO en px de la ORIGINAL (puede salirse)
    factor: float = 1.0                      # 1.0 siempre en modo A y al abrir modo B
    vista_previa: np.ndarray | None = None    # render de LADO_SALIDA ya hecho

    def invalidar_vista_previa(self) -> None:
        """Borra la vista previa (§6.5 regla 12). No limpia `recorte`."""
        self.vista_previa = None


def cargar_imagen(ruta: str) -> np.ndarray:
    """Carga SIEMPRE 8 bits y 3 canales en orden RGB.

    IMREAD_COLOR fuerza 8 bits y 3 canales, venga lo que venga el archivo.
    """
    bgr = cv2.imread(ruta, cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(ruta)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def guardar_imagen(ruta: str, rgb: np.ndarray, mascara: np.ndarray) -> None:
    """PNG RGBA con fondo transparente: np.dstack([rgb, mascara])."""
    rgba = np.dstack([rgb[:, :, :3], mascara])
    Image.fromarray(rgba, mode="RGBA").save(ruta)


def guardar_rgb(ruta: str, rgb: np.ndarray) -> None:
    """PNG/JPEG RGB tal cual, sin canal alfa (§6.5: guardar copia)."""
    Image.fromarray(rgb[:, :, :3]).save(ruta)


def guardar_mascara(ruta: str, mascara: np.ndarray) -> None:
    """PNG de 8 bits en escala de grises (255 = objeto)."""
    Image.fromarray(mascara.astype(np.uint8), mode="L").save(ruta)


def guardar_psd(ruta: str, rgb: np.ndarray, mascara: np.ndarray) -> None:
    """PSD con la capa RGB completa y la mascara como mascara de capa."""
    from psd_tools import PSDImage

    alto, ancho = rgb.shape[:2]
    psd = PSDImage.new("RGB", (ancho, alto))
    capa = psd.create_pixel_layer(Image.fromarray(rgb[:, :, :3]), name="objeto")
    capa.create_mask(Image.fromarray(mascara.astype(np.uint8), mode="L"))
    psd.save(ruta)

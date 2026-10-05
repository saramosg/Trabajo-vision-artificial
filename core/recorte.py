"""Recorte libre a 512x512 con relleno blanco (§6.5 actual).

La ventana de recorte usa un marco FIJO en pantalla y exporta desde la
imagen ORIGINAL: la seleccion (x, y, ancho, alto) rara vez mide 512, asi
que `recorte_libre` la remuestrea con warpAffine y pinta de blanco lo que
caiga fuera de la imagen. Implementaciones anteriores (`recortar`,
`escalar`, `lienzo_blanco`, `aplicar_recorte`) quedan como referencia en
`requisitos.md` §7.7.

core/ no importa Qt: todo son numeros planos y arrays.
"""
import cv2
import numpy as np


def recorte_libre(imagen: np.ndarray, x: int, y: int, ancho: int, alto: int,
                  lado: int, relleno: int = 255) -> np.ndarray:
    """Ventana (x, y, ancho, alto) del lienzo -> imagen de lado x lado.

    La ventana sale del marco FIJO en pantalla: mide lo que mida en px
    del lienzo (cambia con el zoom) y puede estar total o parcialmente
    fuera. Se remuestrea a `lado` y lo de fuera sale BLANCO.
    """
    lado, ancho, alto = int(lado), int(ancho), int(alto)
    if lado <= 0 or ancho <= 0 or alto <= 0:
        raise ValueError("lado, ancho y alto deben ser enteros positivos")
    if imagen.ndim == 2:
        fondo = (int(relleno),)
    else:
        fondo = tuple([int(relleno)] * imagen.shape[2])
    matriz = np.array([[lado / ancho, 0, -x * lado / ancho],
                       [0, lado / alto, -y * lado / alto]], np.float64)
    return cv2.warpAffine(imagen, matriz, (lado, lado),
                         flags=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=fondo)

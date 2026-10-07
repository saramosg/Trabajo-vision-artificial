"""Histograma de intensidades y mascaras por rango.

- `histograma_canal`: 256 conteos de un componente 2D uint8.
- `figura_histograma`: PNG estilo curso (modulo 2: `plt.hist` + titulo y
  etiquetas) con lineas rojas en inf/sup (modulo 8) y eje Y dinamico al
  105 % del pico sin fondo. Se renderiza con el backend Agg (sin ventana).
- `mascara_por_rango`: binaria 0/255 del componente B/N dentro de
  [inf, sup]; es lo que usan el contorno y el preview del histograma.
"""
import io

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def histograma_canal(canal: np.ndarray) -> np.ndarray:
    """256 bins. El .ravel() es obligatorio: sin el NumPy lanza con arrays 2D/3D."""
    return np.bincount(canal.ravel(), minlength=256).astype(np.int64)


def figura_histograma(componente: np.ndarray, inf: int = 0,
                      sup: int = 255) -> bytes:
    """PNG del histograma estilo modulo 2 (Tarea 1):

    plt.hist(img_gray.ravel(), 256) + titulo 'Histograma' +
    xlabel 'Intensidad del pixel' + ylabel 'Cantidad de pixeles'.
    Las lineas de inf/sup van con axvline rojo (Tarea 7).
    """
    gris = np.ascontiguousarray(componente).ravel()
    fig = plt.figure(figsize=(4.67, 3.33), dpi=100)
    try:
        # Solo para pintar: submuestreo (una 45 MP por tick congelaba la
        # UI). Los bins y el ylim siguen exactos con todos los pixeles.
        paso = max(1, gris.size // 2_000_000)
        plt.hist(gris[::paso], 256)
        plt.axvline(x=int(inf), color="red")
        plt.axvline(x=int(sup), color="red")
        # Altura dinamica: 5 % por encima del bin maximo de la imagen
        # completa, sin tener en cuenta los sliders. Se excluyen los
        # saturados (0-5 y 250-255: fondos negros/blancos y su degradado
        # JPEG) y, si el pico restante supera 5 veces al segundo, tambien
        # ese dominante (fondo liso de tono medio). Si no queda nada, se
        # usa el maximo global. Recortar picos es lo mismo que el zoom
        # `ylim(0, 5000)` de la Tarea 1 para ver el detalle.
        conteos = np.bincount(gris.astype(np.uint8), minlength=256)
        interior = conteos[6:250].astype(np.int64)
        if int(interior.max()) > 0:
            ordenados = np.sort(interior)
            m1, m2 = int(ordenados[-1]), int(ordenados[-2])
            pico = m2 if m1 > 5 * max(m2, 1) else m1
        else:
            pico = 0
        if pico <= 0:
            pico = int(conteos.max())
        plt.ylim(0, max(1, pico * 1.05))
        plt.title("Histograma")
        plt.xlabel("Intensidad del pixel")
        plt.ylabel("Cantidad de pixeles")
        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        return buf.getvalue()
    finally:
        plt.close(fig)


def mascara_por_rango(componente: np.ndarray, inf: int, sup: int) -> np.ndarray:
    """Mascara binaria desde el canal en blanco y negro.

    255 donde `inf <= valor <= sup`, 0 fuera. Si el rango viene invertido
    se ordena: un rango vacio daria una mascara vacia sin avisar.
    """
    lo, hi = (int(inf), int(sup)) if int(inf) <= int(sup) \
        else (int(sup), int(inf))
    comp = np.ascontiguousarray(componente)
    return np.where((comp >= lo) & (comp <= hi), 255, 0).astype(np.uint8)

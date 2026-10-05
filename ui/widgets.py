"""Widgets reutilizables de imagen (§5.5).

Quedan solo los que usa la app: `a_pixmap` (numpy -> QPixmap, con soporte
RGB/RGBA/grises) y `ProporcionImagen` (QLabel que encaja la foto sin
deformarla, centrada, con KeepAspectRatio). El histograma se renderiza
con matplotlib (modulo 2) y el recorte usa `VistaRecorte` (QGraphicsView)
en `ui/ventana_recorte.py`; las versiones QPainter anteriores viven en
`requisitos.md` como referencia.
"""
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QPainter
from PySide6.QtWidgets import QLabel, QSizePolicy


def a_pixmap(imagen) -> QPixmap:
    """np.ndarray RGB/RGBA/2D -> QPixmap. Copia el buffer: QImage no lo mantiene vivo.

    Se fuerza C-contiguo: `canal_rgb` devuelve una vista (`imagen[:, :, 0]`)
    cuyos strides no coinciden con el ancho, y `QImage` exige un buffer
    C-contiguo (si no, lanza BufferError).
    """
    if imagen is None:
        return QPixmap()
    imagen = np.ascontiguousarray(imagen)
    alto, ancho = imagen.shape[:2]
    if imagen.ndim == 2:
        return QPixmap.fromImage(
            QImage(imagen.data, ancho, alto, ancho,
                   QImage.Format_Grayscale8).copy())
    if imagen.shape[2] == 4:
        return QPixmap.fromImage(
            QImage(imagen.data, ancho, alto, ancho * 4,
                   QImage.Format_RGBA8888).copy())
    return QPixmap.fromImage(
        QImage(imagen.data, ancho, alto, ancho * 3,
               QImage.Format_RGB888).copy())


# --------------------------------------------------------------------------
# §5.5 ProporcionImagen
# --------------------------------------------------------------------------
class ProporcionImagen(QLabel):
    """Dibuja una imagen respetando siempre la proporcion del cuadro."""

    def __init__(self, razon, size_minimo, parent=None):
        super().__init__(parent)
        self.razon = razon                     # (ancho, alto) del Figma
        self._original = QPixmap()
        self._ajustada = QPixmap()
        self.setMinimumSize(*size_minimo)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)

    def set_imagen(self, pixmap):
        self._original = pixmap
        self._recalcular()
        self.update()

    def _recalcular(self):
        if self._original.isNull():
            return
        if self.width() <= 0 or self.height() <= 0:
            return
        if self._original.width() <= 0 or self._original.height() <= 0:
            return
        escala = min(self.width() / self._original.width(),
                     self.height() / self._original.height())
        ancho = max(1, round(self._original.width() * escala))
        alto = max(1, round(self._original.height() * escala))
        self._ajustada = self._original.scaled(
            ancho, alto, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._recalcular()

    def paintEvent(self, evento):
        super().paintEvent(evento)
        if self._ajustada.isNull():
            return
        p = QPainter(self)
        x = (self.width() - self._ajustada.width()) // 2
        y = (self.height() - self._ajustada.height()) // 2
        p.drawPixmap(x, y, self._ajustada)
        p.end()

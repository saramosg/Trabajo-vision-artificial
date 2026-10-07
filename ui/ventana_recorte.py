"""Pantalla de recorte y redimensionado (§6.5).

Marco FIJO en pantalla (`VistaRecorte`); la imagen se escala (slider) y se
panea (arrastre) debajo. "Redimensionar" exporta con `recorte_libre()` a
512 con blanco fuera, y solo entonces se habilitan los botones de guardado.
"""
import os

from PySide6.QtCore import QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen, QPixmap, QShortcut, QTransform
from PySide6.QtWidgets import (QFileDialog, QFrame, QGraphicsScene,
                               QGraphicsView, QHBoxLayout, QLabel, QMessageBox,
                               QPushButton, QSlider, QVBoxLayout,
                               QWidget)

from core import imagen as core_imagen
from core import recorte
from ui import tokens
from ui.helpers import envolver_en_scroll
from ui.widgets import ProporcionImagen, a_pixmap


class VistaRecorte(QGraphicsView):
    """Lienzo con marco FIJO en pantalla (precedente WhatsApp/GIMP).

    La imagen se escala (slider) y se panea (arrastre) debajo del marco;
    el marco es un cuadrado fijo centrado del viewport y nunca cambia con
    el zoom. Solo pinta el estado: escala/paneo viven en la vista.
    """

    marcoCambiado = Signal()

    REL_MIN, REL_MID, REL_MAX = 0.25, 1.0, 4.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setObjectName("lienzoImagen")
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFrameShape(QFrame.NoFrame)
        self.setCursor(Qt.OpenHandCursor)
        self._arrastrando = False
        self._ultimo = None
        self._rel = VistaRecorte.REL_MID
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFrameShape(QFrame.NoFrame)
        # Barras ocultas: aparecen/desaparecen con el zoom y moverian el
        # marco fijo (581 -> 567). El paneo va por arrastre y flechas.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    # --- estado ---------------------------------------------------
    def set_imagen(self, pixmap: QPixmap) -> None:
        self.scene().clear()
        if pixmap.isNull():
            return
        item = self.scene().addPixmap(pixmap)
        marco = item.boundingRect()
        margen = max(marco.width(), marco.height())
        # Escena acolchada: el paneo es (casi) libre y el marco puede
        # salir total o parcialmente de la imagen.
        self.scene().setSceneRect(marco.adjusted(-margen, -margen,
                                                 margen, margen))
        self.centerOn(marco.center())

    def _encaje(self) -> float:
        """Escala en la que el lienzo cabe justo (rel = 1.0). Se calcula
        en vivo para no depender del tamano del viewport al cargar."""
        items = self.scene().items()
        if not items:
            return 1.0
        marco = items[0].boundingRect()
        if marco.width() <= 0 or marco.height() <= 0:
            return 1.0
        vw, vh = self.viewport().width(), self.viewport().height()
        if vw <= 0 or vh <= 0:
            return 1.0
        return min(vw / marco.width(), vh / marco.height())

    def set_zoom_rel(self, rel: float) -> None:
        """Escala SOLO la imagen alrededor del centro (marco intacto)."""
        if rel > 0:
            self._rel = float(rel)
        self._aplicar()

    def _aplicar(self) -> None:
        """Transform = encaje_en_vivo x rel. Recalcular en cada resize
        evita depender del tamano del viewport al cargar (podia ser 0)."""
        if not self.scene().items():
            return
        s = self._encaje() * self._rel
        if s > 0:
            self.setTransform(QTransform(s, 0, 0, 0, s, 0, 0, 0, 1))

    def marco_vista(self) -> QRect:
        """Cuadrado FIJO al 70 % del viewport, centrado. Solo depende del
        tamano del widget, nunca del zoom."""
        lado = max(64, int(round(min(self.viewport().width(),
                                    self.viewport().height()) * 0.70)))
        return QRect((self.viewport().width() - lado) // 2,
                     (self.viewport().height() - lado) // 2, lado, lado)

    def seleccion(self) -> QRect:
        """Marco en coordenadas de la imagen original (puede salirse)."""
        if not self.scene().items():
            return QRect()
        marco = self.mapToScene(self.marco_vista()).boundingRect()
        return QRect(int(round(marco.x())), int(round(marco.y())),
                     max(1, int(round(marco.width()))),
                     max(1, int(round(marco.height()))))

    # --- eventos --------------------------------------------------
    def drawForeground(self, pintor: QPainter, _rect: QRectF) -> None:
        marco = self.marco_vista()
        vista = self.viewport().rect()
        pintor.save()
        pintor.resetTransform()  # overlay en coords de pantalla, no escena
        velo = QColor(0, 0, 0, 128)
        arriba = QRect(vista.left(), vista.top(), vista.width(),
                       max(0, marco.top() - vista.top()))
        if arriba.height() > 0:
            pintor.fillRect(arriba, velo)
        abajo = QRect(vista.left(), marco.bottom() + 1, vista.width(),
                      max(0, vista.bottom() - marco.bottom()))
        if abajo.height() > 0:
            pintor.fillRect(abajo, velo)
        izquierda = QRect(vista.left(), marco.top(),
                          max(0, marco.left() - vista.left()),
                          marco.height())
        if izquierda.width() > 0:
            pintor.fillRect(izquierda, velo)
        derecha = QRect(marco.right() + 1, marco.top(),
                        max(0, vista.right() - marco.right()),
                        marco.height())
        if derecha.width() > 0:
            pintor.fillRect(derecha, velo)
        pintor.setPen(QPen(QColor(tokens.ACENTO), 2))
        pintor.setBrush(Qt.NoBrush)
        pintor.drawRect(marco)
        pintor.restore()

    def resizeEvent(self, evento) -> None:
        super().resizeEvent(evento)
        self._aplicar()  # re-encajar con el mismo rel al cambiar tamano
        self.marcoCambiado.emit()

    def mousePressEvent(self, evento) -> None:
        if evento.button() == Qt.LeftButton and self.scene().items():
            self._arrastrando = True
            self._ultimo = evento.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento) -> None:
        # Paneo manual (las barras estan ocultas): la imagen sigue al
        # cursor sin limites; el marco fijo ni se toca.
        if self._arrastrando and self._ultimo is not None:
            ahora = evento.position().toPoint()
            delta = ahora - self._ultimo
            self._ultimo = ahora
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            self.marcoCambiado.emit()
            self.viewport().update()
        super().mouseMoveEvent(evento)

    def mouseReleaseEvent(self, evento) -> None:
        self._arrastrando = False
        self._ultimo = None
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(evento)
        self.marcoCambiado.emit()


class VentanaRecorte(QWidget):
    ZOOM_PASOS = 100

    def __init__(self, ventana):
        super().__init__(ventana)
        self.ventana = ventana
        self.estado = ventana.estado

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(tokens.MARGEN, tokens.ESPACIO_ITEM,
                                tokens.MARGEN, tokens.ESPACIO_ITEM)

        cabecera = QHBoxLayout()
        self.titulo = QLabel("Recortar imagen")
        self.titulo.setObjectName("tituloPantalla")
        self.titulo.setAlignment(Qt.AlignCenter)
        self.boton_regresar = QPushButton("REGRESAR")
        self.boton_regresar.setObjectName("navegacion")
        self.boton_regresar.setFixedSize(tokens.BTN_NAV_ANCHO, tokens.BTN_NAV_ALTO)
        self.boton_regresar.clicked.connect(lambda: self.ventana.mostrar("principal"))
        cabecera.addStretch(1)
        cabecera.addWidget(self.titulo)
        cabecera.addStretch(1)
        cabecera.addWidget(self.boton_regresar, alignment=Qt.AlignRight)
        raiz.addLayout(cabecera)
        raiz.addSpacing(tokens.ESPACIO_ITEM)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(tokens.ESPACIO_GRUPO)

        # --- zona de recorte + zoom ---
        izquierda = QVBoxLayout()
        izquierda.setSpacing(tokens.ESPACIO_ITEM)
        self.vista = VistaRecorte(self)
        self.vista.setMinimumSize(tokens.LADO_ZONA_RECORTE,
                                  tokens.LADO_ZONA_RECORTE)
        self.vista.marcoCambiado.connect(self._al_cambiar_encuadre)
        izquierda.addWidget(self.vista, stretch=1)
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setObjectName("zoomRecorte")
        self.zoom.setFixedHeight(44)
        self.zoom.setRange(0, self.ZOOM_PASOS)
        self.zoom.setValue(self.ZOOM_PASOS // 2)  # mitad = 100 %
        self.zoom.setToolTip("Zoom de la imagen (+ / - con teclado)")
        self.zoom.valueChanged.connect(self.al_cambiar_zoom)
        izquierda.addWidget(self.zoom)
        fila_zoom = QHBoxLayout()
        self.lbl_zoom = QLabel("100 %")
        self.lbl_zoom.setObjectName("valorCampo")
        self.lbl_zoom.setAlignment(Qt.AlignCenter)
        self.lbl_zoom.setFixedWidth(80)  # no mover el layout (ni el marco)
        fila_zoom.addStretch(1)
        fila_zoom.addWidget(self.lbl_zoom)
        fila_zoom.addStretch(1)
        izquierda.addLayout(fila_zoom)
        pista = QLabel("Arrastra la imagen · el marco no se mueve")
        pista.setObjectName("valorCampo")
        pista.setAlignment(Qt.AlignCenter)
        izquierda.addWidget(pista)
        cuerpo.addLayout(izquierda, stretch=1)

        # --- vista previa + acciones ---
        derecha = QVBoxLayout()
        derecha.setSpacing(tokens.ESPACIO_ITEM)
        etiqueta_previa = QLabel("Vista previa")
        etiqueta_previa.setObjectName("etiquetaCampo")
        etiqueta_previa.setAlignment(Qt.AlignCenter)
        derecha.addWidget(etiqueta_previa)
        self.previa = ProporcionImagen(
            tokens.RAZON_ZONA, (tokens.CANAL_LADO, tokens.CANAL_LADO), self)
        self.previa.setObjectName("lienzoImagen")
        derecha.addWidget(self.previa, stretch=1)

        self.boton_redimensionar = QPushButton("Redimensionar")
        self.boton_redimensionar.setObjectName("primario")
        self.boton_redimensionar.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_redimensionar.clicked.connect(self.redimensionar)
        self.boton_copia = QPushButton("Guardar copia")
        self.boton_copia.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_copia.clicked.connect(self.guardar_copia)
        self.boton_sobre = QPushButton("Sobreescribir")
        self.boton_sobre.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_sobre.clicked.connect(self.sobreescribir)
        for b in (self.boton_redimensionar, self.boton_copia, self.boton_sobre):
            derecha.addWidget(b, alignment=Qt.AlignHCenter)
        cuerpo.addLayout(derecha, stretch=1)

        raiz.addLayout(cuerpo, stretch=1)
        raiz.addSpacing(tokens.ESPACIO_GRUPO)
        self.zoom.setEnabled(False)
        # Teclado: + / - zoom, flechas paneo (barras ocultas).
        self._atajos_zoom = []
        for tecla, paso in ((Qt.Key_Plus, 5), (Qt.Key_Minus, -5)):
            atajo = QShortcut(QKeySequence(tecla), self)
            atajo.setContext(Qt.WindowShortcut)
            atajo.activated.connect(
                lambda p=paso: self.zoom.setValue(self.zoom.value() + p))
            self._atajos_zoom.append(atajo)
        for tecla, barra, paso in (
                (Qt.Key_Left, "h", -40), (Qt.Key_Right, "h", 40),
                (Qt.Key_Up, "v", -40), (Qt.Key_Down, "v", 40)):
            atajo = QShortcut(QKeySequence(tecla), self)
            atajo.setContext(Qt.WindowShortcut)
            atajo.activated.connect(
                lambda b=barra, p=paso: self._mover_vista(b, p))
            self._atajos_zoom.append(atajo)

    def _mover_vista(self, barra: str, paso: int) -> None:
        vista = self.vista
        sb = vista.horizontalScrollBar() if barra == "h" \
            else vista.verticalScrollBar()
        sb.setValue(sb.value() + paso)
        vista.marcoCambiado.emit()
        self._habilitar_guardar(False)
        self.boton_redimensionar.setEnabled(False)
        envolver_en_scroll(self, raiz)

    # --- zoom (relativo al encaje; 50 = 100 %) -------------------------
    def _rel_de_valor(self, valor: int) -> float:
        mitad = self.ZOOM_PASOS // 2
        if int(valor) <= mitad:
            return VistaRecorte.REL_MIN + (VistaRecorte.REL_MID - VistaRecorte.REL_MIN) * (int(valor) / mitad)
        return VistaRecorte.REL_MID + (VistaRecorte.REL_MAX - VistaRecorte.REL_MID) * ((int(valor) - mitad) / (self.ZOOM_PASOS - mitad))

    def _habilitar_guardar(self, activo):
        self.boton_copia.setEnabled(activo)
        self.boton_sobre.setEnabled(activo)

    def _invalidar(self):
        self.estado.invalidar_vista_previa()
        self.previa.set_imagen(QPixmap())
        self._habilitar_guardar(False)

    def _al_cambiar_encuadre(self):
        # Pan, zoom o resize mueven la seleccion: caduca el preview.
        self.al_recibir_recorte(self.vista.seleccion())

    def _fuente_recorte(self):
        # Solo en este marco el fondo quitado es BLANCO (vista + guardado).
        # Se construye local desde original + mascara (una sola op. numpy,
        # sin remuestreo): estado.preprocesada sigue negra en las demas
        # pantallas y el histograma no se entera.
        if self.estado.mascara is not None:
            img = self.estado.original.copy()
            img[self.estado.mascara == 0] = 255
            return img
        return self.estado.original

    # --- estado -------------------------------------------------------
    def al_entrar(self):
        if self.estado.original is None:
            return
        self.zoom.blockSignals(True)
        self.zoom.setRange(0, self.ZOOM_PASOS)
        self.zoom.setValue(self.ZOOM_PASOS // 2)  # mitad = 100 %
        self.zoom.blockSignals(False)
        # El slider se mueve siempre: ya no hay rango degenerado porque la
        # escala es relativa al encaje, sin tope de memoria.
        self.zoom.setEnabled(True)
        self.vista.set_imagen(a_pixmap(self._fuente_recorte()))
        self.al_cambiar_zoom(self.zoom.value())
        self._al_cambiar_encuadre()

    def al_cambiar_zoom(self, valor: int):
        if self.estado.original is None:
            return
        rel = self._rel_de_valor(valor)
        self.lbl_zoom.setText(f"{rel * 100:.0f} %")
        self.vista.set_zoom_rel(rel)
        self._invalidar()
        self._al_cambiar_encuadre()

    def al_recibir_recorte(self, rect):
        # Cualquier marco vale (incluso fuera): lo faltante sale blanco.
        if rect is None or rect.isEmpty():
            self.estado.recorte = None
            self.boton_redimensionar.setEnabled(False)
            self._invalidar()
            return
        self.estado.recorte = (rect.x(), rect.y(), rect.width(),
                               rect.height())
        self.boton_redimensionar.setEnabled(True)
        self._invalidar()

    def redimensionar(self):
        if self.estado.original is None or self.estado.recorte is None:
            return
        x, y, ancho, alto = self.estado.recorte
        # Exporta desde la fuente (sin fondo si se quito): el zoom solo
        # era vista. Lo fuera de la imagen sale blanco.
        previa = recorte.recorte_libre(self._fuente_recorte(), x, y, ancho,
                                       alto, tokens.LADO_SALIDA)
        self.estado.vista_previa = previa
        self.previa.set_imagen(a_pixmap(previa))
        self._habilitar_guardar(True)

    # --- guardado -----------------------------------------------------
    def guardar_copia(self):
        if self.estado.vista_previa is None:
            return
        base = os.path.splitext(os.path.basename(self.estado.ruta or "imagen"))[0]
        carpeta = os.path.dirname(self.estado.ruta or "")
        sugerido = os.path.join(carpeta, f"{base}_recortada.png")
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar copia", sugerido,
                                              "PNG (*.png)")
        if not ruta:
            return
        if not os.path.splitext(ruta)[1]:
            ruta += ".png"
        core_imagen.guardar_rgb(ruta, self.estado.vista_previa)
        QMessageBox.information(self, "Guardar copia", "Copia guardada.")

    def sobreescribir(self):
        if self.estado.vista_previa is None or not self.estado.ruta:
            return
        respuesta = QMessageBox.question(
            self, "Sobreescribir imagen",
            "¿Sobrescribir el archivo original?\nEsta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if respuesta != QMessageBox.Yes:
            return
        core_imagen.guardar_rgb(self.estado.ruta, self.estado.vista_previa)
        QMessageBox.information(self, "Sobreescribir imagen",
                                "Imagen original sobrescrita.")

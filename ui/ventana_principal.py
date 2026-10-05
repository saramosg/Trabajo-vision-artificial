"""Pantalla principal (preprocesado) y ventana que centraliza las pantallas.

`PantallaPreprocesado`: carga la imagen (click en la zona), elige el modelo
de segmentacion (grabcut/otsu), quita o restaura el fondo sin tocar el
archivo, y navega a canales o recorte. Los botones de accion nacen
deshabilitados hasta cargar imagen.

`VentanaPrincipal`: QMainWindow con QStackedWidget de las cinco pantallas,
estado `EstadoImagen` compartido por referencia, senales de cambio
(`imagenSeleccionada`, `modeloCambiado`, `modoCambiado`) y atajos de
teclado (flechas entre RGB/YCM, Esc a principal).
"""
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout,
                               QLabel, QLineEdit, QAbstractSpinBox, QPlainTextEdit,
                               QTextEdit, QMainWindow, QMessageBox,
                               QStackedWidget, QVBoxLayout, QWidget)

from core import imagen as core_imagen
from core import segmentacion
from ui import tokens
from ui.helpers import boton, envolver_en_scroll
from ui.widgets import ProporcionImagen, a_pixmap
from ui.ventana_rgb import VentanaRGB
from ui.ventana_ycm import VentanaYCM
from ui.ventana_histograma import VentanaHistograma
from ui.ventana_recorte import VentanaRecorte

PANTALLAS_CANALES = ("rgb", "ycm")
CLASES_DE_TEXTO = (QLineEdit, QAbstractSpinBox, QPlainTextEdit, QTextEdit)
FILTRO_IMAGENES = "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)"


class ZonaImagen(ProporcionImagen):
    """Zona de previsualizacion clickeable (§6.1)."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(tokens.RAZON_ZONA, (tokens.CANAL_LADO, tokens.CANAL_LADO),
                         parent)
        self.setObjectName("zonaImagen")
        self.setText("seleccionar imagen")

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(evento)


class PantallaPreprocesado(QWidget):
    """Pantalla principal: cargar imagen y quitar fondo (§6.1)."""

    def __init__(self, ventana):
        super().__init__(ventana)
        self.ventana = ventana
        self.estado = ventana.estado

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(tokens.MARGEN, tokens.ESPACIO_ITEM,
                                tokens.MARGEN, tokens.ESPACIO_ITEM)

        self.titulo = QLabel("Analizador de imágenes")
        self.titulo.setObjectName("tituloPantalla")
        self.titulo.setAlignment(Qt.AlignCenter)
        raiz.addWidget(self.titulo, alignment=Qt.AlignHCenter)
        raiz.addSpacing(tokens.ESPACIO_ITEM)

        self.zona = ZonaImagen(self)
        self.zona.clicked.connect(self.elegir_imagen)

        self.nombre_archivo = QLabel("")
        self.nombre_archivo.setObjectName("valorCampo")
        self.nombre_archivo.setAlignment(Qt.AlignCenter)

        etiqueta_modelo = QLabel("Modelo:")
        etiqueta_modelo.setObjectName("etiquetaCampo")
        self.boton_modelo = boton("grabcut", ancho=tokens.BTN_ANCHO,
                                  alto=tokens.BTN_ALTO)
        self.boton_modelo.clicked.connect(self.alternar_modelo)

        self.boton_fondo = boton("Quitar fondo", ancho=tokens.BTN_ANCHO,
                                 alto=tokens.BTN_ALTO)
        self.boton_fondo.clicked.connect(self.alternar_fondo)

        self.boton_canales = boton("Analizar por canales", "primario",
                                   tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_canales.clicked.connect(lambda: self.ventana.mostrar("rgb"))

        self.boton_recorte = boton("Recortar imagen", ancho=tokens.BTN_ANCHO,
                                   alto=tokens.BTN_ALTO)
        self.boton_recorte.clicked.connect(lambda: self.ventana.mostrar("recorte"))

        # Dos columnas para que quepa sin scroll: a la izquierda la zona de
        # imagen, a la derecha la columna de botones (modelo al lado de su
        # etiqueta, y debajo los otros tres).
        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(tokens.ESPACIO_GRUPO)

        izquierda = QVBoxLayout()
        izquierda.setSpacing(tokens.ESPACIO_ITEM)
        izquierda.addWidget(self.zona, alignment=Qt.AlignHCenter)
        izquierda.addWidget(self.nombre_archivo, alignment=Qt.AlignHCenter)
        izquierda.addStretch(1)

        derecha = QVBoxLayout()
        derecha.setSpacing(tokens.ESPACIO_ITEM)
        fila_modelo = QHBoxLayout()
        fila_modelo.setSpacing(tokens.ESPACIO_ITEM)
        fila_modelo.addWidget(etiqueta_modelo, alignment=Qt.AlignVCenter)
        fila_modelo.addWidget(self.boton_modelo, alignment=Qt.AlignVCenter)
        derecha.addLayout(fila_modelo)
        derecha.addWidget(self.boton_fondo, alignment=Qt.AlignHCenter)
        derecha.addWidget(self.boton_canales, alignment=Qt.AlignHCenter)
        derecha.addWidget(self.boton_recorte, alignment=Qt.AlignHCenter)
        derecha.addStretch(1)

        cuerpo.addLayout(izquierda, stretch=1)
        cuerpo.addLayout(derecha, stretch=1)
        raiz.addLayout(cuerpo, stretch=1)
        self._habilitar(False)
        envolver_en_scroll(self, raiz)

    def _habilitar(self, activo):
        for b in (self.boton_modelo, self.boton_fondo, self.boton_canales,
                  self.boton_recorte):
            b.setEnabled(activo)

    def elegir_imagen(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar imagen", "",
                                              FILTRO_IMAGENES)
        if not ruta:
            return
        try:
            self.estado.original = core_imagen.cargar_imagen(ruta)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Error", f"No se pudo abrir la imagen:\n{e}")
            return
        self.estado.ruta = ruta
        self.estado.preprocesada = None
        self.estado.mascara = None
        self.estado.vista_previa = None
        self.boton_fondo.setText("Quitar fondo")
        self._refrescar_zona()
        self._habilitar(True)
        self.ventana.actualizar_info()
        self.ventana.imagenSeleccionada.emit()

    def _refrescar_zona(self):
        arr = self.estado.preprocesada if self.estado.preprocesada is not None \
            else self.estado.original
        if arr is not None:
            self.zona.setText("")
            self.zona.set_imagen(a_pixmap(arr))
            self.nombre_archivo.setText(os.path.basename(self.estado.ruta or ""))

    def alternar_modelo(self):
        self.estado.modelo = "otsu" if self.estado.modelo == "grabcut" else "grabcut"
        self.boton_modelo.setText(self.estado.modelo)
        if self.estado.preprocesada is not None:
            self.aplicar_fondo()
        self.ventana.modeloCambiado.emit(self.estado.modelo)

    def alternar_fondo(self):
        if self.estado.preprocesada is None:
            self.aplicar_fondo()
        else:
            self.estado.preprocesada = None
            self.estado.mascara = None
            self.boton_fondo.setText("Quitar fondo")
            self._refrescar_zona()

    def aplicar_fondo(self):
        self.estado.mascara = segmentacion.segmentar(self.estado.original,
                                                     self.estado.modelo)
        pre = self.estado.original.copy()
        pre[self.estado.mascara == 0] = 0
        self.estado.preprocesada = pre
        self.boton_fondo.setText("Restaurar original")
        self._refrescar_zona()


class VentanaPrincipal(QMainWindow):
    imagenSeleccionada = Signal()
    modeloCambiado = Signal(str)
    modoCambiado = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analizador de imágenes")
        self.estado = core_imagen.EstadoImagen()
        self.pantalla_actual = "principal"

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.paginas = {
            "principal": PantallaPreprocesado(self),
            "rgb": VentanaRGB(self),
            "ycm": VentanaYCM(self),
            "histograma": VentanaHistograma(self),
            "recorte": VentanaRecorte(self),
        }
        for p in self.paginas.values():
            self.stack.addWidget(p)

        self._crear_atajos()
        self.mostrar("principal")

    # --- navegacion ---------------------------------------------------
    def mostrar(self, nombre: str):
        pagina = self.paginas[nombre]
        if hasattr(pagina, "al_entrar"):
            pagina.al_entrar()
        self.pantalla_actual = nombre
        self.stack.setCurrentWidget(pagina)

    def actualizar_info(self):
        for pagina in self.paginas.values():
            if hasattr(pagina, "actualizar_info"):
                pagina.actualizar_info()

    # --- atajos de teclado (§6.1) ------------------------------------
    def _foco_ocupa_teclado(self) -> bool:
        return isinstance(QApplication.focusWidget(), CLASES_DE_TEXTO)

    def ir_a_ycm(self):
        if self._foco_ocupa_teclado() or self.pantalla_actual not in PANTALLAS_CANALES:
            return
        self.mostrar("ycm")

    def ir_a_rgb(self):
        if self._foco_ocupa_teclado() or self.pantalla_actual not in PANTALLAS_CANALES:
            return
        self.mostrar("rgb")

    def ir_a_principal(self):
        if self._foco_ocupa_teclado() or self.pantalla_actual not in PANTALLAS_CANALES:
            return
        self.mostrar("principal")

    def _crear_atajos(self):
        self._atajos = [QShortcut(QKeySequence(k), self) for k in
                        (Qt.Key_Right, Qt.Key_Left, Qt.Key_Escape)]
        for atajo, slot in zip(self._atajos,
                               (self.ir_a_ycm, self.ir_a_rgb, self.ir_a_principal)):
            atajo.setContext(Qt.WindowShortcut)
            atajo.activated.connect(slot)

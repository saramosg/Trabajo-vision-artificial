"""Base de las pantallas de canales RGB y YCM.

`VentanaCanales` muestra los tres lienzos del espacio (siempre desde la
original, nunca la preprocesada), el boton de modo (color / blanco y
negro), el boton al histograma y REGRESAR. Click en un lienzo lo marca
como canal activo. `VentanaRGB` y `VentanaYCM` solo fijan el espacio.
"""
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

from core import canales
from ui import tokens
from ui.helpers import envolver_en_scroll
from ui.widgets import ProporcionImagen, a_pixmap


class LienzoCanal(ProporcionImagen):
    """Lienzo de canal clickeable (§6.2)."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(tokens.RAZON_CANAL,
                         (tokens.CANAL_LADO, tokens.CANAL_LADO), parent)
        self.setObjectName("lienzoImagen")
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(evento)


class VentanaCanales(QWidget):
    """Base de las pantallas RGB y YCM."""

    def __init__(self, ventana, espacio):
        super().__init__(ventana)
        self.ventana = ventana
        self.estado = ventana.estado
        self.espacio = espacio
        self.letras = ("R", "G", "B") if espacio == "RGB" else ("Y", "C", "M")

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(tokens.MARGEN, tokens.ESPACIO_ITEM,
                                tokens.MARGEN, tokens.ESPACIO_ITEM)

        cabecera = QGridLayout()
        self.lbl_imagen = QLabel("Imagen:")
        self.lbl_imagen.setObjectName("valorCampo")
        self.lbl_directorio = QLabel("Directorio de imagen:")
        self.lbl_directorio.setObjectName("valorCampo")
        self.lbl_directorio.setWordWrap(True)
        info = QVBoxLayout()
        info.setSpacing(2)
        info.addWidget(self.lbl_imagen)
        info.addWidget(self.lbl_directorio)
        cabecera.addLayout(info, 0, 0, Qt.AlignLeft | Qt.AlignTop)

        self.titulo = QLabel(espacio)
        self.titulo.setObjectName("tituloPantalla")
        self.titulo.setAlignment(Qt.AlignCenter)
        cabecera.addWidget(self.titulo, 0, 1, Qt.AlignHCenter)

        botones = QHBoxLayout()
        botones.setSpacing(tokens.ESPACIO_ITEM)
        self.boton_modo = QPushButton("color")
        self.boton_modo.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_modo.clicked.connect(self.alternar_modo)
        self.boton_hist = QPushButton("Histograma de color")
        self.boton_hist.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_hist.clicked.connect(self.ir_a_histograma)
        self.boton_regresar = QPushButton("REGRESAR")
        self.boton_regresar.setObjectName("navegacion")
        self.boton_regresar.setFixedSize(tokens.BTN_NAV_ANCHO, tokens.BTN_NAV_ALTO)
        self.boton_regresar.clicked.connect(lambda: self.ventana.mostrar("principal"))
        botones.addWidget(self.boton_modo)
        botones.addWidget(self.boton_hist)
        botones.addWidget(self.boton_regresar)
        cabecera.addLayout(botones, 0, 2, Qt.AlignRight | Qt.AlignTop)
        cabecera.setColumnStretch(1, 1)
        raiz.addLayout(cabecera)
        raiz.addSpacing(tokens.ESPACIO_GRUPO)

        fila = QHBoxLayout()
        fila.setSpacing(tokens.HUECO_CANAL)
        self.lienzos = {}
        for letra in self.letras:
            columna = QVBoxLayout()
            etiqueta = QLabel(letra)
            etiqueta.setObjectName("tituloPantalla")
            etiqueta.setAlignment(Qt.AlignCenter)
            lienzo = LienzoCanal(self)
            lienzo.clicked.connect(lambda l=letra: self.reaplicar(l))
            columna.addWidget(etiqueta)
            columna.addWidget(lienzo)
            fila.addLayout(columna)
            self.lienzos[letra] = lienzo
        raiz.addLayout(fila, stretch=1)
        raiz.addStretch(0)
        envolver_en_scroll(self, raiz)

    # --- estado -------------------------------------------------------
    def al_entrar(self):
        self.estado.espacio = self.espacio
        if self.estado.canal_actual not in self.letras:
            self.estado.canal_actual = self.letras[0]
        self.boton_modo.setText(self.estado.modo)
        self.actualizar_info()
        self.mostrar_canales()

    def actualizar_info(self):
        ruta = self.estado.ruta
        self.lbl_imagen.setText(f"Imagen: {os.path.basename(ruta) if ruta else ''}")
        carpeta = os.path.basename(os.path.dirname(ruta)) if ruta else ""
        self.lbl_directorio.setText(f"Directorio de imagen: {carpeta}")

    def alternar_modo(self):
        self.estado.modo = "blanco y negro" if self.estado.modo == "color" \
            else "color"
        self.boton_modo.setText(self.estado.modo)
        self.mostrar_canales()
        self.ventana.modoCambiado.emit(self.estado.modo)

    def reaplicar(self, letra):
        self.estado.canal_actual = letra
        self.mostrar_canales()

    def mostrar_canales(self):
        if self.estado.original is None:
            return
        for letra, lienzo in self.lienzos.items():
            arr = canales.aplicar_modo(self.estado.original, self.espacio,
                                       letra, self.estado.modo)
            lienzo.set_imagen(a_pixmap(arr))

    def ir_a_histograma(self):
        self.estado.espacio = self.espacio
        self.estado.canal_actual = self.letras[0]
        self.ventana.mostrar("histograma")

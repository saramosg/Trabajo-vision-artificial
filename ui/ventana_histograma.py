"""Pantalla de histograma de color.

Al entrar fuerza modo blanco y negro. Muestra original, canal activo y
contorno; el grafico es un PNG de matplotlib estilo modulo 2 con lineas
de rango. Los sliders acotan el rango [inf, sup] y alimentan el contorno
binario (mascara por rango del canal + limpieza opcional de huecos e
islas). "Quitar fondo" es solo preview local (no escribe estado) y
"Guardar" escribe la vista previa tal cual.
"""
import os

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QFileDialog, QGridLayout, QHBoxLayout, QLabel,
                               QMessageBox, QPushButton, QSlider, QVBoxLayout,
                               QWidget)

from core import canales, histograma as core_hist
from core import imagen as core_imagen
from core import segmentacion
from ui import tokens
from ui.helpers import envolver_en_scroll
from ui.widgets import ProporcionImagen, a_pixmap


class VentanaHistograma(QWidget):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.ventana = ventana
        self.estado = ventana.estado
        self._bins = [0] * 256
        self._preview_mask = None  # solo preview local: no toca estado

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(tokens.MARGEN, tokens.ESPACIO_ITEM,
                                tokens.MARGEN, tokens.ESPACIO_ITEM)

        cabecera = QHBoxLayout()
        self.titulo = QLabel("Histograma de color")
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

        # --- miniaturas 2x2 ---
        mini = QGridLayout()
        mini.setSpacing(tokens.ESPACIO_ITEM)
        self.mini_original = ProporcionImagen(
            tokens.RAZON_HISTO_IMG, (250, 250), self)
        self.mini_original.setObjectName("lienzoImagen")
        self.mini_canal = ProporcionImagen(
            tokens.RAZON_HISTO_IMG, (250, 250), self)
        self.mini_canal.setObjectName("lienzoImagen")
        self.mini_contorno = ProporcionImagen(
            tokens.RAZON_HISTO_IMG, (250, 250), self)
        self.mini_contorno.setObjectName("lienzoImagen")
        for i, (w, nombre) in enumerate((
                (self.mini_original, "Imagen original"),
                (self.mini_canal, "Canal activo"))):
            etiqueta = QLabel(nombre)
            etiqueta.setObjectName("etiquetaCampo")
            etiqueta.setAlignment(Qt.AlignCenter)
            mini.addWidget(etiqueta, (i // 2) * 2, i % 2)
            mini.addWidget(w, (i // 2) * 2 + 1, i % 2)
        etiqueta_contorno = QLabel("Contorno binario")
        etiqueta_contorno.setObjectName("etiquetaCampo")
        etiqueta_contorno.setAlignment(Qt.AlignCenter)
        mini.addWidget(etiqueta_contorno, 2, 0)
        mini.addWidget(self.mini_contorno, 3, 0)
        cuerpo.addLayout(mini)

        # --- columna derecha: controles + histograma ---
        derecha = QVBoxLayout()
        derecha.setSpacing(tokens.ESPACIO_ITEM)

        fila_canal = QHBoxLayout()
        self.lbl_canal = QLabel("Canal actual:")
        self.lbl_canal.setObjectName("etiquetaCampo")
        self.valor_canal = QLabel("RGB - Rojo")
        self.valor_canal.setObjectName("valorCampo")
        self.boton_canal = QPushButton("R")
        self.boton_canal.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_canal.clicked.connect(self.rotar_canal)
        fila_canal.addWidget(self.lbl_canal)
        fila_canal.addWidget(self.valor_canal)
        fila_canal.addStretch(1)
        fila_canal.addWidget(self.boton_canal)
        derecha.addLayout(fila_canal)

        fila_fondo = QHBoxLayout()
        fila_fondo.setSpacing(tokens.ESPACIO_ITEM)
        self.boton_fondo = QPushButton("Quitar fondo")
        self.boton_fondo.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_fondo.clicked.connect(self.alternar_fondo)
        self.boton_limpiar = QPushButton("Limpiar máscara")
        self.boton_limpiar.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_limpiar.setCheckable(True)
        self.boton_limpiar.setToolTip(
            "Rellena huecos internos y elimina islas flotantes")
        self.boton_limpiar.toggled.connect(self._al_activar_limpieza)
        fila_fondo.addWidget(self.boton_fondo)
        fila_fondo.addWidget(self.boton_limpiar)
        fila_fondo.addStretch(1)
        derecha.addLayout(fila_fondo)

        # Sliders y contenedor del histograma
        self.slider_inf = QSlider(Qt.Horizontal)
        self.slider_inf.setRange(0, 255)
        self.slider_inf.setValue(0)
        self.slider_inf.setMinimumHeight(44)
        self.slider_sup = QSlider(Qt.Horizontal)
        self.slider_sup.setRange(0, 255)
        self.slider_sup.setValue(255)
        self.slider_sup.setMinimumHeight(44)
        self.vista_histograma = ProporcionImagen(
            tokens.RAZON_HISTO_GRAF, (467, 180), self)
        self.vista_histograma.setObjectName("lienzoImagen")
        self.slider_inf.valueChanged.connect(self.al_cambiar_rango)
        self.slider_sup.valueChanged.connect(self.al_cambiar_rango)
        derecha.addWidget(self.vista_histograma, stretch=1)
        derecha.addWidget(self.slider_inf)
        derecha.addWidget(self.slider_sup)

        guardar = QHBoxLayout()
        guardar.setSpacing(tokens.ESPACIO_ITEM)
        self.boton_guardar_img = QPushButton("Guardar imagen")
        self.boton_guardar_img.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_guardar_img.clicked.connect(self.guardar_imagen)
        self.boton_guardar_mask = QPushButton("Guardar máscara")
        self.boton_guardar_mask.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_guardar_mask.clicked.connect(self.guardar_mascara)
        guardar.addWidget(self.boton_guardar_img)
        guardar.addWidget(self.boton_guardar_mask)
        derecha.addLayout(guardar)

        cuerpo.addLayout(derecha, stretch=1)
        raiz.addLayout(cuerpo, stretch=1)
        envolver_en_scroll(self, raiz)

    # --- estado -------------------------------------------------------
    def al_entrar(self):
        if self.estado.espacio == "RGB":
            self.letras = ("R", "G", "B")
        else:
            self.letras = ("Y", "C", "M")
        if self.estado.canal_actual not in self.letras:
            self.estado.canal_actual = self.letras[0]
        # Esta pantalla siempre analiza en blanco y negro: el histograma y
        # las miniaturas son distribucion de intensidades (Tarea 1:
        # `plt.hist(img_gray.ravel(), 256)`), no composicion en color.
        self.estado.modo = "blanco y negro"
        try:
            self.ventana.modoCambiado.emit(self.estado.modo)
        except Exception:  # noqa: BLE001
            pass
        self.slider_inf.setValue(self.estado.inf)
        self.slider_sup.setValue(self.estado.sup)
        # El preview siempre arranca apagado al entrar.
        self._preview_mask = None
        self.boton_fondo.setText("Quitar fondo")
        self.refrescar()

    def _base_histograma(self):
        # El histograma NO lo toca el preview: siempre sobre la original.
        return self.estado.original

    def _letra(self):
        return self.estado.canal_actual

    def _al_activar_limpieza(self, activo: bool) -> None:
        # Estado visual de activo: anillo azul permanente mientras esta ON.
        if activo:
            self.boton_limpiar.setStyleSheet(
                f"border: 2px solid {tokens.ACENTO}; border-radius: 30px;")
        else:
            self.boton_limpiar.setStyleSheet("")
        # Si el preview esta encendido se reconstruye con/sin limpieza.
        if self._preview_mask is not None:
            self._construir_preview()
        self.refrescar()

    def _construir_preview(self) -> None:
        """Mascara del preview: canal B/N + rango y, si limpieza esta
        activa, se aplica DESPUES (huecos rellenos, islas fuera)."""
        comp = canales.componente(self.estado.original,
                                  self.estado.espacio, self._letra())
        mask = core_hist.mascara_por_rango(comp, self.estado.inf,
                                           self.estado.sup)
        if self.boton_limpiar.isChecked():
            mask = segmentacion.limpiar_mascara(mask)
        self._preview_mask = mask

    def _mascara_limitada(self):
        """Mascara acotada por el rango inf/sup sobre el CANAL ACTIVO.

        Antes comparaba sobre el gris (luminancia): rotar R/G/B no
        cambiaba el contorno. Ahora usa el componente B/N del canal
        seleccionado, igual que el histograma.
        """
        base = self._base_histograma()
        if base is None:
            return None
        comp = canales.componente(base, self.estado.espacio, self._letra())
        lo, hi = (self.estado.inf, self.estado.sup) \
            if self.estado.inf <= self.estado.sup \
            else (self.estado.sup, self.estado.inf)
        dentro = (comp >= int(lo)) & (comp <= int(hi))
        if self.estado.mascara is not None:
            return np.where(dentro, self.estado.mascara, 0).astype(np.uint8)
        return np.where(dentro, 255, 0).astype(np.uint8)

    def _refrescar_contorno(self) -> None:
        # Objeto RELLENO (silueta blanca sobre negro) + borde de 1 px
        # encima para definir el perimetro. Con "Limpiar máscara" activo
        # se rellenan huecos y se quitan islas antes de mostrar.
        limitada = self._mascara_limitada()
        if limitada is None or not np.any(limitada):
            self.mini_contorno.set_imagen(QPixmap())
            return
        if getattr(self, "boton_limpiar", None) is not None \
                and self.boton_limpiar.isChecked():
            limitada = segmentacion.limpiar_mascara(limitada)
            if not np.any(limitada):
                self.mini_contorno.set_imagen(QPixmap())
                return
        borde = segmentacion.contorno(limitada)
        relleno = limitada.copy()
        relleno[borde > 0] = 255
        self.mini_contorno.set_imagen(a_pixmap(relleno))

    def refrescar(self):
        if self.estado.original is None:
            return
        letra = self._letra()
        self.boton_canal.setText(letra)
        texto = canales.etiqueta_canal(self.estado.espacio, letra)
        self.valor_canal.setText(texto)
        self.valor_canal.setStyleSheet(
            f"color: {tokens.COLOR_CANAL[letra]};")

        self.mini_original.set_imagen(a_pixmap(self.estado.original))
        canal_arr = canales.aplicar_modo(self.estado.original, self.estado.espacio,
                                         letra, self.estado.modo)
        self.mini_canal.set_imagen(a_pixmap(canal_arr))
        # Preview con mascara: original x mascara y canal x mascara.
        # Solo visualizacion local: no escribe estado, no toca el
        # histograma ni el contorno.
        if self._preview_mask is not None:
            vista_orig = self.estado.original.copy()
            vista_orig[self._preview_mask == 0] = 0
            self.mini_original.set_imagen(a_pixmap(vista_orig))
            vista_canal = canal_arr.copy()
            vista_canal[self._preview_mask == 0] = 0
            self.mini_canal.set_imagen(a_pixmap(vista_canal))

        self._refrescar_contorno()

        base = self._base_histograma()
        componente = canales.componente(base, self.estado.espacio, letra)
        self._bins = core_hist.histograma_canal(componente)
        self._comp = componente
        self._pintar_histograma()

    def rotar_canal(self):
        indice = self.letras.index(self._letra())
        self.estado.canal_actual = self.letras[(indice + 1) % 3]
        self.refrescar()

    def _pintar_histograma(self) -> None:
        """Renderiza el plt del modulo 2 con las lineas inf/sup (Tarea 7)."""
        comp = getattr(self, "_comp", None)
        if comp is None:
            return
        png = core_hist.figura_histograma(comp, self.estado.inf,
                                           self.estado.sup)
        pix = QPixmap()
        pix.loadFromData(png, "PNG")
        self.vista_histograma.set_imagen(pix)

    def al_cambiar_rango(self):
        self.estado.inf = self.slider_inf.value()
        self.estado.sup = self.slider_sup.value()
        self._pintar_histograma()
        self._refrescar_contorno()

    def alternar_fondo(self):
        # Preview local: la mascara sale del canal en blanco y negro
        # seleccionado + el rango inf/sup. No escribe `estado`: el
        # histograma y el contorno quedan intactos.
        if self._preview_mask is None:
            self._construir_preview()
            self.boton_fondo.setText("Restaurar original")
        else:
            self._preview_mask = None
            self.boton_fondo.setText("Quitar fondo")
        self.refrescar()

    # --- guardado -----------------------------------------------------
    def guardar_imagen(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar imagen", "",
                                              "PNG (*.png)")
        if not ruta:
            return
        if not os.path.splitext(ruta)[1]:
            ruta += ".png"
        rgb = self._base_histograma()[:, :, :3]
        mascara = self.estado.mascara
        if mascara is None:
            mascara = np.full(rgb.shape[:2], 255, np.uint8)
        core_imagen.guardar_imagen(ruta, rgb, mascara)
        QMessageBox.information(self, "Guardar imagen", "Imagen guardada.")

    def guardar_mascara(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar máscara", "",
                                              "PNG (*.png)")
        if not ruta:
            return
        if not os.path.splitext(ruta)[1]:
            ruta += ".png"
        if self.boton_limpiar.isChecked():
            mascara = self._mascara_limitada()
            if mascara is not None:
                mascara = segmentacion.limpiar_mascara(mascara)
        else:
            mascara = self.estado.mascara
        if mascara is None or not np.any(mascara):
            mascara = np.zeros(self.estado.original.shape[:2], np.uint8)
        core_imagen.guardar_mascara(ruta, mascara)
        QMessageBox.information(self, "Guardar máscara", "Máscara guardada.")

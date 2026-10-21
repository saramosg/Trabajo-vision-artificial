"""Pantalla de histograma de color.

Al entrar fuerza modo blanco y negro. Muestra original, canal activo y
contorno; el grafico es un PNG de matplotlib estilo modulo 2 con lineas
de rango. Los sliders acotan el rango [inf, sup] y alimentan el contorno
binario (mascara por rango del canal + limpieza opcional de huecos e
islas). "Quitar fondo" es solo preview local (no escribe estado) y
"Guardar" escribe la vista previa tal cual.

La pantalla tiene DOS modos de analisis. "umbral" (predeterminado) es la
pantalla descrita arriba. "bordes" reemplaza grafico/fila canal/fila
"Limpiar mascara" por controles de deteccion de bordes (metodo +
umbrales t1/t2) y vuelve clicable el contorno binario: cada clic rellena
la region cerrada por los bordes y acumula en estado.mascara (ver
core/bordes.py). El boton "Quitar fondo"/"Restaurar original" es el
MISMO en los dos modos, pero cambia de sitio: en umbral va en la fila
de la derecha y en bordes debajo del cuadro "Canal activo" de la
rejilla.
"""

import os

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from core import bordes as core_bordes
from core import canales, histograma as core_hist
from core import imagen as core_imagen
from core import segmentacion
from ui import tokens
from ui.helpers import envolver_en_scroll
from ui.widgets import ProporcionImagen, a_pixmap

# RGB del token ACENTO "#2F6FED" para mezclas numpy sin parsear hex.
_ACENTO_RGB = (0x2F, 0x6F, 0xED)


class ZonaBordes(ProporcionImagen):
    """ProporcionImagen que avisa el px de la IMAGEN (no del widget) al clicar.

    El mapeo replica el letterbox de paintEvent: la imagen centrada en la
    zona dibujada; un clic en la barra del letterbox no emite nada.
    """

    clic_en_imagen = Signal(int, int)  # (x, y) en px de la imagen original

    def _a_imagen(self, px: int, py: int) -> tuple[int, int] | None:
        if self._ajustada.isNull() or self._original.isNull():
            return None
        x0 = (self.width() - self._ajustada.width()) // 2
        y0 = (self.height() - self._ajustada.height()) // 2
        if not (
            x0 <= px < x0 + self._ajustada.width()
            and y0 <= py < y0 + self._ajustada.height()
        ):
            return None
        ix = int((px - x0) * self._original.width() / self._ajustada.width())
        iy = int((py - y0) * self._original.height() / self._ajustada.height())
        ix = min(max(ix, 0), self._original.width() - 1)
        iy = min(max(iy, 0), self._original.height() - 1)
        return ix, iy

    def mousePressEvent(self, evento):
        punto = self._a_imagen(int(evento.position().x()), int(evento.position().y()))
        if punto is not None:
            self.clic_en_imagen.emit(*punto)


class VentanaHistograma(QWidget):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.ventana = ventana
        self.estado = ventana.estado
        self._bins = [0] * 256
        self._fondo_activo = False  # preview local: no escribe estado
        self._modo = "umbral"  # "umbral" | "bordes"
        self._metodo = "canny"  # "canny" | "sobel" | "laplaciano"
        self._t1 = 100  # umbral bajo de canny (sliders en modo bordes)
        self._t2 = 200  # umbral alto de canny / corte de sobel y laplaciano
        self._mapa_bordes = None  # ultimo mapa calculado (uint8 0/255)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(
            tokens.MARGEN, tokens.ESPACIO_ITEM, tokens.MARGEN, tokens.ESPACIO_ITEM
        )

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
        self.boton_modo = QPushButton("Detección de umbral")
        self.boton_modo.setObjectName("navegacion")
        self.boton_modo.setFixedHeight(tokens.BTN_NAV_ALTO)
        self.boton_modo.setMinimumWidth(tokens.BTN_NAV_ANCHO)
        self.boton_modo.clicked.connect(self.alternar_modo)
        cabecera.addWidget(self.boton_modo, alignment=Qt.AlignRight)
        cabecera.addWidget(self.boton_regresar, alignment=Qt.AlignRight)
        raiz.addLayout(cabecera)
        raiz.addSpacing(tokens.ESPACIO_ITEM)

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(tokens.ESPACIO_GRUPO)

        # --- miniaturas 2x2 ---
        mini = QGridLayout()
        mini.setSpacing(tokens.ESPACIO_ITEM)
        self._rejilla = mini
        self.mini_original = ProporcionImagen(tokens.RAZON_HISTO_IMG, (250, 250), self)
        self.mini_original.setObjectName("lienzoImagen")
        self.mini_canal = ProporcionImagen(tokens.RAZON_HISTO_IMG, (250, 250), self)
        self.mini_canal.setObjectName("lienzoImagen")
        self.mini_contorno = ZonaBordes(tokens.RAZON_HISTO_IMG, (250, 250), self)
        self.mini_contorno.setObjectName("lienzoImagen")
        for i, (w, nombre) in enumerate(
            ((self.mini_original, "Imagen original"), (self.mini_canal, "Canal activo"))
        ):
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
        self._fila_fondo = fila_fondo
        self.boton_fondo = QPushButton("Quitar fondo")
        self.boton_fondo.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_fondo.clicked.connect(self.alternar_fondo)
        self.boton_limpiar = QPushButton("Limpiar máscara")
        self.boton_limpiar.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_limpiar.setCheckable(True)
        self.boton_limpiar.setToolTip(
            "Rellena huecos internos y elimina islas flotantes"
        )
        self.boton_limpiar.toggled.connect(self._al_activar_limpieza)
        fila_fondo.addWidget(self.boton_fondo)
        fila_fondo.addWidget(self.boton_limpiar)
        fila_fondo.addStretch(1)
        derecha.addLayout(fila_fondo)

        # Chip de fuente + aviso de mascara: nada falla en silencio.
        fila_estado = QHBoxLayout()
        fila_estado.setSpacing(tokens.ESPACIO_ITEM)
        self.lbl_fuente = QLabel("Analizando: original")
        self.lbl_fuente.setObjectName("valorCampo")
        self.lbl_aviso = QLabel("")
        self.lbl_aviso.setObjectName("valorCampo")
        fila_estado.addWidget(self.lbl_fuente)
        fila_estado.addWidget(self.lbl_aviso)
        fila_estado.addStretch(1)
        derecha.addLayout(fila_estado)

        # Solo modo bordes: fila "Método:" + vaciar el relleno.
        fila_metodo = QHBoxLayout()
        fila_metodo.setSpacing(tokens.ESPACIO_ITEM)
        self.lbl_metodo = QLabel("Método:")
        self.lbl_metodo.setObjectName("etiquetaCampo")
        self.boton_metodo = QPushButton("Canny")
        self.boton_metodo.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_metodo.clicked.connect(self.rotar_metodo)
        self.boton_vaciar = QPushButton("Vaciar relleno")
        self.boton_vaciar.setFixedSize(tokens.BTN_ANCHO, tokens.BTN_ALTO)
        self.boton_vaciar.clicked.connect(self.vaciar_relleno)
        fila_metodo.addWidget(self.lbl_metodo)
        fila_metodo.addWidget(self.boton_metodo)
        fila_metodo.addWidget(self.boton_vaciar)
        fila_metodo.addStretch(1)
        derecha.addLayout(fila_metodo)

        # Sliders y contenedor del histograma
        self.lbl_inf = QLabel("Umbral inferior")
        self.lbl_inf.setObjectName("etiquetaCampo")
        self.lbl_sup = QLabel("Umbral superior")
        self.lbl_sup.setObjectName("etiquetaCampo")
        self.slider_inf = QSlider(Qt.Horizontal)
        self.slider_inf.setRange(0, 255)
        self.slider_inf.setValue(0)
        self.slider_inf.setMinimumHeight(44)
        self.slider_sup = QSlider(Qt.Horizontal)
        self.slider_sup.setRange(0, 255)
        self.slider_sup.setValue(255)
        self.slider_sup.setMinimumHeight(44)
        self.vista_histograma = ZonaBordes(tokens.RAZON_HISTO_GRAF, (467, 180), self)
        self.vista_histograma.setObjectName("lienzoImagen")
        self.mini_contorno.clic_en_imagen.connect(self.al_rellenar)
        self.vista_histograma.clic_en_imagen.connect(self.al_rellenar)
        self.slider_inf.valueChanged.connect(self.al_cambiar_rango)
        self.slider_sup.valueChanged.connect(self.al_cambiar_rango)
        derecha.addWidget(self.vista_histograma, stretch=1)
        derecha.addWidget(self.lbl_inf)
        derecha.addWidget(self.slider_inf)
        derecha.addWidget(self.lbl_sup)
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
        self._aplicar_modo()  # visibilidad inicial del modo umbral

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
        # Esta pantalla siempre ARRANCA en modo umbral, pase lo que pase
        # en la sesion anterior; el relleno acumulado en estado.mascara
        # se conserva.
        self._modo = "umbral"
        self.boton_modo.setText("Detección de umbral")
        # El preview siempre arranca apagado al entrar.
        self._fondo_activo = False
        self.boton_fondo.setText("Quitar fondo")
        self._aplicar_modo()  # visibilidad + sliders del modo + refrescar

    def _base_histograma(self):
        # Preprocesada si existe (quitar fondo de la principal), si no la
        # original. El histograma, el canal y el contorno van sobre esta.
        if self.estado.preprocesada is not None:
            return self.estado.preprocesada
        return self.estado.original

    def _letra(self):
        return self.estado.canal_actual

    def _al_activar_limpieza(self, activo: bool) -> None:
        # Estado visual de activo: anillo azul permanente mientras esta ON.
        if activo:
            self.boton_limpiar.setStyleSheet(
                f"border: 2px solid {tokens.ACENTO}; border-radius: 30px;"
            )
        else:
            self.boton_limpiar.setStyleSheet("")
        self.refrescar()  # unico camino: preview y contorno al dia

    def _reconstruir_mascara(self):
        """UNICO camino de construccion de la mascara (contorno y preview).

        Base = preprocesada si existe, si no original. Rango sobre el
        componente B/N del canal activo, interseccion con estado.mascara
        si existe, limpieza si el toggle esta ON salvo cobertura <2 % o
        >98 % (ahi no hay nada que limpiar y se avisa en vez de fallar
        en silencio). Devuelve (mascara o None, cobertura 0-1, aviso).
        """
        base = self._base_histograma()
        if base is None:
            return None, 0.0, ""
        comp = canales.componente(base, self.estado.espacio, self._letra())
        masc = core_hist.mascara_por_rango(comp, self.estado.inf, self.estado.sup)
        if self.estado.mascara is not None:
            masc = np.where(masc > 0, self.estado.mascara, 0).astype(np.uint8)
        total = masc.size
        cobertura = float(np.count_nonzero(masc)) / total if total else 0.0
        aviso = ""
        if cobertura <= 0.0:
            return None, cobertura, "rango vacio: sin objeto"
        if cobertura >= 1.0:
            aviso = "rango total: la mascara cubre todo"
        if self.boton_limpiar.isChecked() and 0.02 <= cobertura <= 0.98:
            masc = segmentacion.limpiar_mascara(masc)
            if not np.any(masc):
                return None, 0.0, "limpieza dejo vacio: ajusta el rango"
            aviso = (aviso + " + " if aviso else "") + "limpieza activa"
            cobertura = float(np.count_nonzero(masc)) / total
        return masc, cobertura, aviso

    def _refrescar_contorno(self, mascara) -> None:
        # Objeto RELLENO (silueta blanca sobre negro) + borde de 1 px
        # encima para definir el perimetro.
        if mascara is None or not np.any(mascara):
            self.mini_contorno.set_imagen(QPixmap())
            return
        borde = segmentacion.contorno(mascara)
        relleno = mascara.copy()
        relleno[borde > 0] = 255
        self.mini_contorno.set_imagen(a_pixmap(relleno))

    def refrescar(self):
        if self.estado.original is None:
            return
        base = self._base_histograma()
        self.lbl_fuente.setText(
            "Analizando: sin fondo"
            if self.estado.preprocesada is not None
            else "Analizando: original"
        )
        if self._modo == "bordes":
            self._refrescar_bordes(base)
            return
        letra = self._letra()
        self.boton_canal.setText(letra)
        texto = canales.etiqueta_canal(self.estado.espacio, letra)
        self.valor_canal.setText(texto)
        self.valor_canal.setStyleSheet(f"color: {tokens.COLOR_CANAL[letra]};")

        self.mini_original.set_imagen(a_pixmap(self.estado.original))
        canal_arr = canales.aplicar_modo(
            base, self.estado.espacio, letra, self.estado.modo
        )
        self.mini_canal.set_imagen(a_pixmap(canal_arr))
        # Mascara viva del unico camino: contorno y preview nunca se
        # quedan obsoletos porque se reconstruyen aqui en cada refresco.
        mascara, _cobertura, aviso = self._reconstruir_mascara()
        self.lbl_aviso.setText(aviso)
        # Preview con mascara: base x mascara en original y canal.
        # Solo visualizacion local: no escribe estado.
        if self._fondo_activo and mascara is not None:
            vista_orig = base.copy()
            vista_orig[mascara == 0] = 0
            self.mini_original.set_imagen(a_pixmap(vista_orig))
            vista_base = base.copy()
            vista_base[mascara == 0] = 0
            self.mini_canal.set_imagen(
                a_pixmap(
                    canales.aplicar_modo(
                        vista_base, self.estado.espacio, letra, self.estado.modo
                    )
                )
            )

        self._refrescar_contorno(mascara)

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
        png = core_hist.figura_histograma(comp, self.estado.inf, self.estado.sup)
        pix = QPixmap()
        pix.loadFromData(png, "PNG")
        self.vista_histograma.set_imagen(pix)

    def al_cambiar_rango(self):
        if self._modo == "bordes":
            # Sliders = umbrales t1/t2 del metodo; el rango de umbral
            # (estado.inf/sup) queda intacto hasta volver al modo.
            self._t1 = self.slider_inf.value()
            self._t2 = self.slider_sup.value()
        else:
            self.estado.inf = self.slider_inf.value()
            self.estado.sup = self.slider_sup.value()
        self.refrescar()  # unico camino: todo se reconstruye en fresco

    def alternar_fondo(self):
        # Preview local: usa la mascara viva del unico camino. No escribe
        # `estado`: histograma y contorno quedan intactos.
        if self._modo == "bordes" and not self._hay_relleno():
            # Nada falla en silencio: sin relleno no hay fondo que quitar.
            self.lbl_aviso.setText(
                "no hay relleno: haz clic en el contorno para llenar el objeto"
            )
            return
        self._fondo_activo = not self._fondo_activo
        self.boton_fondo.setText(
            "Restaurar original" if self._fondo_activo else "Quitar fondo"
        )
        self.refrescar()

    def _hay_relleno(self) -> bool:
        """Hay alguna region rellena en la mascara compartida."""
        mascara = self.estado.mascara
        return mascara is not None and bool(np.any(mascara))

    def _colocar_boton_fondo(self, bordes: bool) -> None:
        """El boton 'Quitar fondo' cambia de sitio con el modo: en umbral
        va en la fila de la derecha (junto a 'Limpiar mascara'); en bordes
        va en la rejilla de miniaturas, DEBAJO del cuadro 'Canal activo'.
        Es el MISMO boton en los dos modos: un solo estado y un solo texto.
        """
        if bordes:
            self._fila_fondo.removeWidget(self.boton_fondo)
            self._rejilla.addWidget(self.boton_fondo, 3, 1)
        else:
            self._rejilla.removeWidget(self.boton_fondo)
            self._fila_fondo.insertWidget(0, self.boton_fondo)

    # --- modos umbral / bordes ----------------------------------------
    def alternar_modo(self):
        # El texto del boton muestra SIEMPRE el modo activo. No escribe
        # `estado` (salvia del relleno, que solo crece por clics).
        self._modo = "bordes" if self._modo == "umbral" else "umbral"
        self.boton_modo.setText(
            "Detección de bordes" if self._modo == "bordes" else "Detección de umbral"
        )
        # El preview de quitar fondo es de cada modo: al cambiar, se
        # reinicia (el relleno acumulado NO se pierde).
        self._fondo_activo = False
        self.boton_fondo.setText("Quitar fondo")
        self._aplicar_modo()

    def _aplicar_modo(self):
        """Visibilidad de cada fila + recarga de sliders segun el modo.

        El orden importa: `self._modo` ya cambio ANTES de llamar, porque
        setValue dispara valueChanged -> al_cambiar_rango, que ramifica
        por modo (cargar el mismo valor es inocuo; cargar el valor del
        modo equivocado pisaria estado.inf/sup).
        """
        bordes = self._modo == "bordes"
        # La vista grande SIEMPRE se ve: en umbral muestra el histograma,
        # en bordes el mapa de bordes (tambien clicable, §6.4).
        self.vista_histograma.setVisible(True)
        self.lbl_canal.setVisible(not bordes)
        self.valor_canal.setVisible(not bordes)
        self.boton_canal.setVisible(not bordes)
        self.boton_limpiar.setVisible(not bordes)
        # El boton 'Quitar fondo' esta siempre visible: cambia de sitio
        # con el modo (fila derecha en umbral, rejilla en bordes).
        self.boton_fondo.setVisible(True)
        self._colocar_boton_fondo(bordes)
        self.lbl_metodo.setVisible(bordes)
        self.boton_metodo.setVisible(bordes)
        self.boton_vaciar.setVisible(bordes)
        self.lbl_inf.setVisible(bordes)
        self.lbl_sup.setVisible(bordes)
        inf, sup = (
            (self._t1, self._t2) if bordes else (self.estado.inf, self.estado.sup)
        )
        for slider, valor in ((self.slider_inf, inf), (self.slider_sup, sup)):
            slider.blockSignals(True)
            slider.setValue(valor)
            slider.blockSignals(False)
        self.refrescar()

    def rotar_metodo(self):
        metodos = core_bordes.METODOS
        indice = (metodos.index(self._metodo) + 1) % len(metodos)
        self._metodo = metodos[indice]
        self.boton_metodo.setText(self._metodo.capitalize())
        self.refrescar()

    def vaciar_relleno(self):
        # Vaciar relleno = mascara compartida a None: tambien descarta la
        # de "Quitar fondo" de la principal (documentado en 6.4).
        self.estado.mascara = None
        self.refrescar()

    def al_rellenar(self, ix: int, iy: int) -> None:
        """Clic sobre el mapa de bordes: rellena la region y acumula con OR."""
        if self._modo != "bordes" or self.estado.original is None:
            return
        if self._mapa_bordes is None:
            return
        nueva, hubo = core_bordes.rellenar_bordes(
            self._mapa_bordes, self.estado.mascara, (ix, iy), self._metodo
        )
        if hubo:
            self.estado.mascara = nueva
            self.refrescar()
            # El aviso va DESPUES del refresco: el refresco limpia el chip.
            self.lbl_aviso.setText(self._aviso_relleno())
        else:
            # Nada falla en silencio: el clic no cerro region nueva
            # (fondo abierto, punto ya lleno o pared sin libre cercano).
            self.lbl_aviso.setText("clic sin efecto: sin region cerrada ahi")

    def _aviso_relleno(self) -> str:
        """Que paso con el ultimo relleno: nada, cerrado con el marco de
        la imagen, o el contorno tiene un hueco y se llevo el fondo."""
        mascara = self.estado.mascara
        if mascara is None or not np.any(mascara):
            return ""
        toca_borde = bool(
            mascara[0, :].any()
            or mascara[-1, :].any()
            or mascara[:, 0].any()
            or mascara[:, -1].any()
        )
        cobertura = float(np.count_nonzero(mascara)) / mascara.size
        if cobertura > 0.90:
            return "el contorno tiene un hueco: el relleno cubre casi toda la imagen"
        if toca_borde:
            return "objeto cerrado con el borde de la imagen"
        return ""

    def _refrescar_bordes(self, base):
        """Miniaturas + vista grande en modo bordes.

        - Imagen original: base con el relleno acumulado superpuesto; si
          el preview de "Quitar fondo" esta activo, el fondo se deja en
          negro y solo queda el objeto relleno.
        - Canal activo: canal con los bordes superpuestos (tambien sin
          fondo si el preview esta activo).
        - Contorno binario y vista grande: el mapa de bordes.
        """
        letra = self._letra()
        comp = canales.componente(base, self.estado.espacio, letra)
        mapa = core_bordes.detectar_bordes(comp, self._metodo, self._t1, self._t2)
        self._mapa_bordes = mapa
        self.lbl_aviso.setText("")
        hay = self._hay_relleno()
        vista_orig = base.copy()
        if hay:
            mascara = self.estado.mascara
            if self._fondo_activo:
                # Preview: solo el objeto, el fondo en negro.
                vista_orig[mascara == 0] = 0
            else:
                mascara3 = mascara > 0
                vista_orig[mascara3] = (
                    0.5 * vista_orig[mascara3].astype(np.float32)
                    + 0.5 * np.array(_ACENTO_RGB, np.float32)
                ).astype(np.uint8)
        self.mini_original.set_imagen(a_pixmap(vista_orig))
        canal_rgb = np.dstack([comp, comp, comp])
        if hay and self._fondo_activo:
            dentro = self.estado.mascara > 0
            canal_rgb[~dentro] = 0
            bordes_visibles = (mapa > 0) & dentro
        else:
            bordes_visibles = mapa > 0
        canal_rgb[bordes_visibles] = _ACENTO_RGB
        self.mini_canal.set_imagen(a_pixmap(canal_rgb))
        pix_mapa = a_pixmap(mapa)
        self.mini_contorno.set_imagen(pix_mapa)
        self.vista_histograma.set_imagen(pix_mapa)

    # --- guardado -----------------------------------------------------
    def _mascara_a_guardar(self):
        """Mascara que exportan Guardar imagen/mascara segun el modo.

        En umbral: la mascara viva del unico camino (rango + limpieza).
        En bordes: el relleno acumulado tal cual (estado.mascara), sin
        intersecar con el rango: el usuario esta construyendo eso.
        """
        if self._modo == "bordes":
            if self.estado.mascara is None or not np.any(self.estado.mascara):
                return None
            return self.estado.mascara
        return self._reconstruir_mascara()[0]

    def guardar_imagen(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar imagen", "", "PNG (*.png)")
        if not ruta:
            return
        if not os.path.splitext(ruta)[1]:
            ruta += ".png"
        rgb = self._base_histograma()[:, :, :3]
        # La MISMA mascara que exporta "Guardar mascara": en umbral la del
        # rango (con limpieza), en bordes el relleno acumulado. Antes se
        # usaba `estado.mascara` (o alfa 255 en todo el PNG) y la
        # seleccion del usuario se perdia en silencio.
        mascara = self._mascara_a_guardar()
        if mascara is None or not np.any(mascara):
            QMessageBox.warning(
                self,
                "Guardar imagen",
                "No hay nada que guardar: ajusta el rango de los sliders "
                "o rellena el objeto en modo bordes.",
            )
            return
        core_imagen.guardar_imagen(ruta, rgb, mascara)
        QMessageBox.information(self, "Guardar imagen", "Imagen guardada.")

    def guardar_mascara(self):
        # PSD de Photoshop: capa con la imagen original + la mascara como
        # mascara de capa (asi se recuperan pixeles al pintar sobre ella).
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar máscara", "", "Photoshop (*.psd)"
        )
        if not ruta:
            return
        if not os.path.splitext(ruta)[1]:
            ruta += ".psd"
        rgb = self._base_histograma()[:, :, :3]
        mascara = self._mascara_a_guardar()
        if mascara is None or not np.any(mascara):
            mascara = np.zeros(self.estado.original.shape[:2], np.uint8)
        try:
            core_imagen.guardar_psd(ruta, rgb, mascara)
        except ImportError:
            QMessageBox.warning(self, "Guardar máscara", "psd-tools no esta instalado.")
            return
        QMessageBox.information(self, "Guardar máscara", "Máscara guardada.")

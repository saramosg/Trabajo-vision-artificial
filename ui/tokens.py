# Tokens de diseno: unica fuente de verdad de colores, medidas y tipografias.
# `styles.qss` es CSS plano y no puede leer este archivo: los valores van
# copiados a mano y deben mantenerse iguales en ambos lados.
FONDO        = "#FFFFFF"
SUPERFICIE   = "#D9D9D9"
TEXTO        = "#000000"
TEXTO_SUAVE  = "#5F5F5F"
BORDE        = "#9E9E9E"
ACENTO       = "#2F6FED"
ACENTO_HOVER = "#1E5AC8"
PELIGRO      = "#C62828"   # reservado: hoy ninguna accion destructiva lo usa
                           # ("Sobreescribir" pide confirmacion con un QMessageBox,
                           #  no con un boton rojo). No lo elimines sin revisar §6.5.

# Colores de las etiquetas de cada canal.
COLOR_CANAL = {
    "R": "#C62828",   # rojo
    "G": "#2E7D32",   # verde     4.8:1 sobre blanco
    "B": "#1565C0",   # azul
    "Y": "#8D6E00",   # amarillo  4.6:1 sobre blanco
    "C": "#00838F",   # cian
    "M": "#AD1457",   # magenta
}

# Estados deshabilitados (unica definicion; el QSS debe usar estos valores)
SUPERFICIE_DESHABILITADO = "#EFEFEF"
TEXTO_DESHABILITADO      = "#9E9E9E"
BORDE_DESHABILITADO      = "#DCDCDC"

# Lado FIJO de toda salida de la pantalla "Recortar imagen".
LADO_SALIDA = 512

# Tipografias
FUENTE       = "Segoe UI"
TITULO       = 28   # peso bold, para el nombre de cada pantalla
ETIQUETA     = 16   # peso normal
BOTON        = 14   # peso semibold
DATO         = 14   # pesos de metricas y rutas

# Tamano de ventana (inicial) y limites
VENTANA_ANCHO      = 1280
VENTANA_ALTO       = 720
VENTANA_MIN_ANCHO  = 1000   # por debajo no se permite redimensionar
VENTANA_MIN_ALTO   = 560

BTN_ANCHO       = 200   # boton estandar (todos)
BTN_ALTO        = 60    # boton estandar (todos)
BTN_NAV_ANCHO   = 160   # boton de navegacion (REGRESAR)
BTN_NAV_ALTO    = 48

CANAL_LADO      = 300   # lienzos de canal R/G/B y miniaturas
HUECO_CANAL     = 130   # separacion horizontal SOLO entre lienzos de canal
MARGEN           = 60        # margen exterior minimo de la pantalla

# Radios
RADIO_BOTON     = 30    # boton estandar de 60 de alto -> pastilla completa
RADIO_NAV       = 24    # boton de navegacion de 48 de alto -> pastilla completa
RADIO_CAMPO     = 8     # reservado: hoy no hay QLineEdit ni QSpinBox (§5.3)
RADIO_LIENZO    = 12    # cuadros de imagen
TITULO_ALTO     = 48

# Proporcion de los cuadros de imagen, tomada del Figma (ancho:alto).
RAZON_CANAL      = (300, 300)    # lienzos R/G/B y Y/C/M   -> 1:1
RAZON_ZONA       = (300, 300)    # zona de imagen           -> 1:1
RAZON_HISTO_IMG  = (250, 250)    # miniaturas del histograma -> 1:1
RAZON_HISTO_GRAF = (467, 333)    # grafico del histograma   -> ~1.40:1
LADO_ZONA_RECORTE = 613          # lado minimo de la vista de recorte.

# Espaciado (rejilla vertical)
ESPACIO_ITEM    = 24   # entre elementos de un mismo grupo, y entre botones
ESPACIO_GRUPO   = 40   # separacion vertical entre GRUPOS distintos

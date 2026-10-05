# Guía de implementación — Analizador de imágenes (PySide6 + QSS)

> **Propósito de este archivo:** es una guía **ejecutable**. Contiene el contexto, el stack, la preparación del entorno, el sistema de diseño, las pantallas, la lógica de procesamiento, los criterios de aceptación y el empaquetado. Al cargar este archivo, se debe seguir la sección **Cómo usar esta guía** y completar cada paso verificándolo antes de avanzar.
>
> **Decisión clave de diseño:** las medidas del archivo de Figma son un **bosquejo rápido** (botones descentrados, proporciones desiguales). Por lo tanto **NO se copian las coordenadas del Figma al código**. Se adoptan **tamaños uniformes** definidos en el §5 y se usan **layouts de Qt** (`QGridLayout` / `QVBoxLayout`), no coordenadas absolutas.
>
> **Qué sí se toma del Figma, y con qué prioridad:**
> 1. El **inventario** de elementos y su función (qué botones existen y para qué sirven).
> 2. Las **proporciones** de los cuadros de imagen (`RAZON_*`) y su **tamaño de diseño**.
>
> **Qué manda si hay conflicto:** los **tamaños de botones, campos y espaciados salen solo de §5.2 y §5.3**, y prevalecen sobre cualquier medida del Figma. Los tamaños fijos de §5.2 no se sustituyen por medidas del Figma.

---

## 0. Cómo usar esta guía

Ejecutar en este orden. Cada paso termina con un **punto de control** verificable; no avanzar si falla.

| # | Paso | Punto de control |
|---|------|------------------|
| 1 | Preparar entorno virtual e instalar dependencias (§3) | `python -c "import PySide6, cv2, numpy, PIL, psd_tools"` no falla |
| 2 | Crear estructura de carpetas y archivos (§4) | Existen todos los archivos listados |
| 3 | Definir `tokens.py` y `styles.qss` (§5) | `python -c "from ui import tokens; print(tokens.BTN_ALTO)"` imprime el valor |
| 4 | Implementar los módulos de `core/` (§7) | Las funciones devuelven arrays con las formas esperadas |
| 5 | Implementar los widgets de `ui/widgets.py` (§5.5, §6.4, §6.5) | `ProporcionImagen`, `GraficoHistograma`, `OverlayMarcadores`, `Histograma` y `SelectorCuadrado` se instancian sin error |
| 6 | Implementar pantallas en el orden: principal → RGB → YCM → histograma → recorte (§6) | Cada ventana abre y navega sin errores |
| 7 | Verificar criterios de aceptación (§9) | Todos los checks en verde |

> **El empaquetado a `.exe` (§10) NO es parte del desarrollo.** Se hace **solo al final**, cuando el proyecto ya está completo, probado y aceptado. Durante el desarrollo se ejecuta siempre con `python main.py`.

---

## 1. Objetivo y alcance

Construir una **aplicación de escritorio** (ventana nativa propia, **no navegador**) que:

1. Permita **seleccionar una imagen** y visualizarla.
2. Aplique **preprocesado para quitar el fondo** con dos modelos intercambiables: **GrabCut** (predeterminado) y **OTSU**.
3. Muestre el **resultado sin sobrescribir** el archivo original (acción no destructiva).
4. Analice los **canales de color RGB y YCM**, en dos modos de visualización: **color** y **blanco y negro**.
5. Muestre un **histograma de color por canal** con ajuste de rango y permita **guardar la imagen** y la **máscara**.
6. Permita **recortar/redimensionar** y guardar **copia** o **sobrescribir**.

**Fuera de alcance:** diseño con Qt Designer (se usa layout en código + QSS), bases de datos, empaquetado multiplataforma en esta primera versión.

---

## 2. Stack tecnológico

| Capa | Tecnología | Motivo |
|------|-----------|--------|
| Interfaz | **PySide6-Essentials** (Qt 6) | Aplicación de escritorio nativa; conjunto completo de widgets |
| Estilos | **QSS** (`styles.qss`) | Sintaxis similar a CSS,Separada del código Python |
| Layout | **Qt Layouts** (`QGridLayout`, `QVBoxLayout`) | Garantiza alineación y uniformidad sin coordenadas duras |
| Imágenes | **opencv-python (cv2)** | GrabCut, OTSU, morfología, contornos |
| Cálculo | **numpy** | Manipulación de arrays de píxeles |
| E/S de imagen | **pillow (PIL)** | Abrir/guardar PNG, JPEG, RGBA |
| Guardado Photoshop | **psd-tools** | PSD con máscara de capa |
| Empaquetado | **PyInstaller** | Generar `.exe` para Windows |
| Python | **3.11.9** | Versión fijada del proyecto |

---

## 3. Preparación del entorno

### 3.1 Requisitos del sistema
- Windows 10/11.
- Python **3.11.9** instalado.
- VS Code con extensión **Python** y **Jupyter** (opcional, para los notebooks del curso).

### 3.2 Crear el entorno virtual

**PowerShell:**
```powershell
cd "C:\ruta\del\proyecto"
py -3.11 -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
```
Si PowerShell bloquea la ejecución de scripts:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& ".\.venv\Scripts\Activate.ps1"
```

**Git Bash:**
```bash
cd /c/ruta/del/proyecto
py -3.11 -m venv .venv
source .venv/Scripts/activate
```

Sin activar el venv (activación por ruta, útil en VS Code y para PyInstaller):
```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

### 3.3 Dependencias — `requirements.txt`

```
PySide6-Essentials>=6.6,<7
opencv-python>=4.9
numpy>=1.26
pillow>=10.2
psd-tools>=1.9
PyInstaller>=6.3
```

```bash
pip install -r requirements.txt
```

> **Decisión: `PySide6-Essentials`, no `PySide6`.** La aplicación solo usa `QtCore`, `QtGui` y `QtWidgets`. El metapaquete `PySide6` arrastra además QtWebEngine, Qt3D, QtCharts, QtDataVisualization, QtMultimedia y decenas de módulos más que no se usan: pasa de ~120 MB a cerca de 1 GB instalado y de ~40 MB a ~300 MB el `.exe` de PyInstaller. `PySide6-Essentials` es el subconjunto que contiene exactamente lo necesario. `shiboken6` llega como dependencia automática. Si algún día hiciera falta un módulo fuera del Essentials, se sube a `PySide6` en ese momento y con una nota que lo justifique.

> **Decisión: NO se usa `matplotlib`.** El histograma se dibuja con `QPainter` en el widget `GraficoHistograma` (`ui/widgets.py`, §7.6), igual que el resto de la interfaz. Motivos: un canvas de matplotlib no se puede estilizar con el QSS (contradice §8 regla 1), rompe el look de la app y obliga a empaquetar un backend extra en el `.exe`. Por eso `matplotlib` **no está** en `requirements.txt` ni en §11.

### 3.4 Verificación del entorno
```bash
python -c "import PySide6, cv2, numpy, PIL, psd_tools; print('OK')"
```

### 3.5 Configuración de VS Code — `.vscode/settings.json`
```json
{
    "python.defaultInterpreterPath": "C:\\ruta\\del\\proyecto\\.venv\\Scripts\\python.exe",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["."]
}
```
Además: `Ctrl+Shift+P` → **Python: Select Interpreter** → elegir el `.venv`. Para notebooks, `ipykernel` debe estar instalado en el venv:
```bash
pip install ipykernel
```

### 3.6 Ejecución
```bash
python main.py
```

---

## 4. Estructura del proyecto

### 4.0 Regla principal: desarrollo por módulos

**Primero se construye el proyecto en archivos `.py` separados y funcionales.** El `.exe` es un paso final opcional.

- Durante **todo** el desarrollo se ejecuta con `python main.py`.
- No se compila nada hasta que el proyecto esté completo y validado.
- No se crea un archivo gigante con toda la lógica: cada responsabilidad va en su módulo.
- `main.py` solo arranca la aplicación: crea `QApplication`, carga `styles.qss` y muestra la ventana principal. No contiene lógica de negocio ni de imagen.
- Un módulo de `core/` debe poder probarse **sin abrir ninguna ventana**.

### 4.1 Archivos



```
analizador/
├── main.py                  # punto de entrada: crea QApplication y muestra la ventana principal
├── requirements.txt
├── styles.qss               # hoja de estilos global (se carga en runtime)
├── main.spec                # config de PyInstaller. NO se escribe durante el
│                            #   desarrollo: se crea al final, en §10.3
├── ui/
│   ├── __init__.py
│   ├── tokens.py            # colores, tamaños uniformes, tipografías, espaciados
│   ├── ventana_principal.py # pantalla de preprocesado
│   ├── ventana_rgb.py       # pantalla de canales RGB
│   ├── ventana_ycm.py       # pantalla de canales YCM
│   ├── ventana_histograma.py
│   ├── ventana_recorte.py
│   ├── widgets.py           # widgets reutilizables: ProporcionImagen (escala y centra
│                            #   la imagen), SelectorCuadrado (área cuadrada §6.5),
│                            #   Histograma (contenedor), GraficoHistograma (barras),
│                            #   OverlayMarcadores (líneas y flechas §6.4),
│                            #   dibujar_marcadores (§6.4)
├── core/
│   ├── __init__.py
│   ├── imagen.py            # carga/guardado, RGBA, previsualización
│   ├── segmentacion.py      # grabcut, otsu, limpieza de máscara
│   ├── canales.py           # extracción RGB / YCM y modos color | blanco y negro
│   ├── histograma.py        # cálculo del histograma y percentiles
│   └── recorte.py           # recorte y redimensionado
└── assets/
    └── icon.ico
```

**Regla de dependencias:** `ui/` importa de `core/`; `core/` **nunca** importa de `ui/`. Toda la lógica de imagen vive en `core/` y se puede probar sin abrir ventana.

---

## 5. Sistema de diseño — tamaños uniformes y estética

> Los tamaños del Figma son desiguales; esta sección define los tamaños **estándar** a usar en toda la app. Ningún widget debe usar medidas fuera de esta tabla.

### 5.1 Tokens — `ui/tokens.py`

```python
# Colores
FONDO        = "#FFFFFF"
SUPERFICIE   = "#D9D9D9"
TEXTO        = "#000000"
TEXTO_SUAVE  = "#5F5F5F"
BORDE        = "#9E9E9E"
ACENTO       = "#2F6FED"
ACENTO_HOVER = "#1E5AC8"
PELIGRO      = "#C62828"   # reservado: hoy ninguna acción destructiva lo usa
                       # ("Sobreescribir" pide confirmación con un QMessageBox,
                       #  no con un botón rojo). No lo elimines sin revisar §6.5.

# Colores de los marcadores de los sliders sobre el histograma.
# Deben ser distintos entre sí y contrastar con las barras del gráfico.
MARCADOR_INFERIOR = "#E65100"   # naranja  -> límite inferior de intensidad
MARCADOR_SUPERIOR = "#00897B"   # verde    -> límite superior de intensidad

# Colores de las etiquetas de cada canal (campo "Canal actual", §6.4).
# Variantes OSCURAS a propósito: un texto de 14 px sobre blanco #FFFFFF
# necesita ≥ 4.5:1 de contraste (WCAG AA). El amarillo claro (#FDD835) daba
# 1.4:1 y el verde medio (#43A047) 3.3:1, ambos ilegibles.
COLOR_CANAL = {
    "R": "#C62828",   # rojo
    "G": "#2E7D32",   # verde     4.8:1 sobre blanco
    "B": "#1565C0",   # azul
    "Y": "#8D6E00",   # amarillo  4.6:1 sobre blanco
    "C": "#00838F",   # cian
    "M": "#AD1457",   # magenta
}

# Estados deshabilitados (única definición; el QSS debe usar estos valores)
SUPERFICIE_DESHABILITADO = "#EFEFEF"
TEXTO_DESHABILITADO      = "#9E9E9E"
BORDE_DESHABILITADO      = "#DCDCDC"

# Lado FIJO de toda salida de la pantalla "Recortar imagen". Es a la vez el
# tamaño del marco de referencia que ve el usuario y el tamaño exacto del PNG
# que se guarda. NO es configurable: por eso la pantalla no tiene ningún campo
# numérico para cambiarlo.
# Es la ÚNICA definición de 512 en el proyecto: §6.5 (marco y botones), §7.7
# (aplicar_recorte) y `EstadoImagen.vista_previa` la referencian. No volver a
# escribir 512 en otro sitio.
LADO_SALIDA = 512

# Tope del lado más largo de la imagen YA AMPLIADA en el modo B (§6.5). Existe
# porque el zoom no puede ser libre: 4x una imagen de 4000x400 son 16000 px de
# lado y 1600 del otro, 25,6 Mpx (~77 MB con 3 canales). El tope recorta esa vía.
# 4096x4096 = 16,7 Mpx = ~50 MB con 3 canales: holgado para un desktop, y de
# sobra para que un recorte de 512 siga teniendo detalle.
LADO_AMPLIADO_MAX = 4096

# Tipografías (el tamaño en px y el peso van en styles.qss; ver la tabla de
# correspondencia token <-> QSS al final de §5.6)
FUENTE       = "Segoe UI"
TITULO       = 28   # peso bold, para el nombre de cada pantalla
ETIQUETA     = 16   # peso normal
BOTON        = 14   # peso semibold
DATO         = 14   # pesos de métricas y rutas

# Tamaño de ventana (inicial) y límites
VENTANA_ANCHO      = 1280
VENTANA_ALTO       = 720
VENTANA_MIN_ANCHO  = 1000   # por debajo no se permite redimensionar
VENTANA_MIN_ALTO   = 560

BTN_ANCHO       = 200   # botón estándar (todos)
BTN_ALTO        = 60    # botón estándar (todos)
BTN_NAV_ANCHO   = 160   # botón de navegación (REGRESAR)
BTN_NAV_ALTO    = 48

CANAL_LADO      = 300   # lienzos de canal R/G/B y miniaturas
HUECO_CANAL     = 130   # separación horizontal SOLO entre lienzos de canal

# Ancho mínimo que exige el contenido más ancho de la app: la fila de 3 canales
# (3 x 300 + 2 x 130 = 1160 px). El margen se calcula a partir de aquí, NO como
# un porcentaje del ancho: un 28 % por lado dejaba 564 px útiles y la fila de
# canales no cabía nunca, ni con scroll.
#
# ORDEN OBLIGATORIO: esta constante va DESPUÉS de CANAL_LADO y HUECO_CANAL.
# Este archivo es Python y las constantes se evalúan de arriba abajo: si
# ANCHO_CONTENIDO aparece antes de las otras dos, importar ui.tokens lanza
# `NameError: name 'CANAL_LADO' is not defined` y la app no arranca.
ANCHO_CONTENIDO  = 3 * CANAL_LADO + 2 * HUECO_CANAL   # 1160 px
MARGEN           = 60        # margen exterior mínimo de la pantalla

# Radios
RADIO_BOTON     = 30    # botón estándar de 60 de alto -> pastilla completa
RADIO_NAV       = 24    # botón de navegación de 48 de alto -> pastilla completa
RADIO_CAMPO     = 8     # reservado: hoy no hay QLineEdit ni QSpinBox (§5.3)
RADIO_LIENZO    = 12    # cuadros de imagen (zona, lienzos, miniaturas, histograma)
TITULO_ALTO     = 48

# Proporción de los cuadros de imagen, tomada del Figma (ancho:alto).
# Son innegociables: el cuadro NUNCA se deforma.
RAZON_CANAL      = (300, 300)    # lienzos R/G/B y Y/C/M   -> 1:1
RAZON_ZONA       = (300, 300)    # zona de imagen           -> 1:1
RAZON_HISTO_IMG  = (250, 250)    # miniaturas del histograma -> 1:1
RAZON_HISTO_GRAF = (467, 333)    # gráfico del histograma   -> ~1.40:1
RAZON_RECORTE    = (1, 1)        # zona de recorte          -> SIEMPRE cuadrada
ALTO_GRAFICO_MIN = 180          # alto mínimo del gráfico del histograma.
                                    # No hay ancho mínimo: el gráfico crece con
                                    # Expanding y su razón (467x333) la fija
                                    # RAZON_HISTO_GRAF en el paintEvent.
LADO_ZONA_RECORTE = 613          # lado de diseño del CUADRO DE SELECCIÓN, es
                                   # decir el tamaño del área visible de la
                                   # pantalla de recorte. NO es el tamaño de
                                   # la salida: esa es LADO_SALIDA = 512, que va
                                   # dentro de este cuadro.

# Espaciado (rejilla vertical)
ESPACIO_ITEM    = 24   # entre elementos de un mismo grupo, y entre botones
ESPACIO_GRUPO   = 40   # separación vertical entre GRUPOS distintos de una misma
                       # pantalla (p. ej. el bloque de info de rutas frente al
                       # bloque de botones). Se aplica con addSpacing() en el
                       # layout; dentro de un grupo se usa ESPACIO_ITEM.
```

### 5.2 Tabla de tamaños por elemento

| Elemento | Ancho | Alto | Tipografía | Radio |
|----------|-------|------|-----------|-------|
| Título de pantalla | automático (centrado) | 48 (`TITULO_ALTO`) | TITULO bold | — |
| Botón estándar | 200 | 60 | BOTON | **30 (pastilla)** |
| Botón de navegación | 160 | 48 | BOTON | **24 (pastilla)** |
| Campo de entrada | automático | 44 | DATO | 8 (`RADIO_CAMPO`) |
| Etiqueta de campo | automático | 28 | ETIQUETA | — |
| Valor de campo | automático | **mínimo 28, el que necesite** | DATO | — |
| Slider del histograma | **exactamente el ancho del groove** que mapea el gráfico | groove 4 px, **área táctil ≥ 44 px** | — | 2 (groove) |
| Marcador de slider (línea) | 3 px | altura del gráfico | — | — |
| Marcador de slider (flecha) | 14 | 18 | — | — |
| Etiqueta de valor del marcador | 80 | 16 | DATO | — |
| Zona de imagen | 300 | 300 | — | 12 (`RADIO_LIENZO`) |
| Lienzo de canal | 300 | 300 | — | 12 (`RADIO_LIENZO`) |
| Imagen del histograma | 250 | 250 | — | 12 (`RADIO_LIENZO`) |
| Gráfico del histograma | 467 | 333 | — | 12 (`RADIO_LIENZO`) |
| Zona de recorte (cuadrada) | **613, también mínimo** | igual al ancho | — | 12 (`RADIO_LIENZO`) |

El "valor de campo" **no** tiene alto fijo: usa `setMinimumHeight(28)` y crece con `setWordWrap(True)`. Con un alto fijo de 28 px, una ruta larga de Windows se cortaría a mitad.

### 5.3 Reglas de uniformidad (obligatorias)

1. **Todos los botones estándar miden exactamente 200×60.** Ningún botón queda sin ancho o alto fijo.
2. **Alineación:** todos los grupos se centran horizontalmente con `Qt.AlignHCenter`; los campos de información (`Imagen:`, `Directorio:`) se alinean a la izquierda en el mismo margen, calculado dinámicamente (ver §5.4).
3. **Botones en columna:** se apilan verticalmente con `ESPACIO_ITEM` (24 px) de separación y todos con el mismo ancho (200), de modo que formen una columna perfectamente recta.
4. **Espejo de botones:** en una fila de botones, ambos miden 200×60 y están separados por `ESPACIO_ITEM` (24 px). `HUECO_CANAL` (130 px) es **solo** para los lienzos de canal: 130 px entre dos botones los haría leer como grupos distintos.
5. **`setFixedSize()` solo en controles. `setMinimumSize()` + `Expanding` en los cuadros de imagen.** Un widget no puede ser a la vez fijo y expandible: los botones y campos usan `setFixedSize()`; los cuadros de imagen (`ProporcionImagen`, `SelectorCuadrado`, `GraficoHistograma`) usan `setMinimumSize()` + `setSizePolicy(Expanding, Expanding)` para poder crecer al maximizar, y **nunca** `setFixedSize()`. Los **contenedores** usan layouts (`QGridLayout`, `QVBoxLayout`) y ocupan todo el espacio disponible; nunca se usa `move()` ni `setGeometry()` para ubicación.
6. **Textos centrados** dentro de su widget: `setAlignment(Qt.AlignCenter)`.
7. **Estados visuales obligatorios:** normal, hover, presionado, **con foco** y deshabilitado (fondo `SUPERFICIE_DESHABILITADO`, texto `TEXTO_DESHABILITADO`, borde `BORDE_DESHABILITADO`; ver §5.3.1).
8. **Ningún control debe quedar cortado** al redimensionar: si la ventana se reduce por debajo del espacio necesario, la pantalla usa `QScrollArea` con `setWidgetResizable(True)`.

### 5.3.1 Botones redondeados (obligatorio)

1. **Todos los botones son tipo pastilla.** El radio es **igual a la mitad del alto** del botón: 30 px para los de 60 de alto y 24 px para los de 48 de alto. Así quedan completamente redondeados en los extremos.
2. **El radio nunca cambia entre estados.** `normal`, `:hover`, `:pressed`, `:disabled` y `:focus` deben declarar el **mismo** `border-radius`. Si el radio cambia al pasar el mouse, el botón "se deforma" y se ve descuidado.
3. **El tamaño no cambia entre estados.** El hover se logra **solo** cambiando el color de fondo, nunca el alto, el ancho, el padding ni el grosor del borde.
4. **Sin borde grueso.** Borde de **1 px** en `BORDE`; el efecto de profundidad viene del color, no del grosor.
5. **Padding horizontal generoso:** `padding: 12px 28px` para que el texto nunca quede pegado al borde redondeado.
6. **Botón deshabilitado visible:** mantiene la pastilla y usa **únicamente** `SUPERFICIE_DESHABILITADO` (`#EFEFEF`), `TEXTO_DESHABILITADO` (`#9E9E9E`) y `BORDE_DESHABILITADO` (`#DCDCDC`) de §5.1. Un texto deshabilitado de 14 px sobre `#EFEFEF` no puede bajar de `#9E9E9E`, o deja de leerse.
7. **Foco distinguible del hover:** `:focus` lleva un **anillo de foco propio** (`border: 2px solid ACENTO`) y **no** cambia el fondo; si copiara el fondo de `:hover`, el usuario de teclado no distinguiría el foco (WCAG 2.4.7). Excepción: en `#primario`, cuyo fondo ya es `ACENTO`, el anillo va **negro** (`#000000`), porque un anillo del mismo azul sería invisible. Los cinco estados van también en `#navegacion`.
8. **Consistencia absoluta:** un botón deshabilitado, presionado o con foco debe conservar **la misma silueta redondeada**. Revisar visualmente los cuatro estados de cada botón antes de dar por cerrada una pantalla.
9. **Verificación:** al pasar el mouse y al hacer click, el botón no debe cambiar de tamaño ni de forma.

### 5.4 Adaptación a la resolución

La ventana **arranca en 1280×720**, pero debe **poder maximizarse y adaptarse** a cualquier resolución (1920×1080, 1366×768, 2560×1440, scaled displays de Windows).

En `main.py`:
```python
app = QApplication(sys.argv)
ventana = VentanaPrincipal()
ventana.resize(tokens.VENTANA_ANCHO, tokens.VENTANA_ALTO)
ventana.setMinimumSize(tokens.VENTANA_MIN_ANCHO, tokens.VENTANA_MIN_ALTO)
ventana.show()
```

Reglas:

1. **Redimensionable:** usar `resize()` + `setMinimumSize()`; **nunca** `setFixedSize()` en la ventana.
2. **Margen derivado del contenido, no un porcentaje del ancho.** El contenido más ancho de la app es la fila de 3 canales: 1160 px. El margen se calcula para que ese contenido siempre entre, y en pantallas anchas el sobrante se reparte:
   ```python
   margen = max(tokens.MARGEN,
                (self.width() - tokens.ANCHO_CONTENIDO) // 2)
   ```
   Un margen porcentual (28 %) dejaba 564 px útiles a 1280 de ancho y la fila de canales no cabía ni con scroll.
3. **Estiramiento:** el layout raíz recibe un `stretch` para que los grupos se repartan el espacio sobrante vertical; los elementos centrados usan `addStretch()` antes y después.
4. **Escalado opcional de la interfaz:** si la resolución es menor que 1280×720, reducir proporcionalmente los elementos grandes (lienzos de canal, imagen de recorte, gráfico del histograma) con un factor, sin alterar los tamaños de botones:
   ```python
   escala = min(ancho_disponible / 3 / tokens.CANAL_LADO,
                alto_disponible / 2.4 / tokens.CANAL_LADO)
   lado = int(tokens.CANAL_LADO * max(0.5, min(1.0, escala)))
   ```
   El piso es **0.5**, no 0.75: con 0.75 el factor prácticamente no reducía nada y no cabía justo en las pantallas que motivaban la regla. El factor se aplica **también** al cuadro de recorte y al gráfico del histograma, no solo a los canales.

**Excepción: la zona de recorte NO se escala por resolución.** Su mínimo es 613 —el mismo que su diseño— porque por debajo el marco de 512 se sale y `SelectorCuadrado` acabaría con un `QRect` vacío (la red de seguridad de la regla 14). Encoger la ventana de recorte se compensa reduciendo `ANCHO_CONTENIDO`, no la zona. El factor de resolución sigue aplicándose a los cuadros de canal, que no tienen marco fijo.
5. **Al maximizar:** los lienzos de imagen y el gráfico **crecen** con `setSizePolicy(Expanding, Expanding)` manteniendo su relación de aspecto dentro del espacio asignado.
6. **DPI:** soporta escalado de Windows. No fijar `QT_SCALE_FACTOR` ni `Qt.AA_EnableHighDpiScaling` manualmente si la versión de PySide6 ya lo gestiona; verificar legibilidad a 125 % y 150 %.

### 5.5 Proporción de los cuadros de imagen

Los cuadros donde se muestran imágenes **conservan la proporción del Figma respecto al marco**. Redimensionar la ventana cambia el tamaño del cuadro, **nunca su relación de aspecto**.

Proporciones de referencia (del Figma, tamaño de referencia → razón):

| Cuadro | Tamaño en Figma | Razón | Token |
|--------|-----------------|-------|-------|
| Zona de imagen (preprocesado) | 300×300 | 1 : 1 | `RAZON_ZONA` |
| Lienzo de canal R/G/B y Y/C/M | 300×300 | 1 : 1 | `RAZON_CANAL` |
| Miniatura "Imagen original" | 250×250 | 1 : 1 | `RAZON_HISTO_IMG` |
| Miniaturas "Imagen por canales" | 250×250 | 1 : 1 | `RAZON_HISTO_IMG` |
| Canal de contorno binario | 250×250 | 1 : 1 | `RAZON_HISTO_IMG` |
| Gráfico del histograma | 467×333 | 1.40 : 1 | `RAZON_HISTO_GRAF` |
| Zona de recorte | 613×613 | **1 : 1** | `RAZON_RECORTE` |

Reglas obligatorias:

1. **Un solo factor de escala por cuadro.** Al agrandar o achicar la ventana, el alto y el ancho del cuadro se multiplican por el **mismo** factor; si no, se deforma.
2. **La imagen se ajusta sin deformarse.** Usar siempre `Qt.KeepAspectRatio` al escalar el `QPixmap`, y **centrarla** dentro del cuadro. Si sobra espacio, queda en los lados; nunca se estira.
3. **Widget dedicado `ProporcionImagen`.** Ningún `QLabel.setPixmap()` directo sobre un widget redimensionable (eso deforma la imagen). Implementar en `ui/widgets.py`:
   ```python
   class ProporcionImagen(QLabel):
       """Dibuja una imagen respetando siempre la proporción del cuadro."""
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
           escala = min(self.width() / self._original.width(),
                        self.height() / self._original.height())
           ancho = max(1, round(self._original.width() * escala))
           alto = max(1, round(self._original.height() * escala))
           self._ajustada = self._original.scaled(ancho, alto,
                                                 Qt.KeepAspectRatio, Qt.SmoothTransformation)

       def resizeEvent(self, evento):
           super().resizeEvent(evento)
           self._recalcular()

       def paintEvent(self, evento):
           super().paintEvent(evento)
           if self._ajustada.isNull():
               return
           x = (self.width() - self._ajustada.width()) // 2
           y = (self.height() - self._ajustada.height()) // 2
           evento.drawPixmap(x, y, self._ajustada)
   ```
4. **Tamaño mínimo garantizado.** Cada cuadro declara el tamaño del Figma como **mínimo** (`setMinimumSize`) para que nunca se vuelva ilegible, y el layout reparte el excedente hacia arriba manteniendo la razón:
   ```python
   disponible = min(alto_disponible - 180, ancho_disponible / 3 - 40)
   lado = int(disponible / 1)                 # RAZON_CANAL = (300, 300)
   ```
5. **Respetar la razón del Figma, no la de la foto.** El cuadro mantiene siempre la razón del Figma; la foto se adapta dentro con `KeepAspectRatio` y queda centrada.
6. **Verificación obligatoria:** redimensionar la ventana a 1366×768, 1920×1080 y maximizada; ningún cuadro puede verse ovalado ni achatado.

### 5.6 Estilos — `styles.qss`

```css
/* Base */
QWidget {
    background-color: #FFFFFF;
    color: #000000;
    font-family: "Segoe UI";
    font-size: 14px;
}

/* Título de pantalla */
QLabel#tituloPantalla {
    font-size: 28px;
    font-weight: 700;
    color: #000000;
}

/* Etiqueta de campo */
QLabel#etiquetaCampo { font-size: 16px; color: #000000; }
QLabel#valorCampo    { font-size: 14px; color: #5F5F5F; }

/* Botón estándar — pastilla redondeada.
   El border-radius es IGUAL en todos los estados (30 = mitad de 60 de alto)
   y el tamaño nunca cambia: el hover solo altera el color de fondo. */
QPushButton {
    background-color: #D9D9D9;
    color: #000000;
    border: 1px solid #9E9E9E;
    border-radius: 30px;
    padding: 12px 28px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton:hover   { background-color: #C9C9C9; border-radius: 30px; }
QPushButton:pressed { background-color: #B3B3B3; border-radius: 30px; }
/* :focus NO reutiliza el fondo del hover: solo añade el anillo de foco
   ACENTO de §5.1. El radio y el tamaño NO cambian (§5.3.1 reglas 2 y 3). */
QPushButton:focus {
    border: 2px solid #2F6FED;
    border-radius: 30px;
}
QPushButton:disabled {
    background-color: #EFEFEF;   /* SUPERFICIE_DESHABILITADO */
    color: #9E9E9E;             /* TEXTO_DESHABILITADO */
    border-color: #DCDCDC;      /* BORDE_DESHABILITADO */
    border-radius: 30px;
}

/* Botón de navegación (48 de alto -> radio 24) */
QPushButton#navegacion {
    border-radius: 24px;
    padding: 10px 24px;
}
QPushButton#navegacion:hover   { border-radius: 24px; background-color: #C9C9C9; }
QPushButton#navegacion:pressed { border-radius: 24px; background-color: #B3B3B3; }
QPushButton#navegacion:focus   { border-radius: 24px; border: 2px solid #2F6FED; }
QPushButton#navegacion:disabled{
    border-radius: 24px;
    background-color: #EFEFEF;   /* SUPERFICIE_DESHABILITADO */
    color: #9E9E9E;             /* TEXTO_DESHABILITADO */
    border-color: #DCDCDC;      /* BORDE_DESHABILITADO */
}

/* Botón de acento (acción principal de la pantalla) */
QPushButton#primario {
    background-color: #2F6FED;
    color: #FFFFFF;
    border: 1px solid #2F6FED;
    border-radius: 30px;
}
QPushButton#primario:hover   { background-color: #1E5AC8; border-radius: 30px; }
QPushButton#primario:pressed { background-color: #17489E; border-radius: 30px; }
/* El foco no cambia el fondo: solo el anillo. Sobre el azul ACENTO un anillo
   del mismo azul sería invisible, así que aquí va NEGRO (contraste 4.6:1). */
QPushButton#primario:focus   { border: 2px solid #000000; border-radius: 30px; }
/* Deshabilitado: los MISMOS tres tokens que el botón estándar (§5.3.1 regla 6).
   Un azul claro con texto casi blanco daba 1.2:1 y era ilegible. */
QPushButton#primario:disabled {
    background-color: #EFEFEF;   /* SUPERFICIE_DESHABILITADO */
    color: #9E9E9E;             /* TEXTO_DESHABILITADO */
    border-color: #DCDCDC;      /* BORDE_DESHABILITADO */
    border-radius: 30px;
}

/* Etiqueta de valor de campo */

/* Zona de imagen (previsualización) */
QLabel#zonaImagen {
    background-color: #D9D9D9;
    border: 1px dashed #9E9E9E;
    border-radius: 12px;
}

/* Contenedor de imagen / lienzo de canal */
QLabel#lienzoImagen {
    background-color: #D9D9D9;
    border: 1px solid #9E9E9E;
    border-radius: 12px;
}

/* Campos de entrada redondeados — RESERVADOS.
   La app no tiene hoy ningún QLineEdit ni QSpinBox: el selector de modelo es un
   QPushButton que alterna (§6.1) y el zoom del recorte es un QSlider. Estas
   reglas se quedan por si algún campo entra después; si no, se borran. */
QLineEdit, QSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #9E9E9E;
    border-radius: 8px;
    padding: 10px 12px;
}
QLineEdit:focus, QSpinBox:focus { border-color: #2F6FED; }

/* Deslizadores del histograma */
QSlider::groove:horizontal {
    height: 4px; background: #D9D9D9; border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 14px; margin: -6px 0; border-radius: 7px; background: #2F6FED;
}

/* Zoom del recorte (modo B, §6.5). Mismo aspecto que el del histograma para que
   no parezca otro control; el objectName lo separa si algún día divergen.

   El estado deshabilitado se pinta con COLORES, no con `opacity`: Qt Style
   Sheets no soporta `opacity` (la lista de propiedades es cerrada y no la
   incluye), así que una regla con `opacity` no falla —se ignora en silencio— y
   el control queda con el mismo aspecto que el activo. Por eso aquí se
   redefinen `::groove` y `::handle` con los tokens `disabled`. */
QSlider#zoomRecorte::groove:horizontal {
    height: 4px; background: #D9D9D9; border-radius: 2px;
}
QSlider#zoomRecorte::handle:horizontal {
    width: 14px; margin: -6px 0; border-radius: 7px; background: #2F6FED;
}
QSlider#zoomRecorte:disabled::groove:horizontal { background: #EDEDED; }
QSlider#zoomRecorte:disabled::handle:horizontal { background: #B8B8B8; }
```

5. **Identificadores (`objectName`) obligatorios** para poder estilizar por rol: `tituloPantalla`, `etiquetaCampo`, `valorCampo`, `zonaImagen`, `lienzoImagen`, `navegacion`, `primario`.

#### Correspondencia token ↔ valor del QSS

`styles.qss` es CSS plano: **no puede leer `tokens.py`**. Por eso los valores van
escritos a mano, y esta tabla es la que obliga a que coincidan. Si se cambia un
token de la columna izquierda, se cambia **también** su valor aquí.

| Token (§5.1) | Valor en `styles.qss` | Dónde se usa |
|---|---|---|
| `FONDO` | `#FFFFFF` | `QWidget` |
| `SUPERFICIE` | `#D9D9D9` | botón normal, `QSlider::groove`, `zonaImagen`, `lienzoImagen` |
| `TEXTO` | `#000000` | texto base, botón, `tituloPantalla`, `etiquetaCampo` |
| `TEXTO_SUAVE` | `#5F5F5F` | `valorCampo` |
| `BORDE` | `#9E9E9E` | bordes de botón, campos y cuadros |
| `ACENTO` | `#2F6FED` | `QPushButton:focus`, foco de `QLineEdit`/`QSpinBox` (reservados), `QSlider::handle`, `QSlider#zoomRecorte::handle` |
| `ACENTO_HOVER` | `#1E5AC8` | `QPushButton#primario:hover` |
| (derivado, §5.6) | `#C9C9C9` / `#B3B3B3` | hover / presionado del botón estándar |
| (derivado, §5.6) | `#17489E` | `QPushButton#primario:pressed` |
| `SUPERFICIE_DESHABILITADO` | `#EFEFEF` | todos los `:disabled` |
| `TEXTO_DESHABILITADO` | `#9E9E9E` | todos los `:disabled` |
| `BORDE_DESHABILITADO` | `#DCDCDC` | todos los `:disabled` |
| `FUENTE` | `"Segoe UI"` | `QWidget` |
| `TITULO` | `28px` / `font-weight: 700` | `tituloPantalla` |
| `ETIQUETA` | `16px` | `etiquetaCampo` |
| `BOTON` / `DATO` | `14px` (`font-weight: 600` en botones) | botones, campos, valores |
| `RADIO_BOTON` / `RADIO_NAV` | `30px` / `24px` | `border-radius` de los botones |
| `BTN_NAV_ANCHO` / `BTN_NAV_ALTO` | `160px` / `48px` | tamaño fijo de `REGRESAR` (§5.3 regla 1) |
| `RADIO_CAMPO` | `8px` | `QLineEdit`, `QSpinBox` (reservados, §5.3) |
| `RADIO_LIENZO` | `12px` | `zonaImagen`, `lienzoImagen` |

`MARCADOR_INFERIOR` y `MARCADOR_SUPERIOR` **no** aparecen en el QSS: los pinta
`QPainter` en el overlay (§6.4), que sí los lee como `tokens.MARCADOR_*`. Lo mismo
con `COLOR_CANAL`, que se aplica con `setStyleSheet()` desde Python (§7.4).

---

## 6. Pantallas

Todas las ventanas: **arrancan en 1280×720**, son **redimensionables y maximizables** (`resize()` + `setMinimumSize()`, nunca `setFixedSize()`), fondo `FONDO`, y su contenido se adapta según §5.4.

### 6.0 Navegación y adaptación
Un `QStackedWidget` centraliza las pantallas. Cada pantalla tiene:
- Título centrado arriba (`tituloPantalla`).
- El estado de la imagen vive en el dataclass `EstadoImagen`, definido en `core/imagen.py` (§7.1). **No existe un archivo `estado.py`**: un único objeto, compartido por referencia entre las cinco pantallas.

#### Botón de regreso (obligatorio en las 4 pantallas secundarias)

Las **cuatro pantallas secundarias** (RGB, YCM, Histograma y Recortar imagen) tienen un botón de regreso, con el **mismo nombre y el mismo formato** en las cuatro. La pantalla principal **no** lleva este botón: es la inicial.

| Pantalla | Botón | Tamaño | Posición | Acción |
|----------|-------|--------|----------|--------|
| 1. Principal (preprocesado) | — | — | — | no lleva botón: es la pantalla inicial |
| 2. Canales RGB | `REGRESAR` | **160×48** | arriba a la derecha | vuelve a Principal |
| 3. Canales YCM | `REGRESAR` | **160×48** | arriba a la derecha | vuelve a Principal |
| 4. Histograma de color | `REGRESAR` | **160×48** | arriba a la derecha | vuelve a Principal |
| 5. Recortar imagen | `REGRESAR` | **160×48** | arriba a la derecha | vuelve a Principal |

Reglas del botón de regreso:
- Nombre del texto: **`REGRESAR`** en las cuatro pantallas secundarias. Se descarta "VOLVER".
- Tamaño fijo **160×48** y `objectName` = `navegacion` (mismo estilo pastilla que el resto).
- Va siempre en la **esquina superior derecha**, en la misma fila que el título de la pantalla.
- Redondeado tipo pastilla (`RADIO_NAV = 24`); en hover solo cambia el color, nunca la forma ni el tamaño (§5.3).
- No se deshabilita nunca: siempre permite volver a la pantalla principal.
- Vuelve a la pantalla principal **conservando la imagen, el modelo elegido y el modo actual**.

#### Mapa de navegación

```
┌──────────────────────────┐
                       │  1. PRINCIPAL            │
                       │  (preprocesado)          │
                       └───────────┬──────────────┘
                                   │
         ┌─────────────────────────┼──────────────────────┐
         │                         │                      │
         ▼                         ▼                      ▼
 ┌───────────────┐        ┌───────────────┐      ┌────────────────┐
 │ 2. RGB        │ ←→     │ 3. YCM        │      │ 5. RECORTAR    │
 │ (canales)     │  ← →   │ (canales)     │      │ imagen         │
 └───────┬───────┘        └───────┬───────┘      └────────────────┘
         │                        │
         │  botón "Histograma     │
         │  de color"             │
         └────────►┐              │
                  ▼              │
         ┌───────────────────────────────┐
         │ 4. HISTOGRAMA de color       │
         └───────────────┬───────────────┘
                         │  (REGRESAR → 1)
                         └──────────────►  vuelve a 1. PRINCIPAL
```

| Desde | Botón / Tecla | Hacia |
|-------|----------------|-------|
| Principal | "Analizar por canales" | **RGB** |
| Principal | "Recortar imagen" | **Recortar imagen** |
| RGB | `→` (flecha derecha) | **YCM** |
| RGB | botón "Histograma de color" | **Histograma** |
| RGB | "REGRESAR" / `Esc` | Principal |
| YCM | `←` (flecha izquierda) | **RGB** |
| YCM | botón "Histograma de color" | **Histograma** |
| YCM | "REGRESAR" / `Esc` | Principal |
| Histograma | "REGRESAR" | Principal |
| Recortar imagen | "REGRESAR" | Principal |

Reglas:
- Toda pantalla debe ser **alcanzable**: no puede quedar ninguna pantalla huérfana.
- Solo la pantalla principal muestra los botones "Analizar por canales" y "Recortar imagen"; las pantallas de canales muestran "Histograma de color".
- Las pantallas de histograma y recorte **no** tienen flechas de teclado (ver §6.1, Atajos de teclado).

Todas las pantallas:
- Admiten que la ventana se maximice: el layout raíz usa `addStretch()` para centrar el contenido y reparte el espacio sobrante.
- Los controles mantienen su tamaño fijo (200×60); solo los **lienzos y gráficos** se estiran.
- Si el alto disponible no alcanza, se envuelve el contenido en un `QScrollArea` con `setWidgetResizable(True)`.
- Ningún texto se corta: los valores largos (`Directorio de imagen:`) usan `setWordWrap(True)` y elipsis si hace falta.

### 6.1 Pantalla principal — Preprocesado

**Restricción de espacio:** esta pantalla es la más densa (zona de 300×300 + columna de 4 botones de 60 px). Cuando la ventana se reduzca por debajo de ~900 px de alto, la zona de imagen y los botones deben caber usando `QScrollArea` vertical, nunca recortados.

Elementos:

| Elemento | Tipo | Tamaño | Función |
|----------|------|--------|---------|
| Título "Analizador de imágenes" | `QLabel#tituloPantalla` | centrado | Nombre de la app |
| Zona de imagen | `QLabel#zonaImagen` (con `QPixmap`) | **300×300** | Muestra la previsualización; **click** abre el selector de archivos |
| Nombre del archivo | `QLabel` | bajo la zona | Muestra el nombre del archivo cargado |
| Etiqueta "Modelo:" | `QLabel#etiquetaCampo` | — | Antecede al botón de modelo |
| Botón "Elegir modelo" | `QPushButton` | **200×60** | Alterna **grabcut ↔ otsu**; predeterminado **grabcut**; su texto muestra el modelo activo |
| Botón "Quitar fondo" | `QPushButton` | **200×60** | Aplica/Revierte el preprocesado |
| Botón "Analizar por canales" | `QPushButton#primario` | **200×60** | Navega a la pantalla de canales **RGB** (pantalla predeterminada) |
| Botón "Recortar imagen" | `QPushButton` | **200×60** | Navega a la pantalla de recorte |

Comportamiento:

1. **Seleccionar imagen:** click en la zona de imagen → `QFileDialog.getOpenFileName` con filtros `*.png *.jpg *.jpeg *.bmp *.gif`. Se carga a RGB. Al seleccionar una nueva imagen se **reinicia el preprocesado** y se actualizan los campos de información de todas las pantallas.
2. **Zona de imagen:** mientras no haya imagen muestra el texto *"seleccionar imagen"*. Siempre queda clickeable, incluso con imagen cargada, para elegir otra.
3. **Quitar fondo (no destructivo):** opera sobre una **copia** (`img_preprocesada`); la original (`img_original`) nunca se modifica ni se sobrescribe en disco. Si ya hay preprocesado, el botón revierte y vuelve a mostrar el original. El texto del botón alterna entre `Quitar fondo` y `Restaurar original`.
4. **Botones deshabilitados:** `Elegir modelo`, `Quitar fondo`, `Analizar por canales` y `Recortar imagen` arrancan deshabilitados y se habilitan al cargar una imagen.
5. **Cambio de modelo:** si hay una imagen con preprocesado aplicado y se cambia el modelo, el resultado se **recalcula automáticamente** con el nuevo modelo.

#### Atajos de teclado (obligatorios)

Se implementan con `QShortcut` sobre la ventana principal.

| Tecla | Pantalla actual | Acción |
|-------|------------------|--------|
| **→** (flecha derecha) | `rgb` | Cambia a la pantalla **YCM** |
| **←** (flecha izquierda) | `ycm` | Vuelve a la pantalla **RGB** |
| **Esc** | `rgb` o `ycm` | Regresa a la pantalla principal |

```python
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QLineEdit, QAbstractSpinBox, QPlainTextEdit, QTextEdit

PANTALLAS_CANALES = ("rgb", "ycm")
CLASES_DE_TEXTO = (QLineEdit, QAbstractSpinBox, QPlainTextEdit, QTextEdit)

def _foco_ocupa_teclado(self) -> bool:
    """True si el foco está en un campo donde las flechas deben escribir, no navegar."""
    return isinstance(QApplication.focusWidget(), CLASES_DE_TEXTO)

def ir_a_ycm(self):
    if _foco_ocupa_teclado(self) or self.pantalla_actual not in PANTALLAS_CANALES:
        return                      # solo desde rgb o ycm, y nunca sobre un campo
    self.mostrar("ycm")

def ir_a_rgb(self):
    if _foco_ocupa_teclado(self) or self.pantalla_actual not in PANTALLAS_CANALES:
        return
    self.mostrar("rgb")

def ir_a_principal(self):
    if _foco_ocupa_teclado(self) or self.pantalla_actual not in PANTALLAS_CANALES:
        return
    self.mostrar("principal")

# En __init__: los atajos se guardan como ATRIBUTO de la ventana. Nunca en una
# variable local, o el recolector de basura puede destruirlos y dejar de funcionar.
self._atajos = [QShortcut(QKeySequence(k), self) for k in
                (Qt.Key_Right, Qt.Key_Left, Qt.Key_Escape)]
for atajo, slot in zip(self._atajos,
                       (self.ir_a_ycm, self.ir_a_rgb, self.ir_a_principal)):
    atajo.setContext(Qt.WindowShortcut)
    atajo.activated.connect(slot)
```

Cada atajo **valida internamente** dos cosas antes de actuar: que la pantalla activa sea `rgb` o `ycm`, y que el foco no esté en un campo de texto. La app debe mantener `self.pantalla_actual` actualizado en `mostrar()`.

Reglas:
- Las flechas **solo** funcionan cuando la pantalla activa es `rgb` o `ycm`. En la pantalla principal, la flecha derecha/izquierda **no hacen nada**.
- **Esc** solo funciona cuando la pantalla activa es `rgb` o `ycm`; en la pantalla principal no hace nada.
- El atajo **no** debe ejecutarse si el foco está en un campo de entrada, es decir en cualquiera de las clases de `CLASES_DE_TEXTO` (§6.1): `QLineEdit`, `QAbstractSpinBox` (que cubre `QSpinBox`), `QPlainTextEdit`, `QTextEdit`. Hoy la app no tiene ninguno, pero la guarda se queda para que un campo futuro no rompa el teclado.
- Al cambiar de pantalla con el teclado, la imagen y el modo actual se conservan; solo cambia la pantalla visible.

### 6.2 Pantalla de canales RGB

Elementos:

| Elemento | Tamaño | Posición |
|----------|--------|----------|
| `Imagen:` + valor | automático, margen izquierdo | fila superior |
| `Directorio de imagen:` + valor | automático, margen izquierdo | segunda fila |
| Título "RGB" | centrado | sobre los canales |
| Botón "REGRESAR" | **160×48** | esquina superior derecha, misma fila que el título |
| Botón "Modo" | **200×60** | junto al botón de navegación |
| Botón "Histograma de color" | **200×60** | lleva a la pantalla de histograma (§6.4) |
| 3 lienzos de canal | **300×300** cada uno, separados **130 px** | centrados |
| Letra del canal (R, G, B) | TITULO bold | centrada encima de su lienzo |

Comportamiento:

- **Modo:** botón que alterna entre **solo dos modos**, en el orden **color → blanco y negro → color** (predeterminado **color**). Su texto muestra el modo activo.
  - `color`: muestra el canal con los otros dos componentes en negro (R = `(R,0,0)`, G = `(0,G,0)`, B = `(0,0,B)`).
  - `blanco y negro`: muestra el canal seleccionado en escala de grises (array 2D).
  - **No existe el modo `objeto`.** No se implementa la silueta rellena en los lienzos de canal, ni la métrica de área bajo los canales.
- **Interacción:** hacer click sobre un lienzo re-aplica ese canal con el modo actual.
- **Directorio:** se muestra la **carpeta que contiene la imagen** (último componente de `estado.ruta`), en modo texto gris `TEXTO_SUAVE`, con elipsis si no cabe. No se muestra la ruta completa desde la raíz del disco.
- **Origen de los datos:** los tres canales se calculan **siempre sobre la foto original**, aunque se haya aplicado el preprocesado de quitar fondo (§7.1.1). Quitar fondo no cambia lo que se ve en estos cuadros.
- **Atajo:** `→` cambia a la pantalla YCM (ver §6.1, Atajos de teclado).
- **Salida:** botón **"Histograma de color"** → pantalla de histograma; botón **"REGRESAR"** (o `Esc`) → pantalla principal.

### 6.3 Pantalla de canales YCM

Idéntica a RGB, cambiando:
- Título **"YCM"**.
- Canales **Y**, **C**, **M** con las mismas reglas de tamaño y espaciado.
- **Origen de los datos:** igual que en RGB, los canales se calculan **solo sobre la foto original** (§7.1.1).
- Atajo: `←` vuelve a la pantalla **RGB** (ver §6.1, Atajos de teclado).
- **Salida:** botón **"Histograma de color"** → pantalla de histograma; botón **"REGRESAR"** (o `Esc`) → pantalla principal.

Definición de los canales:

| Canal | Componente (2D) | Representación en modo `color` |
|-------|-----------------|----------------------------------|
| **Y** (amarillo) | `(R + G) / 2` | `(R, G, 0)` |
| **C** (cian) | `(G + B) / 2` | `(0, G, B)` |
| **M** (magenta) | `(R + B) / 2` | `(R, 0, B)` |

El cálculo del componente se hace en `float32` y se convierte a `uint8` para evitar desbordamiento.

### 6.4 Pantalla — Histograma de color

Cómo se llega: botón **"Histograma de color"** en las pantallas RGB (§6.2) y YCM (§6.3).
Cómo se sale: botón **"REGRESAR"** (160×48, esquina superior derecha) → pantalla principal. Sin flechas de teclado.

Elementos:

| Elemento | Tamaño | Función |
|----------|--------|---------|
| Título "Histograma de color" | centrado | Nombre de la pantalla |
| Botón "REGRESAR" | **160×48** | Regresa a la pantalla principal (esquina superior derecha) |
| Imagen original | **250×250** | Muestra la imagen tal como fue cargada (con fondo) |
| 2 miniaturas de canal | **250×250** c/u | Canal activo + el siguiente en el orden del espacio (RGB: R→G→B; YCM: Y→C→M) |
| Selector de canal | **200×60** | Botón que rota el canal activo: `R/G/B` en RGB, `Y/C/M` en YCM. Al entrar queda activo el **primero del espacio** (`R` en RGB, `Y` en YCM). Es el único control que cambia el campo "Canal actual" |
| `Canal actual:` | etiqueta + valor | Muestra el espacio de color (**RGB** o **YCM**) y el canal activo en español |
| Botón "Quitar fondo" / "Restaurar original" | **200×60** | Un **único** botón que alterna entre quitar el fondo y restaurarlo, con el modelo elegido. Mismo patrón que en la pantalla principal (§6.1) |
| Canal de contorno binario | **250×250** | Muestra el contorno del objeto en blanco/negro |
| Gráfico del histograma | **467×333** | Frecuencia de píxeles por canal |
| Marcador del slider inferior | ancho 3 px, alto completo | Línea vertical **naranja** + flecha debajo |
| Marcador del slider superior | ancho 3 px, alto completo | Línea vertical **verde** + flecha debajo |
| Slider inferior | ancho del gráfico − 28 | Límite inferior de intensidad (0–255, inicial **0**) |
| Slider superior | ancho del gráfico − 28 | Límite superior de intensidad (0–255, inicial **255**) |
| Botón "Guardar imagen" | **200×60** | Guarda la imagen procesada |
| Botón "Guardar máscara" | **200×60** | Guarda la máscara binaria en archivo separado |

#### Marcadores de los sliders sobre el histograma (obligatorio)

Para que se vea **dónde** está cada límite, sobre el gráfico del histograma se dibuja un marcador por cada slider:

1. **Línea vertical.** Cada límite se marca con una **línea vertical de 3 px** que atraviesa **toda la altura** del gráfico, desde el borde superior hasta las flechas de abajo. No se detiene en la barra ni se oculta detrás de ella.
2. **Flecha debajo.** Debajo del gráfico, en la base, se dibuja una **flecha que apunta hacia arriba** justo en la posición del límite. La punta de la flecha debe caer **exactamente** sobre el valor del slider, sin desfase de un píxel. Para garantizarlo, el marcador **no reimplementa la aritmética**: llama a `x_de_marcador()`, que le pregunta a Qt (`QStyleOptionSlider` + `subControlRect`) dónde está el centro del handle para ese valor. Medido en PySide6 6.11, con un groove de 467 px y un handle de 14, el valor 0 sitúa el handle en `x=7`, no en `x=0`: cualquier fórmula propia desplazaría la flecha hasta 7 px del handle. Los sliders se alinean además con el área de plot del gráfico.
3. **Colores distintos.** Las dos flechas y las dos líneas usan colores **diferentes** para poder distinguirlas de un vistazo:
   - Slider **inferior** → **naranja** `MARCADOR_INFERIOR` (`#E65100`).
   - Slider **superior** → **verde** `MARCADOR_SUPERIOR` (`#00897B`).
4. **Etiquetas de valor.** Cada flecha lleva debajo su valor (`inf` y `sup`, p. ej. `72` y `183`) en el color de su línea, para leer el límite exacto sin mirar el slider.
5. **Siguen al slider en vivo.** Al mover un slider, su línea y su flecha se redibujan en el mismo fotograma; no hay que soltar el ratón para ver el resultado.
6. **Sombra para legibilidad.** Las líneas llevan un contorno blanco de 1 px para separarse de las barras del histograma.
7. **Zona válida resaltada.** El tramo entre ambas líneas se deja más claro y el resto se atenúa, para que se vea de un vistazo qué rango está seleccionado.

```python
from PySide6.QtCore import Qt, QRect, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider

from ui import tokens


def x_de_marcador(slider: QSlider, valor: int) -> int:
    """Devuelve la x EXACTA donde Qt pondría el centro del handle para `valor`.

    Regla 2 de §6.4: la punta de la flecha debe caer sobre el valor del slider
    sin desfase. La única forma de garantarlo es **preguntárselo a Qt**: no
    existe una fórmula cerrada, porque Qt descuenta el ancho del handle de la
    zona de recorrido. Medido en PySide6 6.11 con un groove de 467 px y un
    handle de 14, con valor 0 el centro del handle está en x=7, NO en x=0: un
    mapeo `valor/255 * (ancho-1)` desplazaría la flecha 7 px del handle.

    **No se llama a `slider.setValue()`**: esta función se usa DENTRO de
    `paintEvent`, y mutar un widget mientras se pinta puede provocar un ciclo
    de repintado. En su lugar se copia la opción de estilo y se le sobrescribe
    `sliderValue`/`sliderPosition`, que es exactamente lo que lee el estilo.
    Verificado: da las mismas coordenadas que `setValue()` y deja el slider
    intacto.
    """
    valor = int(min(max(valor, slider.minimum()), slider.maximum()))
    opcion = QStyleOptionSlider()
    slider.initStyleOption(opcion)         # Qt rellena groove, handle y geometría
    opcion.sliderValue = valor             # simula el valor SIN mover el widget
    opcion.sliderPosition = valor - slider.minimum()
    return slider.style().subControlRect(
        QStyle.CC_Slider, opcion, QStyle.SC_SliderHandle, slider
    ).center().x()


def dibujar_marcadores(p: QPainter, area_grafico: QRect, slider_inf: QSlider,
                       slider_sup: QSlider, inf: int, sup: int) -> None:
    """Dibuja líneas, flechas y valores sobre el gráfico.

    NO llama a begin()/end(): usa save()/restore() sobre el QPainter que le
    entrega el paintEvent del widget. 'area_grafico' debe ser el MISMO rectángulo
    que usa GraficoHistograma para plotear las barras (con márgenes ya descontados).

    Recibe **los dos** sliders, no uno: cada límite tiene su propio handle, y la
    flecha de `inf` se mide contra el de `slider_inf` y la de `sup` contra el de
    `slider_sup`. Con un solo slider una de las dos flechas quedaría medida contra
    el handle equivocado. Los dos sliders deben estar alineados y medir lo mismo.
    """
    p.save()
    for valor, slider, color, texto in (
            (inf, slider_inf, tokens.MARCADOR_INFERIOR, f"inf {inf}"),
            (sup, slider_sup, tokens.MARCADOR_SUPERIOR, f"sup {sup}")):
        x = x_de_marcador(slider, valor)    # MISMA x que el centro de SU handle

        # regla 1 + 6: línea de 3 px con contorno blanco de 1 px a cada lado
        p.setPen(Qt.NoPen)
        p.fillRect(QRect(x - 2, area_grafico.top(), 1, area_grafico.height()), QColor("#FFFFFF"))
        p.fillRect(QRect(x - 1, area_grafico.top(), 3, area_grafico.height()), QColor(color))
        p.fillRect(QRect(x + 2, area_grafico.top(), 1, area_grafico.height()), QColor("#FFFFFF"))

        # regla 2: flecha que apunta hacia arriba en la base del gráfico
        base = area_grafico.bottom() + 18
        p.setPen(QPen(QColor(color), 1))
        p.setBrush(QColor(color))
        p.drawPolygon(QPolygonF([QPointF(x - 7, base),
                                 QPointF(x + 7, base),
                                 QPointF(float(x), float(area_grafico.bottom()))]))

        # regla 4: valor bajo la flecha, en el color de su línea
        p.drawText(QRect(x - 40, base + 2, 80, 16), Qt.AlignCenter, texto)
    p.restore()
```

Los marcadores se pintan en un **overlay** encima del gráfico, no dentro del widget del histograma, para poder refrescarlos sin volver a calcular el histograma completo.

El widget que pinta las barras — `GraficoHistograma`. Su `area_grafico` es la **única** fuente de verdad de la geometría: el overlay la recibe como parámetro en vez de recalcularla, para que las flechas no puedan desalinearse de las barras.

```python
# ui/widgets.py — el gráfico de barras. NO pinta marcadores: solo barras y ejes.
from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget, QSizePolicy

MARGEN_IZQ, MARGEN_DER, MARGEN_SUP, MARGEN_INF = 4, 4, 8, 18
# Sin COLOR_BARRA propio: las barras son del color de acento de la app. Un
# segundo token con el MISMO valor "#2F6FED" sería una copia que diverge.

class GraficoHistograma(QWidget):
    """Barras de un histograma de 256 bins. Sin estado propio: solo pinta lo que le den."""

    rangoCambiado = Signal()          # avisa de que hay que repintar el overlay

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(tokens.ALTO_GRAFICO_MIN, tokens.ALTO_GRAFICO_MIN)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._bins = [0] * 256
        self._inf, self._sup = 0, 255

    def set_datos(self, bins, inf, sup) -> None:
        """Recibe la lista de 256 conteos y el rango visible. NO recalcula nada.

        El aviso va AQUÍ y no en paintEvent: paintEvent se dispara en cada
        repintado (y puede ser varias veces seguidas al redimensionar o al
        mover el ratón), así que emitir desde él es reentrada pura. El overlay
        solo necesita enterarse cuando el RANGO cambia de verdad, no cuando se
        redibuja el mismo rango.
        """
        self._bins = list(bins)
        self._inf, self._sup = int(inf), int(sup)
        self.update()
        self.rangoCambiado.emit()

    def area_grafico(self) -> QRect:
        """El rectángulo donde se dibujan las barras, con los márgenes ya descontados.

        Es el MISMO rectángulo que recibe `dibujar_marcadores(p, area_grafico, ...)`,
        y por eso se calcula en un solo sitio: duplicar esta aritmética en el
        overlay es la forma más fácil de que las flechas dejen de caer sobre las
        barras al cambiar el tamaño de la ventana.
        """
        return QRect(self.rect().left() + MARGEN_IZQ,
                     self.rect().top() + MARGEN_SUP,
                     max(1, self.width() - MARGEN_IZQ - MARGEN_DER),
                     max(1, self.height() - MARGEN_SUP - MARGEN_INF))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        try:
            p.fillRect(self.rect(), QColor(tokens.FONDO))
            area = self.area_grafico()
            p.setPen(QPen(QColor(tokens.BORDE)))
            p.drawRect(area)
            pico = max(self._bins) or 1
            ancho = max(1, area.width() // 256)
            for i, cuenta in enumerate(self._bins):
                if not cuenta:
                    continue
                # Solo se pintan los bins DENTRO del rango: el atenuado del resto
                # es trabajo del overlay, no de las barras (§6.4 regla 7).
                if not (self._inf <= i <= self._sup):
                    continue
                alto = int(area.height() * cuenta / pico)
                p.fillRect(area.left() + i * ancho, area.bottom() - alto + 1,
                           ancho, alto, QColor(tokens.ACENTO))
        finally:
            p.end()          # painter de QWidget en Qt6 se cierra solo; end() es el seguro
```

> `paintEvent` **no** emite señales: solo pinta. Quién avisa al overlay de un
> cambio de rango es `set_datos()`, una vez por cambio y no en cada repintado.

El overlay, por su parte, es un `QWidget` **hijo** del gráfico que se apila encima y solo pinta marcadores. No tiene geometría propia: pide la del gráfico, y ese es el motivo de que `area_grafico()` viva en `GraficoHistograma` y no aquí. Si el overlay calculara su propio rectángulo, bastaría un cambio de margen en un sitio para que las flechas dejaran de caer sobre las barras.

```python
class OverlayMarcadores(QWidget):
    """Capa transparente sobre el GraficoHistograma: SOLO marcadores.

    Transparente al raton a proposito: los clicks y el arrastre son del grafico.
    """

    def __init__(self, grafico, slider_inf, slider_sup, parent=None):
        super().__init__(parent if parent is not None else grafico)
        self.grafico = grafico
        self.slider_inf = slider_inf
        self.slider_sup = slider_sup
        self._inf = slider_inf.value()
        self._sup = slider_sup.value()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)   # el raton es del grafico
        self.setAttribute(Qt.WA_NoSystemBackground)          # no pinta fondo propio
        for s in (slider_inf, slider_sup):
            s.valueChanged.connect(self._al_cambiar_rango)
        grafico.rangoCambiado.connect(self.update)

    def _al_cambiar_rango(self, _valor: int) -> None:
        # Se releen LOS DOS sliders: mover el inferior tambien cambia el superior
        # si el rango se mantiene pegado, y leer solo uno deja el otro obsoleto.
        self._inf, self._sup = self.slider_inf.value(), self.slider_sup.value()
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        try:
            # La geometria la decide SIEMPRE el grafico, nunca este widget.
            dibujar_marcadores(p, self.grafico.area_grafico(),
                               self.slider_inf, self.slider_sup,
                               self._inf, self._sup)
        finally:
            p.end()


class Histograma(QWidget):
    """Grafico y overlay en la MISMA celda de un layout.

    No hay ningun resizeEvent que sincronice geometrias: el layout estira los
    dos widgets a la vez. La alternativa (overlay hijo con setGeometry en el
    resizeEvent del padre) NO funciona: un hijo no recibe resizeEvent cuando
    se redimensiona al padre, asi que el overlay se queda con el tamano viejo
    y las flechas se salen del grafico en cuanto cambia la ventana.
    """

    def __init__(self, slider_inf, slider_sup, parent=None):
        super().__init__(parent)
        self.setObjectName("histograma")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(0, tokens.ALTO_GRAFICO_MIN)
        self.grafico = GraficoHistograma(self)
        self.overlay = OverlayMarcadores(self.grafico, slider_inf, slider_sup, self)
        lay = QGridLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.grafico, 0, 0)
        lay.addWidget(self.overlay, 0, 0)    # misma celda: queda ENCIMA
        self.overlay.raise_()

# Se monta asi, en la pantalla de histograma (§6.4):
#   histograma = Histograma(slider_inf, slider_sup)
#   histograma.grafico.set_datos(bins, slider_inf.value(), slider_sup.value())
# `self.overlay` queda encima del grafico y es transparente al raton, asi que
# los clicks siguen llegando al grafico de debajo.
```

Comportamiento:
- El histograma se calcula sobre la imagen **preprocesada** si existe, si no sobre la original.
- Los **sliders** acotan el rango de intensidades (0–255) que se consideran "objeto". Valores iniciales: `inf = 0`, `sup = 255`. Son **solo de visualización**: no modifican la máscara ni los archivos guardados. El resaltado del tramo válido y el atenuado del resto los hace el overlay (regla 7), **no** el pintado de las barras.
- **Guardar imagen:** `QFileDialog.getSaveFileName` con `*.png`; escribe **siempre RGBA con el fondo transparente** (`np.dstack([rgb, mascara])`, §7.5). El fondo negro de `preprocesada` es solo para mostrar en pantalla.
- **Guardar máscara:** guarda la máscara binaria en escala de grises (blanco = objeto).

#### Campo "Canal actual" (obligatorio)

El campo de texto de la pantalla de histograma **no** muestra el modo `color` / `blanco y negro`: muestra **qué espacio de color y qué canal se está analizando**, en el formato:

```
<ESPACIO> - <CANAL EN ESPAÑOL>
```

Valores posibles, uno por cada canal de las dos pantallas:

| Pantalla | Canal | Valor mostrado |
|----------|-------|----------------|
| RGB | R | `RGB - Rojo` |
| RGB | G | `RGB - Verde` |
| RGB | B | `RGB - Azul` |
| YCM | Y | `YCM - Amarillo` |
| YCM | C | `YCM - Cian` |
| YCM | M | `YCM - Magenta` |

Reglas:
1. El valor se escribe como **`RGB - Azul`** (espacio, guion, nombre del canal), con el espacio en **mayúsculas** y el canal en **mayúscula inicial**.
2. Cambia según el **canal que se está viendo**; las miniaturas de la pantalla de histograma se actualizan al mismo tiempo.
3. El texto se muestra en el color del canal (rojo, verde, azul, amarillo, cian o magenta) para que coincida con el lienzo correspondiente.
4. **No** es el modo de la imagen: los modos `color` y `blanco y negro` se controlan con el botón "Modo" de las pantallas RGB/YCM (§6.2).

### 6.5 Pantalla — Recortar imagen

Cómo se llega: botón **"Recortar imagen"** en la pantalla principal (§6.1).
Cómo se sale: botón **"REGRESAR"** (160×48, esquina superior derecha) → pantalla principal. Sin flechas de teclado.

Elementos:

| Elemento | Tamaño | Función |
|----------|--------|---------|
| Título "Recortar imagen" | centrado | Nombre de la pantalla |
| Botón "REGRESAR" | **160×48** | Regresa a la pantalla principal (esquina superior derecha) |
| Zona de selección | **613×613** | Imagen completa con el **marco de `LADO_SALIDA` (512×512)** encima |
| Control de zoom | automático, alto **44** | **Siempre visible** (§6.5 modo B). En modo A está **deshabilitado** —se ve atenuado con los tokens `disabled`—, nunca oculto: un control que aparece y desaparece cambia la pantalla bajo el usuario, mientras que uno atenuado explica por sí solo que ahí no hay nada que hacer. Rango `1.0` → `max(1.0, min(4, LADO_AMPLIADO_MAX/max(alto,ancho)))`, ver "Rango del control de zoom"; si el rango queda en un solo valor, el deslizador también queda deshabilitado. Debajo de la zona va un `addSpacing(ESPACIO_GRUPO)` que separa el bloque de selección del bloque de botones |
| Zona de vista previa | **300×300** | Muestra el PNG de **512×512** que se guardará. Vacía hasta pulsar "Redimensionar" |
| Botón "Redimensionar" | **200×60** | **Renderiza la vista previa.** No escribe ningún archivo |
| Botón "Guardar copia" | **200×60** | Guarda la vista previa como archivo nuevo. Conserva el original |
| Botón "Sobreescribir" | **200×60** | Reemplaza el archivo original con la vista previa |

**Los tres botones NO hacen lo mismo.** "Redimensionar" es un paso previo y
obligatorio; los otros dos escriben en disco lo que ese paso produjo:

```
┌─ Lienzo blanco de 512x512 ───────────┐
   │  con la foto centrada encima         │
   │  arrastrar el marco, y zoom si la    │
   │  foto es menor que el lienzo         │
   └────────────────┬────────────────────┘
                    │  pulsar
                    ▼
         [ Redimensionar ]  ──►  renderiza 512x512  ──►  EstadoImagen.vista_previa
                                                                │
                                          ┌─────────────────────┴───────────┐
                                          ▼                                 ▼
                                [ Guardar copia ]                 [ Sobreescribir ]
                                <original>_recortada.png           pisa el original
```

#### El marco de 512×512 y los dos modos

La salida de esta pantalla es **siempre un PNG de `LADO_SALIDA` = 512×512**.
Ese 512 es fijo: no hay ningún campo numérico para cambiarlo. El marco que ve
el usuario es la referencia que dice "esto es lo que va a salir".

Por debajo del marco hay siempre un **lienzo blanco de 512×512** con la imagen
encajada encima. El modo solo decide si ese lienzo se ve o no:

| Modo | Condición | Qué hace el usuario | ¿Remuestrea píxeles? |
|------|-----------|---------------------|----------------------|
| **A. Recorte** | `min(alto, ancho) ≥ 512` | Solo arrastra el marco sobre la foto. El marco es **1:1 con los píxeles de la imagen** y el lienzo blanco queda **tapado por completo**: no se ve ni un borde blanco | **No.** Cero pérdida |
| **B. Encaje** | `min(alto, ancho) < 512` | La foto se centra en el lienzo y **lo que falta se rellena de blanco**. El control de zoom amplía la foto; si la amplía hasta tapar el lienzo, el relleno desaparece y pasa a ser un recorte | **Solo si el usuario sube el zoom.** Con el zoom en 1.0 no se toca un solo píxel |

Los dos modos hacen lo mismo en el fondo —escalar, centrar en un lienzo de 512 y
recortar la ventana del marco— pero se comportan distinto de forma visible, y por
eso el usuario los reconoce: en el modo A nunca ve blanco y nunca hay zoom; en el
modo B el blanco es normal y el zoom es la manera de quitárselo.

Reglas obligatorias:

1. **Marco fijo de 512×512.** El marco mide `LADO_SALIDA` en píxeles del lienzo, siempre. No hay ningún control para cambiarlo y ninguna ruta que produzca otro tamaño.
2. **Lo que falta se rellena de BLANCO, nunca se estira ni se recorta solo.** Una imagen de 300×300 a factor 1.0 sale como una foto de 300×300 centrada en un cuadro de 512×512 con los bordes blancos. No se deforma para cuadrarlo, porque eso alargaría al objeto, y no se amplía sola, porque ampliar sin que el usuario lo pida es inventarle píxeles que no existían.
3. **Modo A, sin pérdida.** Con imagen de 512 o más en sus dos lados, el marco se arrastra y se guarda tal cual: `aplicar_recorte` no escala ni rellena. Es el caso normal y **no debe** pasar por `cv2.resize`.
4. **Modo B, el zoom es opcional y el blanco es la salida por defecto.** El zoom arranca en **1.0**, no en el factor de llenado: ampliar es una decisión del usuario, no un requisito para que la imagen quepa. El relleno blanco no es un fallo de la operación, es el resultado.
5. **Aviso honesto del modo B.** Si el usuario sube el zoom por encima de 1.0, está **ampliando**: una 300×300 ampliada a 600×600 sigue teniendo 300×300 de resolución real. La pantalla no lo oculta, pero el aviso **no bloquea** el guardado: poder ampliar imágenes pequeñas es justamente para lo que sirve el modo B, y frenarlo lo volvería inútil.
6. **Cuadrado obligatorio.** El marco es cuadrado por construcción: es `LADO_SALIDA` a lo ancho y a lo alto. Es imposible obtener un rectángulo.
7. **Cursor de mano.** Sobre la imagen, el cursor muestra una manita (`Qt.OpenHandCursor`) para indicar que se puede arrastrar. Durante el arrastre pasa a `Qt.ClosedHandCursor`. No se usa `Qt.SizeAllCursor`: esa flecha de cuatro direcciones sugiere que la imagen se mueve, no que se recorta.
8. **Vista en vivo.** Mientras se arrastra, la zona del marco se ve **normal** y el resto del lienzo queda **atenuado** (velo oscuro al 50 %), sin deformar nada. El blanco de relleno también se atenúa: es parte del lienzo, no un borde de la foto.
9. **"Redimensionar" no toca el disco.** Solo calcula la vista previa de 512×512 y la guarda en `EstadoImagen.vista_previa`. Pulsarlo mil veces deja la imagen original intacta.
10. **Guardar escribe la vista previa, no recalcula.** "Guardar copia" y "Sobreescribir" escriben `EstadoImagen.vista_previa` tal cual. Así lo que se ve es exactamente lo que se guarda, sin posibilidad de que se desincronicen.
11. **Guardar está deshabilitado sin vista previa.** Ambos botones arrancan deshabilitados y solo se habilitan tras pulsar "Redimensionar". No existe estado en el que haya algo guardable sin haberlo renderizado.
12. **La vista previa se invalida sola.** Mover el marco o cambiar el zoom la borran y vuelven a deshabilitar los botones de guardar. Una vista previa nunca puede quedarse obsoleta en pantalla: o corresponde al encuadre actual, o no existe.
13. **Mover el marco NO reconstruye el lienzo.** El lienzo depende solo del factor, así que arrastrar únicamente invalida la vista previa (§7.1). Rehacer `escalar()` en cada píxel de arrastre haría que una foto grande se sintiera pegada a mantequilla. Solo el zoom reconstruye, y entonces `set_imagen()` recentra el marco porque el lienzo ha cambiado de dimensiones.
14. **Un `QRect` vacío significa "todavía no hay nada que recortar".** `SelectorCuadrado.set_imagen()` emite `recorteChanged` con un rectángulo **vacío** si recibe un pixmap menor que 512. Quién lo reciba **debe** dejar `EstadoImagen.recorte` en `None` (sin convertirlo en `(0, 0)`), **deshabilitar** "Redimensionar" y mostrar el motivo. Con el diseño actual esto es una red de seguridad y no un camino normal: `ui/ventana_recorte.py` entrega al widget el **lienzo** de 512, que siempre cumple. Se mantiene porque "sin selección" tiene que estar definido, no porque ocurra a menudo.
15. **Sin sobrescrituras implícitas.** Ninguna acción escribe sobre el original salvo el botón explícito "Sobreescribir".

**El widget no sabe nada del relleno.** `SelectorCuadrado` sigue recibiendo un
pixmap cualquiera y no tiene ni un `if` de "esto es un borde blanco". Quien
arma el lienzo es `ui/ventana_recorte.py`, llamando a `lienzo_blanco()` (§7.7) y
pasándole el resultado a `set_imagen()`. Así el widget no cambia, el `QRect` que
emite son coordenadas del **lienzo** (no de la foto), y `aplicar_recorte()`
recibe las mismas coordenadas y reconstruye el mismo lienzo por su cuenta. Las dos
partes están de acuerdo por construcción porque las dos llaman a la misma función.

#### Rango del control de zoom (modo B)

```
factor_min = 1.0                                            # no ampliar sin permiso
factor_max = max(1.0, min(4.0, LADO_AMPLIADO_MAX / max(alto, ancho)))  # tope de memoria
```

- El mínimo es **1.0**, no el factor de llenado. Con 1.0 la foto entra tal cual y
  el blanco sale solo, sin que el usuario haya pedido ni un píxel inventado. Este
  es el cambio de fondo respecto al diseño anterior: antes el control no bajaba
  del factor de llenado, así que una 300×300 salía SIEMPRE ampliada a 512×512.
- El máximo es `4.0`, o menos si la imagen es tan grande que cuatro veces no cabe
  en memoria.
- El tope de memoria (`LADO_AMPLIADO_MAX`) hace falta porque 4× una imagen
  panorámica es mucho: una de 4000×400 daría 16000 px de lado y 1600 del otro,
  25,6 Mpx (~77 MB). Con el
  tope, el factor máximo se recorta a `4096 / 4000` y sigue siendo utilizable.
- El `max(1.0, ...)` del final importa: si la imagen ya tiene un lado de más de
  4096 px, el tope de memoria daría un máximo por debajo de 1.0, pero **1.0 sigue
  siendo un factor válido** —sin ampliar, esa imagen ya se recorta o se rellena
  igual que cualquier otra. Por eso el rango se cierra en 1.0 en lugar de quedar
  vacío. Con `factor_max == factor_min` el deslizador queda **deshabilitado** (no
  hay nada que mover) pero la pantalla funciona: el marco se arrastra, se
  recorta y se guarda. Lo que no tiene sentido es un rango invertido.
- El factor se aplica **una sola vez** sobre el original, con `escalar()`. No se
  escala una imagen ya escalada, así que mover el zoom no degrada de forma
  acumulativa el resultado.
- El valor inicial del deslizador es **1.0**.

Cuando la foto ya tapa el lienzo entero (porque `factor * min(alto, ancho) ≥ 512`)
el modo B se comporta exactamente igual que el modo A y el marco vuelve a ser
arrastrable: el relleno blanco ya no se ve. La transición entre "encaje con
borde blanco" y "recorte puro" ocurre sola, sin ningún aviso ni cambio de
pantalla, y es solo una consecuencia de cuánto se ha ampliado.

#### Quién arma el lienzo — `ui/ventana_recorte.py`

El widget no sabe de factores ni de relleno. Quien arma el lienzo es la ventana,
con **las mismas dos llamadas que hace `aplicar_recorte()`** (§7.7), en el mismo
orden. Esa es toda la garantía de que lo que se ve es lo que se guarda: las dos
partes llaman a la misma función con los mismos números.

```python
# ui/ventana_recorte.py — el puente entre el zoom y el widget
from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap, QImage

from core.recorte import escalar, lienzo_blanco
from ui import tokens

def _a_pixmap(imagen):
    """np.ndarray RGB -> QPixmap. Copia el buffer: QImage no lo mantiene vivo."""
    alto, ancho = imagen.shape[:2]
    return QPixmap.fromImage(
        QImage(imagen.data, ancho, alto, ancho * imagen.shape[2],
               QImage.Format_RGB888).copy())

class VentanaRecorte:
    ZOOM_PASOS = 100        # resolución del deslizador; el factor sigue siendo float

    def __init__(self, estado):
        self.estado = estado            # EstadoImagen (§7.1)
        # El widget recibe el LIENZO, nunca `original` (ver §6.5).
        self.selector.set_imagen(self._pixmap_lienzo())
        # El rango se fija con el MISMO `_factor_maximo` que usa `_zoom_a_factor`.
        # Si los dos se calcularan por separado, el factor podría salirse del
        # rango que el propio control permite.
        self.zoom.setRange(0, self.ZOOM_PASOS)
        self.zoom.setValue(0)             # 0 -> factor 1.0, la foto sin ampliar
        # El control NO se oculta en modo A: se deshabilita. Visible-pero-atenuado
        # explica solo que ahí no hay nada que hacer; visible-que-aparece-desaparece
        # cambia la pantalla bajo el usuario sin avisar.
        self.zoom.setEnabled(self._factor_maximo() > 1.0)
        self.selector.recorteChanged.connect(self._al_recibir_recorte)
        self.zoom.valueChanged.connect(self._al_cambiar_zoom)

    def _factor_maximo(self) -> float:
        """Regla del zoom: 1.0 hasta min(4, tope de memoria). Nunca invertido."""
        alto, ancho = self.estado.original.shape[:2]
        return max(1.0, min(4.0, tokens.LADO_AMPLIADO_MAX / max(alto, ancho)))

    def _pixmap_lienzo(self):
        """La imagen que se ve: ampliada si el usuario lo pidió, sobre blanco.

        Mismo orden que `aplicar_recorte()`: escalar, luego lienzo_blanco().
        Si la ampliada ya cubre 512x512, `lienzo_blanco` la devuelve tal cual y
        el widget recibe la imagen entera, no un 512 recortado: el marco se
        arrastra sobre ella.
        """
        factor = self.estado.factor
        imagen = self.estado.original
        if factor > 1.0:
            imagen = escalar(imagen, factor)
        return _a_pixmap(lienzo_blanco(imagen, tokens.LADO_SALIDA))

    def _zoom_a_factor(self, valor: int) -> float:
        """El entero del QSlider -> el float de `escalar()`, en [1.0, _factor_maximo()].

        El deslizador trabaja en enteros porque un QSlider no tiene decimales, así
        que el mapeo tiene que ser explícito y ser SIEMPRE el mismo que el que
        construye el rango. Con un rango 0..N el factor sale escalando dentro de
        [1.0, factor_max]; si además se usa como DEFAULT el primer valor del
        deslizador tiene que ser el que devuelve factor 1.0, que con la fórmula
        lineal es 0. De ahí que el mínimo sea 1 y no 0.
        """
        maximo = self._factor_maximo()
        if maximo <= 1.0:
            return 1.0                      # rango degenerado: sin zoom posible
        return 1.0 + (maximo - 1.0) * (int(valor) / self.ZOOM_PASOS)

    # --- Slots: el marco se mueve mucho, el zoom poco -----------------------
    def _al_mover_marco(self, rect: QRect):
        """El usuario ha movido el marco: caduca la vista previa (§7.1).

        NO se rehace el lienzo. El lienzo depende solo de `factor`, y el factor
        no ha cambiado: reconstruirlo aquí llamaría a `escalar()` sobre la
        imagen entera en cada pixel de arrastre, que es lo que hace que un
        arrastre se sienta pegado a mantequilla en una foto de 4000x4000.
        """
        self.estado.invalidar_vista_previa()

    def _al_cambiar_zoom(self, valor: int):
        """El zoom SÍ cambia el lienzo: hay que reconstruirlo y recentrar.

        `set_imagen()` vuelve a centrar el marco, que es lo correcto: al pasar
        de un factor a otro el lienzo tiene otras dimensiones y un (x, y) del
        encuadre anterior puede quedarse fuera.
        """
        self.estado.factor = self._zoom_a_factor(valor)
        self._al_mover_marco(None)
        self.selector.set_imagen(self._pixmap_lienzo())

    def _al_recibir_recorte(self, rect: QRect):
        """Regla 14: un QRect vacío NO es un (0,0)."""
        if rect is None or rect.isEmpty():
            self.estado.recorte = None
            self.boton_redimensionar.setEnabled(False)     # y avisar del motivo
            return
        self.estado.recorte = (rect.x(), rect.y())
        self.boton_redimensionar.setEnabled(True)
```

Dos detalles que no son negociables:

- **El widget recibe `lienzo_blanco()`, nunca `original`.** Si recibiera la foto
  de 300×300, el marco saldría vacío y "Redimensionar" quedaría deshabilitado sin
  motivo: la imagen es perfectamente recortable, solo es pequeña.
- **El `QRect` que llega son coordenadas del lienzo**, no de la foto. Por eso
  `aplicar_recorte()` reconstruye el lienzo antes de recortar (§7.7). Duplicar
  aquí el cálculo del relleno —en vez de llamar a `lienzo_blanco()`— sería la
  forma más fácil de que la vista previa y el archivo guardado se desincronicen.

Implementación del widget — `ui/widgets.py`. **Regla de oro: `self._cuadrado` SIEMPRE vive en píxeles de la imagen, nunca del widget.** Todos los eventos convierten en la frontera con `_a_imagen()`:

```python
# Imports comprobados contra PySide6:
#   QtCore  -> Qt, QRect, QPoint, QSize, Signal   (QSizePolicy NO está aquí)
#   QtGui   -> QPixmap, QPainter, QColor, QPen, QRegion
#   QtWidgets-> QLabel, QSizePolicy               (QSizePolicy vive aquí, NO en QtCore)
from PySide6.QtCore import Qt, QRect, QPoint, QSize, Signal
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QRegion
from PySide6.QtWidgets import QLabel, QSizePolicy

from ui import tokens


class SelectorCuadrado(QLabel):
    """Marco de recorte FIJO de LADO_SALIDA x LADO_SALIDA, estilo WhatsApp."""
    recorteChanged = Signal(QRect)

    # El marco mide SIEMPRE tokens.LADO_SALIDA. Es la MISMA constante que usa
    # aplicar_recorte() (§7.7): una sola fuente de verdad para el marco y la
    # salida, así que es imposible que se desincronicen.
    LADO_MARCO = tokens.LADO_SALIDA        # 512

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("lienzoImagen")
        self._pixmap = QPixmap()
        self._cuadrado = QRect()      # SIEMPRE en coordenadas de la imagen
        # El mínimo sale de la RAZÓN, no de un número suelto: la zona es
        # SIEMPRE cuadrada (RAZON_RECORTE = 1:1) y ese 613 es su lado. Si algún
        # día la razón cambiara, el mínimo y el diseño se moverían juntos.
        lado = tokens.RAZON_RECORTE[0] * tokens.LADO_ZONA_RECORTE
        self.setMinimumSize(lado, lado)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.OpenHandCursor)     # regla 7: manita
        self._presionado = False

    def set_imagen(self, pixmap: QPixmap) -> None:
        """Carga la imagen y centra el marco de 512.

        En modo B (§6.5) quien llama ya entrega el pixmap del LIENZO: el resultado
        de `escalar()` y `lienzo_blanco()` (§7.7). Este widget no sabe de factores,
        ni de zoom, ni de que hay un relleno blanco: solo recibe lo que se ve. Por
        eso el marco casi nunca queda vacío —el lienzo siempre es de 512— y las
        coordenadas que emite son de ese lienzo.

        La rama del `QRect` vacío es la red de seguridad de la regla 14: si alguien
        cuela un pixmap menor que 512, `_cuadrado_en` devuelve vacío y se avisa, en
        vez de emitir un recorte de 512 que no existe en la imagen.
        """
        self._pixmap = pixmap
        if not pixmap.isNull():
            self._cuadrado = self._cuadrado_en(
                QPoint(pixmap.width() // 2, pixmap.height() // 2))
            self.recorteChanged.emit(self._cuadrado)
        else:
            self._cuadrado = QRect()
        self.update()

    # --- Conversión de coordenadas (frontera widget <-> imagen) --------
    def _escala(self) -> float:
        if self._pixmap.isNull():
            return 1.0
        return min(self.width() / self._pixmap.width(),
                   self.height() / self._pixmap.height())

    def _a_widget(self) -> QRect:
        """Dónde se dibuja la imagen dentro del widget (centrada)."""
        e = self._escala()
        ancho = int(self._pixmap.width() * e)
        alto = int(self._pixmap.height() * e)
        return QRect((self.width() - ancho) // 2,
                     (self.height() - alto) // 2, ancho, alto)

    def _a_imagen(self, punto: QPoint) -> QPoint:
        """Punto del widget -> punto de la imagen, acotado a sus límites."""
        d = self._a_widget()
        e = self._escala()
        return QPoint(
            min(max(int((punto.x() - d.x()) / e), 0), self._pixmap.width() - 1),
            min(max(int((punto.y() - d.y()) / e), 0), self._pixmap.height() - 1))

    def _a_widget_rect(self, rect: QRect) -> QRect:
        """Rectángulo de la imagen -> rectángulo del widget.

        Un rectángulo VACÍO se propaga vacío. Es lo que evita que un `QRect` sin
        selección se convierta en algo recortable por accidente: si aquí un ancho 0
        se "arreglara" con `max(1, ...)` devolvería un punto de 1x1 que `paintEvent`
        tomaría por una selección válida, velando toda la imagen.
        """
        if rect.isEmpty():
            return QRect()
        d, e = self._a_widget(), self._escala()
        return QRect(d.x() + round(rect.x() * e), d.y() + round(rect.y() * e),
                     max(1, round(rect.width() * e)), max(1, round(rect.height() * e)))

    # --- Geometría del marco (regla 1) -------------------------------
    def _cuadrado_en(self, centro: QPoint) -> QRect:
        """Marco de lado LADO_MARCO centrado en `centro`, sin salirse de la imagen.

        El lado NO es un parámetro: es fijo (regla 1). Si la imagen es menor que
        el marco se devuelve un QRect vacío, porque en ese caso no hay región
        válida. Con el diseño actual (§6.5) eso NO debería ocurrir: la ventana
        entrega el lienzo de 512 y siempre cabe. Es la red de seguridad de la
        regla 14, no el camino normal.
        """
        w, h = self._pixmap.width(), self._pixmap.height()
        lado = self.LADO_MARCO
        if w < lado or h < lado:
            return QRect()             # imagen demasiado pequeña: aún no hay marco
        half = lado // 2
        x = min(max(centro.x(), half), max(0, w - half))
        y = min(max(centro.y(), half), max(0, h - half))
        return QRect(x - half, y - half, lado, lado)

    # --- Interacción ---------------------------------------------------
    def mousePressEvent(self, evento):
        if evento.button() != Qt.LeftButton or self._pixmap.isNull():
            return
        if not self._a_widget().contains(evento.position().toPoint()):
            return                      # el gesto debe empezar sobre la imagen
        self._presionado = True
        self.setCursor(Qt.ClosedHandCursor)   # agarrado durante el arrastre
        self.update()

    def mouseMoveEvent(self, evento):
        if not self._presionado:
            return
        # Solo se MUEVE el marco. Su lado es fijo (regla 1), así que no hay
        # arrastre de tamaño: el gesto no calcula ningún `min(ancho, alto)`.
        self._cuadrado = self._cuadrado_en(self._a_imagen(evento.position().toPoint()))
        self.recorteChanged.emit(self._cuadrado)
        self.update()

    def mouseReleaseEvent(self, evento):
        self._presionado = False
        self.setCursor(Qt.OpenHandCursor)     # vuelve a la manita

    # NO hay wheelEvent: la rueda ya no cambia el lado del marco, porque el 512 es
    # fijo. En el modo B de §6.5 el único control de escala es el deslizador de
    # zoom de `ui/ventana_recorte.py`, que reconstruye el pixmap con `escalar()`
    # y vuelve a llamar a `set_imagen()`. Dejar el wheelEvent sin usar haría
    # creer que la rueda redimensiona, que es justo lo que ya no ocurre.

    # --- Pintado (una sola pasada, sin triple blit) --------------------
    def paintEvent(self, evento):
        super().paintEvent(evento)
        if self._pixmap.isNull():
            return
        destino = self._a_widget()
        seleccion = self._a_widget_rect(self._cuadrado).intersected(destino)
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        # ORDEN OBLIGATORIO: primero la imagen COMPLETA y después el velo encima.
        # Al revés, el velo se pinta sobre el fondo vacío y el recorte se ve
        # como un recorte normal sobre un rectángulo gris, no sobre la foto.
        p.drawPixmap(destino, self._pixmap, QRect(self._pixmap.rect()))
        if not seleccion.isEmpty():
            p.save()
            p.setClipRegion(QRegion(destino).subtracted(QRegion(seleccion)))
            p.fillRect(destino, QColor(0, 0, 0, 128))     # velo 50 % fuera
            p.restore()
            p.setPen(QPen(QColor(tokens.ACENTO), 2))       # marco de la selección
            p.setBrush(Qt.NoBrush)
            p.drawRect(seleccion)
        p.end()
```

Comportamiento de los botones:

- **Redimensionar:** convierte el `QRect` del marco a los enteros planos `(x, y)` que
  espera `aplicar_recorte()` (§7.7 — el `core/` no recibe nunca un `QRect`), llama a
  `aplicar_recorte()` con ese par y el factor actual, pinta el resultado en la **zona
  de vista previa** (300×300) y lo guarda en `EstadoImagen.vista_previa`. **No escribe
  ningún archivo.** Deja los dos botones de guardar **habilitados**. Si ya había una
  vista previa anterior, esta la sustituye: nunca puede haber dos renderizados
  distintos en pantalla.
- **Guardar copia:** escribe `EstadoImagen.vista_previa` tal cual en un archivo
  nuevo; nombre sugerido `<original>_recortada.png`. **Nunca** recalcula el recorte
  ni vuelve a leer la imagen del disco: escribe exactamente los 512×512 que se
  están viendo. Nunca pisa el original.
  El nombre se elige con `QFileDialog.getSaveFileName()`, con el directorio del
  original como carpeta inicial y `<original>_recortada.png` como nombre por
  defecto. **Si el usuario cancela el diálogo no se escribe nada** y no hay ningún
  mensaje de error: cancelar no es fallar. Si escribe un nombre sin extensión, se
  añade `.png`; si escribe otra extensión, se respeta la que escribió.
- **Sobreescribir:** escribe el mismo array, pero pide confirmación explícita antes
  de escribir sobre el archivo original. La confirmación es un `QMessageBox` con
  `QMessageBox.Yes | QMessageBox.No` y el botón por defecto es **No**
  (`setDefaultButton`), para que un Enter a destiempo no borre el archivo.
  `PELIGRO` queda reservado: hoy ningún botón de la app es destructivo.
- Los dos botones de guardar arrancan **deshabilitados** (regla 11) y solo se
  habilitan tras un "Redimensionar" correcto.
- **"Redimensionar" se habilita solo cuando hay marco.** Si el `QRect` que llega
  por `recorteChanged` está vacío (regla 14), el botón queda **deshabilitado**,
  `EstadoImagen.recorte` se queda en `None` y el texto de ayuda explica que no hay
  una región seleccionada. Es el otro botón que arranca deshabilitado, junto con
  los dos de guardar: sin selección no hay nada que renderizar.
- **Cualquier cambio invalida la vista previa.** Mover el marco o tocar el zoom
  ponen `EstadoImagen.vista_previa` a `None`, vacían la zona de vista previa y
  **vuelven a deshabilitar** los dos botones de guardar. No existe el estado
  intermedio "hay una vista previa, pero es de otro encuadre": esa es la única
  forma de que lo que se ve y lo que se guarda dejen de coincidir, y las reglas 9
  y 10 existen precisamente para que eso no pueda ocurrir. El coste es un clic
  extra en "Redimensionar", que es el mismo gesto que ya pide WhatsApp.
- El archivo en disco no se toca hasta pulsar "Guardar copia" o "Sobreescribir".

---

## 7. Lógica de procesamiento (`core/`)

### 7.1 Estado compartido
```python
@dataclass
class EstadoImagen:
    ruta: str | None = None
    original: np.ndarray | None = None   # RGB, nunca se modifica
    preprocesada: np.ndarray | None = None
    mascara: np.ndarray | None = None    # uint8, 255 = objeto (§6.4 "Guardar máscara")
    modelo: str = "grabcut"               # "grabcut" | "otsu"
    modo: str = "color"                   # "color" | "blanco y negro"  (§6.2)
    espacio: str = "RGB"                  # "RGB" | "YCM"  (pantalla de origen)
    canal_actual: str = "R"               # "R".."M"  (campo "Canal actual", §6.4)
    inf: int = 0                          # límite inferior del histograma (0-255)
    sup: int = 255                        # límite superior del histograma (0-255)
    recorte: tuple[int, int] | None = None   # (x, y) del marco, en píxeles del LIENZO (§6.5)
    factor: float = 1.0                      # 1.0 siempre en modo A y al abrir el modo B
    vista_previa: np.ndarray | None = None    # render de LADO_SALIDA ya hecho (§6.5)

    def invalidar_vista_previa(self) -> None:
        """Borra la vista previa (§6.5 regla 12).

        Va en el ESTADO y no en la ventana a propósito: "la vista previa caducó"
        es un hecho del estado, no una decisión de una pantalla concreta. Así no
        puede pasar que una ventana invalide y otra se entere tarde, que es
        justo como un "Guardar" acaba escribiendo un encuadre que ya no se ve.

        No limpia `recorte`: el encuadre sigue siendo válido, lo que caduca es
        el render. Por eso el botón "Redimensionar" sigue habilitado.
        """
        self.vista_previa = None
```

Una única instancia vive en la ventana principal y se pasa por referencia a las demás pantallas.

**`original` es siempre `uint8` de 3 canales en orden RGB, de forma `(alto, ancho, 3)`.**
No es una convención, es un requisito, porque todo lo demás lo da por supuesto: el
histograma tiene 256 bins (§6.4), `inf`/`sup` van de 0 a 255, las fórmulas YCM
terminan en `.astype(np.uint8)` (§7.4) y el PNG de salida se escribe con
`cv2.imencode` a 8 bits por canal (§7.5). Si `original` llegara en `uint16`, esos
cuatro sitios darían números sin sentido o desbordarían.

Por eso la carga es explícita y no deja nada al azar:

```python
# SIEMPRE IMREAD_COLOR: fuerza 8 bits y 3 canales, venga lo que venga el archivo.
# Con IMREAD_UNCHANGED un PNG de 16 bits entraría como uint16 y una imagen con
# alfa entraría con 4 canales, y las dos cosas rompen el resto de la app.
bgr = cv2.imread(ruta, cv2.IMREAD_COLOR)
if bgr is None:
    raise FileNotFoundError(ruta)
estado.original = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
```

Consecuencias asumidas, y son deliberadas:

- Un PNG de **16 bits** se reduce a 8 al abrir. No se conserva el rango completo.
- Una imagen con **alfa** (RGBA) pierde el alfa al abrir. El alfa de la app no viene
  del archivo: lo genera la máscara de segmentación (§7.5).
- Una imagen en **escala de grises** se lee como 3 canales iguales.

**Cada campo tiene un consumidor real.** `canal_actual` lo lee y escribe la pantalla
de histograma (§6.4, campo "Canal actual"); `inf`/`sup` los leen el overlay de
marcadores y los dos sliders (§6.4); `recorte` lo escribe la ventana de recorte al
recibir `recorteChanged`, `factor` lo escribe **la misma ventana** al mover el zoom
—el widget `SelectorCuadrado` no escribe ninguno de los dos, solo emite la señal— y
ambos los lee "Redimensionar" (§6.5);
`vista_previa` la escribe ese mismo botón y **la leen "Guardar copia" y
"Sobreescribir", que guardan ese array tal cual sin recalcular nada** (§6.5 regla 10).

El lado de salida **no** es un campo: es `tokens.LADO_SALIDA` (512), fijo, y por eso
no necesita guardarse en el estado. Las dos rutas que se descartaron y por qué:

| Se descartó | Por qué |
|---|---|
| `lado_destino` | La salida es siempre 512. Un destino variable obligaba a `redimensionar()`/`centralizar()` y a una rama `None` que nunca se daba |
| El `lado` dentro de `recorte` | El marco mide `LADO_SALIDA` siempre, así que guardar el lado en el estado era redundante. `recorte` queda como `(x, y)` y la escala va en su propio campo `factor`: mezclar posición y escala en una tupla `(x, y, lado)` hacía ambiguo qué eje mandaba |

### 7.1.1 Regla fundamental: los canales se calculan **solo** sobre la foto original

Los canales **RGB y YCM se derivan exclusivamente de `original`**, la imagen tal como fue cargada.

- **El preprocesado de quitar fondo NO afecta a los lienzos de canal.** Aunque el usuario haya pulsado "Quitar fondo", los tres cuadros de R/G/B y de Y/C/M se calculan siempre sobre `original`.
- `preprocesada` se usa únicamente para: la vista previa de la pantalla principal, la pantalla de histograma y los guardados. **Nunca** como entrada de los canales.
- Motivo: el objetivo de las pantallas de canales es comparar el color de la imagen **con su fondo**, que es justamente lo que hace visible la diferencia entre un canal y otro. Si se usara la imagen **preprocesada** (sin fondo), todos los canales se **verían** casi iguales.

```python
# En ventana_rgb.py y ventana_ycm.py, SIEMPRE:
imagen = estado.original          # nunca estado.preprocesada
```

Si en el futuro se quiere una vista "sobre fondo negro" de los canales, debe ser un **cuarto cuadro opcional** aparte, no reemplazar los existentes.

### 7.2 Segmentación — `core/segmentacion.py`

**GrabCut** (predeterminado):
1. Si el lado mayor de la imagen supera **500 px**, reducir con `INTER_AREA` (solo para segmentar, por velocidad).
2. `cv2.grabCut(imagen, mascara, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)` con `rect` al **10 %** de los bordes. **`bgd` y `fgd` deben ser arrays preasignados** de `np.float64` con forma `(1, 65)`, y la imagen debe ser **contigua** (`np.ascontiguousarray`): si no, la llamada falla.
3. binaria = píxeles `GC_FGD | GC_PR_FGD`.
4. Reescalar la máscara al tamaño original con `INTER_NEAREST`.

**OTSU:**
1. Aplicar `cv2.threshold(..., THRESH_BINARY + THRESH_OTSU)` sobre **cada canal**.
2. Unir las máscaras con `cv2.bitwise_or`.
3. Si la binaria tiene más del 50 % de píxeles blancos, invertirla (el objeto es la región minoritaria).

**Limpieza común (ambos modelos):**
```python
kernel = np.ones((3, 3), np.uint8)
mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel, iterations=2)
numero, marcada = cv2.connectedComponents(mascara)
if numero > 1:
    mayor = int(np.argmax(np.bincount(marcada.ravel())[1:]) + 1)
    mascara = np.where(marcada == mayor, 255, 0).astype(np.uint8)
```

**Contorno binario** — origen de datos del cuadro "Canal de contorno binario" de §6.4. Las máscaras anteriores son **rellenas**, así que este cuadro necesita su propia función:
```python
def contorno(mascara: np.ndarray) -> np.ndarray:
    """Contorno externo del objeto en blanco sobre negro (uint8 0/255)."""
    binaria = (mascara > 0).astype(np.uint8) * 255
    contornos, _ = cv2.findContours(binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    salida = np.zeros_like(binaria)
    cv2.drawContours(salida, contornos, -1, 255, 1)
    return salida
```

**El punto de entrada** — `segmentar()`. Los dos modelos comparten la misma limpieza, así que el dispatch va en una sola función y no en dos. Devuelve **siempre** `uint8` de 0/255 con la **forma de la imagen original**: reducir para segmentar es un detalle interno que la función deshace antes de devolver, así que quien la llama nunca ve una escala.

```python
# core/segmentacion.py
import cv2
import numpy as np

def _a_escala(imagen: np.ndarray, lado: int = 500):
    """Copia reducida SOLO para segmentar. Devuelve (imagen, escala)."""
    alto, ancho = imagen.shape[:2]
    escala = min(1.0, lado / max(alto, ancho))
    if escala == 1.0:
        return np.ascontiguousarray(imagen), 1.0
    return (np.ascontiguousarray(
                cv2.resize(imagen, (max(1, int(round(ancho * escala))),
                                    max(1, int(round(alto * escala)))),
                           interpolation=cv2.INTER_AREA)),
            escala)

def _devolver_a_escala(mascara: np.ndarray, escala: float,
                      forma_original: tuple[int, int]) -> np.ndarray:
    """Reescala la máscara al tamaño original. INTER_NEAREST, no bilineal:
    con interpolación suave los bordes salen grises y `mascara == 255` deja de
    ser cierto justo en la frontera, que es donde está el objeto."""
    if escala == 1.0:
        return mascara
    return cv2.resize(mascara, (forma_original[1], forma_original[0]),
                      interpolation=cv2.INTER_NEAREST)

def _grabcut(imagen: np.ndarray) -> np.ndarray:
    """GrabCut con rect al 10 % de los bordes (GC_INIT_WITH_RECT).

    `bgd`/`fgd` DEBEN ser arrays preasignados de np.float64 con forma (1, 65) y
    `imagen` debe ser contigua: son requisitos de la API de OpenCV, y si faltan
    la llamada lanza ValueError en lugar de avisar.
    """
    alto, ancho = imagen.shape[:2]
    margen = max(1, int(round(min(alto, ancho) * 0.10)))
    rect = (margen, margen, ancho - 2 * margen, alto - 2 * margen)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(imagen, np.zeros((alto, ancho), np.uint8), rect, bgd, fgd,
                5, cv2.GC_INIT_WITH_RECT)

def _otsu(imagen: np.ndarray) -> np.ndarray:
    """OTSU por canal, unidos con bitwise_or. Si el blanco es mayoría, se invierte."""
    binaria = None
    for c in range(imagen.shape[2]):
        _, canal = cv2.threshold(imagen[:, :, c], 0, 255,
                                 cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        binaria = canal if binaria is None else cv2.bitwise_or(binaria, canal)
    if np.count_nonzero(binaria) > binaria.size // 2:
        binaria = cv2.bitwise_not(binaria)
    return binaria

def segmentar(imagen: np.ndarray, modelo: str = "grabcut") -> np.ndarray:
    """Máscara binaria del objeto: uint8 0/255, con la forma de `imagen`.

    `modelo` es "grabcut" | "otsu" (§7.1). El `ValueError` ante un modelo
    desconocido es deliberado: un `modelo` mal escrito tiene que fallar aquí y
    no tres pantallas más tarde, cuando el recorte ya esté en pantalla.
    """
    if modelo not in ("grabcut", "otsu"):
        raise ValueError(f"modelo de segmentación desconocido: {modelo!r}")
    forma_original = imagen.shape[:2]
    pequena, escala = _a_escala(imagen)
    if modelo == "grabcut":
        binaria = _grabcut(pequena)
    else:
        binaria = _otsu(pequena)
    binaria = _devolver_a_escala(binaria, escala, forma_original)

    # Limpieza común: cierre morfológico y quedarse con el componente mayor.
    kernel = np.ones((3, 3), np.uint8)
    binaria = cv2.morphologyEx(binaria, cv2.MORPH_CLOSE, kernel, iterations=2)
    numero, marcada = cv2.connectedComponents((binaria > 0).astype(np.uint8))
    if numero > 1:
        mayor = int(np.argmax(np.bincount(marcada.ravel())[1:]) + 1)
        binaria = np.where(marcada == mayor, 255, 0).astype(np.uint8)
    return binaria
```

### 7.3 Preprocesado no destructivo
```python
mascara = segmentar(estado.original, estado.modelo)
estado.mascara = mascara
preprocesada = estado.original.copy()
preprocesada[mascara == 0] = 0          # fondo en negro, SOLO para mostrar en pantalla
estado.preprocesada = preprocesada
```
`estado.original` permanece intacta; revertir es asignar `None` a `preprocesada` y `mascara`.

**El fondo negro es solo de visualización.** Lo que se **guarda** es siempre RGBA con transparencia: `np.dstack([original, mascara])` (§7.5). Si se guardara el array con el negro, el PNG saldría con fondo negro en vez de transparente.

### 7.4 Canales y modos — `core/canales.py`
- `canal_rgb(imagen, letra)` → `imagen[:, :, 0|1|2]`
- `componente_ycm(imagen, letra)` → promedio en `float32` de dos canales → `uint8`
- `modo_color(canal, letra)` → array 3D con los otros componentes en 0
- `modo_blanco_y_negro(canal)` → array 2D (el canal tal cual, ya es monocromático)
- `aplicar_modo(canal, letra, modo)` → devuelve el array según `"color"` o `"blanco y negro"`
- `etiqueta_canal(espacio, letra)` → texto del campo "Canal actual" de la pantalla de histograma (§6.4)

```python
NOMBRES_CANAL = {
    "R": "Rojo",      "G": "Verde",     "B": "Azul",
    "Y": "Amarillo",  "C": "Cian",      "M": "Magenta",
}

def etiqueta_canal(espacio: str, letra: str) -> str:
    """'RGB' o 'YCM' + el nombre del canal en español. Ej.: 'RGB - Azul'."""
    if espacio not in ("RGB", "YCM"):
        raise ValueError(f"espacio de color inválido: {espacio}")
    return f"{espacio} - {NOMBRES_CANAL[letra]}"
```

`core/` **no conoce colores**: solo devuelve el texto. El color de cada canal vive en `tokens.COLOR_CANAL` (§5.1) y la vista lo aplica con `setStyleSheet()`, como manda §8 regla 1.

**Solo existen los modos `color` y `blanco y negro`.** No se implementa el modo `objeto` (silueta rellena) ni la métrica de área en los lienzos de canal. La detección de objeto existe únicamente en `core/segmentacion.py` para **quitar el fondo** (§7.2), que es un proceso distinto.

### 7.5 Máscara y guardado
- **Máscara binaria:** `uint8` con 255 = objeto.
- **PNG con transparencia:** `np.dstack([rgb, mascara])` → PIL modo `RGBA`.
- **PSD para Photoshop** (opcional, con `psd-tools`): la capa guarda **el RGB original completo** y la máscara como **máscara de capa**, para que al pintar sobre la máscara se recuperen los píxeles originales:
```python
psd = PSDImage.new("RGB", (ancho, alto))
capa = psd.create_pixel_layer(Image.fromarray(rgb), name="objeto")
capa.create_mask(Image.fromarray(mascara, mode="L"))
psd.save(ruta)
```
Se guarda además la máscara como PNG en escala de grises.

### 7.6 Histograma — `core/histograma.py`
- `histograma_canal(canal)` → 256 bins: `np.bincount(canal.ravel(), minlength=256).astype(np.int64)` (el `.ravel()` es obligatorio: sin él NumPy lanza `ValueError` con arrays 2D/3D).
- `limitar(mascara, imagen, inf, sup)` → acota la máscara por el rango de intensidades. **La comparación se hace sobre la imagen en gris**, porque indexar una máscara 2D con un array 3D lanza `IndexError` en NumPy (no hay broadcasting):
  ```python
  def limitar(mascara: np.ndarray, imagen: np.ndarray, inf: int, sup: int) -> np.ndarray:
      gris = imagen if imagen.ndim == 2 else cv2.cvtColor(imagen, cv2.COLOR_RGB2GRAY)
      fuera = (gris < int(inf)) | (gris > int(sup))
      return np.where(fuera, 0, mascara).astype(np.uint8)
  ```
- **Marcadores del rango (visualización):** el widget `GraficoHistograma` (§6.4) se ocupa solo de pintar las barras; las **líneas verticales, las flechas y los valores** de los dos límites se dibujan encima, en un overlay, con `MARCADOR_INFERIOR` y `MARCADOR_SUPERIOR`. Cada cambio de slider emite `Signal(int)` y el overlay se repinta; el histograma **no** se recalcula al mover los sliders. La posición de cada flecha la decide `x_de_marcador()`, que pregunta a Qt por el handle real (§6.4): el overlay **no** calcula el mapeo por su cuenta.

### 7.7 Recorte — `core/recorte.py`

**`core/` no importa Qt (§8 regla 4).** Por eso estas funciones reciben **enteros
planos** (`x`, `y`, `lado`), no un `QRect`: es `ui/ventana_recorte.py` quien
convierte el `QRect` que emite `SelectorCuadrado` a esos tres números. Así
`core/recorte.py` se puede probar sin abrir ninguna ventana.

```python
def recortar(imagen: np.ndarray, x: int, y: int, lado: int) -> np.ndarray:
    """Extrae la región cuadrada de lado `lado` desde (x, y), acotada a la imagen.

    NumPy NO lanza error con slices fuera de rango: los recorta en silencio y
    devuelve un array vacío o desplazado. Por eso se acota explícitamente.
    """
    lado = int(lado)
    if lado <= 0:
        raise ValueError("el lado del recorte debe ser un entero positivo")
    alto, ancho = imagen.shape[:2]
    x = max(0, min(int(x), ancho - 1))
    y = max(0, min(int(y), alto - 1))
    lado = min(lado, ancho - x, alto - y)      # nunca sobrepasar el array
    if lado <= 0:
        raise ValueError("el recorte queda fuera de la imagen")
    return np.ascontiguousarray(imagen[y:y + lado, x:x + lado])

def escalar(imagen: np.ndarray, factor: float) -> np.ndarray:
    """Amplía la imagen completa un `factor`, CONSERVANDO la proporción.

    Solo se usa en el modo B de §6.5, y solo si el usuario lo pide subiendo el
    zoom por encima de 1.0: ampliar inventará píxeles, pero estirar en un solo
    eje deformaría el objeto, así que los dos lados se escalan por igual y se
    redondea al entero más cercano.

    `factor == 1.0` devuelve una copia sin pasar por cv2: en el modo A la
    imagen NO debe remuestrarse ni un solo píxel (§6.5 regla 3).
    """
    factor = float(factor)
    if factor <= 0:
        raise ValueError("el factor de escala debe ser positivo")
    if factor == 1.0:
        return imagen.copy()
    alto, ancho = imagen.shape[:2]
    destino = (max(1, int(round(ancho * factor))),
               max(1, int(round(alto * factor))))
    return cv2.resize(imagen, destino, interpolation=cv2.INTER_LINEAR)

def lienzo_blanco(imagen: np.ndarray, lado: int) -> np.ndarray:
    """Deja la imagen sobre un lienzo BLANCO de lado x lado, centrada.

    Es el modo B de §6.5. Si la imagen YA es de `lado` o más en los dos ejes no
    hace nada: se devuelve tal cual y no se aloca nada.

    Si le faltan píxeles en uno o los dos ejes, los rellena de BLANCO (255) y
    centra la foto. Y si le SOBRAN en un eje (300x900: sobra en el ancho, falta
    en el alto) recorta el eje sobrante por el centro para que quepa en el lienzo:
    sin ese recorte el desplazamiento sería negativo y la asignación fallaría.

    El relleno es blanco y no transparente a propósito: el PNG de salida se abre
    en cualquier visor y en el papel se imprime, y ahí "sin fondo" se ve como un
    cuadrado negro o gris que no es lo que el usuario eligió. Un canal alfa aquí
    además obligaría a decidir qué es "blanco" en un archivo con alfa, que no
    tiene una respuesta única.
    """
    lado = int(lado)
    alto, ancho = imagen.shape[:2]
    if alto >= lado and ancho >= lado:
        return imagen                      # cabe entero: nada que rellenar
    salida = np.full((lado, lado) + imagen.shape[2:], 255, dtype=imagen.dtype)
    # Troceamos la imagen para que quepa en el lienzo: en cada eje se recorta el
    # sobrante por el centro (0 si no sobra) y se alinea al lado menor.
    ey0 = max(0, (alto - lado) // 2)
    ex0 = max(0, (ancho - lado) // 2)
    ey1 = min(alto, ey0 + lado)
    ex1 = min(ancho, ex0 + lado)
    # En destino el hueco se reparte a partes iguales: (lado - lo que cabe) // 2
    dy0 = (lado - (ey1 - ey0)) // 2
    dx0 = (lado - (ex1 - ex0)) // 2
    salida[dy0:dy0 + (ey1 - ey0), dx0:dx0 + (ex1 - ex0)] = imagen[ey0:ey1, ex0:ex1]
    return salida

def aplicar_recorte(imagen: np.ndarray, x: int, y: int,
                    lado: int, factor: float = 1.0) -> np.ndarray:
    """Produce la VISTA PREVIA de lado x lado. Lo que el botón "Redimensionar" calcula.

    El orden es siempre el mismo y no admite atajos:
      1. ampliar la imagen completa, si el usuario pidió factor > 1.0;
      2. centrarla sobre un lienzo blanco de lado x lado, rellenando lo que falte;
      3. recortar la ventana de lado x lado en (x, y).

    El paso 2 va ANTES del 3 y no es opcional: es lo que garantiza que la salida
    sea siempre cuadrada. Recortar primero dejaría un recorte de 300x300 en una
    imagen de 300x300, y el "relleno" tendría que hacerse después, con el recorte
    ya hecho y sin poder centrarlo.

    `x` e `y` son coordenadas del LIENZO, que es lo que ve el usuario y lo que
    emite `SelectorCuadrado` (§6.5). Si la imagen se rellenó, el lienzo es más
    grande que ella y esas coordenadas ya no son de la imagen original.

    A diferencia de `recortar()`, aquí NO se acorta en silencio: la salida es
    siempre `lado` x `lado` o hay error. Un 450x450 colándose en un dataset de
    512 es justo el fallo que este módulo existe para evitar.
    """
    if factor > 1.0:
        imagen = escalar(imagen, factor)
    region = recortar(lienzo_blanco(imagen, lado), x, y, lado)
    if region.shape[0] != lado or region.shape[1] != lado:
        raise ValueError(
            f"el recorte salió de {region.shape[1]}x{region.shape[0]} y se "
            f"pidió {lado}x{lado}: la región se sale del lienzo")
    return region
```

Reglas:

1. **`lado` es siempre `tokens.LADO_SALIDA` (512).** No hay ningún `lado_destino`: la salida no es configurable. El resultado nunca es rectangular.
2. **`aplicar_recorte` no acorta en silencio, lanza `ValueError`.** `recortar()` sí recorta lo que le quepa (es una utilidad general), pero `aplicar_recorte` tiene una promesa más fuerte: o devuelve `lado`×`lado`, o falla. Un 450×450 colándose en un dataset de 512 es el fallo que este módulo existe para evitar, y por eso la comprobación es explícita y no se delega en el recorte. El guard es una red de seguridad: con `lienzo_blanco()` delante, la región siempre cabe, así que si salta es que `x`/`y` vienen mal de la UI.
3. **`lienzo_blanco` va antes del recorte, siempre.** Es lo que hace que la salida sea cuadrada aunque la imagen sea menor que 512. Ponerlo después obligaría a inventar las coordenadas del relleno, que es imposible de hacer bien.
4. **`factor == 1.0` no toca `cv2.resize`.** Es el caso por defecto (modo A, y también el arranque del modo B) y debe salir **bit a bit** igual que la región original cuando la imagen ya es de 512 o más. Cualquier prueba de igualdad exacta aquí es obligatoria.
5. **`factor > 1.0` primero escala, después rellena y recorta.** Al revés se perdería resolución y el recorte saldría torcido.
6. **`escalar()` conserva la proporción.** Prohibido estirar solo un eje: un círculo debe seguir siendo un círculo.
7. **`escalar()` con `factor == 1.0` devuelve copia y no llama a `cv2`.** Es lo que garantiza la regla 4.
8. El recorte usa la imagen a **tamaño completo**; solo la *pantalla* usa la versión reducida (§7.8).
9. Estas funciones **no importan Qt**: reciben `x`, `y`, `lado` y `factor` como números planos. `ui/ventana_recorte.py` hace la conversión desde el `QRect` de `SelectorCuadrado` (§8 regla 4).

**Por qué `redimensionar()` no existe y por qué `centralizar()` volvió como `lienzo_blanco()`.**
Las dos vivían en este módulo y las dos se reescribieron al fijar la salida en 512 (§6.5):

| Función | Qué pasó | Por qué |
|---|---|---|
| `redimensionar(imagen, lado)` | **Borrada** → `escalar(imagen, factor)` | Forzaba un cuadrado. El modo B necesita **conservar la proporción** (regla 5): un círculo tiene que seguir siendo un círculo, no una elipse |
| `centralizar(imagen, lado_destino)` | **Reescrita** → `lienzo_blanco(imagen, lado)` | Sabía que iba a hacer falta y el error fue borrarla antes de tiempo. Se descartó cuando el diseño exigía ampliar hasta llenar el marco, porque entonces el marco siempre cabía y no había nada que rellenar. Con el relleno blanco (§6.5) sí hace falta: es lo que hace que la salida sea 512×512 aunque la imagen sea de 300×300 |

La diferencia que importa entre la versión vieja y `lienzo_blanco()` no es el nombre,
es la interfaz y el color:

| | `centralizar` (vieja) | `lienzo_blanco` (actual) |
|---|---|---|
| Relleno | transparente (`alpha = 0`) | **blanco (255)** |
| Motivo | Servía para "el lado pedido es mayor que la imagen" | El PNG de salida se imprime y se abre en cualquier visor, donde "sin fondo" se ve como un cuadrado negro que el usuario no eligió |
| Con alfa | Rama extra: había que decidir qué es "blanco" en un RGBA, y no hay respuesta única | `original` es RGB de 3 canales (§7.1), así que no hay alfa que decidir |

Con `factor == 1.0` y `lado = 512`, la versión anterior habría hecho
`redimensionar(region, 512)` sobre una región de 512×512: una copia sin ningún
cambio. Ese es el signo de que ese código ya no hacía falta.

### 7.8 Rendimiento
- Las operaciones pesadas (segmentación, histograma sobre imágenes grandes) **no deben bloquear la interfaz**: ejecutarlas en un `QThread`/`QRunnable` y actualizar la UI con `Signal` (PySide6; `pyqtSignal` es de PyQt y no existe aquí) cuando terminen. El worker **devuelve el array por la señal** y nunca muta `estado.preprocesada` en segundo plano, porque la GUI lee ese atributo a la vez. Las imágenes grandes se reducen para segmentar (§7.2).

---

## 8. Reglas de implementación

1. **Estilos fuera del código:** todo lo visual en `styles.qss`; en Python solo `setObjectName()`. El QSS se carga **una vez** al inicio, con la **ruta resuelta** y `encoding="utf-8"`:
   ```python
   import sys
   from pathlib import Path
   BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
   qss = BASE / "styles.qss"
   if not qss.exists():
       raise FileNotFoundError(f"no se encuentra styles.qss en {BASE}")
   app.setStyleSheet(qss.read_text(encoding="utf-8"))
   ```
   Nunca `open("styles.qss")`: en el `.exe` el directorio de trabajo es donde se hizo doble clic, no la carpeta del binario, y la app abriría **sin estilos** sin dar ningún error.
2. **Layouts, no posiciones:** prohibido `move()` / `setGeometry()` para ubicación. Se usan `addWidget(widget, fila, col, align=Qt.AlignHCenter)`.
3. **`setFixedSize()` solo en controles:** `setFixedSize(BTN_ANCHO, BTN_ALTO)` en botones y campos. Los cuadros de imagen usan `setMinimumSize()` + `setSizePolicy(Expanding, Expanding)` (§5.3 regla 5).
4. **Señales y slots:** la UI emite señales (`imagenSeleccionada`, `modoCambiado`, `modeloCambiado`) y `core/` no sabe nada de Qt.
5. **Botones siempre coherentes:** todos los botones estándar con el mismo `objectName` cuando comparten rol, para heredar el estilo correcto.
6. **Sin sobrescrituras:** ninguna acción de la app modifica el archivo original salvo el botón explícito "Sobreescribir".
7. **Recursos:** iconos en `assets/`; el `.ico` se incluye en el empaquetado (§10).

---

## 9. Criterios de aceptación

- [ ] `python main.py` abre una **ventana de escritorio propia** (no navegador) que **arranca en 1280×720**.
- [ ] La ventana se puede **maximizar** y redimensionar; el contenido **se adapta** (se centra y distribuye) sin deformarse.
- [ ] Al redimensionar, los botones **mantienen 200×60** y los lienzos/gráficos se estiran manteniendo proporción.
- [ ] **Todos los cuadros de imagen conservan la proporción**: 1:1 los de **300×300** (zona de imagen y lienzos de canal), 1:1 los de **250×250** (miniaturas del histograma), **467:333** el gráfico del histograma y **1:1** la zona de recorte.
- [ ] En la pantalla de recorte se puede **arrastrar sobre la imagen para mover el marco**, y el marco es **siempre cuadrado de 512×512**, nunca rectangular ni de otro tamaño.
- [ ] El marco no se puede cambiar de tamaño: no hay `QSpinBox`, ni campo numérico, ni rueda que lo altere. Su lado sale de `tokens.LADO_SALIDA`.
- [ ] Sobre la imagen aparece la **manita** (`OpenHandCursor`), que cambia a puño cerrado mientras se arrastra.
- [ ] Fuera del marco la imagen se ve **atenuada al 50 %**, y dentro se ve **normal**: el velo se pinta **encima** de la imagen completa, no sobre el fondo.
- [ ] Con imagen de 512 o más, "Redimensionar" produce una vista previa **idéntica píxel a píxel** a la región del marco: el resultado de `aplicar_recorte(..., factor=1.0)` es igual con `np.array_equal` a `original[y:y+512, x:x+512]`, sin pasar por `cv2.resize`.
- [ ] "Redimensionar" **no crea ni modifica ningún archivo**: solo pinta la vista previa y habilita los botones de guardar.
- [ ] "Guardar copia" y "Sobreescribir" arrancan **deshabilitados** y solo se habilitan tras un "Redimensionar" correcto.
- [ ] Lo que se guarda es **exactamente** lo que muestra la vista previa: el botón escribe `EstadoImagen.vista_previa` sin recalcular nada.
- [ ] El control de zoom está **siempre visible**: en modo A se ve **deshabilitado** (atenuado), nunca oculto, y en modo B funciona. Con imagen **menor de 512** se habilita, la foto se centra en el lienzo y **lo que falta se rellena de BLANCO**, sin estirar la imagen para cuadrarlo y sin ampliarla sola. El zoom arranca en **1.0**.
- [ ] Una 300×300 con el zoom en 1.0 produce un PNG de 512×512 con la foto de 300×300 **centrada** y los bordes blancos; los píxeles de la foto salen **sin tocar** (no pasan por `cv2.resize`).
- [ ] Subir el zoom hasta que la foto tape el lienzo hace **desaparecer el blanco** sin cambiar de pantalla: el modo B se comporta entonces como el modo A y el marco vuelve a ser arrastrable.
- [ ] Con el relleno activo, la parte del marco de 512 que cae sobre el blanco también se atenúa junto con el resto del lienzo.
- [ ] Con un `QRect` **vacío** "Redimensionar" está **deshabilitado**, `EstadoImagen.recorte` sigue en `None` y al pulsarlo **no** se llama a `aplicar_recorte()`: no se lanza `ValueError`.
- [ ] El factor de zoom nunca produce una imagen ampliada cuyo lado mayor supere `tokens.LADO_AMPLIADO_MAX` (4096).
- [ ] El escalado del modo B **conserva la proporción**: un círculo sigue siendo un círculo, nunca una elipse.
- [ ] El archivo **no** se modifica al elegir el área: solo al pulsar "Guardar copia" o "Sobreescribir".
- [ ] "Guardar copia" y "Sobreescribir" producen **siempre** un PNG de **512×512**, incluso si la región toca el borde de la imagen.
- [ ] La imagen dentro del cuadro nunca se deforma: se escala con `KeepAspectRatio` y queda **centrada**.
- [ ] En resoluciones pequeñas (1366×768) nada queda cortado; si no cabe, aparece scroll vertical.
- [ ] Al maximizar en 1920×1080 el contenido queda centrado, no pegado a una esquina.
- [ ] Todos los botones estándar miden **200×60**; el de navegación **160×48**. Ninguno sin tamaño fijo.
- [ ] Todos los botones son **redondeados tipo pastilla** (radio 30 en los de 60 de alto, 24 en los de 48).
- [ ] Al hacer hover y click, el botón **no cambia de tamaño ni de forma**: solo el color de fondo.
- [ ] Con el **teclado** (Tab), el botón con foco muestra un **anillo** de 2 px que **no** es el fondo del hover, y ese anillo se ve también en `REGRESAR` y en el botón primario.
- [ ] Un botón **deshabilitado** es gris claro (`#EFEFEF`) con texto `#9E9E9E`, y se lee en los tres roles: estándar, `REGRESAR` y primario.
- [ ] Ningún texto de 14 px queda por debajo de 4.5:1 de contraste sobre su fondo, en ningún estado (normal, hover, presionado, foco, deshabilitado).
- [ ] Los tres lienzos de canal están en una fila recta, separados 130 px, con su letra centrada encima.
- [ ] Los grupos de botones están centrados y alineados en una columna recta.
- [ ] Click en la zona de imagen abre el selector y muestra la foto con su nombre.
- [ ] `Elegir modelo` alterna grabcut/otsu, arranca en **grabcut**.
- [ ] El botón **"Analizar por canales"** lleva a la pantalla **RGB** (no a YCM directamente).
- [ ] Con la pantalla **RGB** visible, la **flecha derecha** cambia a **YCM**.
- [ ] Con la pantalla **YCM** visible, la **flecha izquierda** vuelve a **RGB**.
- [ ] **Esc** regresa a la pantalla principal desde RGB o YCM.
- [ ] En la pantalla principal (y en histograma/recorte) las flechas y Esc **no hacen nada**.
- [ ] Las **cuatro pantallas secundarias** (RGB, YCM, Histograma y Recortar imagen) tienen botón **`REGRESAR`** de 160×48 en la esquina superior derecha, y todas vuelven a Principal.
- [ ] Solo hay un nombre para ese botón: `REGRESAR` (no existe "VOLVER").
- [ ] Al mover el slider inferior/superior, aparece una **línea vertical** y una **flecha** debajo del histograma en su posición.
- [ ] La línea del slider **inferior** es **naranja** (`#E65100`), la del slider **superior** es **verde** (`#00897B`).
- [ ] Las dos flechas apuntan hacia arriba y tienen **colores distintos** entre sí.
- [ ] Debajo de cada flecha se muestra su valor (`inf` / `sup`).
- [ ] La zona entre ambas líneas queda resaltada y fuera de ella se atenúa.
- [ ] Los marcadores se actualizan **en tiempo real** (sin soltar el ratón).
- [ ] La punta de cada flecha cae **exactamente** sobre el centro del handle de su slider, con el slider en sus valores extremos (`inf=0`, `sup=255`) y en valores intermedios. Se comprueba con `x_de_marcador()`, que devuelve la misma `x` que `QStyle.subControlRect(SC_SliderHandle)`.
- [ ] Preguntar la posición del handle **no mueve** el slider: tras repintar, `slider.value()` sigue siendo el que tenía.
- [ ] El atajo de teclado no se dispara con el foco en un campo de entrada.
- [ ] `Quitar fondo` no modifica el archivo en disco ni la imagen original en memoria; el botón revierte a "Restaurar original".
- [ ] Cambiar de modelo recalcula el preprocesado automáticamente.
- [ ] El modo alterna **solo entre `color` y `blanco y negro`** (nunca un tercer modo); el botón refleja el modo activo.
- [ ] **No existe el modo `objeto`** en los lienzos de canal ni métrica de área bajo los canales.
- [ ] Los canales RGB y YCM se calculan **siempre sobre la imagen original**, nunca sobre la imagen preprocesada.
- [ ] `original` es siempre `uint8` de 3 canales RGB: un PNG de 16 bits, uno con alfa y uno en escala de grises se abren sin romper el histograma de 256 bins ni desbordar los casts a `uint8` (se carga con `IMREAD_COLOR`, §7.1).
- [ ] Tras aplicar "Quitar fondo", los lienzos de canal RGB/YCM **no cambian**.
- [ ] El campo "Canal actual" del histograma muestra el formato **`RGB - <canal>`** o **`YCM - <canal>`**, con el nombre del canal en español (`Azul`, `Verde`, `Rojo`, `Amarillo`, `Cian`, `Magenta`).
- [ ] Ese campo cambia al cambiar de canal, y sus miniaturas se actualizan junto con él.
- [ ] El campo "Canal actual" **no** muestra el modo `color` / `blanco y negro` (ese lo controla el botón "Modo").
- [ ] El histograma dibuja 256 bins por canal y responde a los dos sliders.
- [ ] `Guardar imagen` produce un **PNG RGBA válido** (abre, tiene canal alfa y el fondo es transparente) y `Guardar máscara` un PNG de 8 bits en escala de grises con 255 = objeto.
- [ ] La fórmula de los canales YCM es la de §6.3: `Y=(R+G)/2`, `C=(G+B)/2`, `M=(R+B)/2`, calculado en `float32` y convertido a `uint8` (sin desbordamiento).
- [ ] GrabCut usa `rect` = 10 % de cada borde y segmenta a máximo 500 px de lado mayor.
- [ ] El cuadro "Canal de contorno binario" muestra el **contorno** del objeto, no la silueta rellena.
- [ ] El campo "Directorio de imagen:" muestra **la carpeta** que contiene el archivo, no la ruta completa desde la raíz.
- [ ] El `.exe` arranca **con los estilos aplicados**: `styles.qss` se localiza por ruta resuelta y no por directorio de trabajo.
- [ ] `Guardar copia` no pisa el original; `Sobreescribir` pide confirmación.
- [ ] Ninguna pantalla permite avanzar sin imagen seleccionada (botones deshabilitados).
- [ ] La interfaz no se congela al procesar imágenes grandes.

---

## 10. Empaquetado a `.exe` (solo al final, opcional)

> ⚠️ **Este paso se ejecuta únicamente cuando el proyecto ya está terminado.** Antes de compilar, todos los criterios de aceptación de §9 deben estar en verde. Si algo falla, se corrige en el código fuente, nunca en el `.exe`.

### 10.0 Precondiciones (verificar antes de compilar)

- [ ] Todos los checks de §9 en verde.
- [ ] La aplicación corre bien con `python main.py`.
- [ ] No hay imports circulares entre `ui/` y `core/`.
- [ ] `styles.qss` y `assets/` existen y se localizan por **ruta resuelta** (§8 regla 1), no por directorio de trabajo.
- [ ] El proyecto **no depende** de rutas absolutas de mi máquina.

### 10.1 Instalación
```bash
pip install pyinstaller
```

### 10.2 Comando directo (verificación rápida)
```bash
pyinstaller --noconfirm --windowed --name Analizador ^
  --add-data "styles.qss;." ^
  --add-data "assets;assets" ^
  main.py
```

### 10.3 Configuración con `main.spec` (recomendado)
```python
# main.spec
from PyInstaller.utils.hooks import collect_all
psd_bin, psd_data, psd_hidden = collect_all('psd_tools')   # psd-tools trae parsers y recursos

a = Analysis(['main.py'],
             pathex=[],
             binaries=psd_bin,
             datas=[('styles.qss', '.'), ('assets', 'assets')] + psd_data,
             hiddenimports=['core.imagen', 'core.segmentacion', 'core.canales',
                            'core.histograma', 'core.recorte',
                            'ui.tokens', 'ui.widgets', 'ui.ventana_principal',
                            'ui.ventana_rgb', 'ui.ventana_ycm',
                            'ui.ventana_histograma', 'ui.ventana_recorte'] + psd_hidden,
             hookspath=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name='Analizador', console=False, icon='assets/icon.ico')
coll = COLLECT(exe, a.binaries, a.datas, name='Analizador')
```
`ui.tokens`, `ui.widgets`, `core.imagen` y `ui.ventana_principal` **no** se importan de forma estática desde todos lados: si el análisis de PyInstaller no los ve, el `.exe` arranca con `No module named`. Por eso van explícitos.
```bash
pyinstaller main.spec --noconfirm
```

### 10.4 Resultado
- `--onedir` (COLLECT, el de arriba): carpeta `dist/Analizador/` con `Analizador.exe`. **Arranca más rápido y es más estable con Qt.** Preferido para este proyecto.
- `--onefile`: un único `.exe`, arranque más lento y más propenso a errores de DLL.
- Ruta de recursos en runtime:
```python
from pathlib import Path
import sys
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
qss = BASE / "styles.qss"
```

---

## 11. Restricciones y notas

- El **Figma es referencia funcional, no de medidas**: si un tamaño del Figma difiere de la tabla §5.2, **gana la tabla**.
- No usar `matplotlib` en ningún momento (§3.3): el histograma se dibuja con `QPainter`. Las paletas de color son las de `tokens.py` y el QSS.
- Las imágenes se cargan siempre en **RGB**; para PNG con transparencia se convierte a RGBA al guardar.
- Si una imagen es muy grande (varios miles de píxeles), reducir para previsualizar y para segmentar; el recorte/guardado usa el tamaño completo.
- La ventana **nunca** se fija: `setFixedSize()` solo se aplica a botones, lienzos y campos, nunca a la ventana principal.
- El preprocesado es **siempre no destructivo** salvo acción explícita de "Sobreescribir" en la pantalla de recorte.

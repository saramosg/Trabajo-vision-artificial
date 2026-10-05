# Trabajo vision artificial

Aplicacion de escritorio en PySide6 para analizar imagenes: preprocesado (quitar
fondo con GrabCut u OTSU), canales de color RGB/YCM, histograma de color y recorte
con marco fijo.

Incluye ademas el dataset de frutas del **Reto 2** (`imagenes/`), construido para
detectar fitopatogenos poscosecha.

## Requisitos

- Windows 10/11
- Python **3.11.9**
- Dependencias de `requirements.txt`

## Instalacion

```powershell
cd "C:\ruta\del\proyecto"
py -3.11 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

## Ejecucion

```powershell
& ".\.venv\Scripts\python.exe" main.py
```

## Estructura

```
trabajo_grupal/
├── main.py                  punto de entrada: QApplication + styles.qss
├── requirements.txt
├── styles.qss               hoja de estilos global
├── requisitos.md            especificacion funcional de referencia
├── descargar_imagenes.py    script del dataset de frutas
├── assets/
├── core/                    logica de imagen (SIN Qt, testeable sin ventanas)
│   ├── imagen.py            carga/guardado + EstadoImagen compartido
│   ├── segmentacion.py      GrabCut / OTSU, limpieza, contorno
│   ├── canales.py           canales RGB/YCM y modos color | blanco y negro
│   ├── histograma.py        histograma (matplotlib) y mascara por rango
│   └── recorte.py           recorte libre a 512 con relleno blanco
├── ui/                      pantallas y widgets (PySide6)
│   ├── tokens.py            tokens de diseno (unica fuente de verdad)
│   ├── helpers.py           botones y envoltorio de scroll compartidos
│   ├── widgets.py           ProporcionImagen, a_pixmap
│   ├── ventana_principal.py pantalla de preprocesado + ventana central
│   ├── ventana_canales.py   base de RGB e YCM
│   ├── ventana_rgb.py       /  ventana_ycm.py
│   ├── ventana_histograma.py pantalla de histograma
│   └── ventana_recorte.py   pantalla de recorte (VistaRecorte)
├── imagenes/                dataset del Reto 2 (ver abajo)
├── frutas/                  fotos de referencia
├── tests/                   suite de verificacion
├── legacy/                  codigo previo, no se usa en runtime
└── docs/
```

**Regla de dependencias:** `ui/` importa de `core/`; `core/` nunca importa de
`ui/` ni de PySide6. Toda la logica de imagen es comprobable sin abrir ventanas.

## Pantallas

1. **Principal** — carga la imagen, elige modelo (grabcut/otsu), quita/restaura
   el fondo sin tocar el archivo, navega a canales o recorte.
2. **Canales RGB** — tres lienzos (300x300) separados 130 px; modo
   `color` / `blanco y negro`; se calculan siempre sobre la **original**.
3. **Canales YCM** — identica a RGB con Y/C/M (`Y=(R+G)/2`, `C=(G+B)/2`,
   `M=(R+B)/2`, calculado en `float32`).
4. **Histograma** — entra siempre en blanco y negro; render con `plt.hist`
   estilo modulo 2; los sliders acotan el rango `[inf, sup]` y alimentan el
   contorno binario. Botones: selector de canal, "Limpiar mascara" (rellena
   huecos y quita islas), "Quitar fondo" (preview local), "Guardar imagen" (RGBA)
   y "Guardar mascara".
5. **Recortar imagen** — marco fijo al 70 % del lienzo; el slider escala la
   imagen y el arrastre la mueve (el marco puede salirse y lo faltante sale
   blanco). La salida es siempre **512x512**.

Navegacion: `REGRESAR` en las cuatro pantallas secundarias, atajos
`->` (RGB→YCM), `<-` (YCM→RGB) y `Esc` (a Principal).

## Dataset de frutas (Reto 2)

- **150 imagenes**: 10 especies x 15 (8 `sana/` + 7 `alterada/`).
- Fuente: Wikimedia Commons (licencias libres, atribucion en el manifest).
- `imagenes/manifest.csv`: archivo, tema, estado, consulta, titulo, url, autor
  y licencia de cada imagen.
- `imagenes/_excedente_sana/`: 80 imagenes sanas sobrantes de la primera
  corrida. Se pueden borrar.

Estructura:

```
imagenes/
├── manzana/{sana,alterada}/001.jpg ...
├── banano/ cereza/ uva/ limon/ mango/ naranja/ pina/ fresa/ sandia/
└── manifest.csv
```

Regenerar o completar (el script es reanudable y respeta el tope de 300):

```powershell
python descargar_imagenes.py --total 150 --max 300
python descargar_imagenes.py --verificar   # solo comprueba las cuotas
```

**Nota sobre las etiquetas:** la carpeta `sana/` o `alterada/` se asigna por la
consulta de busqueda con la que se bajo la imagen, no por inspeccion humana. Es
una **pre-clasificacion** que hay que revisar antes de entrenar: la API busca por
titulo y descripcion, asi que puede colarse una foto de una tarta de manzana en
`alterada/`. Para el dataset final, valida visualmente o anota aparte.

## Tests

```powershell
& ".\.venv\Scripts\python.exe" tests\suite.py            # las 4 suites
& ".\.venv\Scripts\python.exe" tests\suite.py --rapido   # sin Qt
```

## Variables de entorno

| Variable | Uso |
|---|---|
| `FIGMA_TOKEN` | Token personal de Figma (diseño de referencia) |
| `FIGMA_URL` | Enlace al archivo de Figma del proyecto |

Viven en las variables de entorno de usuario, **no** en archivos. `.gitignore`
incluye `.env`, `*.token` y `secrets*` como red de seguridad.

## Notas

- El tamano del recorte es fijo en 512 (`tokens.LADO_SALIDA`); no hay forma de
  cambiarlo desde la interfaz.
- La salida guardada es siempre PNG; "Sobreescribir" pide confirmacion y es la
  unica accion que modifica el archivo original.
- `legacy/` y `tests/scratch/` no participan en runtime.
- `*.psd` esta en `.gitignore` (el de strawberry pesa 255 MB).
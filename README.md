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
   y "Guardar mascara" (PSD con la imagen + mascara de capa).
5. **Recortar imagen** — marco fijo al 70 % del visor; el slider escala la
   imagen y el arrastre la mueve (el marco puede salirse y lo faltante sale
   blanco). La salida es siempre **512x512**.

Navegacion: `REGRESAR` en las cuatro pantallas secundarias, atajos
`->` (RGB→YCM), `<-` (YCM→RGB) y `Esc` (a Principal).

## Dataset de frutas (Reto 2)

- Diseno: 10 especies x 15 (8 `sana/` + 7 `alterada/`), tope 300.
- **Estado actual: 50 imagenes en disco** (se borraron 100; `limon/` quedo
  vacio). `manifest.csv` aun lista las 150 originales.
- Fuente: Wikimedia Commons (licencias libres, atribucion en el manifest).
- `imagenes/manifest.csv`: archivo, tema, estado, consulta, titulo, url,
  autor y licencia de cada imagen.

Estructura:

```
imagenes/
├── manzana/{sana,alterada}/001.jpg ...
├── banano/ cereza/ uva/ limon/ mango/ naranja/ pina/ fresa/ sandia/
└── manifest.csv
```

Completar hasta la cuota (el script es reanudable, solo baja lo faltante):

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

## Compilado (`.exe`)

`main.spec` esta versionado (es artesanal, sin rutas absolutas) con
`collect_all` de `psd-tools` y `matplotlib` + `backend_agg` forzado; sin eso
el histograma falla en el `.exe`. `assets/icon.ico` se genera con
`generar_icono.py` si no existe.

Compilacion limpia en **PowerShell**:

```powershell
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m PyInstaller main.spec --noconfirm --clean
```

En **Git Bash**:

```bash
rm -rf build dist
./.venv/Scripts/python.exe -m PyInstaller main.spec --noconfirm --clean
```

El resultado es `dist/Analizador/Analizador.exe` (~300 MB, modo `--onedir`):
hay que distribuir la carpeta **completa** (`Analizador.exe` + `_internal/`;
sin `_internal` no arranca). Para el release de GitHub se sube comprimida con
`gh release upload` (la web rechaza archivos de mas de 25 MB). Para achicarla,
excluir `IPython`, `jedi` y `tkinter` en el `Analysis` del spec ahorra 50-100 MB.

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
# Analizador de Imágenes (PySide6 + QSS) Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL - Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Construir aplicación de escritorio (PySide6) para preprocesar, analizar canales RGB/YCM, histograma, recorte/redimensionado y guardar.

**Architecture:** core/ (lógica pura de imagen) y ui/ (ventanas/widgets con Qt Layouts + QSS). core/ nunca importa ui/.

**Tech Stack:** Python 3.13 + PySide6 6.11.2, opencv-python, numpy, pillow, psd-tools, PyInstaller. Proyecto con .venv existente.

**Spec:** C:\Users\santiago\Desktop\unal\vision artificial\trabajo\requisitos.md (fuente única de verdad).

## Global Constraints

- Python 3.13.
- PySide6-Essentials >= 6.6, < 7. No matplotlib.
- core/ nunca importa de ui/.
- Salida 512x512. Zona de recorte 613x613 fija.
- Modo A: recorte directo. Modo B: escalar() -> lienzo_blanco() -> recortar().
- Lo que sobra se rellena de BLANCO (255).
- Zoom siempre visible. En modo A deshabilitado nunca oculto. Factor arranca 1.0.
- factor_max = max(1.0, min(4.0, LADO_AMPLIADO_MAX / max(alto, ancho))).
- Overlay con QGridLayout, dos widgets en la misma celda. No usar resizeEvent/setGeometry para sincronizar.
- paintEvent no emite señales; aviso en set_datos().
- Todo script de verificación hace sys.exit(1 if fallos else 0).
- Cada token usado existe. Barras histograma usan tokens.ACENTO.
- Desarrollo por módulos; empaquetado .exe solo al final.

## Review Focus

1. Relleno blanco obligatorio (255) en lienzo 512x512 (modo B).
2. escalar(img,1.0): igual bit-a-bit pero distinto objeto (no misma referencia).
3. recortar(): clipping en bordes, lado 0 lanza ValueError, nunca lado > imagen.
4. escalar(): conserva proporción, funciona en 2D.
5. Overlay QGridLayout estable al redimensionar.

---

### Task 1: requirements.txt (Paso 1 de §0)

**Files:**
- Modify: C:\Users\santiago\Desktop\unal\vision artificial\trabajo\requirements.txt

**Interfaces:**
- Consumes: N/A
- Produces: requirements.txt con dependencias de §3.3

- [ ] **Step 1: Write the failing test**
  Not applicable for config file; verification only.

- [ ] **Step 2: Verify current environment**
  Run: cd 'C:\Users\santiago\Desktop\unal\vision artificial\trabajo'; & .venv\Scripts\python.exe -c "import PySide6, cv2, numpy, PIL, psd_tools; print('OK')"
  Expected: OK

- [ ] **Step 3: Implement requirements.txt**
  Content per §3.3.
  PySide6-Essentials>=6.6,<7; opencv-python>=4.9; numpy>=1.26; pillow>=10.2; psd-tools>=1.9; PyInstaller>=6.3

- [ ] **Step 4: Commit**
  git add requirements.txt; git commit -m 'chore: add requirements.txt per §3.3'

---


### Task 2: Mover suite de tests desde %TEMP%/opencode al proyecto ANTES de código

**Files:**
- Create/Copy: C:\Users\santiago\Desktop\unal\vision artificial\trabajo\tests\ (new dir)
- Copy: suite.py, verificar.py, test_recorte.py, test_widgets.py, test_overlay.py, assets/refs y scripts auxiliares desde C:\Users\santiago\AppData\Local\Temp\opencode\

**Interfaces:**
- Consumes: Tests existentes en temp (suite red de seguridad)
- Produces: tests/ local para validación continua

- [ ] **Step 1: Create tests directory**
  Run: mkdir -Force 'C:\Users\santiago\Desktop\unal\vision artificial\trabajo\tests'

- [ ] **Step 2: Copy test suite files**
  Copy: suite.py, verificar.py, test_recorte.py, test_widgets.py, test_overlay.py, append_nb*.py, diag*.py, extract5.py, init_nb*.py, negctl.py, render*.py, clase*.txt, clase*.png (si existen), c5-*.png, test_*.py relevantes from temp.
  Critical: suite.py must call sys.exit(1 if total else 0) - verify.

- [ ] **Step 3: Update paths in suite.py to use local tests dir**
  Update RAIZ/SCRIPTS paths as needed so running from proyecto/tests or proyecto works.

- [ ] **Step 4: Verify suite runs (red/green context)**
  Run: cd 'C:\Users\santiago\Desktop\unal\vision artificial\trabajo'; ="offscreen"; & .venv\Scripts\python.exe tests\suite.py --rapido
  Expected: executes (may fail until core/recorte.py exists - but we need to understand current state). Document result.

- [ ] **Step 5: Commit**
  git add tests; git commit -m 'chore(tests): add test suite from opencode temp for safety'

---


### Task 3: Estructura de carpetas y archivos (Paso 2 de §0)

**Files:**
- Create dirs: ui/, core/, assets/, docs/superpowers/plans/ (exists)
- Create: main.py, styles.qss, ui/__init__.py, ui/tokens.py, ui/ventana_principal.py, ui/ventana_rgb.py, ui/ventana_ycm.py, ui/ventana_histograma.py, ui/ventana_recorte.py, ui/widgets.py
- Create: core/__init__.py, core/imagen.py, core/segmentacion.py, core/canales.py, core/histograma.py, core/recorte.py
- Create: assets/icon.ico (placeholder ok)

**Interfaces:**
- Consumes: §4.1 structure
- Produces: Empty scaffold files with correct module layout

- [ ] **Step 1: Create directories**
  mkdir -Force ui, core, assets, tests (if not exists)

- [ ] **Step 2: Create __init__.py files**
  touch ui/__init__.py, core/__init__.py

- [ ] **Step 3: Create scaffold modules**
  Create empty files per structure (ui: tokens.py, ventanas, widgets.py; core: imagen.py, segmentacion.py, canales.py, histograma.py, recorte.py; main.py, styles.qss)

- [ ] **Step 4: Verify all files exist**
  List required files; all present.

- [ ] **Step 5: Commit**
  git add main.py styles.qss ui core assets
  git commit -m 'chore: scaffold project structure per §4.1'

---


### Task 4: tokens.py y styles.qss (Paso 3 de §0)

**Files:**
- Create/Modify: ui/tokens.py, styles.qss

**Interfaces:**
- Consumes: §5.1-§5.4 tokens/colors/metrics
- Produces: tokens module importable; QSS file

- [ ] **Step 1: Write failing test (import check)**
  Verify: python -c "from ui import tokens; print(tokens.BTN_ALTO)" should work

- [ ] **Step 2: Implement ui/tokens.py per §5.1**
  Include all colors (FONDO, SUPERFICIE, TEXTO, BORDE, ACENTO, ACENTO_HOVER, PELIGRO),
  MARCADOR_INFERIOR/SUPERIOR, COLOR_CANAL dict with correct dark variants (R=#B71C1C, G=#1B5E20, B=#0D47A1, Y=#F57F17, C=#006064, M=#4A148C),
  Tipografías (FUENTE_FAMILIA, TAM_FUENTE, TAM_FUENTE_PEQ),
  Espaciados (ESP_XS..ESP_XL),
  Botones (BTN_ALTO, BTN_ANCHO), Campos (CAMPO_ALTO), Radios (RADIO),
  Proporciones (RAZON_ZONA, RAZON_CANAL, RAZON_HISTO_IMG, RAZON_HISTO_GRAF, RAZON_RECORTE)
  Heights (ALT_MIN_VENTANA, ALT_MAX_VENTANA),
  Recorte constants (LADO_AMPLIADO_MAX, ZONA_CENTRO_X, ZONA_CENTRO_Y, ZONA_RADIO)
  Scroll (SCROLL_ANCHO)

- [ ] **Step 3: Implement styles.qss per §5.4**
  Global styles using token values; avoid hardcoding conflicting colors. Use tokens.ACENTO for histograma bars as implied.

- [ ] **Step 4: Verify import**
  Run: cd 'C:\Users\santiago\Desktop\unal\vision artificial\trabajo'; & .venv\Scripts\python.exe -c "from ui import tokens; assert tokens.BTN_ALTO==32; print('OK')"
  Expected: OK

- [ ] **Step 5: Commit**
  git add ui/tokens.py styles.qss
  git commit -m 'feat(ui): add tokens.py and styles.qss per §5.1/§5.4'

---


### Task 5: core/recorte.py (TDD - núcleo crítico)

**Files:**
- Create/Modify: core/recorte.py
- Test: tests/test_recorte.py exists (from temp)

**Interfaces:**
- Produces: recortar(img, x, y, lado) -> np.ndarray, escalar(img, factor) -> np.ndarray, lienzo_blanco(alto, ancho) -> np.ndarray, hacer_portada(img, modo='A') -> np.ndarray (según §7.5 y tests)

- [ ] **Step 1: Write failing test (execute test_recorte.py)**
  Run: cd 'C:\Users\santiago\Desktop\unal\vision artificial\trabajo'; ="offscreen"; & .venv\Scripts\python.exe tests/test_recorte.py 2>&1 | tail -30
  Expected: FAIL with missing functions (recortar, escalar, etc.)

- [ ] **Step 2: Implement recortar(img, x, y, lado) per §7.5 + tests**
  Requirements: lado <= 0 -> ValueError; x,y negativos/acotan por bordes (clipping); nunca devuelve lado mayor que imagen; contiguo (C_CONTIGUOUS). Trabaja con 2D o 3D.

- [ ] **Step 3: Implement escalar(img, factor) per §7.5 + tests**
  factor <= 0 -> ValueError; factor==1.0 devuelve COPIA (is not) BIT A BIT igual (np.array_equal); conserva proporción; funciona 2D. No pasar por cv2.resize si factor==1.0.

- [ ] **Step 4: Implement lienzo_blanco(alto, ancho) -> np.ndarray (uint8, BGR o RGB según img? tests: llena BLANCO [255,255,255])**
  Devuelve lienzo blanco 512x512 (or requested) relleno con [255,255,255].

- [ ] **Step 5: Implement hacer_portada(img, modo='A') según reglas Modo A/B**
  Modo A: recorte directo. Modo B: escalar() -> lienzo_blanco() -> recortar(). Salida 512x512. Zona 613x613 fija (concepto).

- [ ] **Step 6: Run tests for recorte.py**
  Run: cd 'C:\Users\santiago\Desktop\unal\vision artificial\trabajo'; & .venv\Scripts\python.exe tests/test_recorte.py
  Expected: all checks PASS. sys.exit(0)

- [ ] **Step 7: Commit**
  git add core/recorte.py
  git commit -m 'feat(core): implement recorte/escalar/lienzo_blanco/hacer_portada per spec'

---


### Task 6: core/imagen.py, segmentacion.py (TDD básico)

**Files:**
- Create/Modify: core/imagen.py, core/segmentacion.py

**Interfaces (per §7):**
- imagen.py: cargar_imagen, guardar_imagen, guardar_mascara, guardar_psd (psd-tools), obtener_previsualizacion
- segmentacion.py: grabcut, otsu, limpiar_mascara, aplicar_mascara

- [ ] **Step 1: Write minimal tests (if missing) or run via suite --rapido**
  Use test_recorte style for new functions as needed. Keep core pure (no Qt).

- [ ] **Step 2: Implement imagen.py**
  Non-destructive: never overwrite original. Handle RGBA. PIL/OpenCV interop.

- [ ] **Step 3: Implement segmentacion.py**
  GrabCut (predeterminado) and OTSU as per §7.2. Return masks/images as numpy arrays.

- [ ] **Step 4: Test without UI**
  Quick smoke tests with sample images if available (frutas/ or clase*.png).

- [ ] **Step 5: Commit**
  git add core/imagen.py core/segmentacion.py
  git commit -m 'feat(core): add imagen and segmentacion modules'

---


### Task 7: core/canales.py, core/histograma.py (TDD)

**Files:**
- Create/Modify: core/canales.py, core/histograma.py

**Interfaces:**
- canales.py: extraer_canales_rgb, extraer_canales_ycm, modo_color_bn (color/blanco y negro) (§7.3)
- histograma.py: calcular_histograma, calcular_percentiles, ajustar_rango (§7.4)

- [ ] **Step 1: Red tests**
  Define expected shapes/behavior per §7.3-7.4.

- [ ] **Step 2: Implement canales.py**
  RGB and YCM. Two modes (color, blanco y negro).

- [ ] **Step 3: Implement histograma.py**
  Histogram calc + percentiles + range adjustment. Pure numpy.

- [ ] **Step 4: Quick verification**
  Run targeted tests; shapes match spec.

- [ ] **Step 5: Commit**
  git add core/canales.py core/histograma.py
  git commit -m 'feat(core): add canales and histograma modules'

---


### Task 8: ui/widgets.py (TDD con PySide6 offscreen)

**Files:**
- Create/Modify: ui/widgets.py
- Test: tests/test_widgets.py, tests/test_overlay.py

**Interfaces:**
- Widgets: ProporcionImagen (escala y centra imagen), SelectorCuadrado (§6.5), Histograma (contenedor), GraficoHistograma (barras - dibujado con QPainter), OverlayMarcadores (§6.4, QGridLayout - dos widgets misma celda), dibujar_marcadores (§6.4).

- [ ] **Step 1: Red tests**
  Run: ="offscreen"; & .venv\Scripts\python.exe tests/test_widgets.py 2>&1 | tail -20
  Expected: FAIL (widgets may not exist/behave).

- [ ] **Step 2: Implement ProporcionImagen**
  Scale+center preserving aspect ratio.

- [ ] **Step 3: Implement SelectorCuadrado**
  Square selection area as per §6.5.

- [ ] **Step 4: Implement GraficoHistograma + Histograma**
  Use QPainter for bars (no matplotlib). Bars color = tokens.ACENTO.

- [ ] **Step 5: Implement OverlayMarcadores with QGridLayout**
  CRITICAL: put two widgets in SAME cell (not separate cells). Do NOT use resizeEvent/setGeometry to sync. paintEvent must not emit signals; aviso via set_datos().

- [ ] **Step 6: Run widget tests**
  ="offscreen"; & .venv\Scripts\python.exe tests/test_widgets.py
  Expected: PASS.

- [ ] **Step 7: Run overlay tests**
  ="offscreen"; & .venv\Scripts\python.exe tests/test_overlay.py
  Expected: PASS.

- [ ] **Step 8: Commit**
  git add ui/widgets.py
  git commit -m 'feat(ui): implement widgets incl. OverlayMarcadores with QGridLayout (stable)'

---


### Task 9: Ventanas UI (Paso 6 de §0 - en orden)

**Files:**
- Create/Modify: ui/ventana_principal.py, ui/ventana_rgb.py, ui/ventana_ycm.py, ui/ventana_histograma.py, ui/ventana_recorte.py

**Interfaces:**
- Implement screens in order: principal -> RGB -> YCM -> histograma -> recorte. Use Qt Layouts (QGridLayout/QVBoxLayout), no absolute coords. Respect tokens.

- [ ] **Step 1: Implement ventana_principal.py**
  Preprocesado: cargar imagen, modelos GrabCut/OTSU, mostrar resultado. No sobrescribe original.

- [ ] **Step 2: Implement ventana_rgb.py**
  Canales RGB, modos color/blanco y negro.

- [ ] **Step 3: Implement ventana_ycm.py**
  Canales YCM, modos color/blanco y negro.

- [ ] **Step 4: Implement ventana_histograma.py**
  Histograma con sliders, guardar imagen/máscara. Miniaturas y gráfico con proporciones correctas.

- [ ] **Step 5: Implement ventana_recorte.py**
  Recorte/redimensionado, modos A/B, zoom siempre visible (modo A deshabilitado, nunca oculto), factor arranca 1.0, factor_max calculado como especificado.

- [ ] **Step 6: Navigation smoke test**
  Instantiate windows offscreen or navigate without errors.

- [ ] **Step 7: Commit**
  git add ui/ventana*.py
  git commit -m 'feat(ui): implement all windows in order'

---


### Task 10: main.py

**Files:**
- Create/Modify: main.py

**Interfaces:**
- Entry point: crea QApplication, carga styles.qss, muestra ventana principal. No lógica de negocio.

- [ ] **Step 1: Implement main.py**
  Minimal, correct imports. Load QSS from styles.qss.

- [ ] **Step 2: Smoke test launch (offscreen)**
  ="offscreen"; & .venv\Scripts\python.exe -c "from main import main; pass" 2>&1 | tail -15

- [ ] **Step 3: Commit**
  git add main.py
  git commit -m 'feat(app): add main entry point'

---


### Task 11: Verificación completa (Paso 7 de §0) + verification-before-completion

**Files:**
- All implemented files

**Interfaces:**
- Run full suite as specified.

- [ ] **Step 1: Copy/move tests if not done (Task 2)**
  Ensure tests/ contains full suite from temp.

- [ ] **Step 2: Run full suite**
  cd 'C:\Users\santiago\Desktop\unal\vision artificial\trabajo'; ="offscreen"; & .venv\Scripts\python.exe tests\suite.py
  Expected: 0 fallos, sys.exit(0).

- [ ] **Step 3: Verify key static checks**
  Check tokens usage, each token exists. Barras histograma use ACENTO. Overlay uses QGridLayout.

- [ ] **Step 4: Smoke functional checks**
  Quick check core modules importable; ui.widgets instantiable offscreen.

- [ ] **Step 5: Commit final verification state**
  git status; all green.

---


## Execution Handoff

Plan complete and saved to C:\Users\santiago\Desktop\unal\vision artificial\trabajo\docs\superpowers\plans\2026-10-03-analizador-imagenes.md

Please review the plan. Which execution approach would you prefer?

- Subagent-driven - Fresh subagent per task with review between tasks, whole-branch review at end.
- Native - Implement all tasks in this session with verification at each step.

For this plan I recommend Native, because tasks build on core first (recorte must be green before UI) with clear TDD checkpoints and the suite gives strong verification; interfaces are well-defined. Does the plan capture what you want, and which approach should we use?


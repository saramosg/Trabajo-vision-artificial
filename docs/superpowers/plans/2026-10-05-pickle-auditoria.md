# Auditoria pickle vs requisitos.md Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir pickle para cumplir requisitos.md §0-§9 sin regresiones.

**Architecture:** Fixes最小 en `main.py`, `ui/`, `core/` + archivos faltantes (`requirements.txt`); tests con rutas relativas; QScrollArea envolvente; histograma con 2 miniaturas.

**Tech Stack:** Python 3.11.9, PySide6-Essentials, opencv, numpy, pillow, psd-tools.

**Spec:** `C:\Users\santiago\Desktop\unal\vision artificial\pickle\requisitos.md`

## Global Constraints

- Python 3.11.9 fijado; PySide6-Essentials>=6.6,<7; opencv>=4.9; numpy>=1.26; pillow>=10.2; psd-tools>=1.9.
- `ui/` importa de `core/`; `core/` nunca importa de `ui/` ni Qt.
- Salida recorte siempre 512 (`tokens.LADO_SALIDA` unica definicion); sin `redimensionar`/`centralizar`.
- Sin matplotlib; histograma con QPainter.
- `main.py` solo arranca QApplication + QSS + ventana.

## Review Focus

- Imagen 16-bit/alpha/grises abierta con IMREAD_COLOR sin romper histograma 256 bins.
- `x_de_marcador()` igual a `QStyle.subControlRect(SC_SliderHandle)` en 0, intermedios, 255 y sin mutar `slider.value()`.
- `aplicar_recorte(...,1.0)` bit-a-bit igual a `original[y:y+512,x:x+512]` en modo A.
- 300x300 factor 1.0 -> PNG 512 con foto centrada sin `cv2.resize` + bordes blancos.
- QRect vacio -> `recorte=None`, Redimensionar deshabilitado, sin `ValueError`.

---

### Task 1: Archivos faltantes y rutas hardcoded

**Files:**
- Create: `requirements.txt`
- Modify: `tests/suite.py`, `tests/verificar.py`, `tests/test_recorte.py`, `tests/test_widgets.py`, `tests/test_overlay.py`
- Test: `tests/suite.py --rapido`

**Interfaces:**
- Consumes: §3.3 lista dependencias, §10.3 hiddenimports.
- Produces: `requirements.txt` instalable; tests con rutas relativas a `pickle/` (no `trabajo` absoluto).

- [ ] **Step 1: Write the failing test**
```python
def test_requirements_y_rutas_relativas():
    assert Path("requirements.txt").exists()
    txt = Path("requirements.txt").read_text()
    assert "PySide6-Essentials" in txt and "opencv-python" in txt
    for f in ["tests/suite.py","tests/verificar.py"]:
        assert "trabajo" not in Path(f).read_text()
```
- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_rutas.py -v`
Expected: FAIL (no requirements.txt, "trabajo" presente)
- [ ] **Step 3: Implement `requirements.txt` + rutas relativas en `exact/path`**
Crear requirements.txt con §3.3; en tests usar `RAIZ=Path(__file__).parent.parent` + `requisitos.md` relativo; `PY=sys.executable`.
- [ ] **Step 4: Run test to verify it passes**
Run: `python tests/suite.py --rapido`
Expected: PASS
- [ ] **Step 5: Commit**
```bash
git add requirements.txt tests/
git commit -m "fix: requirements y rutas relativas"
```

### Task 2: `main.py` QSS robusto §8 regla 1

**Files:**
- Modify: `main.py`
- Test: arranque offscreen + exe-sim (cwd distinto)

**Interfaces:**
- Consumes: `styles.qss`, `tokens.VENTANA_*`.
- Produces: `main() -> int` con `BASE=Path(getattr(sys,"_MEIPASS",Path(__file__).parent))`.

- [ ] **Step 1: Write the failing test**
```python
def test_qss_por_ruta_resuelta():
    src = Path("main.py").read_text()
    assert "_MEIPASS" in src and "FileNotFoundError" in src
```
- [ ] **Step 2: Run test to verify it fails**
Run: `pytest tests/test_main_qss.py -v`
Expected: FAIL (main.py usa `os.path.join(dirname)` sin _MEIPASS)
- [ ] **Step 3: Implement `main()` en `main.py` con Path + _MEIPASS + exists check**
- [ ] **Step 4: Run test to verify it passes**
Run: `QT_QPA_PLATFORM=offscreen python -c "import main; print('import OK')"`
Expected: PASS
- [ ] **Step 5: Commit**

### Task 3: Histograma 2 miniaturas + sliders 44px §6.4

**Files:**
- Modify: `ui/ventana_histograma.py`
- Test: offscreen instanciacion + refrescar

**Interfaces:**
- Consumes: `core.canales.aplicar_modo`, `core.histograma`, `tokens.RAZON_HISTO_IMG`.
- Produces: `mini_canal2` (siguiente canal), sliders `setFixedHeight(44)`.

- [ ] **Step 1: Write the failing test**
```python
def test_histograma_dos_miniaturas():
    v = VentanaHistograma(ventana_fake)
    assert hasattr(v, "mini_canal2")
    assert v.slider_inf.minimumHeight() >= 44 or v.slider_inf.height() == 44
```
- [ ] **Step 2: Run test to verify it fails**
Expected: FAIL (solo `mini_canal`)
- [ ] **Step 3: Implement `mini_canal2` + rotacion `letras[(i+1)%3]` + `setFixedHeight(44)`**
Mostrar canal activo + siguiente; rotar actualiza ambas; etiqueta `etiqueta_canal`.
- [ ] **Step 4: Run test to verify it passes**
Run: `QT_QPA_PLATFORM=offscreen pytest tests/test_hist.py -v`
Expected: PASS
- [ ] **Step 5: Commit**

### Task 4: QScrollArea + margen dinamico §5.3/§5.4/§6.0

**Files:**
- Modify: `ui/ventana_principal.py`, `ui/ventana_canales.py`, `ui/ventana_histograma.py`, `ui/ventana_recorte.py`
- Test: resize 1000x560 sin corte

**Interfaces:**
- Consumes: `tokens.MARGEN`, `tokens.ANCHO_CONTENIDO`.
- Produces: cada pantalla envuelta en `QScrollArea(widgetResizable=True)`; helper `margen_dinamico(width)`.

- [ ] **Step 1: Write the failing test**
```python
def test_scrollarea_presente():
    for cls in [PantallaPreprocesado, VentanaCanales, VentanaHistograma, VentanaRecorte]:
        assert "QScrollArea" in Path(inspect.getfile(cls)).read_text()
```
- [ ] **Step 2: Run test to verify it fails**
Expected: FAIL (0 QScrollArea en ui/)
- [ ] **Step 3: Implement scroll wrapper + `margen=max(MARGEN,(w-ANCHO_CONTENIDO)//2)`**
No `move()/setGeometry()`; botones `setFixedSize`, lienzos `Expanding`.
- [ ] **Step 4: Run test to verify it passes**
Run: offscreen resize + `grab()` sin excepcion
Expected: PASS
- [ ] **Step 5: Commit**

### Task 5: Robustez `ProporcionImagen` + `VentanaRecorte` regla 12/13

**Files:**
- Modify: `ui/widgets.py`, `ui/ventana_recorte.py`
- Test: `tests/test_widgets.py`, `tests/test_recorte.py`

**Interfaces:**
- Consumes: `tokens.LADO_SALIDA`, `core.recorte.aplicar_recorte`.
- Produces: `_recalcular()` con guard division-cero; `al_cambiar_zoom` invalida explicito + `addSpacing(ESPACIO_GRUPO)`.

- [ ] **Step 1: Write the failing test**
```python
def test_proporcion_sin_dividir_por_cero():
    w = ProporcionImagen((300,300),(300,300))
    w.resize(0,0); w.set_imagen(QPixmap(100,100)); assert True
```
- [ ] **Step 2: Run test to verify it fails**
Expected: FAIL o ZeroDivision (width 0)
- [ ] **Step 3: Implement guards + `self.estado.invalidar_vista_previa()` en `al_cambiar_zoom`**
- [ ] **Step 4: Run test to verify it passes**
Run: `python tests/test_recorte.py` + `python tests/test_widgets.py`
Expected: PASS
- [ ] **Step 5: Commit**

# Histograma B/N + contorno fino Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Histograma siempre en blanco y negro, sin panel canal-siguiente, contorno fino sin relleno y barras de histograma continuas.

**Architecture:** Cambios mínimos en `ui/ventana_histograma.py`, `core/segmentacion.py` y `ui/widgets.py`; referencias Tarea 1 (hist + `findContours`/`drawContours`) y Tarea 7 (Canny 1px).

**Tech Stack:** Python 3.11.9, PySide6-Essentials, opencv, numpy.

**Spec:** `C:\Users\santiago\Desktop\unal\vision artificial\pickle\requisitos.md` + usuario (prevalece sobre spec en modo de entrada).

## Global Constraints

- `core/` nunca importa Qt; `ui/` importa de `core/`.
- Salida recorte siempre 512; sin `redimensionar`/`centralizar`.
- Sin matplotlib; histograma con QPainter.

## Review Focus

- Entrar a histograma con `modo=color` debe forzar `blanco y negro` sin romper RGB/YCM.
- Sin `mini_canal2` no debe quedar layout roto ni referencia colgada en `refrescar`.
- `contorno()` sobre máscara vacía/llena no debe lanzar ni rellenar.
- Barras deben llenar todo el ancho y la última llegar al borde derecho.
- Sliders/extremos `inf=0/sup=255` siguen alineados con `x_de_marcador()`.

---

### Task 1: Entrada siempre en blanco y negro

**Files:**
- Modify: `ui/ventana_histograma.py:150-162` (`al_entrar`)
- Test: offscreen `al_entrar` con `modo=color`

**Interfaces:**
- Consumes: `EstadoImagen.modo`
- Produces: `estado.modo == "blanco y negro"` al entrar; minis en gris 2D.

- [ ] **Step 1: Write the failing test**
```python
def test_histograma_fuerza_byn():
    estado.modo = "color"
    ventana.mostrar("histograma")
    assert estado.modo == "blanco y negro"
```
- [ ] **Step 2: Run test to verify it fails**
Run: `QT_QPA_PLATFORM=offscreen python tests/test_hist_modo.py -v`
Expected: FAIL (`modo` sigue `color`)
- [ ] **Step 3: Implement en `al_entrar`: `self.estado.modo = "blanco y negro"` antes de `refrescar()`**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

### Task 2: Quitar panel canal siguiente

**Files:**
- Modify: `ui/ventana_histograma.py:56-79` (creación+layout), `:186-192` (`refrescar`)
- Test: `not hasattr(v, "mini_canal2")`, 3 miniaturas, sin `NameError`

**Interfaces:**
- Consumes: `canales.aplicar_modo`
- Produces: solo `mini_original`, `mini_canal`, `mini_contorno`.

- [ ] **Step 1: Write the failing test**
```python
def test_sin_canal_siguiente():
    assert not hasattr(v, "mini_canal2")
    assert "mini_canal2" not in Path("ui/ventana_histograma.py").read_text()
```
- [ ] **Step 2: Run test to verify it fails** (existe `mini_canal2`)
- [ ] **Step 3: Implement: borrar creación, layout y bloque `siguiente` en `refrescar`; contorno a fila 2**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

### Task 3: Contorno fino sin relleno (Tarea 1 + Tarea 7)

**Files:**
- Modify: `core/segmentacion.py:75-90` (`contorno`)
- Test: `tests/test_contorno.py` + existentes

**Interfaces:**
- Consumes: `mascara` uint8 0/255
- Produces: `uint8` 0/255, solo borde 1px (`RETR_EXTERNAL`, `thickness=1`), nunca relleno.

- [ ] **Step 1: Write the failing test**
```python
def test_contorno_fino_sin_relleno():
    c = contorno(mascara_con_cuadrado_100x100)
    assert c.max() == 255 and 0 < c.sum() // 255 < 100*100  # borde, no sólido
    assert set(np.unique(c)) <= {0, 255}
```
- [ ] **Step 2: Run test to verify it fails** (grosor adaptativo pinta franja gruesa)
- [ ] **Step 3: Implement `thickness=1`, `RETR_EXTERNAL`; docstring Tarea 1/Tarea 7**
- [ ] **Step 4: Run test to verify it passes** + `test_recorte.py`
- [ ] **Step 5: Commit**

### Task 4: Histograma continuo ancho completo (Tarea 1 `plt.hist(...,256)`)

**Files:**
- Modify: `ui/widgets.py:164-182` (`GraficoHistograma.paintEvent`)
- Test: offscreen píxeles ACENTO cubren de `left` a `right`

**Interfaces:**
- Consumes: `bins[256]`, `inf/sup`
- Produces: 256 barras contiguas que llenan `area_grafico`.

- [ ] **Step 1: Write the failing test**
```python
def test_barras_llenan_ancho():
    # con area 459px y bins llenos, hay píxeles ACENTO cerca del borde derecho
    assert px_acento_en_tercio_derecho > 0
```
- [ ] **Step 2: Run test to verify it fails** (barras comprimidas a la izquierda)
- [ ] **Step 3: Implement ancho float `area.width()/256`, `x=left+round(i*w)`, `w=round((i+1)*w)-round(i*w)`**
- [ ] **Step 4: Run test to verify it passes** + suite doc-based intacta
- [ ] **Step 5: Commit**

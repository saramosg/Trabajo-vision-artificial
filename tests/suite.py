"""Suite completa de verificacion de requisitos.md.

1) Coherencia estatica del documento (tokens, sintaxis, QSS, firmas).
2) Ejecucion real de core/recorte.py con NumPy + OpenCV.
3) Ejecucion real de los widgets de PySide6 (offscreen), extrayendolos del doc.
4) El overlay de marcadores, comparado contra la referencia real de Qt.
5) Boton de modo de la pantalla de histograma (offscreen).
6) core/bordes.py: deteccion (canny/sobel/laplaciano) y relleno barrera.
7) Relleno por clics sobre el mapa de bordes (offscreen).

Uso:  python suite.py            (las 7)
      python suite.py --rapido   (1, 2 y 6, sin Qt)
"""

import sys, io, os, subprocess, re

RAIZ = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
TODAS = [
    ("1) Coherencia del documento", "verificar.py"),
    ("2) core/recorte.py (NumPy + OpenCV)", "test_recorte.py"),
    ("3) Widgets PySide6 (offscreen)", "test_widgets.py"),
    ("4) Overlay de marcadores vs Qt", "test_overlay.py"),
    ("5) Boton de modo de la pantalla de histograma (offscreen)", "test_boton_modo.py"),
    ("6) Bordes: canny/sobel/laplaciano + relleno (NumPy + OpenCV)", "test_bordes.py"),
    ("7) Relleno por clics del histograma (offscreen)", "test_relleno.py"),
    ("8) Pantalla de recorte: scroll y atajos (offscreen)", "test_recorte_ui.py"),
]

# El reporte se lee en la consola del evaluador: los acentos tienen que
# salir bien (la consola de Windows usa cp1252).
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - si no hay buffer, se deja como esta
    pass

SUITES = list(TODAS)
rapido = "--rapido" in sys.argv
if rapido:
    SUITES = [s for s in SUITES if s[0].startswith(("1)", "2)", "6)"))]

# Ningun test puede quedarse fuera de la suite: un test huerfano es un
# test que nadie ejecuta (y por tanto que nadie puede hacer fallar).
huerfanos = sorted(
    f
    for f in os.listdir(RAIZ)
    if f.startswith("test_") and f.endswith(".py") and f not in {s for _, s in TODAS}
)


print("#" * 66)
print("#  VERIFICACION DE requisitos.md")
print("#" * 66)
resultados = []
for nombre, script in SUITES:
    print(f"\n{'=' * 66}\n>>> {nombre}\n{'=' * 66}")
    sys.stdout.flush()
    p = subprocess.run(
        [PY, os.path.join(RAIZ, script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    # el doc imprime en UTF-8; filtrar ruido de PowerShell
    salida = p.stdout
    for linea in salida.splitlines():
        if (
            re.match(r"^\s*(OK|FALLA|===|RESULTADO|\[\d)", linea)
            or "fallo" in linea.lower()
        ):
            print(linea)
    m = re.search(r"RESULTADO: (\d+) fallo", salida)
    n = int(m.group(1)) if m else -1
    if n != 0:
        errores = [
            l
            for l in p.stderr.splitlines()
            if l.strip() and "Traceback" in l or l.startswith("  File")
        ]
        for l in errores[:12]:
            print(l)
        print(p.stderr[-900:] if p.stderr else "")
    resultados.append((nombre, n))

print(f"\n{'#' * 66}\n#  RESUMEN\n{'#' * 66}")
for nombre, n in resultados:
    if n == 0:
        detalle = ""
    elif n < 0:
        detalle = "  (ERROR: la suite no llego a imprimir RESULTADO:)"
    else:
        detalle = f"  ({n})"
    print(f"  {'PASA' if n == 0 else 'FALLA':5}  {nombre}{detalle}")

fallos = sum(n for _, n in resultados if n > 0)
errores = sum(1 for _, n in resultados if n < 0)
if huerfanos:
    print(
        f"  FALLA  Tests fuera de la suite (nadie los ejecuta): " + ", ".join(huerfanos)
    )
    errores += len(huerfanos)

if fallos == 0 and errores == 0:
    print("\n  TODO VERIFICADO, 0 fallos")
else:
    partes = []
    if fallos:
        partes.append(f"{fallos} FALLO(S) EN TOTAL")
    if errores:
        partes.append(f"{errores} SUITE(S) CON EXCEPCION")
    print("\n  " + " | ".join(partes))
# Sin esto la suite devuelve 0 aunque falle, y un fallo se camufla de verde:
# el que la ejecuta (o el agente que la lanza) solo ve EXIT=0.
sys.exit(1 if (fallos or errores) else 0)

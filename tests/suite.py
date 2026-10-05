"""Suite completa de verificacion de requisitos.md.

1) Coherencia estatica del documento (tokens, sintaxis, QSS, firmas).
2) Ejecucion real de core/recorte.py con NumPy + OpenCV.
3) Ejecucion real de los widgets de PySide6 (offscreen), extrayendolos del doc.
4) El overlay de marcadores, comparado contra la referencia real de Qt.

Uso:  python suite.py            (las 4)
      python suite.py --rapido   (solo 1 y 2, sin Qt)
"""
import sys, io, os, subprocess, re

RAIZ = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
SUITES = [("1) Coherencia del documento", "verificar.py"),
          ("2) core/recorte.py (NumPy + OpenCV)", "test_recorte.py"),
          ("3) Widgets PySide6 (offscreen)", "test_widgets.py"),
          ("4) Overlay de marcadores vs Qt", "test_overlay.py")]

rapido = "--rapido" in sys.argv
if rapido:
    SUITES = [s for s in SUITES if s[0].startswith(("1)", "2)"))]

print("#" * 66)
print("#  VERIFICACION DE requisitos.md")
print("#" * 66)
resultados = []
for nombre, script in SUITES:
    print(f"\n{'=' * 66}\n>>> {nombre}\n{'=' * 66}")
    sys.stdout.flush()
    p = subprocess.run([PY, os.path.join(RAIZ, script)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    # el doc imprime en UTF-8; filtrar ruido de PowerShell
    salida = p.stdout
    for linea in salida.splitlines():
        if re.match(r"^\s*(OK|FALLA|===|RESULTADO|\[\d)", linea) or "fallo" in linea.lower():
            print(linea)
    m = re.search(r"RESULTADO: (\d+) fallo", salida)
    n = int(m.group(1)) if m else -1
    if n != 0:
        errores = [l for l in p.stderr.splitlines() if l.strip() and "Traceback" in l or l.startswith("  File")]
        for l in errores[:12]:
            print(l)
        print(p.stderr[-900:] if p.stderr else "")
    resultados.append((nombre, n))

print(f"\n{'#' * 66}\n#  RESUMEN\n{'#' * 66}")
for nombre, n in resultados:
    print(f"  {'PASA' if n == 0 else 'FALLA':5}  {nombre}" + ("" if n == 0 else f"  ({n})"))
total = sum(n for _, n in resultados if n > 0)
print(f"\n  {'TODO VERIFICADO, 0 fallos' if total == 0 else f'{total} FALLO(S) EN TOTAL'}")
# Sin esto la suite devuelve 0 aunque falle, y un fallo se camufla de verde:
# el que la ejecuta (o el agente que la lanza) solo ve EXIT=0.
sys.exit(1 if total else 0)

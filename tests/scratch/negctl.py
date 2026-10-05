import subprocess, sys, pathlib, re

D = pathlib.Path(r"C:\Users\santiago\Desktop\unal\vision artificial\trabajo\requisitos.md")
ORIG = D.read_text(encoding="utf-8")
ARBOL_RE = re.compile(r"### 4\.1 Archivos.*?```\n(.*?)```", re.S)


def correr():
    r = subprocess.run([sys.executable, "verificar.py"], capture_output=True, text=True)
    return r.returncode, [l.strip()[:115] for l in r.stdout.splitlines() if "FALLA" in l]


arbol = ARBOL_RE.search(ORIG).group(1)

casos = [
    ("main.spec -> main.specX", "main.spec", "main.specX"),
    ("assets -> icons",        "assets/",  "icons/"),
    ("styles.qss -> theme.qss", "styles.qss", "theme.qss"),
    ("widget fuera de 4.1",    "SelectorCuadrado (", "XXX ("),
]

print("estado real ->", correr())
try:
    for nombre, viejo, nuevo in casos:
        assert viejo in arbol, f"no aparece en el arbol: {viejo!r}"
        mutado = ARBOL_RE.sub(lambda m: m.group(0).replace(viejo, nuevo, 1), ORIG, count=1)
        D.write_text(mutado, encoding="utf-8")
        code, fallos = correr()
        print(f"{nombre:24} EXIT {code}  " + (fallos[0] if fallos else "<-- NO MUERDE"))
finally:
    D.write_text(ORIG, encoding="utf-8")
    print("restaurado ->", correr())
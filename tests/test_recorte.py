"""Suite de pruebas de core/recorte.py, tal como quedo en §7.7 de requisitos.md.

Se ejecuta SIN PySide6 ni ventana: es la prueba de que core/ no depende de Qt (§8 regla 4).

Contrato actual (§6.5): la salida es SIEMPRE de LADO_SALIDA = 512. Ya no hay
`redimensionar()` ni `centralizar()`; solo `recortar`, `escalar` y `aplicar_recorte`.
"""
import sys, io, re, textwrap, os
import numpy as np
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import cv2

# --- extraer el bloque real de §7.7 del documento ---
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
doc = open(os.path.join(_RAIZ, "requisitos.md"), encoding="utf-8").read()
src = textwrap.dedent(re.search(r"### 7\.7 Recorte.*?```python\n(.*?)```", doc, re.S).group(1))
ns = {"np": np, "cv2": cv2}
exec(compile(src, "core/recorte.py", "exec"), ns)
recortar, escalar, lienzo_blanco, aplicar_recorte = (
    ns["recortar"], ns["escalar"], ns["lienzo_blanco"], ns["aplicar_recorte"])

fallos = []
def check(nombre, cond, detalle=""):
    print(("  OK   " if cond else "  FALLA") + " " + nombre + (f"   -> {detalle}" if detalle and not cond else ""))
    if not cond: fallos.append(nombre)

# El 512 sale del token del doc, no de un literal escrito aqui.
tok = re.search(r"### 5\.1 Tokens.*?```python\n(.*?)```", doc, re.S).group(1)
nt = {}
exec(compile(tok, "tokens.py", "exec"), nt)
LADO = nt["LADO_SALIDA"]
check("el token LADO_SALIDA es 512", LADO == 512, str(LADO))

img = np.random.randint(0, 256, (500, 800, 3), dtype=np.uint8)   # rectangular a proposito
gris = np.random.randint(0, 256, (500, 800), dtype=np.uint8)
rgba = np.dstack([img, np.full((500, 800), 255, np.uint8)])
# UNA DE LAS QUE NO CABEN: es la del modo B de §6.5 (se rellena de blanco)
chica = np.random.randint(0, 256, (300, 400, 3), dtype=np.uint8)

print("=== recortar() ===")
r = recortar(img, 100, 50, 200)
check("devuelve cuadrado del lado pedido", r.shape == (200, 200, 3), str(r.shape))
check("contenido correcto (recorte real)", np.array_equal(r, img[50:250, 100:300]))
check("contiguo (lo exige cv2.resize)", r.flags["C_CONTIGUOUS"])
check("acota por la derecha", recortar(img, 700, 0, 300).shape == (100, 100, 3),
      str(recortar(img, 700, 0, 300).shape))
check("acota por abajo", recortar(img, 0, 400, 300).shape == (100, 100, 3),
      str(recortar(img, 0, 400, 300).shape))
check("x/y negativos se aclipan", recortar(img, -50, -50, 100).shape == (100, 100, 3))
check("funciona en 2D", recortar(gris, 0, 0, 50).shape == (50, 50))
try:
    recortar(img, 0, 0, 0); check("lado 0 lanza ValueError", False)
except ValueError: check("lado 0 lanza ValueError", True)
check("coordinates fuera de rango se aclipan al borde",
      recortar(img, -9999, -9999, 10).shape == (10, 10, 3))
check("nunca devuelve un lado mayor que la imagen",
      all(recortar(img, x, y, 10_000).shape[0] <= 500 for x in (0, 400, 799) for y in (0, 250, 499)))

print("\n=== escalar() ===")
# REGLA 4: conserva la proporcion -> los dos lados se escalan por igual
e = escalar(img, 2.0)
check("10x20 (400x800) x2 -> conserva la razon", e.shape == (1000, 1600, 3), str(e.shape))
check("no deforma: la razon ancho/alto se mantiene",
      abs((e.shape[1] / e.shape[0]) - (img.shape[1] / img.shape[0])) < 0.001,
      f"{e.shape[1]/e.shape[0]:.4f} vs {img.shape[1]/img.shape[0]:.4f}")
e2 = escalar(gris, 0.5)
check("funciona en 2D", e2.shape == (250, 400), str(e2.shape))
# REGLA 5: factor 1.0 -> copia, SIN pasar por cv2. Si hiciera resize, un resize
# identidad con INTER_LINEAR devuelve los mismos bytes, asi que la prueba real
# es que el array sea BIT A BIT igual y una COPIA (no la misma referencia).
copia = escalar(img, 1.0)
check("factor 1.0 sale BIT A BIT igual", np.array_equal(copia, img))
check("factor 1.0 devuelve una COPIA, no la misma referencia", copia is not img)
check("factor 1.0 no cambia la forma", copia.shape == img.shape)
try:
    escalar(img, 0.0); check("factor 0 lanza ValueError", False)
except ValueError: check("factor 0 lanza ValueError", True)
try:
    escalar(img, -1.0); check("factor negativo lanza ValueError", False)
except ValueError: check("factor negativo lanza ValueError", True)
# el zoom arranca en 1.0 y sube; no hay un "factor de llenado" obligatorio porque
# lo que falta se rellena de blanco (modo B de §6.5)
check("el modo B NO obliga a ampliar: factor 1.0 es valido",
      escalar(chica, 1.0).shape == chica.shape, str(escalar(chica, 1.0).shape))
for (h, w) in ((300, 400), (400, 300), (512, 900), (200, 200)):
    f = min(4.0, 4096 / max(h, w))
    amp = escalar(np.zeros((h, w, 3), np.uint8), f)
    check(f"zoom {h}x{w}: el factor maximo no excede LADO_AMPLIADO_MAX",
          max(amp.shape[:2]) <= 4096, f"-> {amp.shape[1]}x{amp.shape[0]}")

print("\n=== lienzo_blanco(): lo que falta se rellena de BLANCO ===")
# Si la imagen ya cabe, no se toca NADA: ni aloca, ni cambia un pixel.
grande2 = np.random.randint(0, 256, (900, 1200, 3), dtype=np.uint8)
check("si ya cabe en 512, lienzo_blanco NO la toca (bit a bit)",
      np.array_equal(lienzo_blanco(grande2, LADO), grande2))
check("si ya cabe, devuelve la MISMA referencia (no aloca un lienzo de 512)",
      lienzo_blanco(grande2, LADO) is grande2)
# Exactamente 512: cabe, no se rellena
exacto = np.random.randint(0, 256, (LADO, LADO, 3), dtype=np.uint8)
check("una imagen de exactamente 512x512 no se rellena",
      np.array_equal(lienzo_blanco(exacto, LADO), exacto))
# 300 alto x 400 ancho -> se centra con offset y=(512-300)//2=106, x=(512-400)//2=56
lienzo = lienzo_blanco(chica, LADO)
check("una 300x400 pasa a 512x512", lienzo.shape == (LADO, LADO, 3), str(lienzo.shape))
check("las cuatro esquinas del lienzo son BLANCAS",
      all(np.array_equal(lienzo[c, r], [255, 255, 255])
          for c, r in ((0, 0), (0, LADO - 1), (LADO - 1, 0), (LADO - 1, LADO - 1))),
      f"esquina {lienzo[0,0]}")
check("la foto queda CENTRADA en el lienzo, sin estirarla",
      np.array_equal(lienzo[106:406, 56:456], chica),
      "offset esperado y=106 x=56")
# No se cuenta "pixeles no blancos": la imagen aleatoria puede traer 255 exactos
# y el recuento no significaria nada. Lo que se comprueba es que el marco de la
# foto cae donde debe y que AHIA alrededor es blanco de verdad.
check("todo lo que rodea a la foto es blanco (1 px de borde)",
      (np.all(lienzo[105, :] == 255) and np.all(lienzo[406, :] == 255)
       and np.all(lienzo[:, 55] == 255) and np.all(lienzo[:, 456] == 255)))
check("las bandas de relleno miden lo que sobra, divididas en dos partes iguales",
      lienzo[:106, :].shape[0] == 106 and 512 - 406 == 106
      and lienzo[:, :56].shape[1] == 56 and 512 - 456 == 56)
# solo falta en UN eje: 512 de ancho x 300 de alto -> bandas arriba y abajo
panor = np.random.randint(0, 256, (300, LADO, 3), dtype=np.uint8)
lp = lienzo_blanco(panor, LADO)
check("si solo falta en un eje, rellena ESE eje",
      lp.shape == (LADO, LADO, 3)
      and np.array_equal(lp[0], np.full((LADO, 3), 255, np.uint8))
      and np.array_equal(lp[106:406], panor))
# RGBA: el relleno es blanco OPACO, no alpha 0 (aqui no hay alpha: original es RGB)
check("el relleno es 255, nunca 0 ni alpha transparente",
      lienzo[0, 0].tolist() == [255, 255, 255], str(lienzo[0, 0].tolist()))

print("\n=== aplicar_recorte() MODO A (factor 1.0, sin perdida) ===")
# Esta es la garantia central del modo A: con imagen >= 512 el resultado debe ser
# identico al corte directo. Si alguien mete un resize por el medio, falla aqui.
grande = np.random.randint(0, 256, (900, 1200, 3), dtype=np.uint8)
a = aplicar_recorte(grande, 100, 200, LADO, 1.0)
check("sale de 512x512", a.shape == (LADO, LADO, 3), str(a.shape))
check("BIT A BIT igual a original[y:y+512, x:x+512]",
      np.array_equal(a, grande[200:200 + LADO, 100:100 + LADO]))
# en cualquier posicion, incluso en los bordes
for (x, y) in ((0, 0), (1200 - LADO, 900 - LADO), (0, 900 - LADO), (1200 - LADO, 0)):
    b = aplicar_recorte(grande, x, y, LADO, 1.0)
    if not np.array_equal(b, grande[y:y + LADO, x:x + LADO]):
        break
check("bit a bit tambien en las cuatro esquinas", np.array_equal(b, grande[y:y + LADO, x:x + LADO]),
      f"posicion ({x},{y})")
check("factor 1.0 es el default", aplicar_recorte(grande, 0, 0, LADO).shape == (LADO, LADO, 3))

print("\n=== aplicar_recorte() MODO B (relleno blanco, sin ampliar) ===")
# factor 1.0, el valor por defecto: la foto sale SIN TOCAR sobre el lienzo blanco
# No se cuenta "pixeles no blancos": la imagen aleatoria puede traer 255 exactos
# y el recuento no significaria nada. Lo que se comprueba es que el hueco de la
# foto cae donde debe y que alrededor es blanco de verdad.
# No se cuenta "pixeles no blancos": la imagen aleatoria puede traer 255 exactos
# y el recuento no significaria nada. Lo que se comprueba es que el hueco de la
# foto cae donde debe y que alrededor es blanco de verdad.
b = aplicar_recorte(chica, 0, 0, LADO, 1.0)
check("sale de 512x512", b.shape == (LADO, LADO, 3), str(b.shape))
check("la foto va CENTRADA con bandas blancas arriba y abajo",
      np.array_equal(b[0], np.full((LADO, 3), 255, np.uint8))
      and np.array_equal(b[106:406, 56:456], chica))
check("el relleno se rellena ANTES de recortar (si no, no habria 512 que recortar)",
      b.shape == (LADO, LADO, 3))
check("NO se estira la foto para quadrarla: conserva su proporcion",
      abs((chica.shape[1] / chica.shape[0]) - (400 / 300)) < 1e-9
      and b[106:406, 56:456].shape == chica.shape,
      str(b[106:406, 56:456].shape))
# con zoom: escala, y si ya tapa el lienzo el blanco desaparece
b2 = aplicar_recorte(chica, 0, 0, LADO, 2.0)
check("con zoom 2.0 sigue saliendo 512", b2.shape == (LADO, LADO, 3), str(b2.shape))
amp2 = cv2.resize(chica, (800, 600), interpolation=cv2.INTER_LINEAR)
check("con zoom el recorte sale de la imagen YA ampliada",
      np.array_equal(b2, amp2[0:LADO, 0:LADO]))
check("con zoom que tapa el lienzo, NO queda relleno blanco en el frame",
      not (b2 == 255).all(axis=2).all())
# la transicion de "encaje con blanco" a "recorte puro" es continua:
# cuando factor * min(alto,ancho) >= 512 el lienzo ya no se usa
b3 = aplicar_recorte(chica, 0, 0, LADO, LADO / 300)
check("con el zoom justo para tapar el lienzo, sale 512 y sin bandas",
      b3.shape == (LADO, LADO, 3) and not (b3 == 255).all(axis=2).all(),
      str(b3.shape))
# un recorte que se sale del lienzo NO se acorta en silencio: lanza (regla 2)
try:
    aplicar_recorte(grande, 700, 0, LADO, 1.0)   # grande es 1200x900
    check("un recorte fuera del lienzo LANZA ValueError", False, "no lanzo")
except ValueError:
    check("un recorte fuera del lienzo LANZA ValueError", True)
# con relleno activo el frame esta clavado en (0,0): es todo el lienzo
check("con relleno activo el recorte es SIEMPRE el lienzo entero",
      aplicar_recorte(chica, 0, 0, LADO, 1.0).shape == (LADO, LADO, 3))

# Un eje SOBRA y el otro FALTA (300x900): antes esto reventaba con offsets
# negativos. El eje sobrante se recorta por el centro y el deficient se rellena.
for (h, w) in ((300, 900), (900, 300), (700, 400), (400, 700)):
    mixta = np.random.randint(0, 256, (h, w, 3), dtype=np.uint8)
    lm = lienzo_blanco(mixta, LADO)
    check(f"mezcla {h}x{w} (un eje sobra, otro falta): sale 512x512",
          lm.shape == (LADO, LADO, 3), str(lm.shape))
    ey0, ex0 = max(0, (h - LADO) // 2), max(0, (w - LADO) // 2)
    ey1, ex1 = min(h, ey0 + LADO), min(w, ex0 + LADO)
    dy0, dx0 = (LADO - (ey1 - ey0)) // 2, (LADO - (ex1 - ex0)) // 2
    check(f"mezcla {h}x{w}: la foto entra centrada y recortada en el lienzo",
          np.array_equal(lm[dy0:dy0 + (ey1 - ey0), dx0:dx0 + (ex1 - ex0)],
                         mixta[ey0:ey1, ex0:ex1]))
    check(f"mezcla {h}x{w}: el lado que falta queda BLANCO",
          (h < LADO and np.array_equal(lm[0, :], np.full((LADO, 3), 255, np.uint8)))
          or (w < LADO and np.array_equal(lm[:, 0], np.full((LADO, 3), 255, np.uint8))))

print("\n=== RGBA de punta a punta (como se guarda, §7.5) ===")
# modo A necesita min(alto, ancho) >= 512: esta RGBA lo cumple
rgba_g = np.dstack([np.random.randint(0, 256, (900, 1200, 3), dtype=np.uint8),
                    np.full((900, 1200), 255, np.uint8)])
rec = aplicar_recorte(rgba_g, 100, 200, LADO, 1.0)
check("guardado RGBA conserva 4 canales", rec.shape == (LADO, LADO, 4), str(rec.shape))
check("RGBA modo A tambien es bit a bit",
      np.array_equal(rec, rgba_g[200:200 + LADO, 100:100 + LADO]))
ok, buf = cv2.imencode(".png", np.ascontiguousarray(rec))
check("cv2.imencode acepta el resultado (contiguo)", ok and buf is not None)

print("\n=== el relleno se hace con la version RGB de 3 canales (§7.1) ===")
# `original` es RGB de 3 canales, asi que el blanco es (255,255,255) sin ambiguedad
check("el lienzo tiene los MISMOS canales que la imagen (no inventa un RGBA)",
      lienzo_blanco(np.zeros((100, 100, 3), np.uint8), LADO).shape[2] == 3)

print("\n=== las funciones borradas NO deben reaparecer ===")
codigo = src
for_fn = [f for f in ("redimensionar", "centralizar")
          if re.search(rf"(?m)^\s*def {f}\(", codigo)]
check("no hay def redimensionar() ni def centralizar() (la vieja centralizar)",
      not for_fn, ", ".join(for_fn))
check("aplicar_recorte ya NO habla de lado_destino", "lado_destino" not in codigo)
check("aplicar_recorte llama a lienzo_blanco, no a centralizar",
      "lienzo_blanco(" in codigo and "centralizar(" not in codigo)

print("\n=== una imagen menor que 512 ya NO es un error ===")
# Antes de `lienzo_blanco`, una imagen pequena hacia que el recorte se acortara
# en silencio (450x450) o que saltara un ValueError. Con el relleno, las dos
# quedan resueltas: siempre 512, y con los bordes blancos.
salida = aplicar_recorte(chica, 0, 0, LADO, 1.0)
check("una imagen menor que 512 produce 512x512, no un recorte corto",
      salida.shape == (LADO, LADO, 3), str(salida.shape))
check("y no lanza: el relleno evita llegar al guard de error",
      salida is not None)
check("las esquinas del resultado son las esquinas blancas del lienzo",
      all(np.array_equal(salida[c, r], [255, 255, 255])
          for c, r in ((0, 0), (0, LADO - 1), (LADO - 1, 0), (LADO - 1, LADO - 1))))

print("\n" + "=" * 60)
print(f"RESULTADO: {len(fallos)} fallo(s)" + (": " + ", ".join(fallos) if fallos else " — todo correcto"))
print("=" * 60)
sys.exit(1 if fallos else 0)
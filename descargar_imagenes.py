"""Descarga 150 imagenes uniformes por tema para el dataset del reto.

Fuente: Wikimedia Commons (API sin credenciales, licencias libres con
atribucion). Cada imagen queda en `imagenes/<tema>/NNN.jpg` + `manifest.csv`
con fuente, autor y licencia (base para documentar el dataset del reto 2).

Temas por defecto: 10 especies de `frutas/` x 15 c/u = 150. Cada tema mezcla
consultas normales y de alteracion ("rotten", "moldy") para que el etiquetado
posterior (sana vs alterada) tenga de ambos. Para otro reparto, edita TOPICS
y CUOTA (o pasa --total).

Uso:
    python descargar_imagenes.py                  # 150 imagenes (15 x tema)
    python descargar_imagenes.py --total 60       # 6 x tema
    python descargar_imagenes.py --max 300        # tope de seguridad

Solo libreria estandar + Pillow. Respeta el tope de 300 descargas.
"""
import argparse
import csv
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

BASE = Path(__file__).resolve().parent
DESTINO = BASE / "imagenes"
UA = {"User-Agent": "UNAL-vision-retos/1.0 (dataset academico curso vision)"}
API = "https://commons.wikimedia.org/w/api.php"
PAUSA = 1.5  # segundos entre peticiones (cortesia con la API)
ESPERA_429 = 20  # reintentos ante rate limit de Wikimedia

# tema: lista de (consulta, estado). La cuota se reparte por ESTADO, no por
# consulta: si no, la primera consulta se come todo el cupo y el tema queda
# 100 % sano (fue el bug de la primera version).
TOPICS = {
    "manzana": [("apple fruit", "sana"),
                ("rotten apple", "alterada"),
                ("apple scab disease", "alterada")],
    "banano": [("banana fruit", "sana"),
               ("rotten banana", "alterada"),
               ("banana black sigatoka", "alterada")],
    "cereza": [("cherry fruit", "sana"),
               ("rotten cherries", "alterada"),
               ("cherry brown rot", "alterada")],
    "uva": [("grape fruit", "sana"),
            ("rotten grapes", "alterada"),
            ("grape botrytis", "alterada")],
    "limon": [("lemon fruit", "sana"),
              ("rotten lemon", "alterada"),
              ("lemon mold", "alterada")],
    "mango": [("mango fruit", "sana"),
              ("rotten mango", "alterada"),
              ("mango anthracnose", "alterada")],
    "naranja": [("orange fruit", "sana"),
                ("rotten orange", "alterada"),
                ("orange penicillium mold", "alterada")],
    "pina": [("pineapple fruit", "sana"),
             ("rotten pineapple", "alterada")],
    "fresa": [("strawberry fruit", "sana"),
              ("rotten strawberry", "alterada"),
              ("strawberry gray mold", "alterada")],
    "sandia": [("watermelon fruit", "sana"),
               ("rotten watermelon", "alterada")],
}
ESTADOS = ("sana", "alterada")


def api(params):
    """Llama a la API con reintentos ante 429 (rate limit)."""
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(API + "?" + qs, headers=UA)
    for intento in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                import json
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and intento < 4:
                print(f"  429, esperando {ESPERA_429}s")
                time.sleep(ESPERA_429 * (intento + 1))
                req = urllib.request.Request(API + "?" + qs, headers=UA)
                continue
            raise


def buscar(consulta, n):
    """Titulos File: + url de miniatura (800 px) + autor + licencia."""
    salen = []
    cont = None
    while len(salen) < n:
        p = {"action": "query", "format": "json", "generator": "search",
             "gsrsearch": consulta + " filetype:bitmap", "gsrnamespace": 6,
             "gsrlimit": 50, "prop": "imageinfo",
             "iiprop": "url|extmetadata", "iiurlwidth": 800}
        if cont:
            p.update(cont)
        d = api(p)
        for pg in (d.get("query") or {}).get("pages", {}).values():
            info = (pg.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            salen.append({
                "titulo": pg.get("title", ""),
                "url": info.get("thumburl") or info.get("url", ""),
                "autor": (meta.get("Artist") or {}).get("value", "")[:200],
                "licencia": (meta.get("LicenseShortName") or {}).get("value", ""),
            })
            if len(salen) >= n:
                break
        cont = d.get("continue")
        if not cont:
            break
        time.sleep(PAUSA)
    return salen


def bajar(url, ruta):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        datos = r.read()
    with open(ruta, "wb") as f:
        f.write(datos)


def normalizar(ruta):
    """Todo a JPEG RGB (los PNG con alfa y grises quedan uniformes)."""
    with Image.open(ruta) as im:
        rgb = Image.new("RGB", im.size, (255, 255, 255))
        rgb.paste(im.convert("RGB") if im.mode != "RGBA" else im,
                  mask=im.split()[-1] if im.mode == "RGBA" else None)
        rgb.save(ruta, "JPEG", quality=85)


def verificar(temas, cuota_sana, cuota_alterada):
    """Uniformidad estricta: cada tema con la misma cuota en CADA estado."""
    lineas, ok = [], True
    for tema in temas:
        partes = []
        for estado, cuota in (("sana", cuota_sana), ("alterada", cuota_alterada)):
            d = DESTINO / tema / estado
            n = len(list(d.glob("*.jpg"))) if d.exists() else 0
            partes.append(f"{estado} {n}/{cuota}")
            ok = ok and n == cuota
        lineas.append(f"{tema}: " + " | ".join(partes))
    return ok, "\n".join(lineas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--total", type=int, default=150)
    ap.add_argument("--max", type=int, default=300, dest="tope")
    ap.add_argument("--verificar", action="store_true",
                    help="solo revisa uniformidad, no descarga")
    args = ap.parse_args()

    temas = list(TOPICS)
    cuota = max(2, args.total // len(temas))
    cuota_sana = cuota // 2 + cuota % 2   # ceil: un estado mas no menos
    cuota_alterada = cuota - cuota_sana
    DESTINO.mkdir(exist_ok=True)

    if args.verificar:
        ok, det = verificar(temas, cuota_sana, cuota_alterada)
        print(det)
        raise SystemExit(0 if ok else 1)
    man_path = DESTINO / "manifest.csv"
    hecho = 0
    if man_path.exists():
        with open(man_path, encoding="utf-8") as f:
            hecho = max(0, sum(1 for _ in f) - 1)

    with open(man_path, "a", newline="", encoding="utf-8") as f:
        man = csv.writer(f)
        if hecho == 0:
            man.writerow(["archivo", "tema", "estado", "consulta",
                          "titulo_fuente", "url", "autor", "licencia"])
        total = 0
        for tema in temas:
            faltan = {}
            for estado in ESTADOS:
                d = DESTINO / tema / estado
                d.mkdir(parents=True, exist_ok=True)
                faltan[estado] = (cuota_sana if estado == "sana"
                                  else cuota_alterada) - len(list(d.glob("*.jpg")))
            if all(v <= 0 for v in faltan.values()):
                print(f"{tema}: completo")
                continue
            for consulta, estado in TOPICS[tema]:
                if total + hecho >= args.tope:
                    break
                d = DESTINO / tema / estado
                base_n = len(list(d.glob("*.jpg")))
                for c in buscar(consulta, max(faltan[estado], 1) * 2):
                    if faltan[estado] <= 0 or total + hecho >= args.tope:
                        break
                    base_n += 1
                    nombre = f"{base_n:03d}.jpg"
                    try:
                        bajar(c["url"], d / nombre)
                        normalizar(d / nombre)
                    except Exception as e:
                        print(f"  salto {c['titulo']}: {e}")
                        base_n -= 1
                        continue
                    man.writerow([f"{tema}/{estado}/{nombre}", tema, estado,
                                  consulta, c["titulo"], c["url"], c["autor"],
                                  c["licencia"]])
                    f.flush()
                    faltan[estado] -= 1
                    total += 1
                    time.sleep(PAUSA)
            print(f"{tema}: sana {len(list((DESTINO/tema/'sana').glob('*.jpg')))}"
                  f"/{cuota_sana} | alterada "
                  f"{len(list((DESTINO/tema/'alterada').glob('*.jpg')))}"
                  f"/{cuota_alterada}")
    print(f"listo: {total} nuevas ({hecho + total} en manifest, tope {args.tope})")
    ok, det = verificar(temas, cuota_sana, cuota_alterada)
    print(det)
    if not ok:
        print("quedaron temas por debajo: reejecuta para completar o ajusta consultas")


if __name__ == "__main__":
    main()

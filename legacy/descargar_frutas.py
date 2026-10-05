import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

FRUTAS = [
    "Apple",
    "Banana",
    "Orange (fruit)",
    "Strawberry",
    "Grape",
    "Pineapple",
    "Watermelon",
    "Mango",
    "Cherry",
    "Lemon",
]

LOGIN = "https://en.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": "FruitDownloader/1.0 (script educativo; contacto: ejemplo@correo.com)"
}
CARPETA_SALIDA = Path(__file__).resolve().parent / "frutas"


def obtener_url_imagen(titulo):
    parametros = {
        "action": "query",
        "format": "json",
        "prop": "pageimages",
        "piprop": "original",
        "titles": titulo,
    }
    url = LOGIN + "?" + urllib.parse.urlencode(parametros)
    peticion = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(peticion, timeout=30) as respuesta:
        datos = json.load(respuesta)
    paginas = datos["query"]["pages"]
    for pagina in paginas.values():
        original = (
            pagina.get("original")
            or pagina.get("pageimages", {}).get("original")
            or pagina.get("thumbnail")
        )
        if original:
            return original["source"]
    return None


def descargar_imagen(url, ruta):
    peticion = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(peticion, timeout=60) as respuesta:
        datos = respuesta.read()
    ruta.write_bytes(datos)


def main():
    CARPETA_SALIDA.mkdir(exist_ok=True)
    descargadas = 0
    for fruta in FRUTAS:
        try:
            url = obtener_url_imagen(fruta)
            if url is None:
                print(f"[!] No se encontro imagen para '{fruta}'")
                continue
            ruta = CARPETA_SALIDA / f"{fruta.lower().replace(' ', '_').replace('(', '').replace(')', '')}.jpg"
            descargar_imagen(url, ruta)
            print(f"[OK] {fruta} -> {ruta.name}")
            descargadas += 1
        except Exception as error:
            print(f"[!] Error con '{fruta}': {error}")
        time.sleep(1)
    print(f"\nDescargadas {descargadas} de {len(FRUTAS)} imagenes en {CARPETA_SALIDA}")


if __name__ == "__main__":
    main()
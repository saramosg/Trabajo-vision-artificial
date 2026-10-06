"""Genera assets/icon.ico desde un dibujo simple (sin dependencias graficas).

PyInstaller necesita un .ico para el icono del .exe. Si el proyecto no tiene
uno, esto crea una imagen basica de la app (cuadro azul redondeado con un
circulo, echoing los tokens de acento). Es un placeholder funcional: si mas
adelante hay un icono de marca, se reemplaza este archivo y punto.
"""
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parent
DESTINO = BASE / "assets" / "icon.ico"
TAM = 256
FONDO = (47, 111, 237)    # tokens.ACENTO  #2F6FED
SOBRE = (255, 255, 255)   # tokens.FONDO


def main() -> None:
    DESTINO.parent.mkdir(exist_ok=True)
    img = Image.new("RGBA", (TAM, TAM), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, TAM - 8, TAM - 8), radius=48, fill=FONDO)
    # Fruta estilizada: circulo claro con una hoja.
    d.ellipse((60, 74, 196, 210), fill=SOBRE)
    d.ellipse((128, 44, 176, 92), fill=(46, 125, 50, 255))   # tokens.COLOR_CANAL["G"]
    img.save(DESTINO, format="ICO", sizes=[(16, 16), (32, 32), (48, 48),
                                           (64, 64), (128, 128), (256, 256)])
    print(f"icono creado: {DESTINO} ({DESTINO.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
"""Pantalla de canales RGB: `VentanaCanales` con espacio "RGB" (R/G/B)."""
from ui.ventana_canales import VentanaCanales


class VentanaRGB(VentanaCanales):
    def __init__(self, ventana):
        super().__init__(ventana, "RGB")

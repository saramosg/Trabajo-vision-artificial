"""Pantalla de canales YCM: `VentanaCanales` con espacio "YCM" (Y/C/M)."""
from ui.ventana_canales import VentanaCanales


class VentanaYCM(VentanaCanales):
    def __init__(self, ventana):
        super().__init__(ventana, "YCM")

"""Punto de entrada de la aplicacion.

Crea el QApplication, carga la hoja de estilos global (`styles.qss`)
resolviendo la ruta del ejecutable (compatible con PyInstaller) y muestra
la ventana principal. No contiene logica de negocio ni de imagen: todo
vive en `core/` (procesamiento) y `ui/` (pantallas).

Uso:
    python main.py
"""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui import tokens
from ui.ventana_principal import VentanaPrincipal


def main() -> int:
    app = QApplication(sys.argv)
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    ruta_qss = base / "styles.qss"
    if not ruta_qss.exists():
        raise FileNotFoundError(f"no se encuentra styles.qss en {base}")
    app.setStyleSheet(ruta_qss.read_text(encoding="utf-8"))
    ventana = VentanaPrincipal()
    ventana.setMinimumSize(tokens.VENTANA_MIN_ANCHO, tokens.VENTANA_MIN_ALTO)
    ventana.resize(tokens.VENTANA_ANCHO, tokens.VENTANA_ALTO)
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

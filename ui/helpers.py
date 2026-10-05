"""Ayudas compartidas de las pantallas (botones y scroll).

Un solo hogar para el constructor de botones con tamano fijo y para el
envoltorio de QScrollArea que evita contenido recortado (§5.3 regla 8).
Lo usan las cinco pantallas en vez de triplicar el codigo.
"""
from PySide6.QtWidgets import QPushButton, QScrollArea, QVBoxLayout, QWidget


def boton(texto, object_name=None, ancho=None, alto=None):
    """QPushButton con tamano fijo de tokens (200x60 / 160x48)."""
    b = QPushButton(texto)
    if object_name:
        b.setObjectName(object_name)
    if ancho and alto:
        b.setFixedSize(ancho, alto)
    return b


def envolver_en_scroll(pantalla: QWidget, raiz: QVBoxLayout) -> None:
    """Mueve el contenido de `raiz` a un QScrollArea (§5.3 regla 8)."""
    contenido = QWidget(pantalla)
    interior = QVBoxLayout(contenido)
    while raiz.count():
        item = raiz.takeAt(0)
        if item.widget() is not None:
            interior.addWidget(item.widget())
        elif item.layout() is not None:
            interior.addLayout(item.layout())
        elif item.spacerItem() is not None:
            interior.addSpacerItem(item.spacerItem())
    scroll = QScrollArea(pantalla)
    scroll.setWidgetResizable(True)
    scroll.setWidget(contenido)
    raiz.addWidget(scroll)

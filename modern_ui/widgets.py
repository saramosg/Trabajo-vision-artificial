"""
modern_ui/widgets.py
Componentes reutilizables inspirados en UI Cards de ReactBits para PySide6.
"""
"""
modern_ui/widgets.py
Componentes modernos desacoplados (HoldButton verde, barras de patógenos y métricas).
"""

import math
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QAbstractButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QVariantAnimation, QEasingCurve, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QPainterPath, QPen, QBrush

from modern_ui.styles import THEME, DISEASE_COLORS

class ModernHoldButton(QAbstractButton):
    """
    Botón 'Hold to Confirm' inspirado en React Bits (https://reactbits.dev/).
    Llenado líquido verde con onda senoidal y glow.
    """
    hold_completed = Signal()

    def __init__(
        self,
        idle_text="Mantener presionado para clasificar (CNN)",
        done_text="¡Inferencia Completada!",
        hold_time_ms=1200,
        release_time_ms=160,
        parent=None
    ):
        super().__init__(parent)
        self.idle_text = idle_text
        self.done_text = done_text
        self.hold_time_ms = hold_time_ms
        self.release_time_ms = release_time_ms

        # Paleta Verde Esmeralda AgriTech
        self.bg_color = QColor("#131b2e")
        self.fill_color = QColor("#10b981")        # Verde Esmeralda
        self.border_color = QColor("#1e293b")
        self.text_color = QColor("#f8fafc")
        self.glow_color = QColor(16, 185, 129, 140)

        self.radius = 12
        self.progress = 0.0
        self.phase = "idle"   # "idle", "holding", "releasing", "done"
        self.wave_amplitude = 5.0
        self.wave_frequency = 3.0

        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)

        self.anim = QVariantAnimation(self)
        self.anim.valueChanged.connect(self._on_anim_value)
        self.anim.finished.connect(self._on_anim_finished)

        self.reset_timer = QTimer(self)
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self._reset_to_idle)

    def _on_anim_value(self, val):
        self.progress = float(val)
        self.update()

    def _on_anim_finished(self):
        if self.phase == "holding" and self.progress >= 0.999:
            self.phase = "done"
            self.update()
            self.hold_completed.emit()
            self.reset_timer.start(1400)
        elif self.phase == "releasing" and self.progress <= 0.001:
            self.phase = "idle"
            self.update()

    def _reset_to_idle(self):
        self.phase = "idle"
        self.progress = 0.0
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.phase == "idle" and self.isEnabled():
            self.phase = "holding"
            self.anim.stop()
            self.anim.setDuration(int(self.hold_time_ms * (1.0 - self.progress)))
            self.anim.setStartValue(self.progress)
            self.anim.setEndValue(1.0)
            self.anim.setEasingCurve(QEasingCurve.Linear)
            self.anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.phase == "holding":
            self.phase = "releasing"
            self.anim.stop()
            self.anim.setDuration(int(self.release_time_ms * self.progress))
            self.anim.setStartValue(self.progress)
            self.anim.setEndValue(0.0)
            self.anim.setEasingCurve(QEasingCurve.OutCubic)
            self.anim.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        btn_rect = QRectF(1, 1, w - 2, h - 2)

        # 1. Fondo base
        bg_brush = QBrush(self.bg_color)
        border_pen = QPen(self.border_color, 1.2)
        if self.phase == "holding":
            border_pen.setColor(self.fill_color)
        painter.setPen(border_pen)
        painter.setBrush(bg_brush)
        painter.drawRoundedRect(btn_rect, self.radius, self.radius)

        # 2. Onda líquida de llenado verde
        if self.progress > 0.0:
            fill_clip = QPainterPath()
            fill_clip.addRoundedRect(btn_rect, self.radius, self.radius)
            painter.save()
            painter.setClipPath(fill_clip)

            fill_width = w * self.progress

            wave_path = QPainterPath()
            wave_path.moveTo(0, 0)
            wave_path.lineTo(fill_width, 0)

            if self.progress < 0.98:
                steps = 16
                for i in range(steps + 1):
                    y = (h / steps) * i
                    dx = math.sin((y / h) * math.pi * self.wave_frequency + (self.progress * 8)) * self.wave_amplitude
                    wave_path.lineTo(fill_width + dx, y)
            else:
                wave_path.lineTo(fill_width, h)

            wave_path.lineTo(0, h)
            wave_path.closeSubpath()

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.fill_color))
            painter.drawPath(wave_path)

            if self.phase == "holding":
                glow_pen = QPen(self.glow_color, 3.5)
                painter.setPen(glow_pen)
                painter.drawLine(int(fill_width), 0, int(fill_width), h)

            painter.restore()

        # 3. Texto
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        text = self.done_text if self.phase == "done" else self.idle_text
        painter.setPen(self.text_color)
        painter.drawText(btn_rect, Qt.AlignCenter, text)
        painter.end()


class DiseaseProbBar(QFrame):
    """Barra de diagnóstico por patógeno."""
    def __init__(self, class_name: str, parent=None):
        super().__init__(parent)
        self.class_name = class_name
        self.color = DISEASE_COLORS.get(class_name, THEME["accent_primary"])
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        
        self.lbl_name = QLabel(class_name)
        self.lbl_name.setFixedWidth(145)
        self.lbl_name.setStyleSheet(f"color: {THEME['text_secondary']}; font-weight: 500;")
        
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {self.color}; border-radius: 6px; }}")
        
        layout.addWidget(self.lbl_name)
        layout.addWidget(self.bar)

    def set_probability(self, prob_float: float):
        percentage = int(prob_float * 100)
        self.bar.setValue(percentage)
        self.bar.setFormat(f"{percentage}%")
        if percentage > 40:
            self.lbl_name.setStyleSheet(f"color: {self.color}; font-weight: 700;")
        else:
            self.lbl_name.setStyleSheet(f"color: {THEME['text_secondary']}; font-weight: 500;")


class MetricBadge(QFrame):
    """Tarjeta tipo React Bits para métricas rápidas."""
    def __init__(self, title: str, initial_value: str = "--", parent=None):
        super().__init__(parent)
        self.setProperty("class", "ModernCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 10px; font-weight: 700;")
        
        self.lbl_val = QLabel(initial_value)
        self.lbl_val.setStyleSheet(f"color: {THEME['accent_primary']}; font-size: 16px; font-weight: 700;")
        
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_val)

    def update_value(self, text: str, highlight_color: str = None):
        self.lbl_val.setText(text)
        if highlight_color:
            self.lbl_val.setStyleSheet(f"color: {highlight_color}; font-size: 16px; font-weight: 700;")
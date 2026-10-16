"""
app_modern.py
Punto de entrada moderno. Conecta la lógica existente de procesamiento con la nueva interfaz.

Para ejecutar la aplicación desde la terminal se debe ejecutar el siguiente comando:
python -m modern_ui.app_modern


app_modern.py
Ventana principal moderna conectada a modern_ui y al ModernHoldButton verde.
"""

import sys
import os

# --- AUTO-RESOLUCIÓN DE RUTAS PARA EVITAR ModuleNotFoundError ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QFrame
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from modern_ui.styles import MODERN_QSS, THEME, DISEASE_COLORS
from modern_ui.widgets import DiseaseProbBar, MetricBadge, ModernHoldButton

class ModernMangoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MangoGuard AI - Detección Poscosecha de Fitopatógenos")
        self.resize(1260, 780)
        self.setStyleSheet(MODERN_QSS)
        self.current_image_path = None
        self.setup_ui()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(18)

        # Encabezado
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        lbl_title = QLabel("MANGO PATHO-VISION AI")
        lbl_title.setObjectName("HeaderTitle")
        lbl_sub = QLabel("Sistema de inspección no destructiva de fitopatógenos poscosecha (GrabCut + CNN)")
        lbl_sub.setObjectName("HeaderSubtitle")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        btn_load = QPushButton("Cargar Muestra de Mango")
        btn_load.setProperty("class", "PrimaryButton")
        btn_load.clicked.connect(self.cargar_imagen)
        header_layout.addWidget(btn_load)

        main_layout.addLayout(header_layout)

        # Contenido Central
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # Panel Izquierdo: Visores
        viewers_frame = QFrame()
        viewers_frame.setProperty("class", "ModernCard")
        v_box = QVBoxLayout(viewers_frame)
        
        lbl_viewers_title = QLabel("INSPECCIÓN VISUAL PDI")
        lbl_viewers_title.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 11px;")
        v_box.addWidget(lbl_viewers_title)

        canvas_row = QHBoxLayout()
        
        c1_box = QVBoxLayout()
        c1_box.addWidget(QLabel("Muestra Original (512×512)"))
        self.canvas_orig = QLabel("Selecciona una muestra...")
        self.canvas_orig.setObjectName("ImageCanvas")
        self.canvas_orig.setAlignment(Qt.AlignCenter)
        self.canvas_orig.setFixedSize(380, 380)
        c1_box.addWidget(self.canvas_orig)
        canvas_row.addLayout(c1_box)

        c2_box = QVBoxLayout()
        c2_box.addWidget(QLabel("Segmentación / Normalización (224×224)"))
        self.canvas_proc = QLabel("Procesamiento PDI")
        self.canvas_proc.setObjectName("ImageCanvas")
        self.canvas_proc.setAlignment(Qt.AlignCenter)
        self.canvas_proc.setFixedSize(380, 380)
        c2_box.addWidget(self.canvas_proc)
        canvas_row.addLayout(c2_box)

        v_box.addLayout(canvas_row)

        tools_row = QHBoxLayout()
        btn_grabcut = QPushButton("Aplicar GrabCut / OTSU")
        btn_grabcut.setProperty("class", "SecondaryButton")
        btn_grabcut.clicked.connect(self.ejecutar_segmentacion)
        tools_row.addWidget(btn_grabcut)

        btn_color = QPushButton("Filtrado HSV / YCrCb")
        btn_color.setProperty("class", "SecondaryButton")
        btn_color.clicked.connect(self.ejecutar_analisis_color)
        tools_row.addWidget(btn_color)

        v_box.addLayout(tools_row)
        content_layout.addWidget(viewers_frame, stretch=3)

        # Panel Derecho: Diagnóstico CNN
        diag_frame = QFrame()
        diag_frame.setProperty("class", "ModernCard")
        diag_box = QVBoxLayout(diag_frame)
        
        lbl_diag_title = QLabel("DIAGNÓSTICO FITOPATOLÓGICO")
        lbl_diag_title.setStyleSheet("font-weight: 700; color: #94a3b8; font-size: 11px;")
        diag_box.addWidget(lbl_diag_title)

        metrics_row = QHBoxLayout()
        self.badge_status = MetricBadge("Diagnóstico Predominante", "En espera...")
        self.badge_confidence = MetricBadge("Confianza General", "0.0%")
        metrics_row.addWidget(self.badge_status)
        metrics_row.addWidget(self.badge_confidence)
        diag_box.addLayout(metrics_row)

        diag_box.addWidget(QLabel("Distribución de Probabilidad:"))
        self.prob_bars = {}
        clases = ["Sana", "Moho negro", "Pudrición peduncular", "Alternaria", "Antracnosis"]
        for c in clases:
            bar = DiseaseProbBar(c)
            self.prob_bars[c] = bar
            diag_box.addWidget(bar)

        diag_box.addStretch()

        # AQUÍ INTEGRAMOS EL HOLD BUTTON VERDE
        self.btn_hold = ModernHoldButton(
            idle_text="Mantener presionado para clasificar (CNN)",
            done_text="¡Inferencia Completada!",
            hold_time_ms=1200,
            release_time_ms=160
        )
        self.btn_hold.hold_completed.connect(self.ejecutar_clasificacion)
        diag_box.addWidget(self.btn_hold)

        content_layout.addWidget(diag_frame, stretch=2)
        main_layout.addLayout(content_layout)

    def cargar_imagen(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Mango", "", "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.current_image_path = file_path
            pixmap = QPixmap(file_path).scaled(380, 380, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.canvas_orig.setPixmap(pixmap)

    def ejecutar_segmentacion(self):
        pass

    def ejecutar_analisis_color(self):
        pass

    def ejecutar_clasificacion(self):
        # Simulación de prueba para observar las barras y el diagnóstico:
        demo_probs = {
            "Sana": 0.04,
            "Moho negro": 0.02,
            "Pudrición peduncular": 0.11,
            "Alternaria": 0.08,
            "Antracnosis": 0.75
        }
        for c, p in demo_probs.items():
            self.prob_bars[c].set_probability(p)
        
        self.badge_status.update_value("Antracnosis", DISEASE_COLORS["Antracnosis"])
        self.badge_confidence.update_value("75.0%", DISEASE_COLORS["Antracnosis"])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernMangoApp()
    window.show()
    sys.exit(app.exec())
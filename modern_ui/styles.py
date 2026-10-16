"""
modern_ui/styles.py
Sistema de diseño 'AgriTech Modern Dark' para el clasificador de mango.
Inspirado en componentes modernos de ReactBits (Dark mode, bordes glow, tarjetas flotantes).
"""
"""
modern_ui/styles.py
Tema y estilos visuales para Mango Patho-Vision AI.
"""

THEME = {
    "bg_main": "#0b0f19",
    "bg_card": "#131b2e",
    "border_subtle": "#1e293b",
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "accent_primary": "#10b981",   # Verde Esmeralda AgriTech
    "accent_secondary": "#f59e0b", # Amarillo Mango
}

DISEASE_COLORS = {
    "Sana": "#10b981",
    "Moho negro": "#a855f7",
    "Pudrición peduncular": "#f97316",
    "Alternaria": "#eab308",
    "Antracnosis": "#ef4444",
}

MODERN_QSS = f"""
QMainWindow {{
    background-color: {THEME['bg_main']};
    font-family: 'Segoe UI', Arial, sans-serif;
}}

QWidget {{
    color: {THEME['text_primary']};
    font-size: 13px;
}}

QLabel#HeaderTitle {{
    font-size: 20px;
    font-weight: 700;
    color: {THEME['text_primary']};
}}

QLabel#HeaderSubtitle {{
    font-size: 13px;
    color: {THEME['text_secondary']};
}}

QFrame.ModernCard {{
    background-color: {THEME['bg_card']};
    border: 1px solid {THEME['border_subtle']};
    border-radius: 12px;
    padding: 14px;
}}

QPushButton.PrimaryButton {{
    background-color: {THEME['accent_primary']};
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}}

QPushButton.PrimaryButton:hover {{
    background-color: #059669;
}}

QPushButton.SecondaryButton {{
    background-color: #1e293b;
    color: {THEME['text_primary']};
    border: 1px solid {THEME['border_subtle']};
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 500;
}}

QPushButton.SecondaryButton:hover {{
    background-color: #334155;
}}

QLabel#ImageCanvas {{
    background-color: #070a10;
    border: 2px dashed #1e293b;
    border-radius: 12px;
}}

QProgressBar {{
    background-color: #1e293b;
    border: none;
    border-radius: 6px;
    text-align: right;
    padding-right: 6px;
    font-size: 11px;
    font-weight: 600;
    color: #ffffff;
    height: 18px;
}}
"""
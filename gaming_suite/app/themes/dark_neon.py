COLORS = {
    "bg_deep":       "#06060E",
    "bg_main":       "#0A0A16",
    "bg_surface":    "#0F0F1E",
    "bg_card":       "#131325",
    "bg_card_hover": "#181830",
    "border":        "rgba(0,200,255,0.18)",
    "border_active": "rgba(0,200,255,0.65)",
    "accent_blue":   "#00C8FF",
    "accent_cyan":   "#00FFD4",
    "accent_purple": "#9B5CF6",
    "accent_pink":   "#FF2D78",
    "text_primary":  "#FFFFFF",
    "text_secondary":"rgba(255,255,255,0.55)",
    "text_muted":    "rgba(255,255,255,0.30)",
    "success":       "#00FF9D",
    "warning":       "#FFB800",
    "error":         "#FF3D5A",
}

QSS = """
/* ═══════════════════════════════════════════════
   INFINITY HUB — PREMIUM DARK NEON STYLESHEET
   ═══════════════════════════════════════════════ */

QMainWindow, QDialog {
    background-color: #06060E;
}

QWidget {
    background-color: transparent;
    color: #FFFFFF;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
    selection-background-color: rgba(0,200,255,0.3);
}

/* ──── SCROLLBARS ──────────────────────────────── */
QScrollBar:vertical {
    background: rgba(255,255,255,0.03);
    width: 6px;
    border-radius: 3px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(0,200,255,0.35);
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(0,200,255,0.65);
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: rgba(255,255,255,0.03);
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: rgba(0,200,255,0.35);
    border-radius: 3px;
    min-width: 30px;
}

/* ──── TOOLTIPS ────────────────────────────────── */
QToolTip {
    background-color: #0F0F1E;
    color: #FFFFFF;
    border: 1px solid rgba(0,200,255,0.4);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
}

/* ──── LINE EDIT / SEARCH ──────────────────────── */
QLineEdit {
    background: rgba(0,200,255,0.06);
    border: 1px solid rgba(0,200,255,0.25);
    border-radius: 10px;
    color: #FFFFFF;
    padding: 8px 14px;
    font-size: 13px;
    selection-background-color: rgba(0,200,255,0.3);
}
QLineEdit:focus {
    border: 1px solid rgba(0,200,255,0.75);
    background: rgba(0,200,255,0.10);
}
QLineEdit::placeholder {
    color: rgba(255,255,255,0.3);
}

/* ──── COMBO BOX ───────────────────────────────── */
QComboBox {
    background: rgba(0,200,255,0.06);
    border: 1px solid rgba(0,200,255,0.25);
    border-radius: 8px;
    color: #FFFFFF;
    padding: 6px 12px;
    font-size: 13px;
}
QComboBox:hover {
    border-color: rgba(0,200,255,0.55);
    background: rgba(0,200,255,0.10);
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid rgba(0,200,255,0.7);
}
QComboBox QAbstractItemView {
    background: #0F0F1E;
    border: 1px solid rgba(0,200,255,0.3);
    border-radius: 8px;
    color: #FFFFFF;
    selection-background-color: rgba(0,200,255,0.2);
    outline: none;
}

/* ──── SLIDER ──────────────────────────────────── */
QSlider::groove:horizontal {
    height: 4px;
    background: rgba(255,255,255,0.1);
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #00C8FF;
    border: 2px solid rgba(0,200,255,0.4);
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -6px 0;
}
QSlider::handle:horizontal:hover {
    background: #00FFD4;
    border-color: rgba(0,255,212,0.6);
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #00C8FF, stop:1 #9B5CF6);
    border-radius: 2px;
    height: 4px;
}

/* ──── PROGRESS BAR ────────────────────────────── */
QProgressBar {
    background: rgba(255,255,255,0.07);
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
    border: none;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #00C8FF, stop:1 #9B5CF6);
    border-radius: 4px;
}

/* ──── LABEL ───────────────────────────────────── */
QLabel {
    background: transparent;
    color: #FFFFFF;
}

/* ──── PUSH BUTTON (base) ──────────────────────── */
QPushButton {
    background: rgba(0,200,255,0.10);
    border: 1px solid rgba(0,200,255,0.30);
    border-radius: 8px;
    color: #FFFFFF;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background: rgba(0,200,255,0.20);
    border-color: rgba(0,200,255,0.65);
    color: #00C8FF;
}
QPushButton:pressed {
    background: rgba(0,200,255,0.30);
    border-color: #00C8FF;
}

/* ──── FRAME ───────────────────────────────────── */
QFrame {
    background: transparent;
}

/* ──── STACKED WIDGET ──────────────────────────── */
QStackedWidget {
    background: transparent;
}
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QBrush, QFont
from PyQt6.QtCore import (Qt, QPropertyAnimation, QEasingCurve,
                          pyqtProperty, QTimer, QPoint, QRect)


class TooltipPopup(QWidget):
    """
    Premium floating tooltip with blur-glass look, neon border, and fade animation.
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip |
                         Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._opacity = 0.0

        self._opacity_anim = QPropertyAnimation(self, b"panelOpacity", self)
        self._opacity_anim.setDuration(200)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._start_hide)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # title
        self._title_lbl = QLabel(self)
        title_font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        self._title_lbl.setFont(title_font)
        self._title_lbl.setStyleSheet("color: #00C8FF; background: transparent;")
        layout.addWidget(self._title_lbl)

        # divider
        line = QFrame(self)
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(0,200,255,0.25); border: none;")
        layout.addWidget(line)

        # description
        self._desc_lbl = QLabel(self)
        self._desc_lbl.setWordWrap(True)
        self._desc_lbl.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 12px; background: transparent;")
        layout.addWidget(self._desc_lbl)

        # tags row
        self._tags_lbl = QLabel(self)
        self._tags_lbl.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 11px; background: transparent;")
        layout.addWidget(self._tags_lbl)

    def show_for(self, title: str, description: str,
                 effect: str = "", recommendation: str = "",
                 risk: str = "Low", category: str = "",
                 pos: QPoint = None):
        self._title_lbl.setText(title)
        self._desc_lbl.setText(description)

        tags = []
        if effect:
            tags.append(f"Effect: {effect}")
        if recommendation:
            tags.append(f"Tip: {recommendation}")
        risk_colors = {"Low": "#00FF9D", "Medium": "#FFB800", "High": "#FF3D5A"}
        risk_col = risk_colors.get(risk, "#FFFFFF")
        tags.append(f'Risk: {risk}')
        self._tags_lbl.setText("  ·  ".join(tags))

        self.adjustSize()
        self.setMaximumWidth(320)
        self.adjustSize()

        if pos:
            self.move(pos)
        self.show()
        self._fade_in()

    def _fade_in(self):
        self._opacity_anim.stop()
        self._opacity_anim.setStartValue(self._opacity)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()

    def _start_hide(self):
        self._opacity_anim.stop()
        self._opacity_anim.setStartValue(self._opacity)
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.finished.connect(self.hide)
        self._opacity_anim.start()

    def schedule_hide(self, delay_ms: int = 100):
        self._hide_timer.start(delay_ms)

    def cancel_hide(self):
        self._hide_timer.stop()
        self._opacity_anim.stop()
        self._fade_in()

    # ── animated opacity ──────────────────────────
    def get_panel_opacity(self) -> float:
        return self._opacity

    def set_panel_opacity(self, v: float):
        self._opacity = v
        self.setWindowOpacity(v)

    panelOpacity = pyqtProperty(float, get_panel_opacity, set_panel_opacity)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)

        # glass background
        bg = QLinearGradient(0, 0, 0, self.height())
        bg.setColorAt(0, QColor(18, 18, 38, 235))
        bg.setColorAt(1, QColor(10, 10, 22, 235))
        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 12, 12)

        # neon border
        for w, a in [(5, 25), (2, 60), (1, 130)]:
            p.setPen(QPen(QColor(0, 200, 255, a), w))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 11, 11)
        p.end()

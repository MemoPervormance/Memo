from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QBrush
from PyQt6.QtCore import Qt, QRect, QPoint


class GlassCard(QFrame):
    """
    Premium glassmorphism card with neon border glow and depth shadow.
    accentColor: hex or rgba string for the border glow color
    glow: draw multi-layer neon glow border
    """

    def __init__(self, parent=None, accent: str = "#00C8FF", glow: bool = True,
                 radius: int = 14):
        super().__init__(parent)
        self._accent = QColor(accent)
        self._glow = glow
        self._radius = radius
        self._hover = False
        self.setMouseTracking(True)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = self.rect().adjusted(2, 2, -2, -2)
        rad = self._radius

        # ── inner glass fill ──────────────────────
        bg = QLinearGradient(0, 0, 0, self.height())
        if self._hover:
            bg.setColorAt(0, QColor(22, 22, 44, 210))
            bg.setColorAt(1, QColor(14, 14, 28, 210))
        else:
            bg.setColorAt(0, QColor(18, 18, 38, 200))
            bg.setColorAt(1, QColor(10, 10, 22, 200))
        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(r, rad, rad)

        # ── top shine highlight ────────────────────
        shine = QLinearGradient(0, 0, 0, 40)
        shine.setColorAt(0, QColor(255, 255, 255, 18))
        shine.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(shine))
        painter.drawRoundedRect(r, rad, rad)

        # ── neon glow border ───────────────────────
        if self._glow:
            alpha_base = 90 if self._hover else 50
            for i, (width, alpha_mult) in enumerate([(6, 0.25), (3, 0.5), (1, 1.0)]):
                a = int(alpha_base * alpha_mult)
                pen = QPen(QColor(self._accent.red(),
                                  self._accent.green(),
                                  self._accent.blue(), a), width)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(r.adjusted(i, i, -i, -i), rad - i, rad - i)

        painter.end()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

from PyQt6.QtWidgets import QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtGui import (QPainter, QColor, QPen, QLinearGradient,
                         QBrush, QFont, QCursor)
from PyQt6.QtCore import (Qt, QPropertyAnimation, QEasingCurve,
                          pyqtProperty, QRect)


class NeonButton(QPushButton):
    """
    Premium neon button with animated glow on hover/press.
    variant: "primary" | "secondary" | "danger" | "ghost"
    """

    def __init__(self, text: str = "", parent=None,
                 variant: str = "primary",
                 accent: str = "#00C8FF"):
        super().__init__(text, parent)
        self._variant = variant
        self._accent = QColor(accent)
        self._hover_progress = 0.0
        self._press_progress = 0.0
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        font = QFont("Segoe UI", 12, QFont.Weight.DemiBold)
        self.setFont(font)
        self.setMinimumHeight(40)

        # hover animation
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(200)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # glow shadow
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setOffset(0, 0)
        self._shadow.setColor(self._accent)
        self.setGraphicsEffect(self._shadow)

    def get_hover_progress(self) -> float:
        return self._hover_progress

    def set_hover_progress(self, v: float):
        self._hover_progress = v
        blur = int(v * 20)
        self._shadow.setBlurRadius(blur)
        self.update()

    hoverProgress = pyqtProperty(float, get_hover_progress, set_hover_progress)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)

        h = self._hover_progress
        pr = self._press_progress

        if self._variant == "primary":
            # gradient fill
            grad = QLinearGradient(0, 0, self.width(), 0)
            grad.setColorAt(0, QColor(0, int(120 + 80 * h), int(200 + 55 * h), int(200 + 55 * h)))
            grad.setColorAt(1, QColor(int(60 * h), 80, int(180 + 75 * h), int(200 + 55 * h)))
            p.setBrush(QBrush(grad))

            # border
            border_alpha = int(100 + 155 * h)
            p.setPen(QPen(QColor(0, 200, 255, border_alpha), 1))
            p.drawRoundedRect(r, 9, 9)

            # shine
            shine = QLinearGradient(0, 0, 0, self.height() // 2)
            shine.setColorAt(0, QColor(255, 255, 255, int(30 + 20 * h)))
            shine.setColorAt(1, QColor(255, 255, 255, 0))
            p.setBrush(QBrush(shine))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, 9, 9)

        elif self._variant == "secondary":
            p.setBrush(QColor(30, 30, 55, int(160 + 60 * h)))
            p.setPen(QPen(QColor(0, 200, 255, int(70 + 100 * h)), 1))
            p.drawRoundedRect(r, 9, 9)

        elif self._variant == "ghost":
            p.setBrush(QColor(255, 255, 255, int(8 + 15 * h)))
            p.setPen(QPen(QColor(255, 255, 255, int(50 + 80 * h)), 1))
            p.drawRoundedRect(r, 9, 9)

        elif self._variant == "danger":
            p.setBrush(QColor(180, 30, 60, int(160 + 60 * h)))
            p.setPen(QPen(QColor(255, 60, 100, int(100 + 100 * h)), 1))
            p.drawRoundedRect(r, 9, 9)

        # text
        text_color = QColor(255, 255, 255) if self._variant != "ghost" else QColor(200, 200, 220)
        p.setPen(text_color)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
        p.end()

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()

    def mousePressEvent(self, event):
        self._press_progress = 1.0
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_progress = 0.0
        self.update()
        super().mouseReleaseEvent(event)

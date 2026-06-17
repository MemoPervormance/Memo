from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QBrush, QRadialGradient
from PyQt6.QtCore import (Qt, QPropertyAnimation, QEasingCurve,
                          pyqtProperty, pyqtSignal, QPoint)


class NeonToggle(QWidget):
    toggled = pyqtSignal(bool)

    W, H = 52, 28

    def __init__(self, parent=None, checked: bool = False,
                 accent: str = "#00C8FF"):
        super().__init__(parent)
        self._checked = checked
        self._accent = QColor(accent)
        self._offset = 1.0 if checked else 0.0  # 0=off, 1=on
        self.setFixedSize(self.W, self.H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(280)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ── animated property ──────────────────────────
    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, v: float):
        self._offset = v
        self.update()

    offset = pyqtProperty(float, get_offset, set_offset)

    # ── public API ─────────────────────────────────
    @property
    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, state: bool, animate: bool = True):
        if self._checked == state:
            return
        self._checked = state
        target = 1.0 if state else 0.0
        if animate:
            self._anim.stop()
            self._anim.setStartValue(self._offset)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._offset = target
            self.update()

    def toggle(self):
        self.setChecked(not self._checked)
        self.toggled.emit(self._checked)

    # ── painting ───────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.W, self.H
        r = h // 2

        # track background
        if self._checked:
            track_grad = QLinearGradient(0, 0, w, 0)
            track_grad.setColorAt(0, QColor(0, 140, 200, 200))
            track_grad.setColorAt(1, QColor(0, 200, 255, 200))
            p.setBrush(QBrush(track_grad))
        else:
            p.setBrush(QColor(30, 30, 50, 220))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, w, h, r, r)

        # track border glow
        if self._checked:
            for width, alpha in [(5, 40), (2, 80), (1, 160)]:
                pen = QPen(QColor(0, 200, 255, alpha), width)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(1, 1, w - 2, h - 2, r - 1, r - 1)
        else:
            p.setPen(QPen(QColor(60, 60, 90, 180), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(0, 0, w - 1, h - 1, r, r)

        # thumb
        margin = 3
        travel = w - h
        cx = int(margin + r - margin + travel * self._offset)
        cy = h // 2

        # thumb glow (only when on)
        if self._checked or self._offset > 0.05:
            glow = QRadialGradient(cx, cy, 16)
            a = int(80 * self._offset)
            glow.setColorAt(0, QColor(0, 220, 255, a))
            glow.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(glow))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPoint(cx, cy), 16, 16)

        # thumb fill
        thumb_r = r - margin
        thumb_grad = QRadialGradient(cx - 2, cy - 2, thumb_r * 2)
        if self._checked:
            thumb_grad.setColorAt(0, QColor(220, 255, 255))
            thumb_grad.setColorAt(1, QColor(0, 200, 255))
        else:
            thumb_grad.setColorAt(0, QColor(140, 140, 170))
            thumb_grad.setColorAt(1, QColor(80, 80, 100))
        p.setBrush(QBrush(thumb_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPoint(cx, cy), thumb_r, thumb_r)

        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()

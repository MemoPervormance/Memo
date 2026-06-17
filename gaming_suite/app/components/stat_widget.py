from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtGui import (QPainter, QColor, QPen, QLinearGradient,
                         QBrush, QFont, QConicalGradient, QRadialGradient)
from PyQt6.QtCore import Qt, QRectF, QTimer, QPropertyAnimation, pyqtProperty


class ArcGauge(QWidget):
    """Futuristic arc gauge for CPU/GPU/RAM usage."""

    def __init__(self, label: str, unit: str = "%",
                 accent: str = "#00C8FF", parent=None):
        super().__init__(parent)
        self._label = label
        self._unit = unit
        self._accent = QColor(accent)
        self._value = 0.0
        self._target = 0.0
        self._display_value = 0.0
        self.setFixedSize(110, 110)

        self._anim = QPropertyAnimation(self, b"displayValue", self)
        self._anim.setDuration(600)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_value(self, v: float):
        self._target = max(0.0, min(100.0, v))
        self._anim.stop()
        self._anim.setStartValue(self._display_value)
        self._anim.setEndValue(self._target)
        self._anim.start()

    def get_display_value(self) -> float:
        return self._display_value

    def set_display_value(self, v: float):
        self._display_value = v
        self.update()

    displayValue = pyqtProperty(float, get_display_value, set_display_value)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        margin = 12
        rect = QRectF(margin, margin, w - margin * 2, h - margin * 2)

        pct = self._display_value / 100.0
        start_angle = 220 * 16
        span_angle = -int(260 * 16 * pct)

        # color by value
        if pct < 0.5:
            r = int(0 + pct * 2 * 30)
            g = int(200 - pct * 2 * 50)
            b = 255
        elif pct < 0.8:
            r = int(30 + (pct - 0.5) * 3 * 200)
            g = int(150 + (pct - 0.5) * 3 * 50)
            b = int(255 - (pct - 0.5) * 3 * 200)
        else:
            r = 255
            g = int(200 - (pct - 0.8) * 5 * 150)
            b = int(50 - (pct - 0.8) * 5 * 50)
        arc_color = QColor(max(0, min(255, r)),
                           max(0, min(255, g)),
                           max(0, min(255, b)))

        # track
        p.setPen(QPen(QColor(255, 255, 255, 15), 8,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(rect, 220 * 16, -260 * 16)

        # glow arc
        for thickness, alpha in [(12, 30), (8, 60), (5, 120)]:
            glow_pen = QPen(QColor(arc_color.red(), arc_color.green(),
                                   arc_color.blue(), alpha),
                            thickness, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap)
            p.setPen(glow_pen)
            p.drawArc(rect, start_angle, span_angle)

        # main arc
        p.setPen(QPen(arc_color, 5, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawArc(rect, start_angle, span_angle)

        # center text
        p.setPen(QColor(255, 255, 255))
        val_font = QFont("Segoe UI", 15, QFont.Weight.Bold)
        p.setFont(val_font)
        val_str = f"{int(self._display_value)}{self._unit}"
        p.drawText(QRectF(0, h // 2 - 16, w, 24),
                   Qt.AlignmentFlag.AlignCenter, val_str)

        p.setPen(QColor(150, 150, 180))
        lbl_font = QFont("Segoe UI", 8)
        p.setFont(lbl_font)
        p.drawText(QRectF(0, h // 2 + 8, w, 16),
                   Qt.AlignmentFlag.AlignCenter, self._label)
        p.end()


class StatWidget(QWidget):
    """Row of arc gauges for system stats."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._cpu   = ArcGauge("CPU",  "%", "#00C8FF")
        self._gpu   = ArcGauge("GPU",  "%", "#9B5CF6")
        self._ram   = ArcGauge("RAM",  "%", "#00FFD4")
        self._temp  = ArcGauge("TEMP", "°", "#FF6B35")

        for g in (self._cpu, self._gpu, self._ram, self._temp):
            layout.addWidget(g)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_stats)
        self._timer.start(2000)
        self._update_stats()

    def _update_stats(self):
        try:
            import psutil
            self._cpu.set_value(psutil.cpu_percent(interval=None))
            vm = psutil.virtual_memory()
            self._ram.set_value(vm.percent)
            # GPU and temp require platform libs — show placeholder
            self._gpu.set_value(0)
            self._temp.set_value(0)
        except Exception:
            pass

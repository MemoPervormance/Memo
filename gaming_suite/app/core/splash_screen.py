import math
import random
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import (QPainter, QColor, QPen, QLinearGradient,
                         QBrush, QFont, QRadialGradient, QConicalGradient)
from PyQt6.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve,
                          pyqtProperty, QPointF, QRectF, QPoint)


class Particle:
    def __init__(self, w: int, h: int):
        self.reset(w, h)

    def reset(self, w: int, h: int):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.vx = random.uniform(-0.4, 0.4)
        self.vy = random.uniform(-0.6, -0.1)
        self.life = 1.0
        self.decay = random.uniform(0.003, 0.008)
        self.size = random.uniform(1.5, 4.0)
        self.color_idx = random.randint(0, 2)

    def update(self, w: int, h: int):
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay
        if self.life <= 0 or self.y < -10:
            self.reset(w, h)
            self.y = h + 5


PARTICLE_COLORS = [
    QColor(0, 200, 255),
    QColor(155, 92, 246),
    QColor(0, 255, 212),
]


class SplashScreen(QWidget):
    """
    Epic animated splash screen with particles, pulsing logo, and progress bar.
    Calls `on_done` callback when complete.
    """

    def __init__(self, on_done):
        super().__init__(None, Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint |
                         Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._on_done = on_done

        # sizing
        screen = QApplication.primaryScreen().geometry()
        w, h = min(960, screen.width()), min(600, screen.height())
        self.setFixedSize(w, h)
        self.move((screen.width() - w) // 2, (screen.height() - h) // 2)

        # animation state
        self._progress = 0.0
        self._logo_alpha = 0.0
        self._pulse = 0.0
        self._tick = 0
        self._ring_angle = 0.0
        self._particles = [Particle(w, h) for _ in range(80)]

        # timers
        self._render_timer = QTimer(self)
        self._render_timer.timeout.connect(self._tick_frame)
        self._render_timer.start(16)  # ~60 fps

        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._advance_progress)
        self._progress_timer.start(30)

        # fade out
        self._fade_out_alpha = 0.0
        self._fading = False

    # ── animation loop ─────────────────────────────
    def _tick_frame(self):
        self._tick += 1
        self._pulse = (math.sin(self._tick * 0.06) + 1) / 2
        self._ring_angle = (self._ring_angle + 1.2) % 360
        if self._logo_alpha < 1.0:
            self._logo_alpha = min(1.0, self._logo_alpha + 0.015)
        w, h = self.width(), self.height()
        for pt in self._particles:
            pt.update(w, h)
        if self._fading:
            self._fade_out_alpha = min(1.0, self._fade_out_alpha + 0.05)
            if self._fade_out_alpha >= 1.0:
                self._render_timer.stop()
                self._progress_timer.stop()
                self.close()
                self._on_done()
        self.update()

    def _advance_progress(self):
        if self._progress < 100:
            step = random.uniform(0.8, 2.2)
            self._progress = min(100.0, self._progress + step)
        elif not self._fading:
            self._fading = True
            self._progress_timer.stop()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        # ── background ─────────────────────────────
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0, QColor(6, 6, 14))
        bg.setColorAt(1, QColor(10, 6, 20))
        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect())

        # ── radial glow center ──────────────────────
        glow_alpha = int(40 + 30 * self._pulse) * self._logo_alpha
        for radius, alpha_mult in [(300, 0.15), (180, 0.25), (80, 0.4)]:
            rg = QRadialGradient(cx, cy, radius)
            rg.setColorAt(0, QColor(0, 200, 255, int(glow_alpha * alpha_mult)))
            rg.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(rg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPoint(cx, cy), radius, radius)

        # ── particles ───────────────────────────────
        for pt in self._particles:
            col = PARTICLE_COLORS[pt.color_idx]
            a = int(255 * pt.life * 0.7)
            p.setBrush(QColor(col.red(), col.green(), col.blue(), a))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(pt.x, pt.y), pt.size, pt.size)

        # ── spinning rings ──────────────────────────
        if self._logo_alpha > 0.1:
            for ring_r, ring_w, ring_a, angle_offset in [
                (160, 2, 60, 0), (130, 1, 40, 45), (195, 1, 30, -30)
            ]:
                a = int(ring_a * self._logo_alpha)
                pen = QPen(QColor(0, 200, 255, a), ring_w)
                pen.setDashPattern([4, 6])
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.save()
                p.translate(cx, cy)
                p.rotate(self._ring_angle + angle_offset)
                p.drawEllipse(QPoint(0, 0), ring_r, ring_r)
                p.restore()

        # ── logo icon ──────────────────────────────
        alpha = int(255 * self._logo_alpha)
        p.setPen(QColor(0, 200, 255, alpha))
        icon_font = QFont("Segoe UI", 52, QFont.Weight.Bold)
        p.setFont(icon_font)
        glyph = "◈"
        ir = QRectF(cx - 60, cy - 140, 120, 100)
        p.drawText(ir, Qt.AlignmentFlag.AlignCenter, glyph)

        # ── title ───────────────────────────────────
        # glow passes
        for layer in range(4, 0, -1):
            ga = int(40 * layer / 4 * self._logo_alpha)
            for dx in [-layer, 0, layer]:
                for dy in [-layer, 0, layer]:
                    p.setPen(QColor(0, 200, 255, ga))
                    tf = QFont("Segoe UI", 36, QFont.Weight.Bold)
                    p.setFont(tf)
                    p.drawText(QRectF(cx - 200 + dx, cy - 60 + dy, 400, 60),
                               Qt.AlignmentFlag.AlignCenter, "INFINITY HUB")
        p.setPen(QColor(255, 255, 255, alpha))
        p.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        p.drawText(QRectF(cx - 200, cy - 60, 400, 60),
                   Qt.AlignmentFlag.AlignCenter, "INFINITY HUB")

        # subtitle
        p.setPen(QColor(0, 200, 255, int(180 * self._logo_alpha)))
        p.setFont(QFont("Segoe UI", 11))
        sub = "GAMING OPTIMIZATION SUITE"
        p.drawText(QRectF(cx - 200, cy - 8, 400, 30),
                   Qt.AlignmentFlag.AlignCenter, sub)

        # ── progress bar ────────────────────────────
        bar_y = h - 80
        bar_w = int(w * 0.6)
        bar_x = (w - bar_w) // 2
        bar_h = 4

        # track
        p.setBrush(QColor(255, 255, 255, 18))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 2, 2)

        # fill
        fill_w = int(bar_w * self._progress / 100.0)
        if fill_w > 0:
            fg = QLinearGradient(bar_x, 0, bar_x + fill_w, 0)
            fg.setColorAt(0, QColor(0, 150, 255))
            fg.setColorAt(1, QColor(0, 255, 212))
            p.setBrush(QBrush(fg))
            p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 2, 2)

            # glow
            for bw, ba in [(8, 30), (4, 60)]:
                p.setPen(QPen(QColor(0, 200, 255, ba), bw))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 2, 2)

        # progress text
        p.setPen(QColor(255, 255, 255, int(180 * self._logo_alpha)))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(QRectF(bar_x, bar_y + 12, bar_w, 20),
                   Qt.AlignmentFlag.AlignCenter,
                   f"Initializing system modules… {int(self._progress)}%")

        # ── fade overlay ────────────────────────────
        if self._fade_out_alpha > 0:
            p.setBrush(QColor(6, 6, 14, int(255 * self._fade_out_alpha)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(self.rect())

        p.end()

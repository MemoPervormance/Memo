from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                              QLabel, QHBoxLayout, QSpacerItem,
                              QSizePolicy, QScrollArea, QFrame)
from PyQt6.QtGui import (QPainter, QColor, QPen, QLinearGradient,
                         QBrush, QFont, QRadialGradient)
from PyQt6.QtCore import (Qt, QPropertyAnimation, QEasingCurve,
                           pyqtProperty, pyqtSignal, QPoint, QTimer, QRect)

from app.core.app_state import get_state

NAV_ITEMS = [
    ("dashboard",    "⬡",  "DASHBOARD"),
    ("fps",          "⚡",  "FPS"),
    ("ping",         "📡",  "PING"),
    ("delay",        "⌨️",  "DELAY"),
    ("aim",          "🎯",  "AIM"),
    ("recoil",       "🔫",  "RECOIL"),
    ("bloom",        "👁️",  "BLOOM"),
    ("system",       "🖥️",  "SYSTEM"),
    ("game",         "🎮",  "GAME"),
    ("bios",         "🔬",  "BIOS"),
    ("playstation",  "🎮",  "PS4/5"),
    ("xbox",         "🟢",  "XBOX"),
    ("macros",       "🤖",  "MACROS"),
    ("favorites",    "★",   "FAVORITES"),
]

W_COLLAPSED = 68
W_EXPANDED  = 220


class NavButton(QPushButton):
    """Single sidebar navigation button."""

    def __init__(self, page_id: str, icon: str, label: str, parent=None):
        super().__init__(parent)
        self._page_id = page_id
        self._icon = icon
        self._label = label
        self._active = False
        self._hover = False
        self._expanded = True
        self._glow = 0.0
        self.setFixedHeight(46)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(False)

        self._glow_anim = QPropertyAnimation(self, b"glowValue", self)
        self._glow_anim.setDuration(220)
        self._glow_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_glow_value(self) -> float:
        return self._glow

    def set_glow_value(self, v: float):
        self._glow = v
        self.update()

    glowValue = pyqtProperty(float, get_glow_value, set_glow_value)

    def set_active(self, active: bool):
        self._active = active
        self.update()

    def set_expanded(self, exp: bool):
        self._expanded = exp
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # background
        if self._active:
            bg = QLinearGradient(0, 0, w, 0)
            bg.setColorAt(0, QColor(0, 200, 255, 45))
            bg.setColorAt(1, QColor(0, 200, 255, 5))
            p.setBrush(QBrush(bg))
        elif self._hover:
            p.setBrush(QColor(255, 255, 255, 12))
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(4, 2, w - 8, h - 4, 8, 8)

        # active indicator bar
        if self._active:
            bar_grad = QLinearGradient(0, 0, 0, h)
            bar_grad.setColorAt(0, QColor(0, 220, 255, 255))
            bar_grad.setColorAt(1, QColor(100, 180, 255, 200))
            p.setBrush(QBrush(bar_grad))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(0, 10, 3, h - 20, 2, 2)

        # glow on hover
        if self._glow > 0:
            glow = QRadialGradient(24, h // 2, 30)
            glow.setColorAt(0, QColor(0, 200, 255, int(60 * self._glow)))
            glow.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(glow))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPoint(24, h // 2), 30, 30)

        # icon
        icon_color = QColor(0, 200, 255) if self._active else \
                     QColor(200, 200, 220) if self._hover else QColor(120, 120, 150)
        p.setPen(icon_color)
        p.setFont(QFont("Segoe UI Emoji", 16))
        icon_rect = QRect(12, 0, 32, h)
        p.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, self._icon)

        # label (only when expanded)
        if self._expanded:
            lbl_color = QColor(255, 255, 255) if self._active else \
                        QColor(210, 210, 235) if self._hover else QColor(130, 130, 155)
            p.setPen(lbl_color)
            font = QFont("Segoe UI", 11, QFont.Weight.DemiBold if self._active else QFont.Weight.Normal)
            p.setFont(font)
            p.drawText(QRect(52, 0, w - 60, h), Qt.AlignmentFlag.AlignVCenter, self._label)
        p.end()

    def enterEvent(self, event):
        self._hover = True
        self._glow_anim.stop()
        self._glow_anim.setStartValue(self._glow)
        self._glow_anim.setEndValue(1.0)
        self._glow_anim.start()

    def leaveEvent(self, event):
        self._hover = False
        self._glow_anim.stop()
        self._glow_anim.setStartValue(self._glow)
        self._glow_anim.setEndValue(0.0)
        self._glow_anim.start()


class Sidebar(QWidget):
    """Animated collapsible sidebar navigation."""

    page_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = get_state()
        self._expanded = True
        self._current = "dashboard"
        self._buttons: dict[str, NavButton] = {}

        self.setFixedWidth(W_EXPANDED)
        self._width_anim = QPropertyAnimation(self, b"sidebarWidth", self)
        self._width_anim.setDuration(280)
        self._width_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── logo area ──────────────────────────────
        logo_area = QWidget(self)
        logo_area.setFixedHeight(72)
        la = QHBoxLayout(logo_area)
        la.setContentsMargins(14, 0, 14, 0)

        self._logo_icon = QLabel("◈", logo_area)
        self._logo_icon.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self._logo_icon.setStyleSheet("color: #00C8FF; background: transparent;")
        la.addWidget(self._logo_icon)

        self._logo_text = QLabel("INFINITY HUB", logo_area)
        self._logo_text.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._logo_text.setStyleSheet("color: #FFFFFF; letter-spacing: 1px; background: transparent;")
        la.addWidget(self._logo_text)
        la.addStretch()
        outer.addWidget(logo_area)

        # divider
        div = QFrame(self)
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(0,200,255,0.15);")
        outer.addWidget(div)

        # ── nav buttons ────────────────────────────
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(4, 8, 4, 8)
        nav_layout.setSpacing(2)

        for pid, icon, label in NAV_ITEMS:
            btn = NavButton(pid, icon, label, nav_container)
            btn.clicked.connect(lambda _, p=pid: self._on_nav(p))
            nav_layout.addWidget(btn)
            self._buttons[pid] = btn

        nav_layout.addStretch()
        scroll.setWidget(nav_container)
        outer.addWidget(scroll, stretch=1)

        # ── toggle button ──────────────────────────
        div2 = QFrame(self)
        div2.setFixedHeight(1)
        div2.setStyleSheet("background: rgba(255,255,255,0.08);")
        outer.addWidget(div2)

        self._toggle_btn = QPushButton("◀", self)
        self._toggle_btn.setFixedHeight(44)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: rgba(255,255,255,0.4); font-size: 12px;
            }
            QPushButton:hover { color: #00C8FF; }
        """)
        self._toggle_btn.clicked.connect(self.toggle)
        outer.addWidget(self._toggle_btn)

        self._set_active("dashboard")

    # ── animated width property ────────────────────
    def get_sidebar_width(self) -> int:
        return self.width()

    def set_sidebar_width(self, v: int):
        self.setFixedWidth(v)

    sidebarWidth = pyqtProperty(int, get_sidebar_width, set_sidebar_width)

    def toggle(self):
        self._expanded = not self._expanded
        target = W_EXPANDED if self._expanded else W_COLLAPSED
        self._width_anim.stop()
        self._width_anim.setStartValue(self.width())
        self._width_anim.setEndValue(target)
        self._width_anim.start()
        self._toggle_btn.setText("◀" if self._expanded else "▶")
        self._logo_text.setVisible(self._expanded)
        for btn in self._buttons.values():
            btn.set_expanded(self._expanded)

    def _on_nav(self, page_id: str):
        self._set_active(page_id)
        self.page_requested.emit(page_id)

    def _set_active(self, page_id: str):
        for pid, btn in self._buttons.items():
            btn.set_active(pid == page_id)
        self._current = page_id

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # glass sidebar bg
        bg = QLinearGradient(0, 0, self.width(), 0)
        bg.setColorAt(0, QColor(10, 10, 22, 245))
        bg.setColorAt(1, QColor(14, 14, 28, 245))
        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect())

        # right border glow
        for w, a in [(6, 15), (2, 40), (1, 80)]:
            p.setPen(QPen(QColor(0, 200, 255, a), w))
            p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        p.end()

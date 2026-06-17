from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout,
                              QVBoxLayout, QLabel, QPushButton,
                              QSizeGrip, QFrame)
from PyQt6.QtGui import (QPainter, QColor, QPen, QLinearGradient,
                         QBrush, QFont, QIcon, QCursor)
from PyQt6.QtCore import (Qt, QPoint, QSize, QPropertyAnimation,
                          QEasingCurve, pyqtProperty, QRect)

from app.core.app_state import get_state
from app.sidebar.sidebar_widget import Sidebar
from app.animations.transitions import FadeStackedWidget
from app.pages.dashboard_page import DashboardPage
from app.pages.base_page import BasePage
from app.pages.favorites_page import FavoritesPage
from app.data.page_definitions import ALL_PAGES, PAGE_MAP


class TitleBar(QWidget):
    """Custom frameless title bar with drag, minimize, maximize, close."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self._drag_pos: QPoint | None = None
        self._main = parent

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(0)

        # logo mini
        logo = QLabel("◈  INFINITY HUB")
        logo.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        logo.setStyleSheet("color: rgba(255,255,255,0.6); background: transparent; letter-spacing: 1px;")
        layout.addWidget(logo)
        layout.addStretch()

        # window controls
        for icon, tooltip, cb, color in [
            ("—", "Minimize", self._minimize, "#AAAAAA"),
            ("□", "Maximize", self._maximize, "#AAAAAA"),
            ("✕", "Close",    self._close,    "#FF3D5A"),
        ]:
            btn = QPushButton(icon)
            btn.setFixedSize(38, 38)
            btn.setToolTip(tooltip)
            btn.setFont(QFont("Segoe UI", 12))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: none; color: {color};
                    font-size: 13px;
                }}
                QPushButton:hover {{ background: rgba(255,255,255,0.08); border-radius: 6px; }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(cb)
            layout.addWidget(btn)

    def _minimize(self):
        if self._main:
            self._main.showMinimized()

    def _maximize(self):
        if self._main:
            if self._main.isMaximized():
                self._main.showNormal()
            else:
                self._main.showMaximized()

    def _close(self):
        if self._main:
            self._main.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - \
                             self._main.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self._main.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setBrush(QColor(8, 8, 18, 240))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect())
        p.setPen(QPen(QColor(0, 200, 255, 30), 1))
        p.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        p.end()


class MainWindow(QMainWindow):
    """Main application window: frameless, dark, neon-accented."""

    def __init__(self):
        super().__init__()
        self._state = get_state()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(1200, 750)
        self.resize(1400, 860)
        self.setWindowTitle("Infinity Hub — Gaming Optimization Suite")

        # ── central widget ─────────────────────────
        root = QWidget(self)
        self.setCentralWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # title bar
        self._title_bar = TitleBar(self)
        root_layout.addWidget(self._title_bar)

        # body: sidebar + content
        body = QWidget(root)
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        root_layout.addWidget(body, stretch=1)

        # sidebar
        self._sidebar = Sidebar(body)
        self._sidebar.page_requested.connect(self._navigate)
        body_layout.addWidget(self._sidebar)

        # stacked content
        self._stack = FadeStackedWidget(body)
        body_layout.addWidget(self._stack, stretch=1)

        # ── build pages ────────────────────────────
        self._page_indices: dict[str, int] = {}

        # dashboard
        dash = DashboardPage(self._stack)
        idx = self._stack.addWidget(dash)
        self._page_indices["dashboard"] = idx

        # all category pages (data-driven)
        for page_def in ALL_PAGES:
            page = BasePage(page_def, self._stack)
            idx = self._stack.addWidget(page)
            self._page_indices[page_def["id"]] = idx

        # favorites
        fav = FavoritesPage(self._stack)
        idx = self._stack.addWidget(fav)
        self._page_indices["favorites"] = idx

        # start on dashboard
        self._stack.setCurrentIndex(0)
        self._state.page_changed.connect(self._navigate)

    def _navigate(self, page_id: str):
        if page_id in self._page_indices:
            self._stack.slide_to(self._page_indices[page_id])
            self._sidebar._set_active(page_id)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # outer shadow/border
        r = self.rect().adjusted(1, 1, -1, -1)
        for w, a in [(8, 10), (3, 25), (1, 70)]:
            p.setPen(QPen(QColor(0, 200, 255, a), w))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r, 12, 12)

        # background
        bg = QLinearGradient(0, 0, 0, self.height())
        bg.setColorAt(0, QColor(8, 8, 18))
        bg.setColorAt(1, QColor(6, 6, 14))
        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 12, 12)
        p.end()

    # ── resize grip / drag support ─────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() > self.height() - 10:
                self._resizing = True
                self._resize_start = event.globalPosition().toPoint()
                self._resize_size = self.size()
            else:
                self._resizing = False

    def mouseMoveEvent(self, event):
        if hasattr(self, '_resizing') and self._resizing:
            delta = event.globalPosition().toPoint() - self._resize_start
            new_w = max(self.minimumWidth(),  self._resize_size.width()  + delta.x())
            new_h = max(self.minimumHeight(), self._resize_size.height() + delta.y())
            self.resize(new_w, new_h)

    def mouseReleaseEvent(self, event):
        self._resizing = False

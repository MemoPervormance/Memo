"""
Data-driven page renderer. Reads a PAGE definition dict and builds
a full accordion UI with NeonToggle, tooltips, search, and favorites.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QScrollArea, QFrame, QPushButton, QSizePolicy)
from PyQt6.QtGui import (QPainter, QColor, QPen, QLinearGradient,
                         QBrush, QFont, QPixmap)
from PyQt6.QtCore import Qt, QSize, QPoint, pyqtSignal, QPropertyAnimation, QEasingCurve

from app.components.accordion import AccordionSection
from app.components.neon_toggle import NeonToggle
from app.components.glass_card import GlassCard
from app.components.glow_label import GlowLabel
from app.components.search_bar import SearchBar
from app.components.tooltip_popup import TooltipPopup
from app.core.app_state import get_state


class SettingRow(QWidget):
    """Single setting row: label, description, favorite star, toggle."""

    def __init__(self, setting: dict, accent: str = "#00C8FF", parent=None):
        super().__init__(parent)
        self._setting = setting
        self._state = get_state()
        self._accent = accent
        self._hover = False
        self.setMouseTracking(True)
        self.setMinimumHeight(52)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(10)

        # title + description
        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        self._title_lbl = QLabel(setting["title"], self)
        self._title_lbl.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 600; background: transparent;")
        text_col.addWidget(self._title_lbl)

        desc = setting.get("description", "")
        if desc:
            self._desc_lbl = QLabel(desc[:80] + ("…" if len(desc) > 80 else ""), self)
            self._desc_lbl.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 11px; background: transparent;")
            text_col.addWidget(self._desc_lbl)

        layout.addLayout(text_col, stretch=1)

        # category tag
        cat = setting.get("category", "")
        if cat:
            cat_lbl = QLabel(cat, self)
            cat_lbl.setFixedHeight(20)
            cat_lbl.setStyleSheet(f"""
                QLabel {{
                    color: {accent}; font-size: 10px; font-weight: 700;
                    background: rgba(0,200,255,0.10);
                    border: 1px solid rgba(0,200,255,0.30);
                    border-radius: 4px; padding: 0 6px;
                }}
            """)
            layout.addWidget(cat_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)

        # favorite star
        sid = setting["id"]
        self._fav_btn = QPushButton(self)
        self._fav_btn.setFixedSize(28, 28)
        self._fav_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_fav_style()
        self._fav_btn.clicked.connect(self._toggle_favorite)
        layout.addWidget(self._fav_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        # toggle
        checked = self._state.get(sid, setting.get("default", False))
        self._toggle = NeonToggle(self, checked=bool(checked), accent=accent)
        self._toggle.toggled.connect(self._on_toggled)
        layout.addWidget(self._toggle, alignment=Qt.AlignmentFlag.AlignVCenter)

        self._state.favorites_changed.connect(self._update_fav_style)

    def _on_toggled(self, state: bool):
        self._state.set(self._setting["id"], state)

    def _toggle_favorite(self):
        self._state.toggle_favorite(self._setting["id"])

    def _update_fav_style(self):
        is_fav = self._state.is_favorite(self._setting["id"])
        self._fav_btn.setText("★" if is_fav else "☆")
        color = "#FFB800" if is_fav else "rgba(255,255,255,0.25)"
        self._fav_btn.setStyleSheet(f"""
            QPushButton {{
                color: {color}; font-size: 16px; background: transparent; border: none;
            }}
            QPushButton:hover {{ color: #FFB800; }}
        """)

    def matches_search(self, query: str) -> bool:
        if not query:
            return True
        q = query.lower()
        s = self._setting
        return (q in s.get("title", "").lower() or
                q in s.get("description", "").lower() or
                q in s.get("category", "").lower() or
                q in s.get("effect", "").lower())

    def set_visible_by_search(self, query: str):
        self.setVisible(self.matches_search(query))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hover:
            p.setBrush(QColor(0, 200, 255, 12))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(self.rect().adjusted(2, 1, -2, -1), 8, 8)
        p.end()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()


class PageHeader(QWidget):
    """Top header bar for a page with icon, title, gradient strip."""

    def __init__(self, title: str, subtitle: str, icon: str,
                 accent: str = "#00C8FF", parent=None):
        super().__init__(parent)
        self._accent = QColor(accent)
        self.setFixedHeight(100)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 0, 28, 0)
        layout.setSpacing(18)

        # icon bubble
        icon_frame = QWidget(self)
        icon_frame.setFixedSize(60, 60)
        icon_lbl = QLabel(icon, icon_frame)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 24))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setGeometry(0, 0, 60, 60)
        icon_lbl.setStyleSheet("background: transparent; color: #FFFFFF;")
        layout.addWidget(icon_frame)

        # text
        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        title_lbl = GlowLabel(title, self, color=accent, font_size=22, glow_layers=3)
        title_lbl.setFixedHeight(36)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        text_col.addWidget(title_lbl)

        sub_lbl = QLabel(subtitle, self)
        sub_lbl.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 12px; background: transparent;")
        text_col.addWidget(sub_lbl)

        layout.addLayout(text_col, stretch=1)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()

        # gradient bg
        bg = QLinearGradient(0, 0, self.width(), 0)
        bg.setColorAt(0, QColor(self._accent.red(), self._accent.green(),
                                self._accent.blue(), 25))
        bg.setColorAt(0.6, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(r)

        # bottom line
        p.setPen(QPen(QColor(self._accent.red(), self._accent.green(),
                             self._accent.blue(), 60), 1))
        p.drawLine(0, r.height() - 1, r.width(), r.height() - 1)
        p.end()


class BasePage(QWidget):
    """Generic page that renders from a PAGE definition dict."""

    def __init__(self, page_def: dict, parent=None):
        super().__init__(parent)
        self._page_def = page_def
        self._accent = page_def.get("accent", "#00C8FF")
        self._all_rows: list[SettingRow] = []
        self._sections: list[AccordionSection] = []
        self._tooltip = TooltipPopup()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # header
        header = PageHeader(page_def["title"], page_def.get("subtitle", ""),
                            page_def.get("icon", "◆"), self._accent, self)
        outer.addWidget(header)

        # search
        search_wrap = QWidget(self)
        sl = QHBoxLayout(search_wrap)
        sl.setContentsMargins(16, 10, 16, 6)
        self._search = SearchBar(parent=search_wrap)
        self._search.search_changed.connect(self._on_search)
        sl.addWidget(self._search)
        outer.addWidget(search_wrap)

        # scroll area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll, stretch=1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 8, 16, 24)
        content_layout.setSpacing(6)
        scroll.setWidget(content)

        # build sections
        for sec in page_def.get("sections", []):
            accordion = AccordionSection(
                sec["title"], sec.get("icon", "◆"),
                accent=self._accent, parent=content
            )
            for setting in sec.get("settings", []):
                row = SettingRow(setting, self._accent, accordion)
                accordion.add_widget(row)
                self._all_rows.append(row)
                self._install_tooltip(row, setting)
            content_layout.addWidget(accordion)
            self._sections.append(accordion)

        content_layout.addStretch()

    def _install_tooltip(self, row: SettingRow, setting: dict):
        orig_enter = row.enterEvent
        orig_leave = row.leaveEvent

        def on_enter(event, s=setting, r=row):
            orig_enter(event)
            gp = r.mapToGlobal(QPoint(r.width() // 2, r.height()))
            self._tooltip.cancel_hide()
            self._tooltip.show_for(
                title=s["title"],
                description=s.get("description", ""),
                effect=s.get("effect", ""),
                recommendation=s.get("recommendation", ""),
                risk=s.get("risk", "Low"),
                category=s.get("category", ""),
                pos=gp
            )

        def on_leave(event):
            orig_leave(event)
            self._tooltip.schedule_hide(300)

        row.enterEvent = on_enter
        row.leaveEvent = on_leave

    def _on_search(self, query: str):
        for row in self._all_rows:
            row.set_visible_by_search(query)

    def get_matching_settings(self, query: str) -> list[dict]:
        """Return settings matching the query — used by global search."""
        results = []
        for row in self._all_rows:
            if row.matches_search(query):
                results.append(row._setting)
        return results

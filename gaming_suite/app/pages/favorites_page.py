from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QScrollArea, QFrame)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from app.components.glass_card import GlassCard
from app.components.glow_label import GlowLabel
from app.components.neon_toggle import NeonToggle
from app.core.app_state import get_state
from app.data.page_definitions import ALL_PAGES


def _find_setting(sid: str) -> dict | None:
    for page in ALL_PAGES:
        for sec in page.get("sections", []):
            for s in sec.get("settings", []):
                if s["id"] == sid:
                    return s
    return None


class FavRow(QWidget):
    def __init__(self, setting: dict, parent=None):
        super().__init__(parent)
        self._setting = setting
        self._state = get_state()
        self.setMinimumHeight(54)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(12)

        star = QLabel("★")
        star.setStyleSheet("color: #FFB800; font-size: 18px; background: transparent;")
        layout.addWidget(star)

        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel(setting["title"])
        t.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 600; background: transparent;")
        col.addWidget(t)
        cat = QLabel(setting.get("category", ""))
        cat.setStyleSheet("color: rgba(0,200,255,0.7); font-size: 11px; background: transparent;")
        col.addWidget(cat)
        layout.addLayout(col, stretch=1)

        toggle = NeonToggle(self, checked=bool(self._state.get(setting["id"], False)))
        toggle.toggled.connect(lambda s, sid=setting["id"]: self._state.set(sid, s))
        layout.addWidget(toggle)


class FavoritesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = get_state()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # header
        hdr = QWidget(self)
        hdr.setFixedHeight(80)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(24, 0, 24, 0)
        t = GlowLabel("★  FAVORITES", hdr, color="#FFB800", font_size=22, glow_layers=4)
        t.setFixedHeight(40)
        t.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        hl.addWidget(t)
        outer.addWidget(hdr)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll, stretch=1)

        self._content = QWidget()
        self._cl = QVBoxLayout(self._content)
        self._cl.setContentsMargins(16, 8, 16, 24)
        self._cl.setSpacing(6)
        scroll.setWidget(self._content)

        self._state.favorites_changed.connect(self._rebuild)
        self._rebuild()

    def _rebuild(self):
        # clear
        while self._cl.count():
            item = self._cl.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        favs = self._state.get_favorites()
        if not favs:
            empty = QLabel("No favorites yet.\nHover over a setting and click ☆ to add it here.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: rgba(255,255,255,0.25); font-size: 14px; background: transparent;")
            self._cl.addStretch()
            self._cl.addWidget(empty)
            self._cl.addStretch()
            return

        card = GlassCard(self._content, accent="#FFB800")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 4, 0, 4)
        card_lay.setSpacing(0)

        for sid in favs:
            s = _find_setting(sid)
            if s:
                row = FavRow(s, card)
                card_lay.addWidget(row)

        self._cl.addWidget(card)
        self._cl.addStretch()

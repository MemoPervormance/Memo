from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient, QBrush, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QTimer


class SearchBar(QWidget):
    search_changed = pyqtSignal(str)

    def __init__(self, placeholder: str = "Search settings, features, optimizations…",
                 parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)

        icon = QLabel("🔍", self)
        icon.setFixedSize(20, 20)
        icon.setStyleSheet("color: rgba(0,200,255,0.7); font-size: 14px; background: transparent;")
        layout.addWidget(icon)

        self._input = QLineEdit(self)
        self._input.setPlaceholderText(placeholder)
        self._input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit::placeholder { color: rgba(255,255,255,0.3); }
        """)
        layout.addWidget(self._input)

        # debounce timer
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._emit)
        self._input.textChanged.connect(lambda _: self._timer.start(180))

    def _emit(self):
        self.search_changed.emit(self._input.text().strip())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)

        # glass bg
        p.setBrush(QColor(0, 200, 255, 12))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 12, 12)

        # border
        focused = self._input.hasFocus()
        for w, a in ([(4, 20), (1, 80)] if focused else [(1, 50)]):
            p.setPen(QPen(QColor(0, 200, 255, a), w))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r, 12, 12)
        p.end()

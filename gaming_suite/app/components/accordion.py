from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                              QSizePolicy, QFrame, QScrollArea, QLabel)
from PyQt6.QtGui import (QPainter, QColor, QPen, QLinearGradient,
                         QBrush, QFont, QIcon, QPolygon, QPainterPath)
from PyQt6.QtCore import (Qt, QPropertyAnimation, QEasingCurve,
                          pyqtProperty, QPoint, QSize, pyqtSignal)


class AccordionHeader(QPushButton):
    def __init__(self, title: str, icon: str = "▶",
                 accent: str = "#00C8FF", parent=None):
        super().__init__(parent)
        self._title = title
        self._icon_char = icon
        self._accent = QColor(accent)
        self._expanded = False
        self._hover = False
        self._arrow_angle = 0.0
        self.setFixedHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._arrow_anim = QPropertyAnimation(self, b"arrowAngle", self)
        self._arrow_anim.setDuration(250)
        self._arrow_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_arrow_angle(self) -> float:
        return self._arrow_angle

    def set_arrow_angle(self, v: float):
        self._arrow_angle = v
        self.update()

    arrowAngle = pyqtProperty(float, get_arrow_angle, set_arrow_angle)

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        self._arrow_anim.stop()
        self._arrow_anim.setStartValue(self._arrow_angle)
        self._arrow_anim.setEndValue(90.0 if expanded else 0.0)
        self._arrow_anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        r = self.rect().adjusted(0, 1, 0, -1)

        # background
        if self._hover or self._expanded:
            bg = QLinearGradient(0, 0, w, 0)
            bg.setColorAt(0, QColor(0, 200, 255, 18 if not self._expanded else 28))
            bg.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(bg))
        else:
            p.setBrush(QColor(255, 255, 255, 5))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 8, 8)

        # left accent bar
        if self._expanded:
            p.setBrush(QColor(0, 200, 255, 200))
            p.drawRoundedRect(0, 8, 3, h - 16, 1, 1)

        # icon
        icon_color = self._accent if self._expanded else QColor(180, 180, 210)
        p.setPen(icon_color)
        icon_font = QFont("Segoe UI Emoji", 14)
        p.setFont(icon_font)
        p.drawText(QPoint(14, h // 2 + 6), self._icon_char)

        # title
        title_color = QColor(255, 255, 255) if self._expanded else QColor(210, 210, 230)
        p.setPen(title_color)
        title_font = QFont("Segoe UI", 12, QFont.Weight.DemiBold)
        p.setFont(title_font)
        p.drawText(QPoint(44, h // 2 + 5), self._title)

        # animated arrow
        p.save()
        arrow_x = w - 24
        arrow_y = h // 2
        p.translate(arrow_x, arrow_y)
        p.rotate(self._arrow_angle)
        arrow_color = self._accent if self._expanded else QColor(100, 100, 130)
        p.setPen(QPen(arrow_color, 2, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawLine(-4, -3, 0, 3)
        p.drawLine(0, 3, 4, -3)
        p.restore()
        p.end()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()


class AccordionSection(QWidget):
    """Expandable accordion section with animated height."""

    def __init__(self, title: str, icon: str = "◆",
                 accent: str = "#00C8FF",
                 start_expanded: bool = False,
                 parent=None):
        super().__init__(parent)
        self._expanded = False
        self._content_height = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 4)
        outer.setSpacing(0)

        self._header = AccordionHeader(title, icon, accent, self)
        self._header.clicked.connect(self._toggle)
        outer.addWidget(self._header)

        # content container
        self._content_wrap = QWidget(self)
        self._content_wrap.setMaximumHeight(0)
        self._content_wrap.setMinimumHeight(0)
        outer.addWidget(self._content_wrap)

        self._content_layout = QVBoxLayout(self._content_wrap)
        self._content_layout.setContentsMargins(12, 4, 4, 8)
        self._content_layout.setSpacing(2)

        # height animation
        self._height_anim = QPropertyAnimation(self._content_wrap, b"maximumHeight", self)
        self._height_anim.setDuration(300)
        self._height_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._height_anim.finished.connect(self._on_anim_done)

        if start_expanded:
            self.expand(animate=False)

    def add_widget(self, widget: QWidget):
        self._content_layout.addWidget(widget)

    def _toggle(self):
        if self._expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self, animate: bool = True):
        self._expanded = True
        self._header.set_expanded(True)
        self._content_wrap.setMinimumHeight(0)
        target = self._content_wrap.sizeHint().height() or 200
        if animate:
            self._height_anim.stop()
            self._height_anim.setStartValue(self._content_wrap.maximumHeight())
            self._height_anim.setEndValue(target + 20)
            self._height_anim.start()
        else:
            self._content_wrap.setMaximumHeight(target + 20)

    def collapse(self):
        self._expanded = False
        self._header.set_expanded(False)
        self._height_anim.stop()
        self._height_anim.setStartValue(self._content_wrap.maximumHeight())
        self._height_anim.setEndValue(0)
        self._height_anim.start()

    def _on_anim_done(self):
        if self._expanded:
            self._content_wrap.setMaximumHeight(9999)

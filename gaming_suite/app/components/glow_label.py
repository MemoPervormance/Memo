from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QLinearGradient, QBrush
from PyQt6.QtCore import Qt, QRectF


class GlowLabel(QLabel):
    """
    Label with neon text glow effect.
    glow_layers: number of glow passes (more = brighter)
    gradient: if True, text is rendered with blue→purple gradient
    """

    def __init__(self, text: str = "", parent=None,
                 color: str = "#00C8FF",
                 glow_layers: int = 4,
                 gradient: bool = False,
                 font_size: int = 14,
                 bold: bool = True):
        super().__init__(text, parent)
        self._color = QColor(color)
        self._glow_layers = glow_layers
        self._gradient = gradient
        self._font_size = font_size
        self._bold = bold
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold if bold else QFont.Weight.Normal)
        self.setFont(font)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing,  True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        rect = QRectF(self.rect())
        text = self.text()
        flags = int(self.alignment())

        # glow layers
        for layer in range(self._glow_layers, 0, -1):
            alpha = int(50 * layer / self._glow_layers)
            glow_color = QColor(self._color.red(),
                                self._color.green(),
                                self._color.blue(), alpha)
            p.setPen(glow_color)
            for dx in [-layer, 0, layer]:
                for dy in [-layer, 0, layer]:
                    p.drawText(rect.translated(dx * 0.5, dy * 0.5),
                               flags, text)

        # actual text
        p.setPen(self._color)
        p.drawText(rect, flags, text)
        p.end()

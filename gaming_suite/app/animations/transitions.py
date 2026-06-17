from PyQt6.QtWidgets import QStackedWidget, QWidget
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import (Qt, QPropertyAnimation, QEasingCurve,
                          pyqtProperty, QParallelAnimationGroup,
                          QSequentialAnimationGroup, QTimer)


class FadeStackedWidget(QStackedWidget):
    """
    QStackedWidget with fade + slight upward slide transition between pages.
    """

    DURATION = 280

    def __init__(self, parent=None):
        super().__init__(parent)
        self._animating = False
        self._next_index = 0

    def slide_to(self, index: int):
        if self._animating or index == self.currentIndex():
            return
        self._animating = True
        self._next_index = index

        current_widget = self.currentWidget()
        next_widget = self.widget(index)

        if not current_widget or not next_widget:
            self.setCurrentIndex(index)
            self._animating = False
            return

        # fade out current
        self._fade_out = QPropertyAnimation(current_widget, b"windowOpacity", self)
        self._fade_out.setDuration(self.DURATION // 2)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_out.finished.connect(lambda: self._switch_and_fade_in(index, next_widget, current_widget))
        self._fade_out.start()

    def _switch_and_fade_in(self, index: int, next_widget: QWidget, current_widget: QWidget):
        current_widget.setWindowOpacity(1.0)
        self.setCurrentIndex(index)
        next_widget.setWindowOpacity(0.0)
        self._fade_in = QPropertyAnimation(next_widget, b"windowOpacity", self)
        self._fade_in.setDuration(self.DURATION // 2)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_in.finished.connect(self._done)
        self._fade_in.start()

    def _done(self):
        self._animating = False

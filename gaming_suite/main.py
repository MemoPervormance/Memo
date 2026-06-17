"""
INFINITY HUB — Gaming Optimization Suite
Entry point: shows splash screen, then launches main window.
"""
import sys
import os

# ensure repo root is on path when frozen or run directly
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from app.themes.dark_neon import QSS
from app.core.splash_screen import SplashScreen
from app.core.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Infinity Hub")
    app.setOrganizationName("InfinityHub")
    app.setStyleSheet(QSS)

    # default font
    font = QFont("Segoe UI", 12)
    app.setFont(font)

    # high-DPI
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    window = MainWindow()

    def launch():
        window.show()
        # subtle fade-in
        window.setWindowOpacity(0.0)
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
        anim = QPropertyAnimation(window, b"windowOpacity")
        anim.setDuration(400)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        # keep reference so it's not garbage-collected
        window._launch_anim = anim

    splash = SplashScreen(on_done=launch)
    splash.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

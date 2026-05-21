"""
Game overlay — transparent click-through window drawn over screen.
Renders detection boxes, future position dots, target icons, capture border.
Windows only (layered window via win32api).
Requires: pip install pywin32
"""
from __future__ import annotations
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

from config import OverlayConfig
from detector_yolo import Detection


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    WS_EX_TOPMOST     = 0x00000008
    WS_EX_LAYERED     = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_NOACTIVATE  = 0x08000000
    WS_POPUP          = 0x80000000
    WS_VISIBLE        = 0x10000000
    LWA_ALPHA         = 0x00000002
    LWA_COLORKEY      = 0x00000001
    SWP_NOSIZE        = 0x0001
    SWP_NOMOVE        = 0x0002
    SWP_NOACTIVATE    = 0x0010
    HWND_TOPMOST      = -1


class OverlayWindow:
    """
    Transparent topmost overlay window.
    Falls back to a no-op stub if win32 is unavailable or overlay is disabled.
    """

    def __init__(self, cfg: OverlayConfig) -> None:
        self._cfg   = cfg
        self._hwnd  = None
        self._icons: dict = {}
        self._lock  = threading.Lock()
        self._detections: List[Detection]           = []
        self._future_dots: List[Tuple[float, float]] = []
        self._running = False
        self._thread: Optional[threading.Thread]    = None

        if sys.platform == "win32" and cfg.enabled:
            self._start()

    def update_config(self, cfg: OverlayConfig) -> None:
        with self._lock:
            self._cfg = cfg

    def update_frame(
        self,
        detections: List[Detection],
        future_dots: Optional[List[Tuple[float, float]]] = None,
    ) -> None:
        with self._lock:
            self._detections  = detections
            self._future_dots = future_dots or []

    def stop(self) -> None:
        self._running = False

    # ------------------------------------------------------------------

    def _start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="overlay")
        self._thread.start()

    def _run(self) -> None:
        try:
            import win32api   # type: ignore[import]
            import win32con   # type: ignore[import]
            import win32gui   # type: ignore[import]
            import win32ui    # type: ignore[import]
        except ImportError:
            return

        sw = win32api.GetSystemMetrics(0)
        sh = win32api.GetSystemMetrics(1)

        wnd_class = win32gui.WNDCLASS()
        wnd_class.lpfnWndProc = win32gui.DefWindowProc
        wnd_class.hInstance   = win32api.GetModuleHandle(None)
        wnd_class.lpszClassName = "MaxAIOverlay"
        try:
            win32gui.RegisterClass(wnd_class)
        except Exception:
            pass

        hwnd = win32gui.CreateWindowEx(
            WS_EX_TOPMOST | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE,
            "MaxAIOverlay", "",
            WS_POPUP | WS_VISIBLE,
            0, 0, sw, sh,
            None, None, wnd_class.hInstance, None,
        )
        alpha = int(self._cfg.opacity * 255)
        win32gui.SetLayeredWindowAttributes(hwnd, 0x000000, alpha, LWA_ALPHA | LWA_COLORKEY)
        self._hwnd = hwnd

        while self._running:
            with self._lock:
                cfg  = self._cfg
                dets = list(self._detections)
                dots = list(self._future_dots)

            if not cfg.enabled:
                time.sleep(0.05)
                continue

            hdc_wnd = win32gui.GetDC(hwnd)
            hdc     = win32ui.CreateDCFromHandle(hdc_wnd)

            # Clear with transparent color
            brush = win32ui.CreateBrush()
            brush.CreateSolidBrush(0x000000)
            hdc.FillSolidRect((0, 0, sw, sh), 0x000000)

            if cfg.detection_boxes:
                r, g, b = _hex_to_rgb(cfg.box_color)
                color   = b | (g << 8) | (r << 16)
                pen     = win32ui.CreatePen(win32con.PS_SOLID, cfg.box_thickness, color)
                old_pen = hdc.SelectObject(pen)
                for det in dets:
                    x1, y1, x2, y2 = int(det.x1), int(det.y1), int(det.x2), int(det.y2)
                    hdc.MoveTo(x1, y1)
                    hdc.LineTo(x2, y1)
                    hdc.LineTo(x2, y2)
                    hdc.LineTo(x1, y2)
                    hdc.LineTo(x1, y1)
                hdc.SelectObject(old_pen)

            if cfg.future_dots and dots:
                r, g, b = _hex_to_rgb(cfg.future_dot_color)
                dot_clr = b | (g << 8) | (r << 16)
                dot_pen = win32ui.CreatePen(win32con.PS_SOLID, 3, dot_clr)
                old_pen = hdc.SelectObject(dot_pen)
                for px, py in dots:
                    ix, iy = int(px), int(py)
                    hdc.MoveTo(ix - 2, iy)
                    hdc.LineTo(ix + 2, iy)
                    hdc.MoveTo(ix, iy - 2)
                    hdc.LineTo(ix, iy + 2)
                hdc.SelectObject(old_pen)

            if cfg.capture_border:
                # Draw border around capture region
                import ctypes as _ct
                sw_, sh_ = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
                cap_size = 320  # will be set from config later
                cx, cy   = sw_ // 2, sh_ // 2
                half     = cap_size // 2
                border_pen = win32ui.CreatePen(win32con.PS_SOLID, 1, 0x00FF00)
                old_pen    = hdc.SelectObject(border_pen)
                hdc.MoveTo(cx - half, cy - half)
                hdc.LineTo(cx + half, cy - half)
                hdc.LineTo(cx + half, cy + half)
                hdc.LineTo(cx - half, cy + half)
                hdc.LineTo(cx - half, cy - half)
                hdc.SelectObject(old_pen)

            hdc.Detach()
            win32gui.ReleaseDC(hwnd, hdc_wnd)
            win32gui.UpdateWindow(hwnd)

            time.sleep(1.0 / 60.0)

        win32gui.DestroyWindow(hwnd)

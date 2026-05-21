"""Screen capture via DXGI Desktop Duplication — center-crop, BGRA output."""
from __future__ import annotations
import sys
import threading
import time
from typing import Optional, Tuple

import numpy as np


def screen_size() -> Tuple[int, int]:
    """Return (width, height) of primary monitor."""
    if sys.platform == "win32":
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    # Fallback for non-Windows
    return 1920, 1080


class DXGICapture:
    """
    Thread-safe DXGI-based screen capture with center-crop.

    Returns BGRA numpy arrays of shape (capture_size, capture_size, 4).
    Falls back to dxcam if available, then to a GDI BitBlt stub.
    """

    def __init__(self, monitor: int = 0, capture_size: int = 320) -> None:
        self._monitor = monitor
        self._capture_size = capture_size
        self._lock = threading.Lock()
        self._fail_count = 0
        self._MAX_FAILS = 60
        self._camera = None
        self._init_capture()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_capture(self) -> None:
        """Try dxcam, then GDI fallback."""
        try:
            import dxcam  # type: ignore[import]
            sw, sh = screen_size()
            half = self._capture_size // 2
            cx, cy = sw // 2, sh // 2
            region = (cx - half, cy - half, cx + half, cy + half)
            self._camera = dxcam.create(output_idx=self._monitor, output_color="BGRA")
            self._camera.start(region=region, video_mode=True)
            self._mode = "dxcam"
        except Exception:
            self._camera = None
            self._mode = "gdi"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def grab(self) -> Optional[np.ndarray]:
        """
        Capture one frame. Returns (capture_size, capture_size, 4) BGRA uint8
        or None on failure.
        """
        with self._lock:
            if self._mode == "dxcam":
                return self._grab_dxcam()
            return self._grab_gdi()

    def return_buffer(self) -> None:
        """No-op — buffer reuse handled internally by dxcam."""

    def reset(self) -> None:
        """Reinitialise capture after repeated failures."""
        with self._lock:
            self._fail_count = 0
            if self._camera is not None:
                try:
                    self._camera.stop()
                except Exception:
                    pass
            self._init_capture()

    @property
    def capture_size(self) -> int:
        return self._capture_size

    def crop_offset(self) -> Tuple[int, int]:
        """Return (offset_x, offset_y) — top-left of crop on screen."""
        sw, sh = screen_size()
        half = self._capture_size // 2
        return sw // 2 - half, sh // 2 - half

    # ------------------------------------------------------------------
    # Internal grab methods
    # ------------------------------------------------------------------

    def _grab_dxcam(self) -> Optional[np.ndarray]:
        try:
            frame = self._camera.get_latest_frame()
            if frame is None:
                self._fail_count += 1
                if self._fail_count >= self._MAX_FAILS:
                    self.reset()
                return None
            self._fail_count = 0
            return frame  # already BGRA, already cropped by dxcam region
        except Exception:
            self._fail_count += 1
            if self._fail_count >= self._MAX_FAILS:
                self.reset()
            return None

    def _grab_gdi(self) -> Optional[np.ndarray]:
        """GDI BitBlt fallback — works without dxcam but slower."""
        try:
            import ctypes
            import ctypes.wintypes
            sw, sh = screen_size()
            size = self._capture_size
            half = size // 2
            left = sw // 2 - half
            top  = sh // 2 - half

            hdesktop = ctypes.windll.user32.GetDesktopWindow()
            hdc_src  = ctypes.windll.user32.GetDC(hdesktop)
            hdc_dst  = ctypes.windll.gdi32.CreateCompatibleDC(hdc_src)
            hbmp     = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc_src, size, size)
            ctypes.windll.gdi32.SelectObject(hdc_dst, hbmp)
            ctypes.windll.gdi32.BitBlt(hdc_dst, 0, 0, size, size, hdc_src, left, top, 0x00CC0020)

            bmp_info = (ctypes.c_long * 4)(40, size, -size, 1 | (32 << 16))
            buf = (ctypes.c_byte * (size * size * 4))()
            ctypes.windll.gdi32.GetDIBits(hdc_dst, hbmp, 0, size, buf, bmp_info, 0)

            ctypes.windll.gdi32.DeleteObject(hbmp)
            ctypes.windll.gdi32.DeleteDC(hdc_dst)
            ctypes.windll.user32.ReleaseDC(hdesktop, hdc_src)

            frame = np.frombuffer(buf, dtype=np.uint8).reshape(size, size, 4)
            self._fail_count = 0
            return frame
        except Exception:
            self._fail_count += 1
            if self._fail_count >= self._MAX_FAILS:
                self.reset()
            return None

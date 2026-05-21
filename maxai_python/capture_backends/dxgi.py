"""DXGI Desktop Duplication capture — migrated from capture_dxgi.py, now with circle mask."""
from __future__ import annotations
import sys
import threading
from typing import Optional, Tuple

import numpy as np
from .base import CaptureBackend


def _screen_size() -> Tuple[int, int]:
    if sys.platform == "win32":
        import ctypes
        u = ctypes.windll.user32
        u.SetProcessDPIAware()
        return u.GetSystemMetrics(0), u.GetSystemMetrics(1)
    return 1920, 1080


class DXGICapture(CaptureBackend):
    def __init__(self, monitor: int = 0, capture_size: int = 320,
                 circle_mask: bool = False) -> None:
        self._monitor       = monitor
        self._capture_size  = capture_size
        self._circle_mask   = circle_mask
        self._lock          = threading.Lock()
        self._fail_count    = 0
        self._MAX_FAILS     = 60
        self._camera        = None
        self._mode          = "gdi"
        self._mask: Optional[np.ndarray] = None
        self._init()

    def _init(self) -> None:
        try:
            import dxcam  # type: ignore[import]
            sw, sh = _screen_size()
            half   = self._capture_size // 2
            cx, cy = sw // 2, sh // 2
            region = (cx - half, cy - half, cx + half, cy + half)
            cam = dxcam.create(output_idx=self._monitor, output_color="BGRA")
            cam.start(region=region, video_mode=True)
            self._camera = cam
            self._mode   = "dxcam"
        except Exception:
            self._mode = "gdi"
        if self._circle_mask:
            self._build_mask()

    def _build_mask(self) -> None:
        s   = self._capture_size
        cx  = cy = s // 2
        y_i, x_i = np.ogrid[:s, :s]
        self._mask = ((x_i - cx) ** 2 + (y_i - cy) ** 2) > (cx ** 2)

    def grab(self) -> Optional[np.ndarray]:
        with self._lock:
            frame = self._grab_dxcam() if self._mode == "dxcam" else self._grab_gdi()
            if frame is not None and self._circle_mask and self._mask is not None:
                frame[self._mask] = 0
            return frame

    def crop_offset(self) -> Tuple[int, int]:
        sw, sh = _screen_size()
        half   = self._capture_size // 2
        return sw // 2 - half, sh // 2 - half

    def reset(self) -> None:
        with self._lock:
            self._fail_count = 0
            if self._camera:
                try: self._camera.stop()
                except Exception: pass
            self._init()

    def _grab_dxcam(self) -> Optional[np.ndarray]:
        try:
            frame = self._camera.get_latest_frame()
            if frame is None:
                self._fail_count += 1
                if self._fail_count >= self._MAX_FAILS:
                    self.reset()
                return None
            self._fail_count = 0
            return frame
        except Exception:
            self._fail_count += 1
            if self._fail_count >= self._MAX_FAILS:
                self.reset()
            return None

    def _grab_gdi(self) -> Optional[np.ndarray]:
        try:
            import ctypes
            sw, sh = _screen_size()
            size   = self._capture_size
            half   = size // 2
            left   = sw // 2 - half
            top    = sh // 2 - half
            hd     = ctypes.windll.user32.GetDesktopWindow()
            hdc_s  = ctypes.windll.user32.GetDC(hd)
            hdc_d  = ctypes.windll.gdi32.CreateCompatibleDC(hdc_s)
            hbmp   = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc_s, size, size)
            ctypes.windll.gdi32.SelectObject(hdc_d, hbmp)
            ctypes.windll.gdi32.BitBlt(hdc_d, 0, 0, size, size, hdc_s, left, top, 0x00CC0020)
            info   = (ctypes.c_long * 4)(40, size, -size, 1 | (32 << 16))
            buf    = (ctypes.c_byte * (size * size * 4))()
            ctypes.windll.gdi32.GetDIBits(hdc_d, hbmp, 0, size, buf, info, 0)
            ctypes.windll.gdi32.DeleteObject(hbmp)
            ctypes.windll.gdi32.DeleteDC(hdc_d)
            ctypes.windll.user32.ReleaseDC(hd, hdc_s)
            self._fail_count = 0
            return np.frombuffer(buf, dtype=np.uint8).reshape(size, size, 4)
        except Exception:
            self._fail_count += 1
            if self._fail_count >= self._MAX_FAILS:
                self.reset()
            return None

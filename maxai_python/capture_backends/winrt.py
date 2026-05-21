"""
WinRT Windows.Graphics.Capture backend.
Requires: pip install windows-capture  (or winrt-Windows.Graphics.Capture)
Works without admin rights; supports HDR monitors.
"""
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


class WinRTCapture(CaptureBackend):
    """Windows.Graphics.Capture API via windows-capture Python wrapper."""

    def __init__(self, monitor: int = 0, capture_size: int = 320,
                 circle_mask: bool = False) -> None:
        self._capture_size  = capture_size
        self._circle_mask   = circle_mask
        self._lock          = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._mask: Optional[np.ndarray] = None
        self._capture       = None
        self._init(monitor)

    def _init(self, monitor: int) -> None:
        try:
            from windows_capture import WindowsCapture, Frame, InternalCaptureControl  # type: ignore[import]
            import ctypes
            import ctypes.wintypes

            u = ctypes.windll.user32
            # Get monitor handle for the given index
            monitors = []
            def _cb(hmon, hdc, rect, lp):
                monitors.append(hmon)
                return True
            MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong,
                                                  ctypes.c_ulong,
                                                  ctypes.POINTER(ctypes.wintypes.RECT),
                                                  ctypes.c_double)
            u.EnumDisplayMonitors(None, None, MonitorEnumProc(_cb), 0)
            hmon = monitors[monitor] if monitor < len(monitors) else monitors[0]

            capture = WindowsCapture(
                cursor_capture=False,
                draw_border=None,
                monitor_index=monitor,
            )

            @capture.event
            def on_frame_arrived(frame: Frame, control: InternalCaptureControl):
                img = frame.convert_to_bgra()
                arr = np.frombuffer(img, dtype=np.uint8).reshape(frame.height, frame.width, 4)
                sw, sh = _screen_size()
                half   = self._capture_size // 2
                cx, cy = sw // 2, sh // 2
                y1 = max(0, cy - half)
                x1 = max(0, cx - half)
                cropped = arr[y1:y1 + self._capture_size, x1:x1 + self._capture_size]
                with self._lock:
                    self._latest_frame = cropped

            @capture.event
            def on_closed():
                pass

            capture.start_free_threaded()
            self._capture = capture
        except Exception as exc:
            self._capture = None

        if self._circle_mask:
            s  = self._capture_size
            cx = cy = s // 2
            yi, xi = np.ogrid[:s, :s]
            self._mask = ((xi - cx) ** 2 + (yi - cy) ** 2) > (cx ** 2)

    def grab(self) -> Optional[np.ndarray]:
        with self._lock:
            frame = self._latest_frame
        if frame is not None and self._circle_mask and self._mask is not None:
            frame = frame.copy()
            frame[self._mask] = 0
        return frame

    def crop_offset(self) -> Tuple[int, int]:
        sw, sh = _screen_size()
        half   = self._capture_size // 2
        return sw // 2 - half, sh // 2 - half

    def reset(self) -> None:
        pass

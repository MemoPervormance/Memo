"""
NDI (Network Device Interface) capture backend.
Requires: pip install ndi-python  (and NDI SDK/runtime installed)
Low-latency video from gaming PC / capture card / OBS NDI plugin.
"""
from __future__ import annotations
import threading
from typing import Optional, Tuple
import numpy as np
from .base import CaptureBackend


class NDICapture(CaptureBackend):
    """Receive frames from an NDI source and center-crop."""

    def __init__(self, source_name: str = "", capture_size: int = 320) -> None:
        self._capture_size = capture_size
        self._source_name  = source_name
        self._lock         = threading.Lock()
        self._latest: Optional[np.ndarray] = None
        self._recv         = None
        self._thread: Optional[threading.Thread] = None
        self._init()

    def _init(self) -> None:
        try:
            import ndi  # type: ignore[import]
            if not ndi.initialize():
                raise RuntimeError("NDI SDK init failed")
            finder = ndi.find_create_v3()
            if not finder:
                raise RuntimeError("NDI finder create failed")

            # Wait up to 5s for sources
            import time
            deadline = time.monotonic() + 5.0
            sources = []
            while time.monotonic() < deadline:
                ndi.find_wait_for_sources(finder, 500)
                sources = ndi.find_get_current_sources(finder)
                if sources:
                    break

            target = sources[0]
            if self._source_name:
                for s in sources:
                    if self._source_name.lower() in s.ndi_name.lower():
                        target = s
                        break

            recv_create = ndi.RecvCreateV3()
            recv_create.color_format = ndi.RECV_COLOR_FORMAT_RGBX_RGBA
            self._recv = ndi.recv_create_v3(recv_create)
            ndi.recv_connect(self._recv, target)
            ndi.find_destroy(finder)

            self._thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._thread.start()
        except Exception as exc:
            self._recv = None

    def _recv_loop(self) -> None:
        try:
            import ndi
            while True:
                t, v, a, m = ndi.recv_capture_v3(self._recv, 33)
                if t == ndi.FRAME_TYPE_VIDEO and v is not None:
                    h   = v.yres
                    w   = v.xres
                    arr = np.frombuffer(v.data, dtype=np.uint8).reshape(h, w, 4)
                    # RGBX → BGRA
                    bgra = arr[:, :, [2, 1, 0, 3]]
                    cy  = h // 2; cx = w // 2
                    half = self._capture_size // 2
                    y1  = max(0, cy - half); x1 = max(0, cx - half)
                    crop = bgra[y1:y1 + self._capture_size, x1:x1 + self._capture_size]
                    with self._lock:
                        self._latest = crop.copy()
                    ndi.recv_free_video_v2(self._recv, v)
        except Exception:
            pass

    def grab(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._latest

    def crop_offset(self) -> Tuple[int, int]:
        return 0, 0

    def reset(self) -> None:
        self._init()

"""
Capture Card backend — DirectShow via OpenCV VideoCapture.
Works with Elgato HD60, Fifine A3, and any DirectShow-compatible capture device.
Requires: pip install opencv-python
"""
from __future__ import annotations
import threading
from typing import Optional, Tuple
import numpy as np
from .base import CaptureBackend


class CaptureCardCapture(CaptureBackend):
    """Grabs frames from a video capture device (capture card) via OpenCV."""

    def __init__(self, source_name: str = "", capture_size: int = 320,
                 device_index: int = 0) -> None:
        self._capture_size = capture_size
        self._source_name  = source_name
        self._device_index = device_index
        self._lock         = threading.Lock()
        self._latest: Optional[np.ndarray] = None
        self._cap          = None
        self._thread: Optional[threading.Thread] = None
        self._init()

    def _init(self) -> None:
        try:
            import cv2  # type: ignore[import]

            # Try to find device by name via DirectShow
            idx = self._device_index
            if self._source_name:
                # Enumerate DirectShow devices
                for i in range(8):
                    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                    if cap.isOpened():
                        # No direct name lookup in OpenCV — use index from config
                        cap.release()
                idx = self._device_index

            self._cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if not self._cap.isOpened():
                raise RuntimeError(f"Cannot open capture device #{idx}")

            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1920)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            self._cap.set(cv2.CAP_PROP_FPS,          60)
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

            self._thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._thread.start()
        except Exception:
            self._cap = None

    def _recv_loop(self) -> None:
        import cv2
        while self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if not ret:
                continue
            # frame is BGR; convert to BGRA and center-crop
            h, w = frame.shape[:2]
            bgra  = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
            cy, cx = h // 2, w // 2
            half   = self._capture_size // 2
            y1 = max(0, cy - half); x1 = max(0, cx - half)
            crop = bgra[y1:y1 + self._capture_size, x1:x1 + self._capture_size]
            with self._lock:
                self._latest = crop.copy()

    def grab(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._latest

    def crop_offset(self) -> Tuple[int, int]:
        return 0, 0

    def reset(self) -> None:
        if self._cap:
            try: self._cap.release()
            except Exception: pass
        self._init()

    def __del__(self) -> None:
        try:
            if self._cap:
                self._cap.release()
        except Exception:
            pass

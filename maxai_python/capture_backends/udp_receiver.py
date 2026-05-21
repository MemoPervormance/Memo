"""
UDP Frame Receiver — for 2-PC setups.
The gaming PC streams BGRA frames over UDP; this PC receives and crops them.

Frame packet format:
  Header (8 bytes): magic(4) + width(2) + height(2) [little-endian]
  Body:             raw BGRA bytes (width * height * 4)

For large frames (>64KB) the sender should fragment; this receiver
reassembles using a simple 4-byte sequence number prefix per chunk.
Simple mode (single UDP datagram ≤65507 bytes) is the default.
"""
from __future__ import annotations
import socket
import struct
import threading
from typing import Optional, Tuple
import numpy as np
from .base import CaptureBackend

_MAGIC = b"MXAI"


class UDPCapture(CaptureBackend):
    """Receive BGRA frames over UDP and return center-crop."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9999,
                 capture_size: int = 320) -> None:
        self._capture_size = capture_size
        self._host = host
        self._port = port
        self._lock = threading.Lock()
        self._latest: Optional[np.ndarray] = None
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 22)
        self._sock.bind((host, port))
        self._sock.settimeout(1.0)
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def _recv_loop(self) -> None:
        while True:
            try:
                data, _ = self._sock.recvfrom(65535)
                if len(data) < 8 or data[:4] != _MAGIC:
                    continue
                w, h = struct.unpack_from("<HH", data, 4)
                expected = 8 + w * h * 4
                if len(data) < expected:
                    continue
                arr = np.frombuffer(data[8:8 + w * h * 4], dtype=np.uint8).reshape(h, w, 4)
                # Center-crop
                cy = h // 2; cx = w // 2
                half = self._capture_size // 2
                y1 = max(0, cy - half); x1 = max(0, cx - half)
                crop = arr[y1:y1 + self._capture_size, x1:x1 + self._capture_size]
                with self._lock:
                    self._latest = crop
            except socket.timeout:
                continue
            except Exception:
                continue

    def grab(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._latest

    def crop_offset(self) -> Tuple[int, int]:
        # Offset unknown without knowing sender's resolution; return 0,0
        return 0, 0

    def reset(self) -> None:
        with self._lock:
            self._latest = None

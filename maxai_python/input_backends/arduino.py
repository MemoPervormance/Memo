"""
Arduino (Leonardo / Pro Micro) serial input backend.
Flash the companion sketch to the Arduino first (see README).
Protocol: binary packets over serial.

Packet format (7 bytes):
  [0]   0xAA  — header
  [1]   cmd   — 0x01=move, 0x02=lclick_down, 0x03=lclick_up,
                0x04=rclick_down, 0x05=rclick_up
  [2-3] dx    — signed int16 little-endian
  [4-5] dy    — signed int16 little-endian
  [6]   0xBB  — footer
"""
from __future__ import annotations
import struct
import threading
import time
from typing import Optional
from .base import InputBackend

_HDR = 0xAA
_FTR = 0xBB

CMD_MOVE          = 0x01
CMD_LCLICK_DOWN   = 0x02
CMD_LCLICK_UP     = 0x03
CMD_RCLICK_DOWN   = 0x04
CMD_RCLICK_UP     = 0x05


def _build_packet(cmd: int, dx: int = 0, dy: int = 0) -> bytes:
    dx = max(-32768, min(32767, dx))
    dy = max(-32768, min(32767, dy))
    return struct.pack("<BBhhB", _HDR, cmd, dx, dy, _FTR)


class ArduinoBackend(InputBackend):
    """Serial HID backend for Arduino Leonardo / Pro Micro."""

    def __init__(self, port: str = "COM3", baud: int = 115200) -> None:
        try:
            import serial  # type: ignore[import]
        except ImportError:
            raise RuntimeError("pyserial not installed. Run: pip install pyserial")
        self._ser = serial.Serial(port, baud, timeout=0.1)
        time.sleep(2.0)   # Arduino resets on serial connect
        self._lock = threading.Lock()
        self._fire_held = False
        self._ads_held  = False

    def _send(self, cmd: int, dx: int = 0, dy: int = 0) -> None:
        pkt = _build_packet(cmd, dx, dy)
        with self._lock:
            try:
                self._ser.write(pkt)
            except Exception:
                pass

    def move_cursor(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        # Split into chunks ≤127 px to stay within HID report range
        while abs(dx) > 127 or abs(dy) > 127:
            step_x = max(-127, min(127, dx))
            step_y = max(-127, min(127, dy))
            self._send(CMD_MOVE, step_x, step_y)
            dx -= step_x
            dy -= step_y
        if dx or dy:
            self._send(CMD_MOVE, dx, dy)

    def press_fire(self) -> None:
        if not self._fire_held:
            self._send(CMD_LCLICK_DOWN)
            self._fire_held = True

    def release_fire(self) -> None:
        if self._fire_held:
            self._send(CMD_LCLICK_UP)
            self._fire_held = False

    def press_ads(self) -> None:
        if not self._ads_held:
            self._send(CMD_RCLICK_DOWN)
            self._ads_held = True

    def release_ads(self) -> None:
        if self._ads_held:
            self._send(CMD_RCLICK_UP)
            self._ads_held = False

    def release_all(self) -> None:
        self.release_fire()
        self.release_ads()

    def __del__(self) -> None:
        try:
            self.release_all()
            self._ser.close()
        except Exception:
            pass

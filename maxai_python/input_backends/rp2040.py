"""
RP2040 / RP2350 (Raspberry Pi Pico) input backend.
Flash the companion CircuitPython/MicroPython sketch that reads serial commands
and re-emits them as USB HID mouse events.

Supports both RP2040 (Pico) and RP2350 (Pico 2) — same serial protocol.

Binary protocol (same as Arduino backend):
  [0]   0xAA  header
  [1]   cmd   0x01=move, 0x02=ldown, 0x03=lup, 0x04=rdown, 0x05=rup,
              0x10=scroll_y
  [2-3] dx    int16 LE
  [4-5] dy    int16 LE
  [6]   0xBB  footer
"""
from __future__ import annotations
import struct
import threading
import time
from .base import InputBackend

_HDR = 0xAA
_FTR = 0xBB

CMD_MOVE    = 0x01
CMD_LDOWN   = 0x02
CMD_LUP     = 0x03
CMD_RDOWN   = 0x04
CMD_RUP     = 0x05
CMD_SCROLL  = 0x10


class RP2040Backend(InputBackend):
    """RP2040 / RP2350 serial HID backend."""

    def __init__(self, port: str = "COM5", baud: int = 115200) -> None:
        try:
            import serial  # type: ignore[import]
        except ImportError:
            raise RuntimeError("pyserial not installed. Run: pip install pyserial")
        self._ser  = serial.Serial(port, baud, timeout=0.1)
        time.sleep(1.0)
        self._lock = threading.Lock()
        self._fire_held = False
        self._ads_held  = False

    def _send(self, cmd: int, p1: int = 0, p2: int = 0) -> None:
        p1 = max(-32768, min(32767, p1))
        p2 = max(-32768, min(32767, p2))
        pkt = struct.pack("<BBhhB", _HDR, cmd, p1, p2, _FTR)
        with self._lock:
            try:
                self._ser.write(pkt)
            except Exception:
                pass

    def move_cursor(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        self._send(CMD_MOVE, dx, dy)

    def press_fire(self) -> None:
        if not self._fire_held:
            self._send(CMD_LDOWN)
            self._fire_held = True

    def release_fire(self) -> None:
        if self._fire_held:
            self._send(CMD_LUP)
            self._fire_held = False

    def press_ads(self) -> None:
        if not self._ads_held:
            self._send(CMD_RDOWN)
            self._ads_held = True

    def release_ads(self) -> None:
        if self._ads_held:
            self._send(CMD_RUP)
            self._ads_held = False

    def release_all(self) -> None:
        self.release_fire()
        self.release_ads()

    def scroll(self, dy: int) -> None:
        self._send(CMD_SCROLL, 0, dy)

    def __del__(self) -> None:
        try:
            self.release_all()
            self._ser.close()
        except Exception:
            pass

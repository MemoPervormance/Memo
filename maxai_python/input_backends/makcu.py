"""
MAKCU (ESP32-S3) input backend — serial USB-HID emulation.
Same wire protocol as Arduino backend; MAKCU presents as USB HID mouse.

Packet format (7 bytes):
  [0]   0xAA  header
  [1]   cmd   0x01=move, 0x02=ldown, 0x03=lup, 0x04=rdown, 0x05=rup
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

CMD_MOVE   = 0x01
CMD_LDOWN  = 0x02
CMD_LUP    = 0x03
CMD_RDOWN  = 0x04
CMD_RUP    = 0x05


class MAKCUBackend(InputBackend):
    """MAKCU (ESP32-S3) serial HID backend for 2-PC setups."""

    def __init__(self, port: str = "COM4", baud: int = 115200) -> None:
        try:
            import serial  # type: ignore[import]
        except ImportError:
            raise RuntimeError("pyserial not installed. Run: pip install pyserial")
        self._ser  = serial.Serial(port, baud, timeout=0.1)
        time.sleep(1.0)
        self._lock = threading.Lock()
        self._fire_held = False
        self._ads_held  = False

    def _send(self, cmd: int, dx: int = 0, dy: int = 0) -> None:
        dx = max(-32768, min(32767, dx))
        dy = max(-32768, min(32767, dy))
        pkt = struct.pack("<BBhhB", _HDR, cmd, dx, dy, _FTR)
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

    def __del__(self) -> None:
        try:
            self.release_all()
            self._ser.close()
        except Exception:
            pass

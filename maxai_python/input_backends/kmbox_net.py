"""
KMBOX Net (ESP32-based) input backend — UDP command protocol.
Official KMBOX Net protocol: 8-byte command packets over UDP.

Packet layout (8 bytes):
  [0-3]  magic   = 0x434F4D4D ("COMM")
  [4]    cmd     = 0x01=move_rel, 0x02=lclick, 0x03=rclick,
                   0x04=ldown, 0x05=lup, 0x06=rdown, 0x07=rup
  [5]    param1  = dx (signed byte) for move
  [6]    param2  = dy (signed byte) for move
  [7]    checksum = XOR of bytes 0-6
"""
from __future__ import annotations
import socket
import struct
import threading
from .base import InputBackend

_MAGIC  = b"COMM"
CMD_MOVE_REL  = 0x01
CMD_LDOWN     = 0x04
CMD_LUP       = 0x05
CMD_RDOWN     = 0x06
CMD_RUP       = 0x07


def _packet(cmd: int, p1: int = 0, p2: int = 0) -> bytes:
    p1 = p1 & 0xFF
    p2 = p2 & 0xFF
    data = _MAGIC + bytes([cmd, p1, p2])
    chk  = 0
    for b in data:
        chk ^= b
    return data + bytes([chk])


class KMBoxNetBackend(InputBackend):
    """KMBOX Net UDP backend for 2-PC or direct setups."""

    def __init__(self, ip: str = "192.168.2.188", port: int = 1408) -> None:
        self._addr = (ip, port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(0.05)
        self._lock = threading.Lock()
        self._fire_held = False
        self._ads_held  = False

    def _send(self, cmd: int, p1: int = 0, p2: int = 0) -> None:
        pkt = _packet(cmd, p1, p2)
        with self._lock:
            try:
                self._sock.sendto(pkt, self._addr)
            except Exception:
                pass

    def move_cursor(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        # KMBOX Net accepts -127..127 per packet
        while abs(dx) > 127 or abs(dy) > 127:
            step_x = max(-127, min(127, dx))
            step_y = max(-127, min(127, dy))
            self._send(CMD_MOVE_REL,
                       step_x if step_x >= 0 else 256 + step_x,
                       step_y if step_y >= 0 else 256 + step_y)
            dx -= step_x
            dy -= step_y
        if dx or dy:
            self._send(CMD_MOVE_REL,
                       dx if dx >= 0 else 256 + dx,
                       dy if dy >= 0 else 256 + dy)

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
            self._sock.close()
        except Exception:
            pass

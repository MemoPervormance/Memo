"""
Titan Two (ConsoleTuner) input backend — USB HID via Memory-Mapped API.
Titan Two exposes a virtual COM port and a scripting API.
We send GPC script commands via serial to trigger mouse movements.

GPC command format sent over serial:
  Simple text line: "M dx dy\\n"   → mouse_move(dx, dy)
  "B 1 1\\n"                       → mouse button 1 down
  "B 1 0\\n"                       → mouse button 1 up
  "B 2 1\\n" / "B 2 0\\n"          → right button
Titan Two GPC script must be pre-loaded with the companion script.
"""
from __future__ import annotations
import threading
import time
from .base import InputBackend


class TitanTwoBackend(InputBackend):
    """Titan Two serial command backend."""

    def __init__(self, port: str = "COM6", baud: int = 115200) -> None:
        try:
            import serial  # type: ignore[import]
        except ImportError:
            raise RuntimeError("pyserial not installed. Run: pip install pyserial")
        self._ser  = serial.Serial(port, baud, timeout=0.1)
        time.sleep(1.0)
        self._lock = threading.Lock()
        self._fire_held = False
        self._ads_held  = False

    def _cmd(self, line: str) -> None:
        with self._lock:
            try:
                self._ser.write((line + "\n").encode())
            except Exception:
                pass

    def move_cursor(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        # Titan Two HID accepts -128..127 per event
        while abs(dx) > 127 or abs(dy) > 127:
            step_x = max(-127, min(127, dx))
            step_y = max(-127, min(127, dy))
            self._cmd(f"M {step_x} {step_y}")
            dx -= step_x
            dy -= step_y
        if dx or dy:
            self._cmd(f"M {dx} {dy}")

    def press_fire(self) -> None:
        if not self._fire_held:
            self._cmd("B 1 1")
            self._fire_held = True

    def release_fire(self) -> None:
        if self._fire_held:
            self._cmd("B 1 0")
            self._fire_held = False

    def press_ads(self) -> None:
        if not self._ads_held:
            self._cmd("B 2 1")
            self._ads_held = True

    def release_ads(self) -> None:
        if self._ads_held:
            self._cmd("B 2 0")
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

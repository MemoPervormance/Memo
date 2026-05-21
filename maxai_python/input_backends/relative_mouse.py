"""Relative-mouse input backend — SendInput MOUSEEVENTF_MOVE (no kernel driver)."""
from __future__ import annotations
import ctypes
import ctypes.wintypes
import sys
from .base import InputBackend

if sys.platform == "win32":
    MOUSEEVENTF_MOVE        = 0x0001
    MOUSEEVENTF_LEFTDOWN    = 0x0002
    MOUSEEVENTF_LEFTUP      = 0x0004
    MOUSEEVENTF_RIGHTDOWN   = 0x0008
    MOUSEEVENTF_RIGHTUP     = 0x0010
    MOUSEEVENTF_MIDDLEDOWN  = 0x0020
    MOUSEEVENTF_MIDDLEUP    = 0x0040
    INPUT_MOUSE             = 0

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx",          ctypes.c_long),
            ("dy",          ctypes.c_long),
            ("mouseData",   ctypes.c_ulong),
            ("dwFlags",     ctypes.c_ulong),
            ("time",        ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]

    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("_u", _INPUT_UNION)]

    _user32 = ctypes.windll.user32

    def _send_mouse(flags: int, dx: int = 0, dy: int = 0) -> None:
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp._u.mi.dx = dx
        inp._u.mi.dy = dy
        inp._u.mi.mouseData = 0
        inp._u.mi.dwFlags = flags
        inp._u.mi.time = 0
        inp._u.mi.dwExtraInfo = None
        _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


class RelativeMouseBackend(InputBackend):
    """Moves the in-game crosshair via relative SendInput calls — no driver needed."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("RelativeMouseBackend requires Windows.")
        self._fire_held = False
        self._ads_held  = False

    def move_cursor(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        _send_mouse(MOUSEEVENTF_MOVE, dx, dy)

    def press_fire(self) -> None:
        if not self._fire_held:
            _send_mouse(MOUSEEVENTF_LEFTDOWN)
            self._fire_held = True

    def release_fire(self) -> None:
        if self._fire_held:
            _send_mouse(MOUSEEVENTF_LEFTUP)
            self._fire_held = False

    def press_ads(self) -> None:
        if not self._ads_held:
            _send_mouse(MOUSEEVENTF_RIGHTDOWN)
            self._ads_held = True

    def release_ads(self) -> None:
        if self._ads_held:
            _send_mouse(MOUSEEVENTF_RIGHTUP)
            self._ads_held = False

    def release_all(self) -> None:
        self.release_fire()
        self.release_ads()

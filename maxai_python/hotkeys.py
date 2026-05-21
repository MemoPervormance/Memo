"""Hotkey polling via GetAsyncKeyState (Windows only)."""
from __future__ import annotations
import ctypes
import sys
from typing import Dict

# Virtual-key code table — case-insensitive lookup
_VK_MAP: Dict[str, int] = {
    # Mouse buttons
    "mouse1": 0x01, "lbutton": 0x01,
    "mouse2": 0x02, "rbutton": 0x02,
    "mouse3": 0x04, "mbutton": 0x04,
    "mouse4": 0x05, "xbutton1": 0x05,
    "mouse5": 0x06, "xbutton2": 0x06,
    # Control keys
    "backspace": 0x08, "tab": 0x09, "enter": 0x0D,
    "shift": 0x10, "ctrl": 0x11, "alt": 0x12,
    "pause": 0x13, "caps": 0x14, "esc": 0x1B, "escape": 0x1B,
    "space": 0x20, "pageup": 0x21, "pagedown": 0x22,
    "end": 0x23, "home": 0x24,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "insert": 0x2D, "delete": 0x2E,
    # F-keys
    **{f"f{i}": 0x6F + i for i in range(1, 13)},
    # Digits 0-9
    **{str(i): 0x30 + i for i in range(10)},
    # Letters a-z
    **{chr(c): 0x41 + (c - ord("a")) for c in range(ord("a"), ord("z") + 1)},
    # Numpad
    **{f"num{i}": 0x60 + i for i in range(10)},
}

# Fix F1 offset: F1=0x70, not 0x70. Let's be explicit.
_VK_MAP.update({f"f{i}": 0x6F + i for i in range(1, 13)})
# Correct: F1=0x70
_VK_MAP.update({
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
})


def _get_vk(key_name: str) -> int:
    k = key_name.lower().strip()
    code = _VK_MAP.get(k)
    if code is None:
        raise ValueError(f"Unknown key: {key_name!r}")
    return code


if sys.platform == "win32":
    _user32 = ctypes.windll.user32

    def is_pressed(key_name: str) -> bool:
        """Return True while the key is held down."""
        try:
            vk = _get_vk(key_name)
        except ValueError:
            return False
        return bool(_user32.GetAsyncKeyState(vk) & 0x8000)

    def was_pressed(key_name: str) -> bool:
        """Return True if the key was pressed since the last call (toggle detection)."""
        try:
            vk = _get_vk(key_name)
        except ValueError:
            return False
        # bit 0 = pressed since last call
        return bool(_user32.GetAsyncKeyState(vk) & 0x0001)

else:
    # Stub for non-Windows (CI, tests)
    def is_pressed(key_name: str) -> bool:  # type: ignore[misc]
        return False

    def was_pressed(key_name: str) -> bool:  # type: ignore[misc]
        return False

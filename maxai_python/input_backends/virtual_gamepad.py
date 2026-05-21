"""Virtual gamepad backend — ViGEmBus Xbox360 controller (pyvigem)."""
from __future__ import annotations
import sys
from .base import InputBackend


class VirtualGamepadBackend(InputBackend):
    """Maps cursor movement to Xbox360 right stick via ViGEmBus."""

    def __init__(self, sensitivity: float = 0.75) -> None:
        if sys.platform != "win32":
            raise RuntimeError("VirtualGamepadBackend requires Windows.")
        try:
            import vigem  # type: ignore[import]
            self._vigem = vigem
        except ImportError:
            raise RuntimeError(
                "pyvigem not installed. Run: pip install pyvigem\n"
                "Also ensure ViGEmBus driver is installed."
            )
        self._sensitivity = sensitivity
        self._client = vigem.Client()
        try:
            self._client.connect()
        except Exception as exc:
            raise RuntimeError(
                f"ViGEm connect failed: {exc}\n"
                "Install ViGEmBus: https://github.com/nefarius/ViGEmBus/releases"
            ) from exc
        self._pad = vigem.Xbox360()
        self._client.target_add(self._pad)
        self._report = vigem.Xbox360Report()
        self._lt_held = False
        self._rt_held = False

    def move_cursor(self, dx: int, dy: int) -> None:
        # Map pixel delta to stick axis [-32768, 32767]
        scale = self._sensitivity * 32767 / 100.0
        sx = int(max(-32768, min(32767,  dx * scale)))
        sy = int(max(-32768, min(32767, -dy * scale)))  # y inverted
        self._report.sThumbRX = sx
        self._report.sThumbRY = sy
        self._pad.update(self._report)

    def press_fire(self) -> None:
        if not self._rt_held:
            self._report.bRightTrigger = 255
            self._pad.update(self._report)
            self._rt_held = True

    def release_fire(self) -> None:
        if self._rt_held:
            self._report.bRightTrigger = 0
            self._pad.update(self._report)
            self._rt_held = False

    def press_ads(self) -> None:
        if not self._lt_held:
            self._report.bLeftTrigger = 255
            self._pad.update(self._report)
            self._lt_held = True

    def release_ads(self) -> None:
        if self._lt_held:
            self._report.bLeftTrigger = 0
            self._pad.update(self._report)
            self._lt_held = False

    def release_all(self) -> None:
        self._report.sThumbRX = 0
        self._report.sThumbRY = 0
        self._report.bRightTrigger = 0
        self._report.bLeftTrigger = 0
        self._pad.update(self._report)
        self._rt_held = False
        self._lt_held = False

    def __del__(self) -> None:
        try:
            self.release_all()
            self._client.target_remove(self._pad)
            self._client.disconnect()
        except Exception:
            pass

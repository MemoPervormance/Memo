"""Kernel-driver input backend — IOCTL adapter placeholder.

The user must supply a compatible kernel driver. This module acts as a thin
adapter that forwards move/fire commands via DeviceIoControl.

Expected driver interface (configurable via config driver_path / driver_ioctl_*):
  IOCTL_MOVE  : sends (dx: i32, dy: i32) struct
  IOCTL_FIRE  : sends (state: u8) byte
  IOCTL_ADS   : sends (state: u8) byte
"""
from __future__ import annotations
import ctypes
import struct
import sys
from pathlib import Path
from .base import InputBackend

if sys.platform == "win32":
    import ctypes.wintypes

    GENERIC_READ  = 0x80000000
    GENERIC_WRITE = 0x40000000
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    METHOD_BUFFERED = 0
    FILE_ANY_ACCESS = 0

    def _ctl_code(device_type: int, function: int,
                  method: int, access: int) -> int:
        return (device_type << 16) | (access << 14) | (function << 2) | method

    IOCTL_MOVE = _ctl_code(0x8000, 0x800, METHOD_BUFFERED, FILE_ANY_ACCESS)
    IOCTL_FIRE = _ctl_code(0x8000, 0x801, METHOD_BUFFERED, FILE_ANY_ACCESS)
    IOCTL_ADS  = _ctl_code(0x8000, 0x802, METHOD_BUFFERED, FILE_ANY_ACCESS)

    _kernel32 = ctypes.windll.kernel32

    def _open_device(path: str):
        handle = _kernel32.CreateFileW(
            path,
            GENERIC_READ | GENERIC_WRITE,
            0, None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None,
        )
        if handle == ctypes.wintypes.HANDLE(-1).value:
            err = ctypes.get_last_error()
            raise OSError(f"Cannot open driver device '{path}': error {err}")
        return handle

    def _ioctl(handle, code: int, data: bytes) -> None:
        buf = ctypes.create_string_buffer(data)
        returned = ctypes.c_ulong(0)
        ok = _kernel32.DeviceIoControl(
            handle, code, buf, len(data), None, 0,
            ctypes.byref(returned), None,
        )
        if not ok:
            err = ctypes.get_last_error()
            raise OSError(f"DeviceIoControl failed: error {err}")


class KernelDriverBackend(InputBackend):
    """Forwards input commands to a user-supplied kernel driver via IOCTL."""

    def __init__(self, device_path: str = r"\\.\CroixAIDriver") -> None:
        if sys.platform != "win32":
            raise RuntimeError("KernelDriverBackend requires Windows.")
        try:
            self._handle = _open_device(device_path)
        except OSError as exc:
            raise RuntimeError(
                f"Kernel driver not available at '{device_path}'.\n"
                "Please install a compatible driver and set driver_path in config.\n"
                f"Detail: {exc}"
            ) from exc
        self._fire_held = False
        self._ads_held  = False

    def move_cursor(self, dx: int, dy: int) -> None:
        payload = struct.pack("<ii", dx, dy)
        try:
            _ioctl(self._handle, IOCTL_MOVE, payload)
        except OSError:
            pass  # log silently to avoid hot-path overhead

    def press_fire(self) -> None:
        if not self._fire_held:
            _ioctl(self._handle, IOCTL_FIRE, b"\x01")
            self._fire_held = True

    def release_fire(self) -> None:
        if self._fire_held:
            _ioctl(self._handle, IOCTL_FIRE, b"\x00")
            self._fire_held = False

    def press_ads(self) -> None:
        if not self._ads_held:
            _ioctl(self._handle, IOCTL_ADS, b"\x01")
            self._ads_held = True

    def release_ads(self) -> None:
        if self._ads_held:
            _ioctl(self._handle, IOCTL_ADS, b"\x00")
            self._ads_held = False

    def release_all(self) -> None:
        self.release_fire()
        self.release_ads()
        self.move_cursor(0, 0)

    def __del__(self) -> None:
        try:
            self.release_all()
            ctypes.windll.kernel32.CloseHandle(self._handle)
        except Exception:
            pass

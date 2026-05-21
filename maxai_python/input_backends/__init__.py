"""Input backend registry — all 9 backends."""
from __future__ import annotations
from .base import InputBackend

BACKEND_NAMES = [
    "relative_mouse",
    "virtual_gamepad",
    "kernel_driver",
    "ghub",
    "arduino",
    "kmbox_net",
    "makcu",
    "rp2040",
    "rp2350",     # alias for rp2040 backend (same hardware class, different chip)
    "titan_two",
]

BACKEND_LABELS = {
    "relative_mouse":  "WIN32 Relative Mouse (SendInput — kein Treiber)",
    "virtual_gamepad": "Virtual Gamepad (ViGEmBus Xbox360)",
    "kernel_driver":   "Kernel Driver (IOCTL)",
    "ghub":            "Logitech G-Hub (HTTP API)",
    "arduino":         "Arduino Leonardo / Pro Micro (Serial HID)",
    "kmbox_net":       "KMBOX Net / ESP32 (UDP)",
    "makcu":           "MAKCU ESP32-S3 (Serial HID)",
    "rp2040":          "RP2040 / Raspberry Pi Pico (Serial HID)",
    "rp2350":          "RP2350 / Raspberry Pi Pico 2 (Serial HID)",
    "titan_two":       "Titan Two (ConsoleTuner Serial)",
}


def create_backend(name: str, cfg=None) -> InputBackend:
    """Instantiate the named backend. Raises ValueError for unknown names."""
    name = name.lower().strip()

    if name == "relative_mouse":
        from .relative_mouse import RelativeMouseBackend
        return RelativeMouseBackend()

    if name == "virtual_gamepad":
        sens = cfg.controller.stick_sensitivity if cfg else 0.75
        from .virtual_gamepad import VirtualGamepadBackend
        return VirtualGamepadBackend(sensitivity=sens)

    if name == "kernel_driver":
        path = (cfg.input.driver_path if cfg else r"\\.\CroixAIDriver")
        from .kernel_driver import KernelDriverBackend
        return KernelDriverBackend(device_path=path)

    if name == "ghub":
        port = cfg.input.ghub_port if cfg else 12010
        from .ghub import GHubBackend
        return GHubBackend(port=port)

    if name == "arduino":
        port = cfg.input.serial_port if cfg else "COM3"
        baud = cfg.input.serial_baud if cfg else 115200
        from .arduino import ArduinoBackend
        return ArduinoBackend(port=port, baud=baud)

    if name == "kmbox_net":
        ip   = cfg.input.kmbox_ip   if cfg else "192.168.2.188"
        port = cfg.input.kmbox_port if cfg else 1408
        from .kmbox_net import KMBoxNetBackend
        return KMBoxNetBackend(ip=ip, port=port)

    if name == "makcu":
        port = cfg.input.serial_port if cfg else "COM4"
        baud = cfg.input.serial_baud if cfg else 115200
        from .makcu import MAKCUBackend
        return MAKCUBackend(port=port, baud=baud)

    if name in ("rp2040", "rp2350"):
        port = cfg.input.serial_port if cfg else "COM5"
        baud = cfg.input.serial_baud if cfg else 115200
        from .rp2040 import RP2040Backend
        return RP2040Backend(port=port, baud=baud)

    if name == "titan_two":
        port = cfg.input.serial_port if cfg else "COM6"
        baud = cfg.input.serial_baud if cfg else 115200
        from .titan_two import TitanTwoBackend
        return TitanTwoBackend(port=port, baud=baud)

    raise ValueError(
        f"Unknown input backend: {name!r}\n"
        f"Valid options: {', '.join(BACKEND_NAMES)}"
    )


__all__ = ["InputBackend", "create_backend", "BACKEND_NAMES", "BACKEND_LABELS"]

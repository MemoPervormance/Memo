"""Input backend registry."""
from __future__ import annotations
from .base import InputBackend


def create_backend(name: str, cfg=None) -> InputBackend:
    """Instantiate the named backend. name: 'relative_mouse' | 'virtual_gamepad' | 'kernel_driver'."""
    name = name.lower().strip()
    if name == "relative_mouse":
        from .relative_mouse import RelativeMouseBackend
        return RelativeMouseBackend()
    if name == "virtual_gamepad":
        sens = cfg.controller.stick_sensitivity if cfg else 0.75
        from .virtual_gamepad import VirtualGamepadBackend
        return VirtualGamepadBackend(sensitivity=sens)
    if name == "kernel_driver":
        from .kernel_driver import KernelDriverBackend
        return KernelDriverBackend()
    raise ValueError(f"Unknown input backend: {name!r}. Choose: relative_mouse, virtual_gamepad, kernel_driver")


__all__ = ["InputBackend", "create_backend"]

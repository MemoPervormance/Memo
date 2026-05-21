"""Capture backend registry."""
from __future__ import annotations
from .base import CaptureBackend

BACKEND_NAMES = ["dxgi", "winrt", "capture_card", "udp", "ndi"]
BACKEND_LABELS = {
    "dxgi":         "DXGI Desktop Duplication API (Standard)",
    "winrt":        "Windows.Graphics.Capture (WinRT)",
    "capture_card": "Capture Card (DirectShow)",
    "udp":          "UDP Frame Receiver (2-PC)",
    "ndi":          "NDI Network Video",
}


def create_capture(cfg) -> CaptureBackend:
    name = (cfg.capture.backend if cfg else "dxgi").lower()

    if name == "dxgi":
        from .dxgi import DXGICapture
        return DXGICapture(
            monitor=cfg.capture.monitor,
            capture_size=cfg.capture.capture_size,
            circle_mask=cfg.capture.circle_mask,
        )
    if name == "winrt":
        from .winrt import WinRTCapture
        return WinRTCapture(
            monitor=cfg.capture.monitor,
            capture_size=cfg.capture.capture_size,
            circle_mask=cfg.capture.circle_mask,
        )
    if name == "capture_card":
        from .capture_card import CaptureCardCapture
        return CaptureCardCapture(
            source_name=cfg.capture.capture_card_source,
            capture_size=cfg.capture.capture_size,
        )
    if name == "udp":
        from .udp_receiver import UDPCapture
        return UDPCapture(
            host=cfg.capture.udp_host,
            port=cfg.capture.udp_port,
            capture_size=cfg.capture.capture_size,
        )
    if name == "ndi":
        from .ndi_receiver import NDICapture
        return NDICapture(
            source_name=cfg.capture.ndi_source,
            capture_size=cfg.capture.capture_size,
        )
    raise ValueError(f"Unknown capture backend: {name!r}")


__all__ = ["CaptureBackend", "create_capture", "BACKEND_NAMES", "BACKEND_LABELS"]

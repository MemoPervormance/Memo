"""
Logitech G-Hub input backend — sends mouse movement via G-Hub's local HTTP API.
G-Hub must be running. Logitech Gaming Software API listens on localhost:12010.
"""
from __future__ import annotations
import json
import sys
import urllib.request
from .base import InputBackend


class GHubBackend(InputBackend):
    """
    Uses Logitech G-Hub's localhost HTTP endpoint to send relative mouse moves.
    No driver installation needed beyond G-Hub itself.
    """

    def __init__(self, port: int = 12010) -> None:
        self._base = f"http://localhost:{port}"
        self._fire_held = False
        self._ads_held  = False
        # Verify G-Hub is reachable
        try:
            urllib.request.urlopen(f"{self._base}/", timeout=2)
        except Exception:
            pass  # G-Hub may not respond to GET / — continue anyway

    def _post(self, path: str, data: dict) -> None:
        payload = json.dumps(data).encode()
        req = urllib.request.Request(
            f"{self._base}{path}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=0.05)
        except Exception:
            pass

    def move_cursor(self, dx: int, dy: int) -> None:
        if dx == 0 and dy == 0:
            return
        self._post("/mouse_move", {"dx": dx, "dy": dy})

    def press_fire(self) -> None:
        if not self._fire_held:
            self._post("/mouse_button", {"button": 1, "state": "pressed"})
            self._fire_held = True

    def release_fire(self) -> None:
        if self._fire_held:
            self._post("/mouse_button", {"button": 1, "state": "released"})
            self._fire_held = False

    def press_ads(self) -> None:
        if not self._ads_held:
            self._post("/mouse_button", {"button": 2, "state": "pressed"})
            self._ads_held = True

    def release_ads(self) -> None:
        if self._ads_held:
            self._post("/mouse_button", {"button": 2, "state": "released"})
            self._ads_held = False

    def release_all(self) -> None:
        self.release_fire()
        self.release_ads()

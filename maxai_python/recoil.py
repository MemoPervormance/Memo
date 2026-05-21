"""Recoil compensation — downward counter-movement while firing."""
from __future__ import annotations
from config import RecoilConfig


class RecoilCompensator:
    """
    Applies a counter-movement opposing detected recoil while the fire button is held.
    Strength maps to negative dy added each frame during fire.
    Smoothing prevents instant step changes.
    """

    def __init__(self, cfg: RecoilConfig) -> None:
        self._cfg = cfg
        self._acc = 0.0
        self._firing_frames = 0

    def update_config(self, cfg: RecoilConfig) -> None:
        self._cfg = cfg

    def reset(self) -> None:
        self._acc = 0.0
        self._firing_frames = 0

    def apply(self, dy: int, is_firing: bool) -> int:
        """Return adjusted dy with recoil compensation added."""
        if not self._cfg.enabled:
            return dy

        if is_firing:
            self._firing_frames += 1
            # Recoil grows slightly over continuous fire (ramp), capped
            ramp = min(self._firing_frames / 10.0, 1.0)
            compensation = -self._cfg.strength * ramp
            smooth = self._cfg.smoothness
            self._acc = self._acc * (1.0 - 1.0 / smooth) + compensation / smooth
        else:
            self._acc *= 0.8   # decay quickly when not firing
            self._firing_frames = 0

        result = dy + round(self._acc)
        return result

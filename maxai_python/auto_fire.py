"""Auto-fire module — state machine: Idle → Confirming → Delay → Firing → Cooldown."""
from __future__ import annotations
import enum
import time
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from config import TriggerbotConfig
from detector_yolo import Detection
from math_utils import distance


class _State(enum.Enum):
    IDLE       = "idle"
    CONFIRMING = "confirming"
    DELAY      = "delay"
    FIRING     = "firing"
    COOLDOWN   = "cooldown"


@dataclass
class TriggerResult:
    should_fire: bool
    state: str


class AutoFireModule:
    """
    Trigger logic:
    - Detects if a target's bounding box overlaps the crosshair (within radius).
    - Optional pixel-variance visibility check.
    - State machine controls confirmation frames, delay, burst, and cooldown.
    """

    def __init__(self, cfg: TriggerbotConfig) -> None:
        self._cfg = cfg
        self._state = _State.IDLE
        self._confirm_frames = 0
        self._state_start = 0.0

    def update_config(self, cfg: TriggerbotConfig) -> None:
        self._cfg = cfg

    def update(
        self,
        detections: List[Detection],
        screen_cx: float,
        screen_cy: float,
        frame_bgra: Optional[np.ndarray] = None,
        crop_offset: tuple = (0, 0),
    ) -> TriggerResult:
        cfg = self._cfg
        now = time.monotonic()

        target = self._find_trigger_target(detections, screen_cx, screen_cy, cfg)

        on_target = target is not None
        if on_target and cfg.visibility_check and frame_bgra is not None:
            on_target = self._check_visibility(target, frame_bgra, crop_offset, cfg)

        # State machine
        if self._state == _State.IDLE:
            if on_target:
                self._state = _State.CONFIRMING
                self._confirm_frames = 1
                self._state_start = now
            return TriggerResult(False, self._state.value)

        elif self._state == _State.CONFIRMING:
            if on_target:
                self._confirm_frames += 1
                if self._confirm_frames >= cfg.min_frames:
                    self._state = _State.DELAY
                    self._state_start = now
            else:
                self._state = _State.IDLE
                self._confirm_frames = 0
            return TriggerResult(False, self._state.value)

        elif self._state == _State.DELAY:
            elapsed_ms = (now - self._state_start) * 1000
            if elapsed_ms >= cfg.delay_ms:
                self._state = _State.FIRING
                self._state_start = now
            elif not on_target:
                self._state = _State.IDLE
            return TriggerResult(False, self._state.value)

        elif self._state == _State.FIRING:
            elapsed_ms = (now - self._state_start) * 1000
            if elapsed_ms >= cfg.burst_ms:
                self._state = _State.COOLDOWN
                self._state_start = now
                return TriggerResult(False, self._state.value)
            return TriggerResult(True, self._state.value)

        elif self._state == _State.COOLDOWN:
            elapsed_ms = (now - self._state_start) * 1000
            if elapsed_ms >= cfg.cooldown_ms:
                self._state = _State.IDLE
            return TriggerResult(False, self._state.value)

        return TriggerResult(False, self._state.value)

    def reset(self) -> None:
        self._state = _State.IDLE
        self._confirm_frames = 0

    # ------------------------------------------------------------------

    def _find_trigger_target(
        self,
        detections: List[Detection],
        cx: float, cy: float,
        cfg: TriggerbotConfig,
    ) -> Optional[Detection]:
        for det in detections:
            if det.confidence < cfg.min_confidence:
                continue
            # Check if crosshair is inside the bounding box (with radius tolerance)
            inside_x = det.x1 - cfg.crosshair_radius <= cx <= det.x2 + cfg.crosshair_radius
            inside_y = det.y1 - cfg.crosshair_radius <= cy <= det.y2 + cfg.crosshair_radius
            if inside_x and inside_y:
                return det
        return None

    def _check_visibility(
        self,
        target: Detection,
        frame_bgra: np.ndarray,
        crop_offset: tuple,
        cfg: TriggerbotConfig,
    ) -> bool:
        """Return True if pixel variance in target centre suggests a real target."""
        ox, oy = crop_offset
        h, w = frame_bgra.shape[:2]
        cx = int((target.x1 + target.x2) / 2 - ox)
        cy = int((target.y1 + target.y2) / 2 - oy)
        half = cfg.sample_size // 2
        x1 = max(0, cx - half)
        y1 = max(0, cy - half)
        x2 = min(w, cx + half + 1)
        y2 = min(h, cy + half + 1)
        if x2 <= x1 or y2 <= y1:
            return True  # can't sample, assume visible
        patch = frame_bgra[y1:y2, x1:x2, :3].astype(np.float32)
        variance = float(np.var(patch))
        return variance >= cfg.min_pixel_variance

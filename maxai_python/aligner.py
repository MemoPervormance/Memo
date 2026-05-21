"""Crosshair Aligner — target selection, prediction, smooth movement delta."""
from __future__ import annotations
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Optional, Tuple

from config import AimConfig, ControllerConfig, CrosshairConfig
from detector_yolo import Detection
from math_utils import clamp, distance, iou, normalize, magnitude


# ---------------------------------------------------------------------------
# Target Predictor (ring buffer velocity → lead pixel)
# ---------------------------------------------------------------------------

@dataclass
class _Sample:
    x: float
    y: float
    t: float  # time.monotonic()


class TargetPredictor:
    """Predict future target position based on recent movement history."""

    BUFFER_SIZE = 8

    def __init__(self, cfg_pred) -> None:
        self._buf: Deque[_Sample] = deque(maxlen=self.BUFFER_SIZE)
        self._cfg = cfg_pred

    def update(self, tx: float, ty: float) -> Tuple[float, float]:
        """Add current target centre, return predicted (tx, ty) with lead."""
        now = time.monotonic()
        cfg = self._cfg

        # Detect jump (target switch)
        if self._buf:
            last = self._buf[-1]
            jump = distance(last.x, last.y, tx, ty)
            if jump > cfg.lead_max_jump:
                self._buf.clear()

        self._buf.append(_Sample(tx, ty, now))

        if not cfg.enabled or len(self._buf) < 2:
            return tx, ty

        oldest = self._buf[0]
        newest = self._buf[-1]
        dt = newest.t - oldest.t
        if dt < 1e-4:
            return tx, ty

        vx = (newest.x - oldest.x) / dt
        vy = (newest.y - oldest.y) / dt
        speed = magnitude(vx, vy)

        if speed < cfg.min_speed:
            return tx, ty

        lead_px = clamp(speed * cfg.lead_factor / 1000.0, 0.0, cfg.max_offset)
        nx, ny = normalize(vx, vy)
        return tx + nx * lead_px, ty + ny * lead_px * 0.3

    def reset(self) -> None:
        self._buf.clear()

    def check_same_target(self, x1: float, y1: float, x2: float, y2: float,
                          prev_box: Optional[Tuple[float, float, float, float]]) -> bool:
        if prev_box is None or not self._buf:
            return False
        return iou((x1, y1, x2, y2), prev_box) > 0.2


# ---------------------------------------------------------------------------
# Crosshair Aligner
# ---------------------------------------------------------------------------

class CrosshairAligner:
    """
    Selects the best detection and computes (dx, dy) integer pixel movement.

    Movement formula mirrors Rust: sub-pixel accumulator + smoothness.
    """

    def __init__(
        self,
        aim_cfg: AimConfig,
        ctrl_cfg: ControllerConfig,
        ch_cfg: CrosshairConfig,
    ) -> None:
        self._aim  = aim_cfg
        self._ctrl = ctrl_cfg
        self._ch   = ch_cfg
        self._pred = TargetPredictor(aim_cfg.prediction)
        self._acc_x = 0.0
        self._acc_y = 0.0
        self._prev_box: Optional[Tuple[float, float, float, float]] = None

    def update_config(self, aim_cfg: AimConfig, ctrl_cfg: ControllerConfig,
                      ch_cfg: CrosshairConfig) -> None:
        self._aim  = aim_cfg
        self._ctrl = ctrl_cfg
        self._ch   = ch_cfg
        self._pred._cfg = aim_cfg.prediction

    def reset(self) -> None:
        self._pred.reset()
        self._acc_x = 0.0
        self._acc_y = 0.0
        self._prev_box = None

    def update(
        self,
        detections: List[Detection],
        screen_cx: float,
        screen_cy: float,
        priority_classes: Optional[List[int]] = None,
        target_classes: Optional[List[int]] = None,
    ) -> Tuple[int, int]:
        """
        Select best target and return (dx, dy) integer pixel delta to send.
        Returns (0, 0) if no valid target.
        """
        target = self._select_target(
            detections, screen_cx, screen_cy,
            priority_classes or [], target_classes or [],
        )
        if target is None:
            self.reset()
            return 0, 0

        # Aim point (head from top)
        tx = (target.x1 + target.x2) / 2.0
        ty = target.y1 + (target.y2 - target.y1) * self._aim.head_from_top

        # Parallax
        crosshair_x = screen_cx + self._ch.offset_x
        crosshair_y = screen_cy + self._ch.offset_y
        if self._ch.parallax_x != 0 or self._ch.parallax_y != 0:
            crosshair_x += self._ch.parallax_x * (tx - screen_cx)
            crosshair_y += self._ch.parallax_y * (ty - screen_cy)

        # Prediction
        tx, ty = self._pred.update(tx, ty)
        self._prev_box = target.box()

        raw_dx = tx - crosshair_x
        raw_dy = ty - crosshair_y

        # Smoothness / speed
        smoothness = max(1.0, self._aim.aim_smoothness)
        dist = magnitude(raw_dx, raw_dy)

        # Reduce smoothing inside snap zone
        if dist < self._aim.snap_zone_px:
            effective_smooth = max(1.0, smoothness * 0.5)
        else:
            effective_smooth = smoothness

        step_x = raw_dx / effective_smooth
        step_y = raw_dy / effective_smooth

        # Sub-pixel accumulator (mirrors Rust)
        self._acc_x += step_x
        self._acc_y += step_y

        int_x = int(self._acc_x)
        int_y = int(self._acc_y)
        self._acc_x -= int_x
        self._acc_y -= int_y

        # Minimum move threshold (rs_min_magnitude → min_move_pixels)
        min_mag = self._ctrl.rs_min_magnitude * 10  # rough pixel equivalent
        if magnitude(int_x, int_y) < min_mag:
            return 0, 0

        return int_x, int_y

    # ------------------------------------------------------------------

    def _select_target(
        self,
        detections: List[Detection],
        cx: float, cy: float,
        priority_classes: List[int],
        target_classes: List[int],
    ) -> Optional[Detection]:
        candidates = [
            d for d in detections
            if (not target_classes or d.class_id in target_classes)
            and distance(d.cx, d.cy, cx, cy) <= self._aim.fov_radius
        ]
        if not candidates:
            return None

        # Priority class first
        if priority_classes:
            prio = [d for d in candidates if d.class_id in priority_classes]
            if prio:
                candidates = prio

        return min(candidates, key=lambda d: distance(d.cx, d.cy, cx, cy))

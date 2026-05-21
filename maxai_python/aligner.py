"""
Crosshair Aligner — full product spec:
  position (head/body), FOV X/Y, speed, snap/near radius,
  scope multiplier, sticky target, prediction, wind mouse.
"""
from __future__ import annotations
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple

from config import AimConfig, ControllerConfig, CrosshairConfig
from detector_yolo import Detection
from math_utils import clamp, distance, iou, normalize, magnitude
from wind_mouse import wind_mouse_steps


# ---------------------------------------------------------------------------
# Target Predictor
# ---------------------------------------------------------------------------

@dataclass
class _Sample:
    x: float
    y: float
    t: float


class TargetPredictor:
    BUFFER_SIZE = 8

    def __init__(self, cfg) -> None:
        self._buf: Deque[_Sample] = deque(maxlen=self.BUFFER_SIZE)
        self._cfg = cfg

    def update(self, tx: float, ty: float) -> Tuple[float, float]:
        now = time.monotonic()
        cfg = self._cfg

        if self._buf:
            last = self._buf[-1]
            if distance(last.x, last.y, tx, ty) > cfg.lead_max_jump:
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

        # Project future_positions steps ahead via interval
        steps = max(1, cfg.future_positions)
        interval = cfg.interval  # seconds per step
        lead_t = steps * interval if interval > 0 else (cfg.lead_factor / 1000.0)
        lead_px = clamp(speed * lead_t, 0.0, cfg.max_offset)
        nx, ny  = normalize(vx, vy)
        return tx + nx * lead_px, ty + ny * lead_px * 0.3

    def future_dots(
        self, tx: float, ty: float
    ) -> List[Tuple[float, float]]:
        """Return projected future positions for overlay rendering."""
        cfg = self._cfg
        if not self._buf or len(self._buf) < 2:
            return []
        oldest = self._buf[0]
        newest = self._buf[-1]
        dt = newest.t - oldest.t
        if dt < 1e-4:
            return []
        vx = (newest.x - oldest.x) / dt
        vy = (newest.y - oldest.y) / dt
        pts = []
        interval = cfg.interval if cfg.interval > 0 else 0.016
        for i in range(1, cfg.future_positions + 1):
            pts.append((tx + vx * interval * i, ty + vy * interval * i))
        return pts

    def reset(self) -> None:
        self._buf.clear()


# ---------------------------------------------------------------------------
# Sticky Target tracker
# ---------------------------------------------------------------------------

class StickyTracker:
    def __init__(self, cfg) -> None:
        self._cfg = cfg
        self._locked_id: Optional[int] = None
        self._lock_time: float = 0.0
        self._locked_box: Optional[Tuple[float, float, float, float]] = None

    def update_config(self, cfg) -> None:
        self._cfg = cfg

    def select(
        self,
        candidates: List[Detection],
        cx: float, cy: float,
    ) -> Optional[Detection]:
        cfg = self._cfg
        now = time.monotonic()

        if not cfg.enabled:
            return _closest(candidates, cx, cy)

        # Try to re-identify locked target by IoU
        if self._locked_box is not None:
            for d in candidates:
                if iou(d.box(), self._locked_box) > 0.2:
                    if cfg.static_filter and _is_static(d):
                        self._locked_box = None
                        break
                    self._locked_box = d.box()
                    return d

        # Lock expired or lost — pick new closest
        if now - self._lock_time > cfg.hold_duration:
            best = _closest(candidates, cx, cy)
            if best:
                if cfg.static_filter and _is_static(best):
                    return None
                self._locked_id   = id(best)
                self._lock_time   = now
                self._locked_box  = best.box()
            return best

        return None

    def reset(self) -> None:
        self._locked_id  = None
        self._lock_time  = 0.0
        self._locked_box = None


def _closest(dets: List[Detection], cx: float, cy: float) -> Optional[Detection]:
    if not dets:
        return None
    return min(dets, key=lambda d: distance(d.cx, d.cy, cx, cy))


def _is_static(d: Detection) -> bool:
    return False   # placeholder — needs velocity history


# ---------------------------------------------------------------------------
# Crosshair Aligner
# ---------------------------------------------------------------------------

class CrosshairAligner:
    def __init__(
        self,
        aim_cfg: AimConfig,
        ctrl_cfg: ControllerConfig,
        ch_cfg: CrosshairConfig,
    ) -> None:
        self._aim    = aim_cfg
        self._ctrl   = ctrl_cfg
        self._ch     = ch_cfg
        self._pred   = TargetPredictor(aim_cfg.prediction)
        self._sticky = StickyTracker(aim_cfg.sticky_target)
        self._acc_x  = 0.0
        self._acc_y  = 0.0
        self._wm_buf: List[Tuple[int, int]] = []

    def update_config(
        self,
        aim_cfg: AimConfig,
        ctrl_cfg: ControllerConfig,
        ch_cfg: CrosshairConfig,
    ) -> None:
        self._aim  = aim_cfg
        self._ctrl = ctrl_cfg
        self._ch   = ch_cfg
        self._pred._cfg   = aim_cfg.prediction
        self._sticky.update_config(aim_cfg.sticky_target)

    def reset(self) -> None:
        self._pred.reset()
        self._sticky.reset()
        self._acc_x = 0.0
        self._acc_y = 0.0
        self._wm_buf.clear()

    # ------------------------------------------------------------------

    def update(
        self,
        detections: List[Detection],
        screen_cx: float,
        screen_cy: float,
        priority_classes: Optional[List[int]] = None,
        target_classes: Optional[List[int]] = None,
        scoped: bool = False,
    ) -> Tuple[int, int]:
        target = self._select_target(
            detections, screen_cx, screen_cy,
            priority_classes or [], target_classes or [],
        )
        if target is None:
            self.reset()
            return 0, 0

        # Aim point based on position setting
        tx = (target.x1 + target.x2) / 2.0
        if self._aim.position == "body":
            ty = target.y1 + (target.y2 - target.y1) * 0.5
        else:  # head
            ty = target.y1 + (target.y2 - target.y1) * self._aim.head_from_top

        # Parallax
        crosshair_x = screen_cx + self._ch.offset_x
        crosshair_y = screen_cy + self._ch.offset_y
        if self._ch.parallax_x or self._ch.parallax_y:
            crosshair_x += self._ch.parallax_x * (tx - screen_cx)
            crosshair_y += self._ch.parallax_y * (ty - screen_cy)

        # Scope multiplier — reduce movement speed when scoped
        scope_scale = (1.0 / self._aim.scope_multiplier) if scoped and self._aim.scope_multiplier > 0 else 1.0

        # Prediction
        tx, ty = self._pred.update(tx, ty)

        raw_dx = (tx - crosshair_x) * scope_scale
        raw_dy = (ty - crosshair_y) * scope_scale

        # Speed factor (0.1–3.0)
        raw_dx *= self._aim.speed
        raw_dy *= self._aim.speed

        dist = magnitude(raw_dx, raw_dy)

        # Wind mouse — consumes buffered steps first
        if self._aim.wind_mouse.enabled:
            if self._wm_buf:
                step = self._wm_buf.pop(0)
                return step
            # Refill buffer for this movement
            self._wm_buf = list(wind_mouse_steps(raw_dx, raw_dy, self._aim.wind_mouse))
            if self._wm_buf:
                return self._wm_buf.pop(0)
            return 0, 0

        # Standard smoothing
        snap = self._aim.snap_radius
        near = self._aim.near_radius
        smoothness = max(1.0, self._aim.aim_smoothness)

        if dist <= snap:
            effective_smooth = 1.0            # instant snap in zone
        elif dist <= near:
            effective_smooth = smoothness * 0.6
        else:
            effective_smooth = smoothness

        step_x = raw_dx / effective_smooth
        step_y = raw_dy / effective_smooth

        # Sub-pixel accumulator
        self._acc_x += step_x
        self._acc_y += step_y
        int_x = int(self._acc_x)
        int_y = int(self._acc_y)
        self._acc_x -= int_x
        self._acc_y -= int_y

        min_px = self._ctrl.rs_min_magnitude * 10
        if magnitude(int_x, int_y) < min_px:
            return 0, 0

        return int_x, int_y

    def get_future_dots(
        self,
        target: Detection,
    ) -> List[Tuple[float, float]]:
        tx = (target.x1 + target.x2) / 2.0
        ty = target.y1 + (target.y2 - target.y1) * self._aim.head_from_top
        return self._pred.future_dots(tx, ty)

    # ------------------------------------------------------------------

    def _select_target(
        self,
        detections: List[Detection],
        cx: float, cy: float,
        priority_classes: List[int],
        target_classes: List[int],
    ) -> Optional[Detection]:
        # FOV filter — use fov_x/fov_y as pixel radii (proportional to blob size)
        fov_x = self._aim.fov_x * 3.0   # rough px conversion
        fov_y = self._aim.fov_y * 3.0

        candidates = [
            d for d in detections
            if (not target_classes or d.class_id in target_classes)
            and abs(d.cx - cx) <= fov_x
            and abs(d.cy - cy) <= fov_y
        ]
        if not candidates:
            return None

        if priority_classes:
            prio = [d for d in candidates if d.class_id in priority_classes]
            if prio:
                candidates = prio

        return self._sticky.select(candidates, cx, cy)

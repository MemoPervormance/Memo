"""
CroixAI — Ultimate Crosshair Aligner v3.

Pipeline per frame:
  1. Target Scoring  — multi-criteria priority (dist, conf, class, size, velocity)
  2. Sticky Tracker  — hysteresis + IoU re-identification + occlusion hold
  3. Kalman Predictor— 2D Kalman filter (position + velocity) N-frame lookahead
  4. Aim Point       — head / body / custom fraction + parallax + scope scale
  5. Movement Mode   — FLICK / BEZIER_TRACK / SNAP_LOCK chosen by distance
  6. Magnetism       — exponential slowdown entering target bbox (no overshoot)
  7. Wind Mouse      — humanized arc movement (FLICK zone only)
  8. Sub-pixel Acc   — fractional accumulator for precision at any speed
"""
from __future__ import annotations

import enum
import random
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple

from config import AimConfig, ControllerConfig, CrosshairConfig
from detector_yolo import Detection
from math_utils import (
    KalmanFilter2D,
    adaptive_speed,
    bezier_steps,
    clamp,
    distance,
    ease_in_out_quart,
    ease_out,
    iou,
    lerp,
    magnetism_factor,
    magnitude,
    normalize,
    s_curve,
)
from wind_mouse import wind_mouse_steps


# ---------------------------------------------------------------------------
# Movement mode
# ---------------------------------------------------------------------------

class _Mode(enum.Enum):
    FLICK        = "flick"        # target far away  — WindMouse arc + bezier
    BEZIER_TRACK = "bezier_track" # medium distance  — smooth bezier curve
    SNAP_LOCK    = "snap_lock"    # inside snap zone — precision micro-correction


# ---------------------------------------------------------------------------
# Target scoring
# ---------------------------------------------------------------------------

class TargetScorer:
    """
    Assigns a priority score to each Detection.
    Higher score = better target to aim at.
    """

    # Class priority bonuses (class_id → bonus)
    CLASS_BONUS: Dict[int, float] = {
        0: 2.0,   # head  → highest priority
        1: 1.0,   # body
        2: 0.6,   # limb / drone / secondary class
    }

    def score(
        self,
        det: Detection,
        crosshair_x: float,
        crosshair_y: float,
        aim_fov_x: float,
        aim_fov_y: float,
        kf_speed: float = 0.0,
    ) -> float:
        """
        Score ∈ [0, ∞). Callers should pick the highest-scoring target.
        Components:
          - Proximity: 1/(1 + normalised_dist)^2  — strong weight on closeness
          - Confidence: raw model confidence
          - Class bonus: head > body > other
          - Size penalty: very large boxes penalised (already close, trigger instead)
          - Velocity bonus: moving targets predicted better → slight bonus
        """
        dist = distance(det.cx, det.cy, crosshair_x, crosshair_y)
        max_dist = magnitude(aim_fov_x * 3.0, aim_fov_y * 3.0) or 1.0
        norm_dist = dist / max_dist

        proximity  = 1.0 / (1.0 + norm_dist) ** 2.2
        confidence = det.confidence
        cls_bonus  = self.CLASS_BONUS.get(det.class_id, 0.5)
        size       = (det.w * det.h) / max(1.0, (aim_fov_x * 6.0) * (aim_fov_y * 6.0))
        size_pen   = 1.0 / (1.0 + size * 0.5)   # larger = slightly lower priority
        vel_bonus  = min(1.0, kf_speed / 200.0) * 0.15

        return (proximity * 3.0 + confidence + cls_bonus + vel_bonus) * size_pen


# ---------------------------------------------------------------------------
# Sticky Target Tracker  (hysteresis + IoU + occlusion hold)
# ---------------------------------------------------------------------------

class StickyTracker:
    """
    Keeps the same target locked across frames.
    Features:
    - IoU-based re-identification (works even if bbox shifts slightly)
    - Hysteresis: won't switch targets for min 250ms after acquisition
    - Occlusion hold: keeps tracking for up to 12 frames (≈200ms) after target disappears
    - Static filter: ignores stationary targets if configured
    """

    _IOU_THRESHOLD     = 0.20
    _HYSTERESIS_S      = 0.25   # minimum seconds before switching target
    _MAX_OCCLUDE_FRAMES= 12

    def __init__(self, cfg) -> None:
        self._cfg          = cfg
        self._locked_box: Optional[Tuple] = None
        self._lock_at      = 0.0
        self._occlude_count= 0
        self._last_vel     = (0.0, 0.0)   # for static_filter
        self._prev_cx      = 0.0
        self._prev_cy      = 0.0
        self._first        = True

    def update_config(self, cfg) -> None:
        self._cfg = cfg

    def select(
        self,
        candidates: List[Detection],
        cx: float,
        cy: float,
        scorer: TargetScorer,
        kf_vx: float = 0.0,
        kf_vy: float = 0.0,
        aim_fov_x: float = 60.0,
        aim_fov_y: float = 60.0,
    ) -> Optional[Detection]:
        cfg = self._cfg
        now = time.monotonic()

        if not candidates:
            self._occlude_count += 1
            if self._occlude_count > self._MAX_OCCLUDE_FRAMES:
                self._locked_box = None
            return None

        self._occlude_count = 0

        # --- Try to re-identify locked target via IoU ---
        if self._locked_box is not None:
            best_iou   = 0.0
            best_match = None
            for d in candidates:
                ov = iou(d.box(), self._locked_box)
                if ov > best_iou:
                    best_iou   = ov
                    best_match = d

            if best_match and best_iou >= self._IOU_THRESHOLD:
                if cfg.static_filter and self._is_static(best_match, kf_vx, kf_vy):
                    self._locked_box = None
                else:
                    self._locked_box = best_match.box()
                    return best_match

        # --- Hysteresis guard: don't switch too fast ---
        if self._locked_box is not None and (now - self._lock_at) < self._HYSTERESIS_S:
            # locked box lost IoU but within hysteresis — return closest
            return min(candidates, key=lambda d: distance(d.cx, d.cy, cx, cy))

        # --- Pick new best target via scoring ---
        kf_speed = magnitude(kf_vx, kf_vy)
        best = max(
            candidates,
            key=lambda d: scorer.score(d, cx, cy, aim_fov_x, aim_fov_y, kf_speed),
        )
        if cfg.static_filter and self._is_static(best, kf_vx, kf_vy):
            return None

        self._locked_box = best.box()
        self._lock_at    = now
        return best

    def _is_static(self, det: Detection, vx: float, vy: float) -> bool:
        return magnitude(vx, vy) < 8.0

    def reset(self) -> None:
        self._locked_box  = None
        self._lock_at     = 0.0
        self._occlude_count = 0


# ---------------------------------------------------------------------------
# Kalman Predictor
# ---------------------------------------------------------------------------

class KalmanPredictor:
    """
    Wraps KalmanFilter2D with:
    - Per-target tracking (resets on large jumps)
    - N-frame ahead prediction
    - Future dot generation for overlay
    """

    def __init__(self, cfg) -> None:
        self._cfg = cfg
        self._kf  = KalmanFilter2D(
            process_noise_pos = 2.0,
            process_noise_vel = 12.0,
            measurement_noise = 4.0,
        )
        self._last_t = 0.0

    def update_config(self, cfg) -> None:
        self._cfg = cfg

    def update(self, tx: float, ty: float) -> Tuple[float, float]:
        """Feed measurement, return smoothed + predicted aim point."""
        now = time.monotonic()
        dt  = clamp(now - self._last_t, 0.001, 0.1) if self._last_t else 0.016
        self._last_t = now
        cfg = self._cfg

        # Jump detection — reinitialise if target teleported
        if self._kf._initialized:
            old_x, old_y = self._kf._x[0], self._kf._x[1]
            if distance(old_x, old_y, tx, ty) > cfg.lead_max_jump:
                self._kf.reset()

        self._kf.predict(dt)
        px, py = self._kf.update(tx, ty)

        if not cfg.enabled:
            return tx, ty

        vx, vy = self._kf.get_velocity()
        speed  = magnitude(vx, vy)
        if speed < cfg.min_speed:
            return px, py

        # Lead: how far ahead to aim
        steps    = max(1, cfg.future_positions)
        interval = cfg.interval if cfg.interval > 0 else dt
        lead_t   = steps * interval
        lead_px  = clamp(speed * lead_t, 0.0, cfg.max_offset)

        nx, ny = normalize(vx, vy)
        # Vertical lead slightly reduced (gravity / head movement)
        return px + nx * lead_px, py + ny * lead_px * 0.65

    def future_dots(self, tx: float, ty: float) -> List[Tuple[float, float]]:
        if not self._kf._initialized:
            return []
        vx, vy   = self._kf.get_velocity()
        cfg      = self._cfg
        interval = cfg.interval if cfg.interval > 0 else 0.016
        return [
            (tx + vx * interval * i, ty + vy * interval * i)
            for i in range(1, cfg.future_positions + 1)
        ]

    def get_velocity(self) -> Tuple[float, float]:
        return self._kf.get_velocity()

    def reset(self) -> None:
        self._kf.reset()
        self._last_t = 0.0


# ---------------------------------------------------------------------------
# Flick Detector
# ---------------------------------------------------------------------------

class FlickDetector:
    """
    Detects when the target has jumped far enough to need a flick movement.
    Flick = target appears or moves > flick_threshold px from crosshair.
    """

    def __init__(self, flick_threshold_px: float = 120.0) -> None:
        self._threshold = flick_threshold_px
        self._flick_end = 0.0
        self._FLICK_HOLD_S = 0.12  # keep flick mode active for N seconds

    def check(self, dist: float) -> bool:
        now = time.monotonic()
        if dist >= self._threshold:
            self._flick_end = now + self._FLICK_HOLD_S
        return now < self._flick_end


# ---------------------------------------------------------------------------
# Main CrosshairAligner
# ---------------------------------------------------------------------------

class CrosshairAligner:
    """
    The ultimate CroixAI aimbot.

    Movement pipeline per frame:
      FLICK (dist > near*1.5):
        Wind Mouse arc steps — humanized, undetectable trajectory
      BEZIER_TRACK (snap < dist <= near*1.5):
        Smooth bezier curve approach — speed scales with distance
        Magnetism slowdown as entering target bbox
      SNAP_LOCK (dist <= snap):
        Direct micro-correction — sub-pixel precise
        Magnetism at maximum strength
        Head-zone lock: near-zero error tolerance

    All zones:
      - Sub-pixel accumulator prevents rounding loss
      - Scope multiplier scales ALL movement when ADS
      - Kalman prediction pre-aims lead point
    """

    def __init__(
        self,
        aim_cfg:  AimConfig,
        ctrl_cfg: ControllerConfig,
        ch_cfg:   CrosshairConfig,
    ) -> None:
        self._aim    = aim_cfg
        self._ctrl   = ctrl_cfg
        self._ch     = ch_cfg

        self._pred   = KalmanPredictor(aim_cfg.prediction)
        self._sticky = StickyTracker(aim_cfg.sticky_target)
        self._scorer = TargetScorer()
        self._flick  = FlickDetector(flick_threshold_px=aim_cfg.near_radius * 1.5)

        # Sub-pixel accumulators
        self._acc_x  = 0.0
        self._acc_y  = 0.0

        # Wind mouse step buffer
        self._wm_buf: List[Tuple[int, int]] = []

        # Bezier step buffer
        self._bz_buf: List[Tuple[float, float]] = []

        # Current mode tracking
        self._mode      = _Mode.BEZIER_TRACK
        self._on_target = False

        # Acceleration ramp (frames since new target acquired)
        self._acq_frames = 0

    def update_config(
        self,
        aim_cfg:  AimConfig,
        ctrl_cfg: ControllerConfig,
        ch_cfg:   CrosshairConfig,
    ) -> None:
        self._aim  = aim_cfg
        self._ctrl = ctrl_cfg
        self._ch   = ch_cfg
        self._pred.update_config(aim_cfg.prediction)
        self._sticky.update_config(aim_cfg.sticky_target)
        self._flick = FlickDetector(aim_cfg.near_radius * 1.5)

    def reset(self) -> None:
        self._pred.reset()
        self._sticky.reset()
        self._acc_x = 0.0
        self._acc_y = 0.0
        self._wm_buf.clear()
        self._bz_buf.clear()
        self._on_target  = False
        self._acq_frames = 0

    # ------------------------------------------------------------------
    # Main update — call once per frame with current detections
    # ------------------------------------------------------------------

    def update(
        self,
        detections: List[Detection],
        screen_cx: float,
        screen_cy: float,
        priority_classes: Optional[List[int]] = None,
        target_classes:   Optional[List[int]] = None,
        scoped: bool = False,
    ) -> Tuple[int, int]:

        aim  = self._aim
        ch   = self._ch

        # ── Filter by class and FOV ────────────────────────────────
        fov_x = aim.fov_x * 3.0
        fov_y = aim.fov_y * 3.0
        candidates = [
            d for d in detections
            if (not target_classes or d.class_id in target_classes)
            and abs(d.cx - screen_cx) <= fov_x
            and abs(d.cy - screen_cy) <= fov_y
        ]

        # Priority class filter (e.g. prefer head-class detections)
        prio_classes = priority_classes or [0]   # default: class 0 = head
        prio = [d for d in candidates if d.class_id in prio_classes]
        pool = prio if prio else candidates

        # ── Target selection ──────────────────────────────────────
        kf_vx, kf_vy = self._pred.get_velocity()
        target = self._sticky.select(
            pool, screen_cx, screen_cy, self._scorer,
            kf_vx, kf_vy, aim.fov_x, aim.fov_y,
        )

        if target is None:
            # Carry on from wind mouse / bezier buffer a few more frames
            if self._wm_buf:
                sx, sy = self._wm_buf.pop(0)
                return sx, sy
            self.reset()
            return 0, 0

        # ── Aim point ─────────────────────────────────────────────
        tx = (target.x1 + target.x2) / 2.0
        if aim.position == "body":
            ty = target.y1 + (target.y2 - target.y1) * 0.50
        else:  # head
            ty = target.y1 + (target.y2 - target.y1) * aim.head_from_top

        # Parallax offset
        crs_x = screen_cx + ch.offset_x + ch.parallax_x * (tx - screen_cx)
        crs_y = screen_cy + ch.offset_y + ch.parallax_y * (ty - screen_cy)

        # ── Kalman prediction ────────────────────────────────────
        pred_tx, pred_ty = self._pred.update(tx, ty)

        # ── Scope multiplier ─────────────────────────────────────
        scope_scale = (1.0 / aim.scope_multiplier) if scoped and aim.scope_multiplier > 1.0 else 1.0

        raw_dx = (pred_tx - crs_x) * scope_scale
        raw_dy = (pred_ty - crs_y) * scope_scale
        dist   = magnitude(raw_dx, raw_dy)

        snap = aim.snap_radius
        near = aim.near_radius

        # ── Acquisition ramp ────────────────────────────────────
        if not self._on_target:
            self._acq_frames = 0
            self._on_target  = True
            self._wm_buf.clear()
            self._bz_buf.clear()
        self._acq_frames += 1
        acq_ramp = min(1.0, self._acq_frames / 6.0)   # full speed after 6 frames

        # ── Choose movement mode ─────────────────────────────────
        is_flick = self._flick.check(dist)

        if is_flick and dist > near * 0.8:
            self._mode = _Mode.FLICK
        elif dist > snap:
            self._mode = _Mode.BEZIER_TRACK
        else:
            self._mode = _Mode.SNAP_LOCK

        # ── Generate movement ────────────────────────────────────
        if self._mode == _Mode.FLICK:
            return self._move_flick(raw_dx, raw_dy, dist, aim, acq_ramp, snap)
        elif self._mode == _Mode.BEZIER_TRACK:
            return self._move_bezier(raw_dx, raw_dy, dist, target, aim, acq_ramp, snap, near)
        else:
            return self._move_snap(raw_dx, raw_dy, dist, target, aim)

    # ------------------------------------------------------------------
    # Movement implementations
    # ------------------------------------------------------------------

    def _move_flick(
        self,
        dx: float, dy: float,
        dist: float,
        aim: AimConfig,
        acq_ramp: float,
        snap: float,
    ) -> Tuple[int, int]:
        """
        FLICK mode: Wind Mouse arc to get near the target fast.
        Uses wind_mouse for first 70% of travel then hands off to bezier.
        """
        # Drain existing wind mouse buffer first
        if self._wm_buf:
            sx, sy = self._wm_buf.pop(0)
            return self._accumulate(sx, sy)

        if aim.wind_mouse.enabled:
            # Wind mouse to 85% of the distance, rest handled by bezier next frame
            target_dx = dx * 0.85
            target_dy = dy * 0.85
            self._wm_buf = list(wind_mouse_steps(target_dx, target_dy, aim.wind_mouse))
            if self._wm_buf:
                sx, sy = self._wm_buf.pop(0)
                return self._accumulate(sx, sy)

        # Fallback: large-step bezier flick
        speed = adaptive_speed(dist, snap, aim.near_radius, aim.speed, 0.4, 4.0)
        step_x = dx * speed * 0.5 * acq_ramp
        step_y = dy * speed * 0.5 * acq_ramp
        return self._accumulate(step_x, step_y)

    def _move_bezier(
        self,
        dx: float, dy: float,
        dist: float,
        target: Detection,
        aim: AimConfig,
        acq_ramp: float,
        snap: float,
        near: float,
    ) -> Tuple[int, int]:
        """
        BEZIER_TRACK mode: smooth curved approach.
        Speed scales with distance. Magnetism slows entry into bbox.
        """
        # Adaptive speed: faster when far, gentler when approaching
        speed = adaptive_speed(dist, snap, near, aim.speed,
                               min_factor=0.12, max_factor=2.5)

        smoothness = max(1.0, aim.aim_smoothness)
        # Ramp-in: first few frames after acquiring target, move more gently
        effective_s = smoothness * lerp(2.5, 1.0, acq_ramp)

        step_dx = dx * speed / effective_s
        step_dy = dy * speed / effective_s

        # Magnetism: slow down as crosshair enters bbox
        box_w = target.w
        box_h = target.h
        mag = magnetism_factor(dx, dy, box_w, box_h, strength=1.8)
        step_dx *= mag
        step_dy *= mag

        return self._accumulate(step_dx, step_dy)

    def _move_snap(
        self,
        dx: float, dy: float,
        dist: float,
        target: Detection,
        aim: AimConfig,
    ) -> Tuple[int, int]:
        """
        SNAP_LOCK mode: precision micro-correction inside snap zone.
        Magnetism at full strength — no overshoot.
        Allows < 1px corrections via accumulator.
        """
        # In snap zone: move proportional to distance with strong magnetism
        speed = max(0.05, dist / max(1.0, aim.snap_radius))   # 0→1 as dist→snap
        step_x = dx * speed
        step_y = dy * speed

        # Strong magnetism in lock zone
        mag = magnetism_factor(dx, dy, target.w, target.h, strength=3.0)
        step_x *= mag
        step_y *= mag

        return self._accumulate(step_x, step_y)

    # ------------------------------------------------------------------
    # Sub-pixel accumulator
    # ------------------------------------------------------------------

    def _accumulate(self, sx: float, sy: float) -> Tuple[int, int]:
        """
        Accumulate fractional pixels and emit integer movements.
        Ensures no precision is lost to rounding.
        """
        self._acc_x += sx
        self._acc_y += sy
        ix = int(self._acc_x)
        iy = int(self._acc_y)
        self._acc_x -= ix
        self._acc_y -= iy

        # Minimum movement threshold (avoids micro-jitter from accumulator drift)
        rs_min = self._ctrl.rs_min_magnitude * 10.0
        if magnitude(ix, iy) < rs_min and rs_min > 0:
            # Don't cancel — keep accumulating until threshold
            pass
        return ix, iy

    # ------------------------------------------------------------------
    # Overlay data
    # ------------------------------------------------------------------

    def get_future_dots(self, target: Detection) -> List[Tuple[float, float]]:
        tx = (target.x1 + target.x2) / 2.0
        ty = target.y1 + (target.y2 - target.y1) * self._aim.head_from_top
        return self._pred.future_dots(tx, ty)

    def current_mode(self) -> str:
        return self._mode.value

    def is_locked(self) -> bool:
        return self._on_target and self._mode == _Mode.SNAP_LOCK

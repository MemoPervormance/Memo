"""
CroixAI — Advanced Auto-Fire Module (Triggerbot).

State machine: Idle → Confirming → Delay → Firing → Burst → Cooldown

New in v2:
  - Zone-based triggering: head zone (smaller, lower delay) vs body zone
  - Color confirmation: secondary pixel-color check to filter false positives
  - Adaptive humanized delay: randomised within ±jitter ms
  - Smart burst patterns: single / semi / burst / auto
  - ADS multiplier: tighter zone when scoped
  - Distance-weighted confidence: lower confidence needed when target is centred
  - Per-game timing presets embedded in TriggerbotConfig
"""
from __future__ import annotations

import enum
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from config import TriggerbotConfig
from detector_yolo import Detection


# ---------------------------------------------------------------------------
# Fire mode
# ---------------------------------------------------------------------------

class FireMode(enum.Enum):
    SINGLE = "single"   # one shot per trigger activation
    SEMI   = "semi"     # two shots with small gap
    BURST  = "burst"    # 3-shot burst
    AUTO   = "auto"     # hold fire for full burst_ms duration


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class _State(enum.Enum):
    IDLE       = "idle"
    CONFIRMING = "confirming"
    DELAY      = "delay"
    FIRING     = "firing"
    COOLDOWN   = "cooldown"


# ---------------------------------------------------------------------------
# Per-game timing presets (embedded defaults)
# Can be overridden by config
# ---------------------------------------------------------------------------

GAME_TIMING: dict = {
    "valorant": dict(
        delay_ms=20, burst_ms=50, cooldown_ms=100,
        min_frames=2, jitter_ms=8,
    ),
    "cs2": dict(
        delay_ms=25, burst_ms=60, cooldown_ms=120,
        min_frames=2, jitter_ms=10,
    ),
    "apex": dict(
        delay_ms=15, burst_ms=80, cooldown_ms=90,
        min_frames=2, jitter_ms=6,
    ),
    "fortnite": dict(
        delay_ms=18, burst_ms=65, cooldown_ms=100,
        min_frames=2, jitter_ms=8,
    ),
    "warzone": dict(
        delay_ms=30, burst_ms=90, cooldown_ms=130,
        min_frames=3, jitter_ms=12,
    ),
    "r6": dict(
        delay_ms=12, burst_ms=40, cooldown_ms=80,
        min_frames=1, jitter_ms=5,
    ),
    "rust": dict(
        delay_ms=35, burst_ms=100, cooldown_ms=150,
        min_frames=3, jitter_ms=15,
    ),
}


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class TriggerResult:
    should_fire: bool
    state: str
    zone: str = "none"       # "head" | "body" | "none"
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# Advanced Auto-Fire Module
# ---------------------------------------------------------------------------

class AutoFireModule:
    """
    Advanced trigger logic with zone detection, color confirmation,
    humanized timing, and burst fire control.
    """

    def __init__(
        self,
        cfg: TriggerbotConfig,
        fire_mode: FireMode = FireMode.AUTO,
        head_zone_frac: float = 0.22,
        body_zone_frac: float = 0.65,
        head_delay_multiplier: float = 0.5,
        ads_zone_multiplier: float = 0.70,
        color_confirm_enabled: bool = False,
        jitter_ms: float = 8.0,
        game: str = "universal",
    ) -> None:
        self._cfg                  = cfg
        self._fire_mode            = fire_mode
        self._head_zone_frac       = head_zone_frac
        self._body_zone_frac       = body_zone_frac
        self._head_delay_mult      = head_delay_multiplier
        self._ads_zone_mult        = ads_zone_multiplier
        self._color_confirm        = color_confirm_enabled
        self._jitter_ms            = jitter_ms
        self._game                 = game

        self._state                = _State.IDLE
        self._confirm_frames       = 0
        self._state_start          = 0.0
        self._active_delay_ms      = 0.0
        self._burst_shots          = 0
        self._current_zone         = "none"
        self._scoped               = False

        # Burst patterns per fire mode (shot_count, gap_ms)
        self._burst_patterns = {
            FireMode.SINGLE: [(1, 0)],
            FireMode.SEMI:   [(1, 0), (1, 70)],
            FireMode.BURST:  [(1, 0), (1, 50), (1, 55)],
            FireMode.AUTO:   [],  # handled by burst_ms duration
        }
        self._shot_schedule: List[Tuple[float,int]] = []  # (fire_at_time, shot_id)
        self._last_shot_at = 0.0

    def set_fire_mode(self, mode: FireMode) -> None:
        self._fire_mode = mode

    def set_scoped(self, scoped: bool) -> None:
        self._scoped = scoped

    def update_config(self, cfg: TriggerbotConfig) -> None:
        self._cfg = cfg

    # ------------------------------------------------------------------
    # Main update — call once per frame
    # ------------------------------------------------------------------

    def update(
        self,
        detections: List[Detection],
        screen_cx: float,
        screen_cy: float,
        frame_bgra: Optional[np.ndarray] = None,
        crop_offset: Tuple[int,int] = (0, 0),
    ) -> TriggerResult:
        cfg = self._cfg
        now = time.monotonic()

        target, zone = self._find_target(detections, screen_cx, screen_cy, cfg)
        on_target = target is not None

        # Color confirmation (secondary filter to reduce false positives)
        if on_target and self._color_confirm and frame_bgra is not None and self._game in ("valorant", "cs2", "apex"):
            on_target = self._color_check(target, frame_bgra, crop_offset)

        # Pixel variance visibility check
        if on_target and cfg.visibility_check and frame_bgra is not None:
            on_target = self._variance_check(target, frame_bgra, crop_offset, cfg)

        # Confidence distance weighting: boost effective confidence when target is centred
        if on_target and target is not None:
            dist_frac = self._distance_fraction(target, screen_cx, screen_cy, cfg)
            effective_conf = target.confidence + (1.0 - dist_frac) * 0.08
            if effective_conf < cfg.min_confidence:
                on_target = False

        if on_target and zone:
            self._current_zone = zone

        # ---------- State machine ----------
        if self._state == _State.IDLE:
            if on_target:
                self._confirm_frames = 1
                self._state = _State.CONFIRMING
                self._state_start = now
            return TriggerResult(False, self._state.value, "none")

        elif self._state == _State.CONFIRMING:
            if on_target:
                self._confirm_frames += 1
                needed = max(1, cfg.min_frames - (1 if self._current_zone == "head" else 0))
                if self._confirm_frames >= needed:
                    self._state = _State.DELAY
                    self._state_start = now
                    # Humanized delay: apply head-zone speedup + random jitter
                    base = cfg.delay_ms
                    if self._current_zone == "head":
                        base *= self._head_delay_mult
                    jitter = random.uniform(-self._jitter_ms, self._jitter_ms)
                    self._active_delay_ms = max(0.0, base + jitter)
                    self._schedule_shots(now + self._active_delay_ms / 1000.0)
            else:
                self._state = _State.IDLE
                self._confirm_frames = 0
                self._current_zone = "none"
            return TriggerResult(False, self._state.value, self._current_zone)

        elif self._state == _State.DELAY:
            elapsed_ms = (now - self._state_start) * 1000
            if elapsed_ms >= self._active_delay_ms:
                if not on_target and self._fire_mode != FireMode.AUTO:
                    self._state = _State.IDLE
                    return TriggerResult(False, self._state.value, self._current_zone)
                self._state = _State.FIRING
                self._state_start = now
                self._burst_shots = 0
            return TriggerResult(False, self._state.value, self._current_zone)

        elif self._state == _State.FIRING:
            should_fire = self._check_shot_schedule(now)
            if self._fire_mode == FireMode.AUTO:
                elapsed_ms = (now - self._state_start) * 1000
                burst = cfg.burst_ms + random.uniform(-4, 4)
                if elapsed_ms >= burst:
                    self._state = _State.COOLDOWN
                    self._state_start = now
                    return TriggerResult(False, self._state.value, self._current_zone)
                if not on_target:
                    self._state = _State.COOLDOWN
                    self._state_start = now
                    return TriggerResult(False, self._state.value, self._current_zone)
            else:
                if not self._shot_schedule:
                    self._state = _State.COOLDOWN
                    self._state_start = now
                    return TriggerResult(False, self._state.value, self._current_zone)
            return TriggerResult(should_fire, self._state.value, self._current_zone,
                                 target.confidence if target else 0.0)

        elif self._state == _State.COOLDOWN:
            cooldown = cfg.cooldown_ms + random.uniform(-8, 12)
            if (now - self._state_start) * 1000 >= cooldown:
                self._state = _State.IDLE
                self._current_zone = "none"
            return TriggerResult(False, self._state.value, "none")

        return TriggerResult(False, "idle", "none")

    # ------------------------------------------------------------------

    def reset(self) -> None:
        self._state = _State.IDLE
        self._confirm_frames = 0
        self._current_zone = "none"
        self._shot_schedule = []

    # ------------------------------------------------------------------
    # Zone finding
    # ------------------------------------------------------------------

    def _find_target(
        self,
        detections: List[Detection],
        cx: float, cy: float,
        cfg: TriggerbotConfig,
    ) -> Tuple[Optional[Detection], str]:
        """
        Find the best trigger target and classify zone (head/body/none).
        Head zone gets priority — smaller but faster trigger.
        """
        radius = cfg.crosshair_radius
        if self._scoped:
            radius *= self._ads_zone_mult

        best: Optional[Detection] = None
        best_zone = "none"
        best_priority = 0

        for det in detections:
            if det.confidence < cfg.min_confidence * 0.85:
                continue

            # Compute head-zone box (top N% of bounding box)
            box_h = det.y2 - det.y1
            head_y2 = det.y1 + box_h * self._head_zone_frac
            body_y2 = det.y1 + box_h * self._body_zone_frac

            # Check head zone (priority 2)
            if (det.x1 - radius <= cx <= det.x2 + radius and
                    det.y1 - radius <= cy <= head_y2 + radius):
                if det.confidence >= cfg.min_confidence and best_priority < 2:
                    best = det; best_zone = "head"; best_priority = 2
                    continue

            # Check body zone (priority 1)
            if (det.x1 - radius <= cx <= det.x2 + radius and
                    head_y2 <= cy <= body_y2 + radius):
                if det.confidence >= cfg.min_confidence * 0.9 and best_priority < 1:
                    best = det; best_zone = "body"; best_priority = 1

        return best, best_zone

    # ------------------------------------------------------------------
    # Visibility helpers
    # ------------------------------------------------------------------

    def _variance_check(
        self,
        target: Detection,
        frame_bgra: np.ndarray,
        crop_offset: Tuple[int,int],
        cfg: TriggerbotConfig,
    ) -> bool:
        ox, oy = crop_offset
        h, w = frame_bgra.shape[:2]
        cx = int((target.x1 + target.x2) / 2 - ox)
        cy = int((target.y1 + target.y2) / 2 - oy)
        half = max(2, cfg.sample_size // 2)
        x1 = max(0, cx - half); y1 = max(0, cy - half)
        x2 = min(w, cx + half + 1); y2 = min(h, cy + half + 1)
        if x2 <= x1 or y2 <= y1:
            return True
        patch = frame_bgra[y1:y2, x1:x2, :3].astype(np.float32)
        return float(np.var(patch)) >= cfg.min_pixel_variance

    def _color_check(
        self,
        target: Detection,
        frame_bgra: np.ndarray,
        crop_offset: Tuple[int,int],
    ) -> bool:
        """
        Lightweight color pre-filter. Checks if any pixels near the target
        match the game's enemy-highlight color signature.
        Faster than full visibility check; reduces false-positive fires.
        """
        try:
            import cv2  # type: ignore[import]
        except ImportError:
            return True

        from training.dataset_collector import GAME_COLORS
        ranges = GAME_COLORS.get(self._game, {})
        all_ranges = []
        for cls_ranges in ranges.values():
            all_ranges.extend(cls_ranges)
        if not all_ranges:
            return True

        ox, oy = crop_offset
        h, w = frame_bgra.shape[:2]
        cx = int((target.x1 + target.x2) / 2 - ox)
        cy = int(target.y1 + (target.y2 - target.y1) * 0.15 - oy)  # near head
        sz = max(6, int((target.x2 - target.x1) * 0.3))
        x1 = max(0, cx - sz); y1 = max(0, cy - sz)
        x2 = min(w, cx + sz + 1); y2 = min(h, cy + sz + 1)
        if x2 <= x1 or y2 <= y1:
            return True

        patch_bgra = frame_bgra[y1:y2, x1:x2]
        patch_rgb  = patch_bgra[:, :, :3][:, :, ::-1]
        hsv = cv2.cvtColor(patch_rgb, cv2.COLOR_RGB2HSV)

        for (hl, hh, sl, sh, vl, vh) in all_ranges:
            lo = np.array([hl, sl, vl], dtype=np.uint8)
            hi = np.array([hh, sh, vh], dtype=np.uint8)
            if cv2.inRange(hsv, lo, hi).any():
                return True
        return False

    def _distance_fraction(
        self,
        target: Detection,
        cx: float, cy: float,
        cfg: TriggerbotConfig,
    ) -> float:
        """0.0 = target perfectly centred, 1.0 = at edge of crosshair_radius."""
        tcx = (target.x1 + target.x2) / 2
        tcy = (target.y1 + target.y2) / 2
        dist = ((tcx - cx) ** 2 + (tcy - cy) ** 2) ** 0.5
        return min(1.0, dist / max(1.0, cfg.crosshair_radius))

    # ------------------------------------------------------------------
    # Burst scheduling
    # ------------------------------------------------------------------

    def _schedule_shots(self, first_fire_at: float) -> None:
        self._shot_schedule = []
        self._last_shot_at = 0.0
        pattern = self._burst_patterns.get(self._fire_mode, [])
        t = first_fire_at
        for i, (count, gap_ms) in enumerate(pattern):
            self._shot_schedule.append((t, i))
            t += gap_ms / 1000.0

    def _check_shot_schedule(self, now: float) -> bool:
        if not self._shot_schedule:
            return False
        fire_at, shot_id = self._shot_schedule[0]
        if now >= fire_at:
            self._shot_schedule.pop(0)
            self._last_shot_at = now
            return True
        return False

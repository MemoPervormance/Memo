"""
CroixAI — Wind Mouse Algorithm v2.
Humanized mouse movement: gravity + wind + speed clamping.
Yields (dx, dy) integer steps that sum to (dx_total, dy_total).
Handles large distances correctly with momentum ramp-up / deceleration.
"""
from __future__ import annotations
import math
import random
from typing import Iterator, List, Tuple

from config import WindMouseConfig


def wind_mouse_steps(
    dx_total: float,
    dy_total: float,
    cfg: WindMouseConfig,
) -> Iterator[Tuple[int, int]]:
    """
    Yield (dx, dy) integer steps following the Wind Mouse formula.
    Improvements over v1:
    - Momentum ramp-up at start (looks more human — you don't flick at max speed instantly)
    - Deceleration zone in last 15% — natural stop
    - Wind turbulence decreases as target approaches (precision near end)
    - Overshoot detection and correction
    """
    G       = cfg.gravity
    W       = cfg.wind
    M       = cfg.max_step
    T       = cfg.target_area

    total   = math.hypot(dx_total, dy_total)
    if total < T:
        return

    xs = ys = 0.0
    remaining_x = float(dx_total)
    remaining_y = float(dy_total)
    traveled    = 0.0
    decel_start = total * 0.82   # start decelerating at 82% of distance

    while True:
        dist = math.hypot(remaining_x, remaining_y)
        if dist < T:
            break

        # Progress along movement: 0.0 = start, 1.0 = arrival
        progress = (total - dist) / total

        # Wind turbulence: full at start, reduces near target
        wind_scale = 1.0 - progress * 0.7
        wind_x = random.uniform(-W, W) * wind_scale
        wind_y = random.uniform(-W, W) * wind_scale

        # Gravity toward target
        xs = xs / 2.0 + (remaining_x / dist) * G + wind_x
        ys = ys / 2.0 + (remaining_y / dist) * G + wind_y

        # Speed cap: ramp-up for first 15% (start slow), decelerate near end
        speed = math.hypot(xs, ys)
        if progress < 0.15:
            # Ramp-up: limit to a fraction of max
            cap = M * (0.3 + progress / 0.15 * 0.7)
        elif dist < total * 0.18:
            # Deceleration zone
            decel_frac = dist / (total * 0.18)
            cap = max(T * 0.5, M * (0.25 + decel_frac * 0.75))
        else:
            cap = M

        if speed > cap:
            scale = cap / speed
            xs *= scale
            ys *= scale

        step_x = round(xs)
        step_y = round(ys)

        # Prevent zero steps from stalling
        if step_x == 0 and step_y == 0:
            step_x = 1 if remaining_x >= 0 else -1
            step_y = 1 if remaining_y >= 0 else -1

        remaining_x -= step_x
        remaining_y -= step_y
        traveled    += math.hypot(step_x, step_y)

        yield step_x, step_y

        # Overshoot detection
        if (remaining_x * dx_total < 0 and abs(remaining_x) > T) or \
           (remaining_y * dy_total < 0 and abs(remaining_y) > T):
            break

    # Final precision correction
    fx = round(remaining_x)
    fy = round(remaining_y)
    if fx != 0 or fy != 0:
        yield fx, fy


def wind_mouse_path(
    dx_total: float,
    dy_total: float,
    cfg: WindMouseConfig,
) -> List[Tuple[int, int]]:
    """Return all steps as a list (for buffering)."""
    return list(wind_mouse_steps(dx_total, dy_total, cfg))

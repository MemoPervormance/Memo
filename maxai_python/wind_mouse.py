"""
Wind Mouse algorithm — humanized mouse movement.
Simulates physical mouse behavior with momentum, gravity, and wind forces.
Outputs a sequence of (dx, dy) integer steps to reach target.
"""
from __future__ import annotations
import math
import random
from typing import Iterator, Tuple

from config import WindMouseConfig


def wind_mouse_steps(
    dx_total: float,
    dy_total: float,
    cfg: WindMouseConfig,
) -> Iterator[Tuple[int, int]]:
    """
    Yield (dx, dy) integer steps that together approximate the target (dx_total, dy_total).
    Uses the Wind Mouse formula for naturalistic movement.
    """
    G  = cfg.gravity      # pull toward target
    W  = cfg.wind         # random lateral force
    M  = cfg.max_step     # max pixels per step
    T  = cfg.target_area  # stop threshold

    xs = ys = 0.0   # velocity
    remaining_x = float(dx_total)
    remaining_y = float(dy_total)

    while True:
        dist = math.hypot(remaining_x, remaining_y)
        if dist < T:
            break

        wind_x = random.uniform(-W, W)
        wind_y = random.uniform(-W, W)

        # Gravity toward target
        xs = xs / 2.0 + (remaining_x / dist) * G + wind_x
        ys = ys / 2.0 + (remaining_y / dist) * G + wind_y

        # Clamp to max step
        speed = math.hypot(xs, ys)
        if speed > M:
            scale = M / speed
            xs *= scale
            ys *= scale

        step_x = round(xs)
        step_y = round(ys)
        if step_x == 0 and step_y == 0:
            step_x = 1 if remaining_x > 0 else -1
            step_y = 1 if remaining_y > 0 else -1

        remaining_x -= step_x
        remaining_y -= step_y

        yield step_x, step_y

        # Check if overshot
        if (remaining_x * dx_total < 0) or (remaining_y * dy_total < 0):
            break

    # Final correction step
    final_x = round(remaining_x)
    final_y = round(remaining_y)
    if final_x or final_y:
        yield final_x, final_y

"""
CroixAI — Math Utilities v2.
Distance, IoU, vector ops, Kalman filter 2D, bezier, S-curve, EMA.
"""
from __future__ import annotations
import math
import random
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Basic ops
# ---------------------------------------------------------------------------

def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def iou(
    box_a: Tuple[float, float, float, float],
    box_b: Tuple[float, float, float, float],
) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    ix1 = max(ax1, bx1); iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2); iy2 = min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def normalize(dx: float, dy: float) -> Tuple[float, float]:
    mag = math.hypot(dx, dy)
    if mag < 1e-9:
        return 0.0, 0.0
    return dx / mag, dy / mag


def magnitude(dx: float, dy: float) -> float:
    return math.hypot(dx, dy)


# ---------------------------------------------------------------------------
# Easing / curve functions
# ---------------------------------------------------------------------------

def s_curve(t: float) -> float:
    """Smoothstep S-curve — smooth ease-in/out for t in [0,1]."""
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ease_out(t: float, power: float = 2.0) -> float:
    """Ease-out: fast start, slow finish."""
    t = clamp(t, 0.0, 1.0)
    return 1.0 - (1.0 - t) ** power


def ease_in_out_quart(t: float) -> float:
    """Quartic ease-in-out — very smooth start and end."""
    t = clamp(t, 0.0, 1.0)
    if t < 0.5:
        return 8.0 * t * t * t * t
    t2 = -2.0 * t + 2.0
    return 1.0 - t2 ** 4 / 2.0


def adaptive_speed(
    dist: float,
    snap: float,
    near: float,
    base_speed: float,
    min_factor: float = 0.10,
    max_factor: float = 3.0,
) -> float:
    """
    Speed multiplier that scales with distance:
    - Inside snap:  min_factor (precision mode)
    - At near:      1.0 × base
    - Beyond near:  ramps up toward max_factor
    """
    if dist <= snap:
        return min_factor
    elif dist <= near:
        t = (dist - snap) / max(1.0, near - snap)
        return lerp(min_factor, 1.0, s_curve(t))
    else:
        t = clamp((dist - near) / max(1.0, near * 2.0), 0.0, 1.0)
        return lerp(1.0, max_factor, ease_out(t, 1.5)) * base_speed


def magnetism_factor(
    dx: float,
    dy: float,
    box_w: float,
    box_h: float,
    strength: float = 2.5,
) -> float:
    """
    Returns a slowdown factor in [0, 1].
    The closer to the bbox centre, the slower the movement (controller aim assist feel).
    Factor = 1.0 far from box, approaches 0.0 at dead centre.
    """
    half_w = max(1.0, box_w * 0.5)
    half_h = max(1.0, box_h * 0.5)
    norm_x = abs(dx) / half_w
    norm_y = abs(dy) / half_h
    dist_norm = min(1.0, math.hypot(norm_x, norm_y))
    # Exponential pull — strongest at centre
    return 1.0 - math.exp(-dist_norm * strength) * (1.0 - dist_norm)


# ---------------------------------------------------------------------------
# Bezier curve
# ---------------------------------------------------------------------------

def bezier_quadratic(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    t: float,
) -> Tuple[float, float]:
    """Quadratic Bezier point at parameter t ∈ [0,1]."""
    one_t = 1.0 - t
    x = one_t**2 * p0[0] + 2*one_t*t * p1[0] + t**2 * p2[0]
    y = one_t**2 * p0[1] + 2*one_t*t * p1[1] + t**2 * p2[1]
    return x, y


def bezier_steps(
    dx_total: float,
    dy_total: float,
    steps: int,
    curve_factor: float = 0.25,
) -> List[Tuple[float, float]]:
    """
    Generate `steps` float (dx, dy) steps along a curved bezier path.
    curve_factor: how much the path curves (0=straight, 0.5=strong arc).
    Returns relative movements, not absolute positions.
    """
    if steps < 1:
        return [(dx_total, dy_total)]

    # Control point offset — perpendicular to motion for natural arc
    perp_x = -dy_total * curve_factor
    perp_y =  dx_total * curve_factor
    p0 = (0.0, 0.0)
    p1 = (dx_total * 0.5 + perp_x, dy_total * 0.5 + perp_y)
    p2 = (dx_total, dy_total)

    pts: List[Tuple[float, float]] = []
    prev = (0.0, 0.0)
    for i in range(1, steps + 1):
        t = i / steps
        pt = bezier_quadratic(p0, p1, p2, t)
        pts.append((pt[0] - prev[0], pt[1] - prev[1]))
        prev = pt
    return pts


# ---------------------------------------------------------------------------
# Kalman Filter 2D — constant-velocity model
# ---------------------------------------------------------------------------

class KalmanFilter2D:
    """
    2D Kalman filter for tracking position + velocity.
    State: [x, y, vx, vy]
    Measurement: [x, y]

    Handles:
    - Smooth position estimation from noisy bbox centres
    - Velocity estimation for prediction
    - Occlusion (no measurement for N frames → pure prediction)
    """

    def __init__(
        self,
        process_noise_pos:  float = 2.0,
        process_noise_vel:  float = 10.0,
        measurement_noise:  float = 5.0,
    ) -> None:
        # State: [x, y, vx, vy]
        self._x  = [0.0, 0.0, 0.0, 0.0]
        # Covariance matrix P (4×4, stored as flat 16 floats)
        self._P  = _mat_identity(4, scale=100.0)
        # Process noise Q
        self._Q  = _build_Q(process_noise_pos, process_noise_vel)
        # Measurement noise R (2×2)
        r = measurement_noise
        self._R  = [[r*r, 0.0], [0.0, r*r]]
        self._initialized = False
        self._miss_count  = 0

    def init(self, x: float, y: float) -> None:
        self._x = [x, y, 0.0, 0.0]
        self._P = _mat_identity(4, scale=50.0)
        self._initialized = True
        self._miss_count = 0

    def predict(self, dt: float = 0.016) -> Tuple[float, float]:
        """Advance state by dt seconds. Returns predicted [x, y]."""
        if not self._initialized:
            return self._x[0], self._x[1]
        # F = [[1,0,dt,0],[0,1,0,dt],[0,0,1,0],[0,0,0,1]]
        x, y, vx, vy = self._x
        self._x = [x + vx*dt, y + vy*dt, vx, vy]
        # P = F·P·Fᵀ + Q  (simplified for constant-velocity)
        self._P = _add_mat(_fPFt(self._P, dt), self._Q)
        self._miss_count += 1
        return self._x[0], self._x[1]

    def update(self, mx: float, my: float) -> Tuple[float, float]:
        """Update with measurement [mx, my]. Returns corrected [x, y]."""
        if not self._initialized:
            self.init(mx, my)
            return mx, my

        self._miss_count = 0
        px, py, pvx, pvy = self._x
        # Innovation: z - H·x
        inn_x = mx - px
        inn_y = my - py
        # S = H·P·Hᵀ + R
        s00 = self._P[0][0] + self._R[0][0]
        s11 = self._P[1][1] + self._R[1][1]
        s01 = self._P[0][1]
        det = s00*s11 - s01*s01
        if abs(det) < 1e-9:
            return mx, my
        # K = P·Hᵀ·S⁻¹  (Kalman gain, 4×2)
        inv_s = [[s11/det, -s01/det], [-s01/det, s00/det]]
        kx0 = self._P[0][0]*inv_s[0][0] + self._P[0][1]*inv_s[1][0]
        kx1 = self._P[0][0]*inv_s[0][1] + self._P[0][1]*inv_s[1][1]
        ky0 = self._P[1][0]*inv_s[0][0] + self._P[1][1]*inv_s[1][0]
        ky1 = self._P[1][0]*inv_s[0][1] + self._P[1][1]*inv_s[1][1]
        kz0 = self._P[2][0]*inv_s[0][0] + self._P[2][1]*inv_s[1][0]
        kz1 = self._P[2][0]*inv_s[0][1] + self._P[2][1]*inv_s[1][1]
        kw0 = self._P[3][0]*inv_s[0][0] + self._P[3][1]*inv_s[1][0]
        kw1 = self._P[3][0]*inv_s[0][1] + self._P[3][1]*inv_s[1][1]
        # x += K·innovation
        self._x[0] = px  + kx0*inn_x + kx1*inn_y
        self._x[1] = py  + ky0*inn_x + ky1*inn_y
        self._x[2] = pvx + kz0*inn_x + kz1*inn_y
        self._x[3] = pvy + kw0*inn_x + kw1*inn_y
        # P = (I - K·H)·P  (Joseph form simplified)
        self._P[0][0] *= (1 - kx0); self._P[1][1] *= (1 - ky1)
        self._P[2][2] *= (1 - kz0); self._P[3][3] *= (1 - kw1)
        return self._x[0], self._x[1]

    def get_velocity(self) -> Tuple[float, float]:
        return self._x[2], self._x[3]

    def get_speed(self) -> float:
        return math.hypot(self._x[2], self._x[3])

    def predict_ahead(self, frames: int, dt: float = 0.016) -> Tuple[float, float]:
        """Predict position N frames into the future without modifying state."""
        x, y, vx, vy = self._x
        return x + vx * dt * frames, y + vy * dt * frames

    @property
    def missing_frames(self) -> int:
        return self._miss_count

    def reset(self) -> None:
        self._initialized = False
        self._miss_count  = 0
        self._x           = [0.0, 0.0, 0.0, 0.0]


# ---------------------------------------------------------------------------
# Kalman helper matrices (pure-Python, no numpy required)
# ---------------------------------------------------------------------------

def _mat_identity(n: int, scale: float = 1.0) -> List[List[float]]:
    return [[scale if i == j else 0.0 for j in range(n)] for i in range(n)]


def _build_Q(qp: float, qv: float) -> List[List[float]]:
    return [
        [qp*qp, 0.0,   0.0,   0.0  ],
        [0.0,   qp*qp, 0.0,   0.0  ],
        [0.0,   0.0,   qv*qv, 0.0  ],
        [0.0,   0.0,   0.0,   qv*qv],
    ]


def _fPFt(P: List[List[float]], dt: float) -> List[List[float]]:
    """F·P·Fᵀ for constant-velocity F."""
    R = [[0.0]*4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            # F·P: rows 0,1 are x+vx*dt, y+vy*dt; rows 2,3 unchanged
            fp = P[i][j]
            if i == 0: fp += dt * P[2][j]
            if i == 1: fp += dt * P[3][j]
            R[i][j] = fp
    # R·Fᵀ
    out = [[0.0]*4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            v = R[i][j]
            if j == 0: v += dt * R[i][2]
            if j == 1: v += dt * R[i][3]
            out[i][j] = v
    return out


def _add_mat(A: List[List[float]], B: List[List[float]]) -> List[List[float]]:
    n = len(A)
    return [[A[i][j] + B[i][j] for j in range(n)] for i in range(n)]

"""Estimate vertical launch angle (psi) from the OPS243 radial-velocity timeline.

Fallback for when no K-LD7 vertical radar is present: the post-impact decay
shape of v_r(t) = V(t) * cos(psi) carries the signature of psi. A 2D ballistic
model (same aero coefficients as ballistics.py) is integrated for each
candidate psi and least-squares fitted against the measured v_r(t).
"""

import math
from dataclasses import dataclass
from typing import Optional

from .ballistics import (
    AIR_DENSITY_STD,
    MPH_TO_MPS,
    _derivatives,
    _rk4_step,
)
from .rolling_buffer.types import SpeedTimeline

# Candidate grid for psi (degrees). Coarse: the 4096-sample rolling buffer
# (~136 ms) only shows ~1-2 mph of decay, so psi is weakly constrained.
PSI_MIN_DEG = 2.0
PSI_MAX_DEG = 30.0
PSI_STEP_DEG = 0.5

# Only readings within this tolerance of the detected ball speed are used.
BALL_SPEED_TOLERANCE_MPH = 3.0

# Integration step for the 2D model.
DT_S = 0.002
MAX_T_S = 0.5


@dataclass
class LaunchAngleEstimate:
    psi_deg: float
    confidence: float
    sse: float
    n_points: int


def _simulate_vr(v0_mps: float, psi_deg: float, omega: float, t_eval_s: list) -> list:
    """Integrate 2D flight (x downrange, z up) and return v_r(t) = V(t)*cos(psi)."""
    psi = math.radians(psi_deg)
    vx = v0_mps * math.cos(psi)
    vz = v0_mps * math.sin(psi)
    # Pure backspin axis (spin_axis_deg=0 convention from ballistics.py).
    axis = (0.0, -1.0, 0.0)
    state = (0.0, 0.0, 0.0, vx, 0.0, vz)
    t = 0.0
    out = []
    idx = 0
    while t < MAX_T_S and idx < len(t_eval_s):
        while t < t_eval_s[idx] and t < MAX_T_S:
            state = _rk4_step(state, omega, axis, AIR_DENSITY_STD, DT_S)
            t += DT_S
        _, _, _, svx, _, svz = state
        v = math.hypot(svx, svz)
        out.append(v * math.cos(psi))
        idx += 1
    # If integration stopped early (ground hit), pad with last value.
    while idx < len(t_eval_s):
        _, _, _, svx, _, svz = state
        out.append(math.hypot(svx, svz) * math.cos(psi))
        idx += 1
    return out


def estimate_launch_angle(
    timeline: SpeedTimeline,
    ball_speed_mph: float,
    spin_rpm: Optional[float] = None,
    impact_ms: Optional[float] = None,
) -> Optional[LaunchAngleEstimate]:
    """Fit psi from post-impact v_r(t) readings around the detected ball speed."""
    omega = (spin_rpm or 0.0) * 2 * math.pi / 60.0

    pts = [
        (r.timestamp_ms, r.speed_mph * MPH_TO_MPS)
        for r in timeline.readings
        if r.is_outbound and abs(r.speed_mph - ball_speed_mph) <= BALL_SPEED_TOLERANCE_MPH
    ]
    if impact_ms is not None:
        pts = [(t, v) for t, v in pts if t >= impact_ms]
    if len(pts) < 5:
        return None

    pts.sort()
    t_s = [(t - pts[0][0]) / 1000.0 for t, _ in pts]
    vr_meas = [v for _, v in pts]
    mean_meas = sum(vr_meas) / len(vr_meas)
    sst = sum((v - mean_meas) ** 2 for v in vr_meas) or 1e-12

    best = None
    psi = PSI_MIN_DEG
    while psi <= PSI_MAX_DEG:
        # Measured ball speed is v_r at impact = V0*cos(psi) -> de-project.
        v0 = ball_speed_mph * MPH_TO_MPS / max(math.cos(math.radians(psi)), 0.1)
        vr_model = _simulate_vr(v0, psi, omega, t_s)
        # Least-squares scale c (v_r_model = c * vr_model_raw / cos handled inside).
        num = sum(m * r for m, r in zip(vr_model, vr_meas))
        den = sum(m * m for m in vr_model) or 1e-12
        c = num / den
        sse = sum((r - c * m) ** 2 for m, r in zip(vr_model, vr_meas))
        if best is None or sse < best[1]:
            best = (psi, sse)
        psi += PSI_STEP_DEG

    psi_deg, sse = best
    return LaunchAngleEstimate(
        psi_deg=psi_deg,
        confidence=max(0.0, 1.0 - sse / sst),
        sse=sse,
        n_points=len(pts),
    )

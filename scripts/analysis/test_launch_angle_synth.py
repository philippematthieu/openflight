# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Validate estimate_launch_angle() on synthetic v_r(t) with known psi."""
import math
import numpy as np

from openflight.launch_angle import (
    BALL_SPEED_TOLERANCE_MPH,
    LaunchAngleEstimate,
    _simulate_vr,
    estimate_launch_angle,
)
from openflight.ballistics import MPH_TO_MPS
from openflight.rolling_buffer.types import SpeedReading, SpeedTimeline

TRUE_PSI = 15.0
BALL_MPH = 94.9
OMEGA = 2500 * 2 * math.pi / 60  # 2500 rpm backspin

# Synthetic post-impact timeline: 68 ms -> 136 ms (rolling buffer window)
t_ms = np.arange(68.0, 136.0, 1.07)
v0 = BALL_MPH * MPH_TO_MPS / math.cos(math.radians(TRUE_PSI))
t_s = (t_ms - t_ms[0]) / 1000.0
vr = _simulate_vr(v0, TRUE_PSI, OMEGA, list(t_s))
# measured ball speed is v_r at impact
meas_ball = vr[0] / MPH_TO_MPS

readings = [
    SpeedReading(speed_mph=v / MPH_TO_MPS, magnitude=100.0, timestamp_ms=float(t), direction="outbound")
    for t, v in zip(t_ms, vr)
]
tl = SpeedTimeline(readings=readings, sample_rate_hz=937.0)

est = estimate_launch_angle(tl, meas_ball, spin_rpm=2500, impact_ms=68.0)
print(f"true psi = {TRUE_PSI} deg")
print(f"fit  psi = {est.psi_deg:.1f} deg, conf = {est.confidence:.3f}, n={est.n_points}")
print(f"error    = {est.psi_deg - TRUE_PSI:+.2f} deg")

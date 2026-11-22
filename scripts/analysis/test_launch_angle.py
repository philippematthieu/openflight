# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Test estimate_launch_angle() on a session_logs .pkl capture."""
import pickle
import sys

from openflight.launch_angle import estimate_launch_angle
from openflight.rolling_buffer.processor import RollingBufferProcessor
from openflight.rolling_buffer.types import IQCapture

pkl = sys.argv[1] if len(sys.argv) > 1 else "session_logs/capture_20260310_151805.pkl"
idx = int(sys.argv[2]) if len(sys.argv) > 2 else 1

with open(pkl, "rb") as f:
    data = pickle.load(f)
fs = data["metadata"]["sample_rate"]
cap = data["captures"][idx - 1]

iq = IQCapture(
    sample_time=cap.get("radar_sample_time", 0.0),
    trigger_time=cap.get("radar_trigger_time", 0.0),
    i_samples=cap["i_samples"],
    q_samples=cap["q_samples"],
)
proc = RollingBufferProcessor(sample_rate=fs)
result = proc.process_capture(iq)

est = estimate_launch_angle(
    result.timeline,
    result.ball_speed_mph,
    spin_rpm=result.spin.spin_rpm if result.spin else None,
    impact_ms=result.impact_timestamp_ms,
)
print(f"capture #{idx}: ball={result.ball_speed_mph:.1f} mph, impact={result.impact_timestamp_ms} ms")
if est:
    print(f"  psi = {est.psi_deg:.1f} deg, conf = {est.confidence:.3f}, n={est.n_points}")
else:
    print("  estimate_launch_angle returned None (not enough points)")

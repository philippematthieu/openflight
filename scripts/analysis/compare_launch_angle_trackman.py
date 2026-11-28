# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Run estimate_launch_angle() on a session JSONL and compare with TrackMan
launch_v_tm from comparison_20260506.csv. Prints a markdown table."""
import csv
import json
import sys

from openflight.launch_angle import estimate_launch_angle
from openflight.rolling_buffer.processor import RollingBufferProcessor
from openflight.rolling_buffer.types import IQCapture

SESSION = "session_logs/session_20260506_152406_range.jsonl"
COMP = "session_logs/comparison_20260506.csv"

tm = {}
with open(COMP) as f:
    for row in csv.DictReader(f):
        try:
            tm[int(row["shot_number_of"])] = float(row["launch_v_tm"])
        except (ValueError, KeyError):
            pass

rows = []
with open(SESSION) as f:
    for line in f:
        rec = json.loads(line)
        if rec.get("type") != "rolling_buffer_capture":
            continue
        iq = IQCapture(sample_time=rec["sample_time"], trigger_time=rec["trigger_time"],
                       i_samples=rec["i_samples"], q_samples=rec["q_samples"])
        result = RollingBufferProcessor(sample_rate=30000).process_capture(iq)
        est = estimate_launch_angle(result.timeline, result.ball_speed_mph,
                                    spin_rpm=result.spin.spin_rpm if result.spin else None,
                                    impact_ms=result.impact_timestamp_ms)
        n = rec.get("shot_number")
        launch_tm = tm.get(n)
        psi = est.psi_deg if est else None
        conf = est.confidence if est else None
        delta = (psi - launch_tm) if (psi is not None and launch_tm is not None) else None
        rows.append((n, result.ball_speed_mph, psi, conf, launch_tm, delta))

print("| shot | ball mph | ψ̂ (°) | conf | launch_v TM (°) | Δ ψ̂−TM (°) |")
print("|---|---|---|---|---|---|")
for n, b, psi, conf, ltm, d in rows:
    f = lambda v, nd=2: f"{v:.{nd}f}" if v is not None else "—"
    print(f"| {n} | {f(b,1)} | {f(psi,1)} | {f(conf,3)} | {f(ltm,1)} | {f(d,1)} |")

valid = [d for *_, d in rows if d is not None]
if valid:
    mae = sum(abs(d) for d in valid) / len(valid)
    print(f"\nMAE vs TrackMan = {mae:.2f}° sur {len(valid)} shots")

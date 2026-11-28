# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy"]
# ///
"""Test estimate_launch_angle() on session captures (.pkl or session .jsonl).

Version history:
  name: test_launch_angle.py
  v0.1.0 - 2026-11-23 - initial: run estimator on a .pkl capture (rolling buffer)
  v0.2.0 - 2026-11-23 - also accept session_logs/*.jsonl: iterate
             rolling_buffer_capture records and build IQCapture directly
"""
import json
import pickle
import sys

from openflight.launch_angle import estimate_launch_angle
from openflight.rolling_buffer.processor import RollingBufferProcessor
from openflight.rolling_buffer.types import IQCapture


def iter_pkl_captures(path, idx):
    with open(path, "rb") as f:
        data = pickle.load(f)
    fs = data["metadata"]["sample_rate"]
    cap = data["captures"][idx - 1]
    iq = IQCapture(
        sample_time=cap.get("radar_sample_time", 0.0),
        trigger_time=cap.get("radar_trigger_time", 0.0),
        i_samples=cap["i_samples"],
        q_samples=cap["q_samples"],
    )
    yield fs, iq, cap


def iter_jsonl_captures(path):
    with open(path) as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("type") != "rolling_buffer_capture":
                continue
            fs = 30000  # OPS243 rolling buffer default
            iq = IQCapture(
                sample_time=rec["sample_time"],
                trigger_time=rec["trigger_time"],
                i_samples=rec["i_samples"],
                q_samples=rec["q_samples"],
            )
            yield fs, iq, rec


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "session_logs/capture_20260310_151805.pkl"
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    if path.endswith(".jsonl"):
        sources = iter_jsonl_captures(path)
    else:
        sources = iter_pkl_captures(path, idx)

    for fs, iq, meta in sources:
        proc = RollingBufferProcessor(sample_rate=fs)
        result = proc.process_capture(iq)
        est = estimate_launch_angle(
            result.timeline,
            result.ball_speed_mph,
            spin_rpm=result.spin.spin_rpm if result.spin else None,
            impact_ms=result.impact_timestamp_ms,
        )
        shot = meta.get("shot_number", idx)
        print(f"shot {shot}: ball={result.ball_speed_mph:.1f} mph, impact={result.impact_timestamp_ms:.1f} ms", end="")
        if est:
            print(f"  ->  psi_hat = {est.psi_deg:.1f} deg, conf = {est.confidence:.3f}, n={est.n_points}")
        else:
            print("  ->  estimate_launch_angle returned None")


if __name__ == "__main__":
    main()

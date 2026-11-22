# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "matplotlib"]
# ///
"""Extract v_r(t) using the repo's OFFICIAL RollingBufferProcessor (CFAR etc.)."""
import pickle
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from openflight.rolling_buffer.processor import RollingBufferProcessor
from openflight.rolling_buffer.types import IQCapture


def main():
    import sys
    pkl = sys.argv[1] if len(sys.argv) > 1 else "session_logs/capture_20260310_151805.pkl"
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    out = sys.argv[3] if len(sys.argv) > 3 else "/Users/matthieuphilippe/Downloads/vr_official_c1.png"

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
    timeline = proc.process_overlapping(iq)

    # v_r(t): strongest positive reading per timestamp
    best = {}
    for r in timeline.readings:
        if r.speed_mph > 0 and (r.timestamp_ms not in best or r.magnitude > best[r.timestamp_ms].magnitude):
            best[r.timestamp_ms] = r
    ts = sorted(best)
    t_ms = np.array(ts)
    vr_mph = np.array([best[t].speed_mph for t in ts])
    trig = cap.get("trigger_offset_ms", 0)

    print(f"capture #{idx}, fs={fs} Hz, ball_speed_mph={cap.get('ball_speed_mph')}, readings={len(timeline.readings)}")
    print(f"peak v_r = {vr_mph.max():.1f} mph at t={t_ms[np.argmax(vr_mph)]:.1f} ms (trigger {trig:.0f} ms)")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t_ms, vr_mph, linewidth=1.5)
    ax.axvline(trig, color="red", ls="--", label=f"trigger {trig:.0f} ms")
    ax.set_xlabel("t (ms)"); ax.set_ylabel("v_r (mph)")
    ax.set_title(f"v_r(t) via RollingBufferProcessor — capture #{idx} ({pkl.split('/')[-1]})")
    ax.grid(True); ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()

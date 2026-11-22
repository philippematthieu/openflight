# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "matplotlib"]
# ///
"""Use the OFFICIAL process_capture() to extract ball speed/club/spin, and plot
the ball-only v_r(t) (readings within tolerance of detected ball speed)."""
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
    out = sys.argv[3] if len(sys.argv) > 3 else "/Users/matthieuphilippe/Downloads/ball_official_c1.png"

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

    print(f"=== ProcessedCapture (officiel) — capture #{idx}, {pkl.split('/')[-1]}")
    print(f"  ball_speed_mph  = {result.ball_speed_mph}")
    print(f"  club_speed_mph  = {result.club_speed_mph}")
    print(f"  smash           = {result.smash_factor}")
    sp = result.spin
    print(f"  spin_rpm        = {sp.spin_rpm if sp else None} (conf={sp.confidence if sp else None})")
    print(f"  (pkl metadata  : ball={cap.get('ball_speed_mph')}, club={cap.get('club_speed_mph')}, spin={cap.get('spin_rpm')})")

    # Ball-only v_r(t): overlapping timeline filtered around detected ball speed
    timeline = proc.process_overlapping(iq)
    tol = proc.BALL_SPEED_MATCH_TOLERANCE_MPH
    bs = result.ball_speed_mph
    pts = {}
    for r in timeline.readings:
        if r.is_outbound and abs(r.speed_mph - bs) <= tol:
            if r.timestamp_ms not in pts or r.magnitude > pts[r.timestamp_ms][1]:
                pts[r.timestamp_ms] = (r.speed_mph, r.magnitude)
    ts = sorted(pts)
    t_ms = np.array(ts)
    vr = np.array([pts[t][0] for t in ts])
    trig = cap.get("trigger_offset_ms", 0)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t_ms, vr, linewidth=1.5, label=f"balle (±{tol:.0f} mph autour de {bs:.1f})")
    ax.axvline(trig, color="red", ls="--", label=f"trigger {trig:.0f} ms")
    ax.set_xlabel("t (ms)"); ax.set_ylabel("v_r balle (mph)")
    ax.set_title(f"v_r(t) composante balle — capture #{idx} ({pkl.split('/')[-1]})")
    ax.grid(True); ax.legend()
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"Saved: {out}  ({len(ts)} points balle)")


if __name__ == "__main__":
    main()

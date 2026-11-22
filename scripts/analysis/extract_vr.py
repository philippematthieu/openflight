# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "matplotlib"]
# ///
"""Extract radial velocity v_r(t) from an OPS243 rolling-buffer .pkl capture."""
import pickle
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FC = 24.125e9
C = 299792458


def v_r_from_fd(fd):
    return fd * C / (2 * FC)  # m/s


def extract_vr(pkl_path, capture_idx=1, win=128, hop=32):
    with open(pkl_path, "rb") as f:
        data = pickle.load(f)
    fs = data["metadata"]["sample_rate"]
    cap = data["captures"][capture_idx - 1]
    i = np.array(cap["i_samples"], dtype=np.float64)
    q = np.array(cap["q_samples"], dtype=np.float64)
    s = (i - i.mean()) + 1j * (q - q.mean())

    window = np.hanning(win)
    n_fft = 4096
    freqs = np.fft.fftshift(np.fft.fftfreq(n_fft, 1 / fs))
    vr_bins = v_r_from_fd(freqs)
    dc_mask = np.abs(vr_bins) > 5.0  # exclude DC +/-5 m/s

    n = (len(s) - win) // hop + 1
    t_ms = np.zeros(n)
    vr = np.zeros(n)
    for k in range(n):
        seg = s[k * hop: k * hop + win] * window
        sp = np.abs(np.fft.fftshift(np.fft.fft(seg, n=n_fft)))
        sp = np.where(dc_mask, sp, 0)
        vr[k] = vr_bins[np.argmax(sp)]
        t_ms[k] = (k * hop + win / 2) / fs * 1000
    return t_ms, vr, cap, fs


if __name__ == "__main__":
    import sys
    pkl = sys.argv[1] if len(sys.argv) > 1 else "session_logs/capture_20260310_151805.pkl"
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    t, vr, cap, fs = extract_vr(pkl, idx)
    mph = vr * 2.23694
    print(f"capture #{idx}, fs={fs} Hz, ball_speed_mph={cap.get('ball_speed_mph')}")
    print(f"{'t (ms)':>8s} {'v_r (mph)':>10s}")
    for k in range(0, len(t), 4):
        print(f"{t[k]:8.1f} {mph[k]:10.1f}")
    print(f"peak v_r = {mph.max():.1f} mph at t={t[np.argmax(mph)]:.1f} ms")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, mph)
    ax.axvline(cap.get("trigger_offset_ms", 0), color="r", ls="--", label="trigger")
    ax.set_xlabel("t (ms)"); ax.set_ylabel("v_r (mph)"); ax.grid(True); ax.legend()
    ax.set_title(f"v_r(t) — capture #{idx}")
    fig.tight_layout()
    out = f"/Users/matthieuphilippe/Downloads/vr_capture_{idx}.png"
    fig.savefig(out, dpi=150)
    print(f"Saved: {out}")

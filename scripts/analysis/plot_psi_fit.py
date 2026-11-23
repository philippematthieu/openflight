# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "matplotlib"]
# ///
"""Didactic plot: measured v_r(t) vs model v_hat_r(t; psi_hat) for several psi_hat."""
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from openflight.launch_angle import _simulate_vr
from openflight.ballistics import MPH_TO_MPS

TRUE_PSI = 15.0
BALL_MPH = 94.9
OMEGA = 2500 * 2 * math.pi / 60

t_ms = np.arange(68.0, 136.0, 1.07)
t_s = (t_ms - t_ms[0]) / 1000.0
v0 = BALL_MPH * MPH_TO_MPS / math.cos(math.radians(TRUE_PSI))
vr_true = np.array(_simulate_vr(v0, TRUE_PSI, OMEGA, list(t_s)))
meas_mph = vr_true / MPH_TO_MPS

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(t_ms, meas_mph, "k-", linewidth=2.5, label="measured $v_r(t)$ (true $\\psi$ = 15°)")

for psi in [5, 10, 15, 20, 25]:
    v0c = BALL_MPH * MPH_TO_MPS / math.cos(math.radians(psi))
    vr = np.array(_simulate_vr(v0c, psi, OMEGA, list(t_s)))
    vr_mph = vr / MPH_TO_MPS
    num = np.sum(vr * vr_true)
    den = np.sum(vr * vr)
    c = num / den
    sse = np.sum((vr_true - c * vr) ** 2)
    style = dict(linewidth=2.2) if psi == TRUE_PSI else dict(linewidth=1.2, alpha=0.7)
    lbl = f"$\\widehat{{v_r}}(t; \\widehat{{\\psi}}={psi:.0f}°)$" + ("  ← best fit (SSE min)" if psi == TRUE_PSI else f"  (SSE={sse:.2f})")
    ax.plot(t_ms, c * vr_mph, "--", label=lbl, **style)

ax.set_xlabel("t (ms)")
ax.set_ylabel("radial speed (mph)")
ax.set_title("ψ̂ fit: model curves $\\widehat{v_r}(t;\\widehat{\\psi})$ vs measured $v_r(t)$")
ax.legend(fontsize=9)
ax.grid(True)
fig.tight_layout()
out = "/Users/matthieuphilippe/Library/Mobile Documents/iCloud~md~obsidian/Documents/Tests/SimulateurGolf/images/psi_fit_didactic.png"
fig.savefig(out, dpi=150)
print(f"Saved: {out}")

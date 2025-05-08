#!/usr/bin/env python3
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ── CONFIG ─────────────────────────────────────────────────────────────────────
DATA_DIR = "/home/kevin/catkin_ws/data"
FILENAMES = {
    "Full task-space": "Full_task.csv",
    "DS-based": "Task_spcaed.csv",
    "Passive": "passive.csv"
}
K_GAIN = 400  # stiffness per axis
D_GAIN = 10   # damping per axis
MAX_TIME = 20  # seconds to plot
CLIP_MAX = 1200  # max V(t) value to allow
SMOOTH_WINDOW = 10  # rolling mean window

# ── COMPUTE V(t) FROM TRAJECTORY ───────────────────────────────────────────────
def compute_lyapunov_energy(df):
    df.columns = df.columns.str.strip().str.lower()

    required = ['x','y','z','x_d','y_d','z_d','vx','vy','vz','time']
    if not all(col in df for col in required):
        raise ValueError("Missing required columns")

    pos = df[['x','y','z']].to_numpy()
    pos_d = df[['x_d','y_d','z_d']].to_numpy()
    vel = df[['vx','vy','vz']].to_numpy()

    pos_err = pos - pos_d
    vel_err = vel

    V_pos = 0.5 * K_GAIN * np.sum(pos_err**2, axis=1)
    V_vel = 0.5 * D_GAIN * np.sum(vel_err**2, axis=1)
    V = V_pos + V_vel

    # Time normalization
    t = df['time'].to_numpy()
    t = t - t[0]

    # Clip large spikes
    V = np.clip(V, None, CLIP_MAX)

    # Smooth
    V = pd.Series(V).rolling(window=SMOOTH_WINDOW, min_periods=1).mean().to_numpy()

    # Strict mask: time window & valid values & remove last 1s
    mask = (t >= 0.1) & (t <= 14.5) & np.isfinite(V)
    return t[mask], V[mask]

# ── PLOTTING ───────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5))
for label, fname in FILENAMES.items():
    path = os.path.join(DATA_DIR, fname)
    try:
        df = pd.read_csv(path)
        t, V = compute_lyapunov_energy(df)
        ax.plot(t, V, label=label)
        print(f"[OK] Processed {label} | Final V values: {V[-3:].round(2)}")
    except Exception as e:
        print(f"[WARN] Skipped {label}: {e}")

ax.set_title("Lyapunov-like Energy Over Time (Uncertain)", fontsize=14)
ax.set_xlabel("Time (s)", fontsize=12)
ax.set_ylabel("V(t) [Joules, unscaled]", fontsize=12)
ax.grid(True, linestyle="--", alpha=0.5)
ax.legend()
plt.tight_layout()
plt.savefig("stability_lyapunov_plot.png", dpi=300)
print("Saved stability_lyapunov_plot.png")


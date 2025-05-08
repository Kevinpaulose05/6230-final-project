#!/usr/bin/env python3
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ── CONFIG ────────────────────────────────────────────────────────────────────
DATA_DIR    = "/home/kevin/catkin_ws/data"
SUMMARY_CSV = os.path.join(DATA_DIR, "comparison_summary.csv")
COLORS      = ["#1b9e77", "#d95f02"]   # colorblind‐friendly palette

# ── LOAD SUMMARY ───────────────────────────────────────────────────────────────
df = pd.read_csv(SUMMARY_CSV)

# ── DATA PREP ─────────────────────────────────────────────────────────────────
controllers = df['controller'].unique().tolist()
envs        = ['Certain','Uncertain']

# Build lookup dicts
metric_dicts = {
    'rmse_error':             {(r.controller, r.environment): r.rmse_error for _,r in df.iterrows()},
    'peak_error':             {(r.controller, r.environment): r.peak_error for _,r in df.iterrows()},
    'final_cumulative_energy':{(r.controller, r.environment): r.final_cumulative_energy for _,r in df.iterrows()},
    'peak_force_mag':         {(r.controller, r.environment): r.peak_force_mag for _,r in df.iterrows()},
}
settling_s = df[df.environment=='Uncertain'].set_index('controller')['settling_time_s']

# ── PLOTTING HELPERS ───────────────────────────────────────────────────────────
def annotate_bars(ax, bars):
    """Place a label on top of each bar."""
    y_min, y_max = ax.get_ylim()
    offset = (y_max - y_min) * 0.02
    for bar in bars:
        h = bar.get_height()
        if np.isnan(h):
            continue
        ax.text(
            bar.get_x() + bar.get_width()/2,
            h + offset,
            f"{h:.2f}",
            ha='center', va='bottom', fontsize=10
        )

def grouped_bar(ax, data, ylabel, ylim=None):
    n, m = len(controllers), len(envs)
    width = 0.8 / m
    x = np.arange(n)
    for i, env in enumerate(envs):
        vals = [ data.get((c,env), np.nan) for c in controllers ]
        bars = ax.bar(x + i*width, vals, width, label=env, color=COLORS[i])
        annotate_bars(ax, bars)
    ax.set_xticks(x + width*(m-1)/2)
    ax.set_xticklabels(controllers, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=14)
    if ylim:
        ax.set_ylim(ylim)
    ax.yaxis.grid(True, linestyle='--', linewidth=0.5, alpha=0.7)
    ax.legend(title="Environment", bbox_to_anchor=(1.02,1), loc='upper left')
    ax.tick_params(axis='y', labelsize=12)

# ── 1) ERROR COMPARISON ─────────────────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1,2, figsize=(12,5))
grouped_bar(ax1, metric_dicts['rmse_error'], "RMSE Error")
ax1.set_title("RMSE Error", fontsize=16)
grouped_bar(ax2, metric_dicts['peak_error'], "Peak Error")
ax2.set_title("Peak Error", fontsize=16)
fig.tight_layout(pad=3)
fig.savefig("error_comparison.png", dpi=300)
print("Saved error_comparison.png")

# ── 2) ENERGY DISSIPATION ───────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6,5))
energies = list(metric_dicts['final_cumulative_energy'].values())
ylim_e = (min(energies)-0.2, max(energies)+0.2)
grouped_bar(ax, metric_dicts['final_cumulative_energy'], "Cumulative Energy", ylim=ylim_e)
ax.set_title("Final Cumulative Energy", fontsize=16)
fig.tight_layout(pad=3)
fig.savefig("energy_comparison.png", dpi=300)
print("Saved energy_comparison.png")

# ── 3) PEAK FORCE ──────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6,5))
forces = list(metric_dicts['peak_force_mag'].values())
ylim_f = (0, max(forces)*1.1)
grouped_bar(ax, metric_dicts['peak_force_mag'], "Force (N)", ylim=ylim_f)
ax.set_title("Peak External Force", fontsize=16)
fig.tight_layout(pad=3)
fig.savefig("force_comparison.png", dpi=300)
print("Saved force_comparison.png")

# ── 4) SETTLING TIME ────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6,5))
bars = ax.bar(settling_s.index, settling_s.values, color=COLORS[1], width=0.5)
annotate_bars(ax, bars)
ax.set_title("Settling Time After Collision\n(Uncertain)", fontsize=16)
ax.set_ylabel("Time (s)", fontsize=14)
ax.set_xlabel("Controller", fontsize=14)
ax.yaxis.grid(True, linestyle='--', linewidth=0.5, alpha=0.7)
# annotate 'N/A'
y_min, y_max = ax.get_ylim()
offset = (y_max - y_min) * 0.02
for i, ctrl in enumerate(controllers):
    if ctrl not in settling_s.index:
        ax.text(i, offset, "N/A", ha='center', va='bottom', fontsize=12, color='gray')
fig.tight_layout(pad=3)
fig.savefig("settling_time_comparison.png", dpi=300)
print("Saved settling_time_comparison.png")

plt.show()


#!/usr/bin/env python3
import os
import glob
import sys
import numpy as np
import pandas as pd

# === CONFIG ===
DATA_DIR    = "/home/kevin/catkin_ws/data"
OUTPUT_CSV  = os.path.join(DATA_DIR, "comparison_summary.csv")
SKIP_FILES  = { os.path.basename(OUTPUT_CSV) }  # ignore the summary itself

# collision & settling‐time params
COLLISION_THRESHOLD_MULTIPLIER = 5.0
SETTLING_BAND                  = 0.05

# === HELPERS ===
def classify_controller_and_env(fname):
    fn = fname.lower()
    if "full_task" in fn:
        ctrl = "Full task-space"
    elif "passive" in fn:
        ctrl = "Passive"
    elif "task_spcaed" in fn or "task_space" in fn:
        ctrl = "DS-based"
    else:
        ctrl = "Unknown"
    env = "Certain" if "nowall" in fn else "Uncertain"
    return ctrl, env

def safe_array(df, col):
    if col in df.columns:
        arr = df[col].dropna().to_numpy()
        return arr.flatten() if arr.ndim > 1 else arr
    return np.array([])

def compute_metrics(df):
    m = {k: np.nan for k in (
        'rmse_error','peak_error',
        'final_cumulative_energy',
        'mean_power','peak_power',
        'peak_force_mag','settling_time_s'
    )}
    if df.empty:
        return m

    # 1) Tracking error
    err = safe_array(df, 'error')
    if err.size:
        m['rmse_error'] = np.sqrt(np.mean(err**2))
        m['peak_error'] = np.max(np.abs(err))

    # 2) Energy / power
    ce = safe_array(df, 'cumulative_energy')
    if ce.size:
        m['final_cumulative_energy'] = ce[-1]
    p = safe_array(df, 'power')
    if p.size:
        m['mean_power'] = np.mean(p)
        m['peak_power'] = np.max(p)

    # 3) Peak force & settling time
    fx, fy, fz = safe_array(df,'fx'), safe_array(df,'fy'), safe_array(df,'fz')
    if fx.size and fy.size and fz.size:
        fmag = np.sqrt(fx**2 + fy**2 + fz**2)
        m['peak_force_mag'] = np.max(fmag)

        # detect collision & compute settling
        baseline_n = max(1, int(0.1 * len(fmag)))
        std0       = np.std(fmag[:baseline_n])
        thr        = COLLISION_THRESHOLD_MULTIPLIER * std0
        coll_idxs  = np.where(fmag > thr)[0]
        if coll_idxs.size and err.size:
            cidx = coll_idxs[0]
            band = SETTLING_BAND * (m['peak_error'] if not np.isnan(m['peak_error']) else 0)
            post_ok = np.abs(err[cidx:]) <= band
            if np.any(post_ok):
                sidx = cidx + np.argmax(post_ok)
                t = safe_array(df, 'time')
                if t.size >= 2:
                    dt = t[1] - t[0]
                    m['settling_time_s'] = (sidx - cidx) * dt

    return m

# === MAIN ===
def main():
    # collect only raw runs (skip the summary CSV)
    all_csvs = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    raw_runs = [f for f in all_csvs if os.path.basename(f) not in SKIP_FILES]

    if not raw_runs:
        print(f"[ERROR] No raw CSV files found in {DATA_DIR}", file=sys.stderr)
        sys.exit(1)

    results = []
    for path in raw_runs:
        name = os.path.basename(path)
        try:
            df = pd.read_csv(path)
        except Exception as e:
            print(f"[WARN] Skipping '{name}' (read error: {e})", file=sys.stderr)
            continue

        ctrl, env  = classify_controller_and_env(name)
        metrics     = compute_metrics(df)
        metrics.update({
            'run':         name,
            'controller':  ctrl,
            'environment': env
        })
        results.append(metrics)

    # build and save summary back into DATA_DIR
    cols = [
        'run','controller','environment',
        'rmse_error','peak_error',
        'final_cumulative_energy',
        'mean_power','peak_power',
        'peak_force_mag','settling_time_s'
    ]
    summary = pd.DataFrame(results, columns=cols)
    summary.to_csv(OUTPUT_CSV, index=False)

    print("\n=== Comparison Summary ===")
    print(summary.to_string(index=False))
    print(f"\nSaved summary to '{OUTPUT_CSV}'")

if __name__ == "__main__":
    main()


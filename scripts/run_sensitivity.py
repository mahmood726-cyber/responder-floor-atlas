"""Stage 6 — normality sensitivity audit on real data.

For each OK trial (status=OK in reconstructions.parquet), simulate p̂ under
log-normal shifted, beta_bounded, and truncated_normal distributions with
moment-matched parameters (same mean, same SD as the trial's reported arm).
Compare to the analytic Normal p̂ to bound the skew-induced reconstruction
error per arm. Aggregate per-instrument and report the worst-case |Δ p̂|
under each distribution as a sensitivity bound.

Output: outputs/sensitivity_summary.parquet (per-instrument, per-distribution
percentile bounds on |Δ p̂|).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from responder_floor.instruments import load_instruments
from responder_floor.sensitivity import reconstruction_under_dist


DISTS = ["lognormal_shifted", "beta_bounded", "truncated_normal"]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--reconstructions", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--n-draws", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=20260425)
    a = p.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(a.reconstructions)
    ok = df[df["status"] == "OK"].copy()
    instruments = {i.id: i for i in load_instruments()}
    base_rng = np.random.default_rng(seed=a.seed)  # noqa: F841 — seed anchor for reproducibility

    rows_out: list[dict] = []

    # For each OK trial × each arm × each candidate distribution, MC-simulate p̂
    # and record the absolute deviation from the analytic Normal p̂.
    for idx, row in ok.iterrows():
        instr = instruments.get(row["instrument_id"])
        if instr is None:
            continue
        d = instr.direction
        scale_min = instr.scale_min
        scale_max = instr.scale_max
        mid = float(row["model1_mid"])
        for arm in ("t", "c"):
            mean = row[f"mean_{arm}"]
            sd = row[f"sd_{arm}"]
            if pd.isna(mean) or pd.isna(sd) or sd <= 0:
                continue
            p_normal = float(row[f"p_hat_{arm}"])  # already computed in reconstructions
            # Re-derive a per-call rng so results are deterministic given seed + (idx, arm)
            arm_seed = a.seed + idx * 2 + (0 if arm == "t" else 1)
            for dist in DISTS:
                rng = np.random.default_rng(seed=arm_seed)
                try:
                    if dist == "lognormal_shifted":
                        p_alt = reconstruction_under_dist(
                            dist=dist, mean=float(mean), sd=float(sd),
                            mid=mid, direction=d, n_draws=a.n_draws, rng=rng,
                        )
                    else:
                        p_alt = reconstruction_under_dist(
                            dist=dist, mean=float(mean), sd=float(sd),
                            mid=mid, direction=d, n_draws=a.n_draws, rng=rng,
                            scale_min=float(scale_min), scale_max=float(scale_max),
                        )
                except Exception as e:
                    rows_out.append({
                        "review_id": row["review_id"], "trial_id": row["trial_id"],
                        "instrument_id": row["instrument_id"], "arm": arm,
                        "dist": dist, "p_normal": p_normal, "p_alt": float("nan"),
                        "delta_p": float("nan"), "error": str(e),
                    })
                    continue
                rows_out.append({
                    "review_id": row["review_id"], "trial_id": row["trial_id"],
                    "instrument_id": row["instrument_id"], "arm": arm,
                    "dist": dist, "p_normal": p_normal, "p_alt": p_alt,
                    "delta_p": abs(p_alt - p_normal), "error": None,
                })

    raw = pd.DataFrame(rows_out)
    raw_path = a.output_dir / "sensitivity_per_arm.parquet"
    raw.to_parquet(raw_path, index=False)

    # Aggregate per (instrument, dist): median, 95th percentile of |Δ p̂|
    agg = raw[raw["error"].isna()].groupby(["instrument_id", "dist"]).agg(
        n_arms=("delta_p", "count"),
        median_delta_p=("delta_p", "median"),
        p95_delta_p=("delta_p", lambda s: float(np.quantile(s, 0.95))),
        max_delta_p=("delta_p", "max"),
    ).reset_index()
    agg_path = a.output_dir / "sensitivity_summary.parquet"
    agg.to_parquet(agg_path, index=False)

    import io
    stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    stdout.write(f"Per-arm sensitivity rows: {len(raw)} ({raw['error'].isna().sum()} successful)\n")
    stdout.write(f"Per-(instrument, dist) summary: {len(agg)} rows\n")
    stdout.write("\n")
    stdout.write("Sensitivity summary (median |delta_p|, 95th percentile |delta_p|, max |delta_p|):\n")
    stdout.write(agg.to_string(index=False) + "\n")
    stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())

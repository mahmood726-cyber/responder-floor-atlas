"""Clustered bootstrap for per-instrument empirical-MID confidence intervals.

Cluster on review_id (matches spec §3.1 cluster definition). Within each
bootstrap resample, recompute the per-instrument median δ̂_trial and its
ratio to the canonical MID. Report point + 95% percentile CI.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from responder_floor.instruments import load_instruments


def bootstrap_mid_ratios(
    df_reconstructions: pd.DataFrame,
    n_boot: int = 2000,
    rng: np.random.Generator | None = None,
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Return per-instrument bootstrap CIs.

    Input: outputs/reconstructions.parquet rows (or filtered subset of OK rows).
    Output schema: instrument_id, n_trials, n_reviews, empirical_mid, canonical_mid,
                   ratio, ratio_ci_lower, ratio_ci_upper, n_boot.
    """
    rng = rng or np.random.default_rng(seed=20260425)
    instruments = {i.id: i for i in load_instruments()}
    ok = df_reconstructions[df_reconstructions["status"] == "OK"].copy()
    if "delta_hat_trial" not in ok.columns:
        raise ValueError("reconstructions.parquet missing delta_hat_trial column")

    rows_out = []
    for instr_id, g in ok.groupby("instrument_id"):
        if instr_id not in instruments:
            continue
        canonical = instruments[instr_id].canonical_mid
        # Cluster bootstrap: clusters = unique review_ids in this instrument's group
        clusters = g["review_id"].unique()
        n_c = len(clusters)
        if n_c < 1:
            continue
        boot_medians = np.empty(n_boot)
        for b in range(n_boot):
            sample_clusters = rng.choice(clusters, size=n_c, replace=True)
            # Re-aggregate: sum the rows where review is in sample (with multiplicity)
            sample_rows = pd.concat([g[g["review_id"] == c] for c in sample_clusters], ignore_index=True)
            if len(sample_rows) == 0:
                boot_medians[b] = np.nan
            else:
                boot_medians[b] = sample_rows["delta_hat_trial"].median()
        boot_medians = boot_medians[np.isfinite(boot_medians)]
        if len(boot_medians) < n_boot // 2:
            # Too many degenerate samples; fail-closed
            rows_out.append({
                "instrument_id": instr_id, "n_trials": len(g), "n_reviews": n_c,
                "empirical_mid": float(g["delta_hat_trial"].median()),
                "canonical_mid": canonical,
                "ratio": float(g["delta_hat_trial"].median()) / canonical if canonical else float("nan"),
                "ratio_ci_lower": float("nan"), "ratio_ci_upper": float("nan"),
                "n_boot": len(boot_medians),
                "status": "BOOTSTRAP_DEGENERATE",
            })
            continue
        emp_mid = float(g["delta_hat_trial"].median())
        ratio_point = emp_mid / canonical
        ratio_lo = float(np.quantile(boot_medians, alpha / 2)) / canonical
        ratio_hi = float(np.quantile(boot_medians, 1 - alpha / 2)) / canonical
        rows_out.append({
            "instrument_id": instr_id, "n_trials": len(g), "n_reviews": n_c,
            "empirical_mid": emp_mid, "canonical_mid": canonical,
            "ratio": ratio_point,
            "ratio_ci_lower": ratio_lo, "ratio_ci_upper": ratio_hi,
            "n_boot": len(boot_medians), "status": "OK",
        })
    return pd.DataFrame(rows_out)

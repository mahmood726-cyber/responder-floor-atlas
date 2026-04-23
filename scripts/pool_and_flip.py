"""Stage 4 — per-review pool under both framings, detect flip at α=0.05 and magnitude >0.1."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from responder_floor.pooling import pool_reml_hksj_pi


def _smd_from_arm(row) -> tuple[float, float]:
    """Hedges' g SMD and its variance from continuous arm stats."""
    n_t, n_c = int(row["n_t"]), int(row["n_c"])
    m_t, m_c = float(row["mean_t"]), float(row["mean_c"])
    s_t, s_c = float(row["sd_t"]), float(row["sd_c"])
    s_pool = math.sqrt(((n_t - 1) * s_t ** 2 + (n_c - 1) * s_c ** 2) / (n_t + n_c - 2))
    d = (m_t - m_c) / s_pool
    # Hedges' small-sample correction
    j = 1 - 3 / (4 * (n_t + n_c) - 9)
    g = j * d
    v = (n_t + n_c) / (n_t * n_c) + g ** 2 / (2 * (n_t + n_c))
    return g, v


def _log_rr_obs_from_arm(row) -> tuple[float, float]:
    """log RR and its variance from dichotomous arm counts, with 0.5 correction iff any zero cell."""
    a = float(row["events_t"]); b = float(row["n_t_dich"]) - a
    c = float(row["events_c"]); d = float(row["n_c_dich"]) - c
    if 0 in (a, b, c, d):
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    rr = (a / (a + b)) / (c / (c + d))
    log_rr = math.log(rr)
    var = 1 / a - 1 / (a + b) + 1 / c - 1 / (c + d)
    return log_rr, var


def _pool_review(
    review_id: str,
    trials: pd.DataFrame,
    alpha: float = 0.05,
    mag_thresh: float = 0.1,
) -> dict:
    smd_effects = np.array([_smd_from_arm(r)[0] for _, r in trials.iterrows()])
    smd_vars = np.array([_smd_from_arm(r)[1] for _, r in trials.iterrows()])
    rr_effects = np.array([_log_rr_obs_from_arm(r)[0] for _, r in trials.iterrows()])
    rr_vars = np.array([_log_rr_obs_from_arm(r)[1] for _, r in trials.iterrows()])

    smd = pool_reml_hksj_pi(smd_effects, smd_vars)
    rr = pool_reml_hksj_pi(rr_effects, rr_vars)
    smd_sig = smd.p_value < alpha
    rr_sig = rr.p_value < alpha

    # Magnitude flip: compare absolute pooled effects after scaling SMD to logRR-comparable units
    # via OR→SMD constant (sqrt(3)/pi ≈ 0.5513, per advanced-stats.md).
    # Note: this is approximate; the conversion formally applies to logOR↔SMD, but we use it here
    # as a directional magnitude check between the two framings.
    smd_scaled_as_logrr = smd.estimate / 0.5513
    magnitude_flip = bool(abs(rr.estimate - smd_scaled_as_logrr) > mag_thresh)

    return {
        "review_id": review_id,
        "k": len(trials),
        "smd_estimate": float(smd.estimate),
        "smd_p": float(smd.p_value),
        "smd_significant": bool(smd_sig),
        "smd_tau2": float(smd.tau2),
        "smd_hksj_factor": float(smd.hksj_factor),
        "rr_estimate": float(rr.estimate),
        "rr_p": float(rr.p_value),
        "rr_significant": bool(rr_sig),
        "rr_tau2": float(rr.tau2),
        "rr_hksj_factor": float(rr.hksj_factor),
        "framing_flip": bool(smd_sig != rr_sig),
        "magnitude_flip": magnitude_flip,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconstructions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--magnitude-threshold", type=float, default=0.1)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.reconstructions)
    ok = df[df["status"] == "OK"]
    results = []
    for review_id, trials in ok.groupby("review_id"):
        if len(trials) < 3:
            continue
        try:
            results.append(_pool_review(review_id, trials, args.alpha, args.magnitude_threshold))
        except ValueError as e:
            # Fail-closed: record the review as unpooled with reason.
            results.append({
                "review_id": review_id,
                "k": len(trials),
                "framing_flip": None,
                "magnitude_flip": None,
                "pooling_error": str(e),
            })

    out_df = pd.DataFrame(results)
    out = args.output_dir / "flip_results.parquet"
    out_df.to_parquet(out, index=False)
    flip_count = int(out_df["framing_flip"].fillna(False).sum()) if len(out_df) else 0
    print(f"Pooled {len(out_df)} reviews; flip count = {flip_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

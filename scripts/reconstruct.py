"""Stage 3 — reconstruct per-trial responder probability and compute reconstruction error."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import pandas as pd

from responder_floor.math import p_hat_arm, log_rr_hat, log_rr_hat_se_delta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mid-inferences", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.mid_inferences)

    def recon(row):
        d = int(row["direction"])
        mid = row["model1_mid"]
        p_hat_t = p_hat_arm(row["mean_t"], row["sd_t"], mid, d)
        p_hat_c = p_hat_arm(row["mean_c"], row["sd_c"], mid, d)
        p_obs_t = row["events_t"] / row["n_t_dich"]
        p_obs_c = row["events_c"] / row["n_c_dich"]
        log_rr_h = log_rr_hat(row["mean_t"], row["sd_t"], row["n_t"],
                              row["mean_c"], row["sd_c"], row["n_c"], mid, d)
        se_hat = log_rr_hat_se_delta(row["mean_t"], row["sd_t"], row["n_t"],
                                     row["mean_c"], row["sd_c"], row["n_c"], mid, d)
        log_rr_o = math.log(p_obs_t / p_obs_c) if p_obs_t > 0 and p_obs_c > 0 else float("nan")
        return pd.Series({
            "p_hat_t": p_hat_t, "p_hat_c": p_hat_c,
            "p_obs_t": p_obs_t, "p_obs_c": p_obs_c,
            "epsilon_t": abs(p_hat_t - p_obs_t),
            "epsilon_c": abs(p_hat_c - p_obs_c),
            "log_rr_hat": log_rr_h, "se_log_rr_hat": se_hat,
            "log_rr_obs": log_rr_o,
            "epsilon_log_rr": abs(log_rr_h - log_rr_o) if math.isfinite(log_rr_o) else float("nan"),
        })

    recon_df = df.apply(recon, axis=1)
    out_df = pd.concat([df.reset_index(drop=True), recon_df.reset_index(drop=True)], axis=1)
    out = args.output_dir / "reconstructions.parquet"
    out_df.to_parquet(out, index=False)
    print(f"Wrote {len(out_df)} rows to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

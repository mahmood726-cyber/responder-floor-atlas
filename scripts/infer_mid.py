"""Stage 2 — compute Model 1 (review-level MID) and Model 2 (trial-level implied MID)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from responder_floor.instruments import load_instruments
from responder_floor.math import delta_hat_arm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.index)
    ok = df[df["status"] == "OK"].copy()
    instruments = {i.id: i for i in load_instruments()}

    def direction(row):
        return instruments[row["instrument_id"]].direction

    def canonical_mid(row):
        return instruments[row["instrument_id"]].canonical_mid

    ok["direction"] = ok.apply(direction, axis=1)
    # Model 1: use canonical MID (review-stated MID parsing deferred).
    ok["model1_mid"] = ok.apply(canonical_mid, axis=1)
    ok["model1_source"] = "canonical_v1_panel"

    # Model 2: back out δ per arm, average for trial-level.
    def back_out_arm(mean, sd, events, n, d):
        p = events / n
        return delta_hat_arm(mean=mean, sd=sd, p_obs=p, direction=d)

    ok["delta_hat_t"] = ok.apply(
        lambda r: back_out_arm(r["mean_t"], r["sd_t"], r["events_t"], r["n_t_dich"], r["direction"]), axis=1)
    ok["delta_hat_c"] = ok.apply(
        lambda r: back_out_arm(r["mean_c"], r["sd_c"], r["events_c"], r["n_c_dich"], r["direction"]), axis=1)
    ok["delta_hat_trial"] = (ok["delta_hat_t"] + ok["delta_hat_c"]) / 2.0

    out = args.output_dir / "mid_inferences.parquet"
    ok.to_parquet(out, index=False)
    print(f"Wrote {len(ok)} rows to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

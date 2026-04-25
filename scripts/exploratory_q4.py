"""Q4 exploratory analysis: trials appearing in ≥2 reviews of the same instrument.

Per spec §3.4 / Gate D: find studies that contribute to multiple Cochrane reviews
of the same instrument, and check whether δ̂ is consistent across those reviews.
Reports the count + per-overlap consistency (max - min δ̂_trial across reviews).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--reconstructions", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(a.reconstructions)
    ok = df[df["status"] == "OK"].copy()

    # Trial identity is the trial_id field (composite already).
    # But the same Study may appear under different composite IDs across reviews,
    # so use the bare Study substring before "|" as the cross-review identifier.
    ok["bare_study"] = ok["trial_id"].astype(str).str.split("|", n=1).str[0]

    # Group by (instrument, bare_study) and count distinct review_ids.
    overlap = ok.groupby(["instrument_id", "bare_study"]).agg(
        n_reviews=("review_id", "nunique"),
        delta_hats=("delta_hat_trial", list),
        review_ids=("review_id", lambda s: sorted(s.unique().tolist())),
    ).reset_index()

    multi = overlap[overlap["n_reviews"] >= 2].copy()
    if len(multi):
        multi["delta_min"] = multi["delta_hats"].apply(lambda lst: min(lst))
        multi["delta_max"] = multi["delta_hats"].apply(lambda lst: max(lst))
        multi["delta_range"] = multi["delta_max"] - multi["delta_min"]

    summary = {
        "total_unique_trials": int(ok.groupby(["instrument_id", "bare_study"]).ngroups),
        "trials_in_multiple_reviews": int(len(multi)),
        "trials_in_single_review": int(len(overlap) - len(multi)),
        "max_review_overlap": int(overlap["n_reviews"].max() if len(overlap) else 0),
    }

    out_md = a.output_dir / "q4_overlap.md"
    lines = ["# Q4 — Cross-review trial overlap (exploratory)", "", json.dumps(summary, indent=2), ""]
    if len(multi):
        lines.append("## Trials in ≥2 reviews")
        lines.append("")
        for _, r in multi.iterrows():
            lines.append(f"- `{r['instrument_id']}` / `{r['bare_study']}`: in {r['n_reviews']} reviews "
                         f"({r['review_ids']}); δ̂ range = {r['delta_range']:.3f} "
                         f"({r['delta_min']:.3f} to {r['delta_max']:.3f})")
    else:
        lines.append("**No trials found in ≥2 reviews under the v1.1 instrument panel.**")
        lines.append("")
        lines.append("This is itself a finding: the dual-framing slice of Pairwise70 is not just thin, "
                     "but compositionally non-overlapping — every analyzable trial is unique to its review. "
                     "Cross-review consistency of implied MIDs cannot be assessed on this corpus.")
    out_md.write_text("\n".join(lines), encoding="utf-8")

    out_json = a.output_dir / "q4_overlap.json"
    out_json.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

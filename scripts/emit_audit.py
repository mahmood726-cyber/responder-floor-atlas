"""Emit outputs/analysis_audit.md + outputs/paper_numbers.json for paper / dashboard consumption."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dual-framing-index", type=Path, required=True)
    parser.add_argument("--flips", type=Path, required=True)
    parser.add_argument("--reconstructions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    idx = pd.read_parquet(args.dual_framing_index)
    flips = pd.read_parquet(args.flips)
    recon = pd.read_parquet(args.reconstructions)

    # paper_numbers.json — single source of truth for paper claims.
    numbers = {
        "total_rows_scanned": int(len(idx)),
        "rows_ok": int((idx["status"] == "OK").sum()),
        "reviews_pooled": int(len(flips)),
        "q1_flip_rate": float(flips["framing_flip"].mean()) if len(flips) else None,
        "q1_magnitude_flip_rate": float(flips["magnitude_flip"].mean()) if len(flips) else None,
        "q2_median_epsilon": float(
            pd.concat([recon["epsilon_t"].dropna(), recon["epsilon_c"].dropna()]).median()
        ) if len(recon) else None,
        "q3_per_instrument_median_delta_hat": recon.groupby("instrument_id")["delta_hat_trial"]
            .median().dropna().to_dict() if len(recon) else {},
    }
    (args.output_dir / "paper_numbers.json").write_text(json.dumps(numbers, indent=2))

    # analysis_audit.md — DossierGap-pattern honest enumeration.
    lines = ["# Analysis audit", "",
             "Every limit and exclusion, enumerated.", "",
             "## Row-status counts (Stage 1)", ""]
    for status, n in idx["status"].value_counts().items():
        lines.append(f"- **{status}**: {n}")
    lines += ["", "## Per-instrument coverage (OK rows)", ""]
    if "instrument_id" in idx.columns:
        for instr, n in idx[idx["status"] == "OK"].groupby("instrument_id").size().items():
            lines.append(f"- {instr}: {n}")
    lines += ["", "## Reviews with framing flip (Q1)", ""]
    if len(flips):
        flipped = flips[flips["framing_flip"].fillna(False).astype(bool)]
        if len(flipped):
            for _, r in flipped.iterrows():
                lines.append(
                    f"- {r['review_id']}: SMD p={r['smd_p']:.3f} "
                    f"({'sig' if r['smd_significant'] else 'ns'}) vs "
                    f"RR p={r['rr_p']:.3f} ({'sig' if r['rr_significant'] else 'ns'})"
                )
        else:
            lines.append("- (no framing flips detected)")
    else:
        lines.append("- (no reviews pooled)")
    (args.output_dir / "analysis_audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.output_dir / 'paper_numbers.json'} and {args.output_dir / 'analysis_audit.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

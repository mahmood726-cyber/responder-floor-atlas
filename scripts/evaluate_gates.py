"""Evaluate feasibility gates A/B/C/D per spec §6.3 and emit FEASIBILITY_REPORT.md."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from responder_floor.instruments import load_instruments


def load_gate_thresholds() -> dict:
    cfg = yaml.safe_load(Path("configs/pipeline.yml").read_text(encoding="utf-8"))
    return cfg["gates"]


def evaluate(df: pd.DataFrame, thresholds: dict) -> dict:
    ok = df[df["status"] == "OK"]

    # Gate A: reviews with ≥3 trials OK across both arms
    per_review = ok.groupby("review_id").size()
    a_reviews = per_review[per_review >= thresholds["A_trials_per_review_min"]].index
    a_count = len(a_reviews)
    gate_a = {
        "threshold_reviews_min": thresholds["A_arm_level_reviews_min"],
        "threshold_trials_per_review_min": thresholds["A_trials_per_review_min"],
        "count": a_count,
        "passed": a_count >= thresholds["A_arm_level_reviews_min"],
    }

    # Gate B: instruments with ≥5 qualifying reviews
    instr_reviews = ok[ok["review_id"].isin(a_reviews)].groupby("instrument_id")["review_id"].nunique()
    b_eligible = instr_reviews[instr_reviews >= thresholds["B_reviews_per_instrument_min"]]
    gate_b = {
        "threshold_instruments_min": thresholds["B_instruments_min"],
        "eligible_instruments": list(b_eligible.index),
        "counts": b_eligible.to_dict(),
        "passed": len(b_eligible) >= thresholds["B_instruments_min"],
    }

    # Gate C: fraction of dual-framing reviews with MID available (canonical from v1 panel)
    instr_ids = {i.id for i in load_instruments()}
    reviews_with_mid = ok[ok["instrument_id"].isin(instr_ids)]["review_id"].nunique()
    total_dual = df["review_id"].nunique()
    mid_pct = reviews_with_mid / total_dual if total_dual > 0 else 0.0
    gate_c = {
        "threshold_pct_min": thresholds["C_mid_availability_pct_min"],
        "actual_pct": mid_pct,
        "passed": mid_pct >= thresholds["C_mid_availability_pct_min"],
    }

    # Gate D: cross-review trial overlap (exploratory Q4)
    trial_review = ok.groupby("trial_id")["review_id"].nunique()
    overlap = int((trial_review >= 2).sum())
    gate_d = {
        "threshold_min": thresholds["D_cross_review_trial_overlap_min"],
        "count": overlap,
        "passed": overlap >= thresholds["D_cross_review_trial_overlap_min"],
    }

    return {"A": gate_a, "B": gate_b, "C": gate_c, "D": gate_d}


def render_report(gates: dict) -> str:
    lines = ["# Feasibility Report (Stage 1)", "",
             "Per spec §6.3. Gates A/B/C are hard stops; D is exploratory.", ""]
    for name, g in gates.items():
        mark = "PASS" if g["passed"] else "FAIL"
        lines.append(f"## Gate {name}: {mark}")
        lines.append("```json")
        lines.append(json.dumps(g, indent=2))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()

    df = pd.read_parquet(args.index)
    thresholds = load_gate_thresholds()
    gates = evaluate(df, thresholds)
    args.output.write_text(render_report(gates), encoding="utf-8")
    args.json.write_text(json.dumps(gates, indent=2))
    all_pass = all(gates[k]["passed"] for k in ("A", "B", "C"))
    print(f"Gates A/B/C: {'PASS' if all_pass else 'FAIL — pivot protocol applies (spec §6.4)'}")
    return 0 if all_pass else 2


if __name__ == "__main__":
    sys.exit(main())

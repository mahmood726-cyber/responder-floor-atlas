"""Stage 1 — scan Pairwise70 RDAs for dual-framing outcomes.

Emits outputs/dual_framing_index.parquet with per-trial rows for every review
pooling the same outcome in both continuous and dichotomous form.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from responder_floor.fuzzy_match import are_same_outcome
from responder_floor.instruments import load_instruments, match_instrument
from responder_floor.rda_loader import load_rda
from responder_floor.status import StatusCode, TrialArmInput, classify_arm

CONT_TYPES = {"MD", "SMD"}
DICH_TYPES = {"RR", "OR", "RD"}


def _group_dual_framing(outcomes: list[dict]) -> list[tuple[dict, dict]]:
    """Return pairs (continuous_ma, dichotomous_ma) for same outcome+comparison."""
    pairs = []
    cont = [o for o in outcomes if o["measure_type"] in CONT_TYPES]
    dich = [o for o in outcomes if o["measure_type"] in DICH_TYPES]
    for c in cont:
        for d in dich:
            if c.get("comparison") != d.get("comparison"):
                continue
            if are_same_outcome(c["label"], d["label"]):
                pairs.append((c, d))
    return pairs


def _trials_as_records(trials) -> list[dict]:
    """Normalize trials list into list-of-dicts.

    RDA loader may return trials as list-of-dicts (rpy2/jsonlite path) or
    as a pandas DataFrame (pyreadr path). Normalize to list-of-dicts.
    """
    if hasattr(trials, "to_dict"):
        return trials.to_dict(orient="records")
    return list(trials)


def _extract_trial_rows(
    review_id: str,
    cont: dict,
    dich: dict,
    instruments,
) -> list[dict]:
    instr = match_instrument(cont["label"], instruments)
    instrument_id = instr.id if instr else None
    cont_trials = _trials_as_records(cont["trials"])
    dich_trials = _trials_as_records(dich["trials"])
    cont_by_id = {t["trial_id"]: t for t in cont_trials}
    dich_by_id = {t["trial_id"]: t for t in dich_trials}
    shared_ids = set(cont_by_id) & set(dich_by_id)
    rows = []
    for tid in sorted(shared_ids):
        ct = cont_by_id[tid]
        dt = dich_by_id[tid]
        row = {
            "review_id": review_id,
            "outcome_group": cont["label"],
            "trial_id": tid,
            "mean_t": ct.get("mean_t"), "sd_t": ct.get("sd_t"), "n_t": ct.get("n_t"),
            "mean_c": ct.get("mean_c"), "sd_c": ct.get("sd_c"), "n_c": ct.get("n_c"),
            "events_t": dt.get("events_t"), "n_t_dich": dt.get("n_t"),
            "events_c": dt.get("events_c"), "n_c_dich": dt.get("n_c"),
            "instrument_id": instrument_id,
        }
        # Per-arm classify; trial status is worst-of both arms.
        t_status, t_reason = classify_arm(TrialArmInput(
            mean=row["mean_t"], sd=row["sd_t"], n=row["n_t"], events=row["events_t"],
        ))
        c_status, c_reason = classify_arm(TrialArmInput(
            mean=row["mean_c"], sd=row["sd_c"], n=row["n_c"], events=row["events_c"],
        ))
        status = t_status if t_status is not StatusCode.OK else c_status
        reason = t_reason if t_status is not StatusCode.OK else c_reason
        if instrument_id is None:
            status, reason = StatusCode.UNKNOWN_INSTRUMENT, f"no v1-panel match for label: {cont['label']}"
        row["status"] = status.value
        row["reason"] = reason
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True,
                        help="Directory of RDA files (Pairwise70 or fixture)")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    instruments = load_instruments()
    all_rows: list[dict] = []
    manifest: dict[str, Any] = {"reviews_scanned": 0, "dual_framing_reviews": 0, "errors": []}

    for rda_path in sorted(args.corpus.rglob("*.rda")):
        manifest["reviews_scanned"] += 1
        try:
            review = load_rda(rda_path)
        except Exception as e:
            manifest["errors"].append({"file": str(rda_path), "error": str(e)})
            continue
        outcomes = review.get("outcomes", [])
        # outcomes may itself be a list-of-dicts or a dict-of-index-keyed-dicts depending on loader
        if isinstance(outcomes, dict):
            # rpy2/jsonlite can yield {"0": {...}, "1": {...}} or similar
            outcomes = [outcomes[k] for k in sorted(outcomes.keys())]
        pairs = _group_dual_framing(outcomes)
        if pairs:
            manifest["dual_framing_reviews"] += 1
        for cont, dich in pairs:
            all_rows.extend(_extract_trial_rows(review["review_id"], cont, dich, instruments))

    df = pd.DataFrame(all_rows)
    out_parquet = args.output_dir / "dual_framing_index.parquet"
    df.to_parquet(out_parquet, index=False)
    (args.output_dir / "stage1_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {len(df)} rows to {out_parquet}")
    print(f"Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

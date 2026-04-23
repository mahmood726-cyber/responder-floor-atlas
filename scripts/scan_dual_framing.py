"""Stage 1 — scan Pairwise70 flat-frame RDAs for dual-framing outcomes.

Real Pairwise70 stores one data.frame per review with (Analysis.number, Subgroup.number)
identifying each MA. measure_type is inferred from which arm-level columns are populated.
"""
from __future__ import annotations

import argparse
import json
import sys
import math
from pathlib import Path
from typing import Any

import pandas as pd

from responder_floor.fuzzy_match import are_same_outcome
from responder_floor.instruments import load_instruments, match_instrument
from responder_floor.rda_loader import load_rda
from responder_floor.status import StatusCode, TrialArmInput, classify_arm


def _is_finite_number(x) -> bool:
    try:
        return pd.notna(x) and math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def _classify_ma(rows: pd.DataFrame) -> str:
    """Infer measure_type per MA: 'continuous', 'dichotomous', 'giv', or 'mixed'."""
    has_continuous = False
    has_dichotomous = False
    for _, r in rows.iterrows():
        mean_ok = _is_finite_number(r.get("Experimental.mean")) and _is_finite_number(r.get("Experimental.SD"))
        # Some reviews use 0/0 placeholders — treat zero SD as NOT continuous
        sd_meaningful = _is_finite_number(r.get("Experimental.SD")) and float(r.get("Experimental.SD")) > 0
        if mean_ok and sd_meaningful:
            has_continuous = True
        cases_ok = _is_finite_number(r.get("Experimental.cases")) and _is_finite_number(r.get("Experimental.N"))
        if cases_ok:
            has_dichotomous = True
    if has_continuous and has_dichotomous:
        return "mixed"
    if has_continuous:
        return "continuous"
    if has_dichotomous:
        return "dichotomous"
    return "giv"


def _ma_key(row: pd.Series) -> tuple:
    try:
        an = int(row.get("Analysis.number", -1))
    except (TypeError, ValueError):
        an = -1
    sn_raw = row.get("Subgroup.number", 1)
    try:
        sn = int(sn_raw) if pd.notna(sn_raw) else 1
    except (TypeError, ValueError):
        sn = 1
    return (an, sn)


def _ma_label(rows: pd.DataFrame) -> str:
    name = rows.iloc[0].get("Analysis.name", "")
    subgroup = rows.iloc[0].get("Subgroup", "")
    if subgroup and not pd.isna(subgroup) and str(subgroup).strip():
        return f"{name} — {subgroup}"
    return str(name)


def _review_id_from_path(path: Path) -> str:
    stem = path.stem
    # "CD000028_pub4_data" → "CD000028_pub4"
    if stem.endswith("_data"):
        stem = stem[:-5]
    return stem


def _extract_trial_rows(review_id: str, cont_rows: pd.DataFrame, dich_rows: pd.DataFrame,
                        outcome_label: str, instruments) -> list[dict]:
    instr = match_instrument(outcome_label, instruments)
    instrument_id = instr.id if instr else None

    # Index by Study (trial identifier); if a study appears multiple times, mark ID_AMBIGUOUS.
    def _index(rows):
        counts = rows["Study"].value_counts()
        unique = set(counts[counts == 1].index)
        idx = {r["Study"]: r for _, r in rows.iterrows() if r["Study"] in unique}
        ambiguous = set(counts[counts > 1].index)
        return idx, ambiguous

    cont_idx, cont_amb = _index(cont_rows)
    dich_idx, dich_amb = _index(dich_rows)
    shared = set(cont_idx) & set(dich_idx)
    amb = cont_amb | dich_amb

    def _int_or_none(x):
        try:
            return int(x) if pd.notna(x) else None
        except (TypeError, ValueError):
            return None

    def _float_or_none(x):
        try:
            return float(x) if pd.notna(x) else None
        except (TypeError, ValueError):
            return None

    rows_out = []
    for study in sorted(shared):
        c = cont_idx[study]
        d = dich_idx[study]
        row = {
            "review_id": review_id,
            "outcome_group": outcome_label,
            "trial_id": str(study),
            "mean_t":    _float_or_none(c.get("Experimental.mean")),
            "sd_t":      _float_or_none(c.get("Experimental.SD")),
            "n_t":       _int_or_none(c.get("Experimental.N")),
            "mean_c":    _float_or_none(c.get("Control.mean")),
            "sd_c":      _float_or_none(c.get("Control.SD")),
            "n_c":       _int_or_none(c.get("Control.N")),
            "events_t":  _int_or_none(d.get("Experimental.cases")),
            "n_t_dich":  _int_or_none(d.get("Experimental.N")),
            "events_c":  _int_or_none(d.get("Control.cases")),
            "n_c_dich":  _int_or_none(d.get("Control.N")),
            "instrument_id": instrument_id,
        }
        t_status, t_reason = classify_arm(TrialArmInput(row["mean_t"], row["sd_t"], row["n_t"], row["events_t"]))
        c_status, c_reason = classify_arm(TrialArmInput(row["mean_c"], row["sd_c"], row["n_c"], row["events_c"]))
        status = t_status if t_status is not StatusCode.OK else c_status
        reason = t_reason if t_status is not StatusCode.OK else c_reason
        if instrument_id is None:
            status, reason = StatusCode.UNKNOWN_INSTRUMENT, f"no v1-panel match for: {outcome_label}"
        row["status"] = status.value
        row["reason"] = reason
        rows_out.append(row)

    # Also emit ambiguous-ID rows with status=ID_AMBIGUOUS
    for study in sorted(amb):
        rows_out.append({
            "review_id": review_id, "outcome_group": outcome_label, "trial_id": str(study),
            "mean_t": None, "sd_t": None, "n_t": None, "mean_c": None, "sd_c": None, "n_c": None,
            "events_t": None, "n_t_dich": None, "events_c": None, "n_c_dich": None,
            "instrument_id": instrument_id,
            "status": StatusCode.ID_AMBIGUOUS.value,
            "reason": f"trial {study} appears in multiple rows within one MA",
        })
    return rows_out


def process_review(path: Path, instruments) -> tuple[list[dict], dict]:
    review_id = _review_id_from_path(path)
    try:
        raw = load_rda(path)
        df = pd.DataFrame(raw) if not isinstance(raw, pd.DataFrame) else raw
    except Exception as e:
        return [], {"review_id": review_id, "error": f"load_rda failed: {e}"}

    if df.empty or "Analysis.number" not in df.columns:
        return [], {"review_id": review_id, "error": "unexpected schema (no Analysis.number column)"}

    # Partition into MAs by (Analysis.number, Subgroup.number).
    df = df.copy()
    df["_ma_key"] = df.apply(_ma_key, axis=1)
    mas: dict[tuple, dict] = {}
    for key, group_rows in df.groupby("_ma_key"):
        mtype = _classify_ma(group_rows)
        label = _ma_label(group_rows)
        mas[key] = {"type": mtype, "label": label, "rows": group_rows}

    cont_mas = [(k, ma) for k, ma in mas.items() if ma["type"] == "continuous"]
    dich_mas = [(k, ma) for k, ma in mas.items() if ma["type"] == "dichotomous"]

    pairs: list[tuple] = []
    for _ck, cma in cont_mas:
        for _dk, dma in dich_mas:
            if are_same_outcome(cma["label"], dma["label"]):
                pairs.append((cma, dma))

    all_rows = []
    for cma, dma in pairs:
        all_rows.extend(_extract_trial_rows(review_id, cma["rows"], dma["rows"], cma["label"], instruments))

    manifest = {
        "review_id": review_id,
        "n_mas_total": len(mas),
        "n_continuous": len(cont_mas),
        "n_dichotomous": len(dich_mas),
        "n_mixed": sum(1 for k, ma in mas.items() if ma["type"] == "mixed"),
        "n_giv": sum(1 for k, ma in mas.items() if ma["type"] == "giv"),
        "n_dual_pairs": len(pairs),
        "n_trial_rows_emitted": len(all_rows),
    }
    return all_rows, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None, help="Process at most N RDAs (for debugging)")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    instruments = load_instruments()
    all_rows: list[dict] = []
    per_review_manifests: list[dict] = []
    manifest: dict[str, Any] = {
        "reviews_scanned": 0,
        "reviews_with_dual_pairs": 0,
        "total_rows_emitted": 0,
        "errors": [],
        "per_review": per_review_manifests,
    }

    rda_paths = sorted(Path(args.corpus).rglob("*.rda"))
    if args.limit:
        rda_paths = rda_paths[:args.limit]

    for i, rda_path in enumerate(rda_paths):
        if i % 50 == 0:
            print(f"[{i}/{len(rda_paths)}] {rda_path.name}", flush=True)
        rows, rev_manifest = process_review(rda_path, instruments)
        manifest["reviews_scanned"] += 1
        if "error" in rev_manifest:
            manifest["errors"].append({"file": str(rda_path), "error": rev_manifest["error"]})
            continue
        per_review_manifests.append(rev_manifest)
        if rev_manifest["n_dual_pairs"] > 0:
            manifest["reviews_with_dual_pairs"] += 1
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    out_parquet = args.output_dir / "dual_framing_index.parquet"
    df.to_parquet(out_parquet, index=False)
    manifest["total_rows_emitted"] = len(df)
    (args.output_dir / "stage1_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(
        f"\nScanned {manifest['reviews_scanned']} reviews; "
        f"{manifest['reviews_with_dual_pairs']} had dual-framing pairs; "
        f"{len(df)} trial rows emitted; "
        f"{len(manifest['errors'])} errors"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

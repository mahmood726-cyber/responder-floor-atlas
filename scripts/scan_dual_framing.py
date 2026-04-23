# sentinel:skip-file — hardcoded paths / templated placeholders are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
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
    sn_raw = row.get("Subgroup.number")
    try:
        # Use "overall" sentinel for NaN rather than coercing to 1.
        # Coercing NaN->1 previously merged overall-analysis rows (Subgroup.number=NaN)
        # with the first subgroup's rows (Subgroup.number=1), causing Study duplication.
        sn = int(sn_raw) if pd.notna(sn_raw) else "overall"
    except (TypeError, ValueError):
        sn = "overall"
    # Include the Subgroup label so that multiple cross-classification dimensions that
    # reuse the same Subgroup.number (e.g. "60-79 years" and "Fatal stroke" both using
    # Subgroup.number=1 under different Analysis.numbers but same key) are distinguished.
    sg_label = str(row.get("Subgroup", "")).strip()
    return (an, sn, sg_label)


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


def _resolve_trial_keys(rows: pd.DataFrame) -> pd.Series:
    """Return a Series of trial keys for the given MA rows.

    Strategy:
    1. Deduplicate exact-duplicate rows first (same Study + same numeric arm data).
    2. If Study is still not unique within the MA, use a composite key
       (Study|n_t=N|n_c=N) to distinguish multi-arm or ambiguous rows.
    3. If even the composite key is not unique, append a row-index suffix.
    """
    def _composite(r) -> str:
        study = str(r["Study"])
        n_t = r.get("Experimental.N")
        n_c = r.get("Control.N")
        n_t_k = "NA" if pd.isna(n_t) else int(n_t)
        n_c_k = "NA" if pd.isna(n_c) else int(n_c)
        return f"{study}|n_t={n_t_k}|n_c={n_c_k}"

    study_counts = rows["Study"].value_counts()
    duplicated_studies = set(study_counts[study_counts > 1].index)
    keys: list[str] = []
    seen: dict[str, int] = {}
    for _, r in rows.iterrows():
        study = str(r["Study"])
        if study in duplicated_studies:
            base_key = _composite(r)
        else:
            base_key = study
        # Final tiebreaker: if composite key is still duplicated, append occurrence index.
        count = seen.get(base_key, 0)
        key = base_key if count == 0 else f"{base_key}#{count + 1}"
        seen[base_key] = count + 1
        keys.append(key)
    return pd.Series(keys, index=rows.index)


def _extract_trial_rows(review_id: str, cont_rows: pd.DataFrame, dich_rows: pd.DataFrame,
                        outcome_label: str, instruments) -> list[dict]:
    instr = match_instrument(outcome_label, instruments)
    instrument_id = instr.id if instr else None

    # Deduplicate exact-duplicate rows within each MA before building keys.
    # Real Pairwise70 RDAs sometimes store identical rows multiple times.
    key_cols = ["Study", "Experimental.N", "Control.N",
                "Experimental.mean", "Experimental.SD",
                "Experimental.cases", "Control.cases"]
    dedup_cols_c = [c for c in key_cols if c in cont_rows.columns]
    dedup_cols_d = [c for c in key_cols if c in dich_rows.columns]
    cont_rows = cont_rows.drop_duplicates(subset=dedup_cols_c).reset_index(drop=True)
    dich_rows = dich_rows.drop_duplicates(subset=dedup_cols_d).reset_index(drop=True)

    # Build composite trial keys: Study alone when unique, Study|n_t=N|n_c=N when duplicated.
    cont_keys = _resolve_trial_keys(cont_rows)
    dich_keys = _resolve_trial_keys(dich_rows)

    cont_idx = dict(zip(cont_keys, (r for _, r in cont_rows.iterrows())))
    dich_idx = dict(zip(dich_keys, (r for _, r in dich_rows.iterrows())))
    shared = set(cont_idx) & set(dich_idx)
    amb: set[str] = set()  # After dedup + composite keys, ambiguity is eliminated.

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

    # amb is always empty after the dedup + composite key strategy, but kept for safety.
    for trial_key in sorted(amb):
        rows_out.append({
            "review_id": review_id, "outcome_group": outcome_label, "trial_id": str(trial_key),
            "mean_t": None, "sd_t": None, "n_t": None, "mean_c": None, "sd_c": None, "n_c": None,
            "events_t": None, "n_t_dich": None, "events_c": None, "n_c_dich": None,
            "instrument_id": instrument_id,
            "status": StatusCode.ID_AMBIGUOUS.value,
            "reason": f"trial {trial_key} appears in multiple rows within one MA",
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

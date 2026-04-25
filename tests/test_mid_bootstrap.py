import numpy as np
import pandas as pd
import pytest

from responder_floor.mid_bootstrap import bootstrap_mid_ratios


def test_bootstrap_returns_per_instrument_cis():
    # Synthetic reconstructions: 2 instruments × 3 reviews × 5 trials each
    # Use a single advancing RNG so each trial gets a different value (ensuring CI spread).
    data_rng = np.random.default_rng(seed=42)
    rows = []
    for instr_id, true_mid in [("body_weight_kg", 8.0), ("sf36_pcs", 6.6)]:
        for r in range(3):
            for t in range(5):
                rows.append({
                    "review_id": f"R{r}_{instr_id}",
                    "instrument_id": instr_id,
                    "delta_hat_trial": float(data_rng.normal(true_mid, 2.0)),
                    "status": "OK",
                })
    df = pd.DataFrame(rows)
    result = bootstrap_mid_ratios(df, n_boot=500, rng=np.random.default_rng(seed=0))
    assert len(result) == 2
    assert all(c in result.columns for c in [
        "instrument_id", "empirical_mid", "canonical_mid", "ratio",
        "ratio_ci_lower", "ratio_ci_upper", "n_trials", "n_reviews"
    ])
    bw = result[result["instrument_id"] == "body_weight_kg"].iloc[0]
    assert bw["ratio_ci_lower"] < bw["ratio"] < bw["ratio_ci_upper"]


def test_bootstrap_handles_unknown_instrument():
    df = pd.DataFrame([
        {"review_id": "R1", "instrument_id": None, "delta_hat_trial": 5.0, "status": "OK"}
    ])
    result = bootstrap_mid_ratios(df, n_boot=100, rng=np.random.default_rng(seed=0))
    assert len(result) == 0  # Unknown instruments are filtered out

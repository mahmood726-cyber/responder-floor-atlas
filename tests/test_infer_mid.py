"""Test Stage 2 MID inference (Model 1 canonical + Model 2 back-out)."""
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_infer_mid_emits_model1_and_model2_per_review(tmp_path):
    rows = []
    for t in ("T1", "T2", "T3"):
        rows.append({
            "review_id": "R001", "outcome_group": "KCCQ OS", "trial_id": t,
            "mean_t": 10, "sd_t": 15, "n_t": 100,
            "mean_c": 5, "sd_c": 15, "n_c": 100,
            "events_t": 63, "events_c": 45, "n_t_dich": 100, "n_c_dich": 100,
            "instrument_id": "kccq_os", "status": "OK", "reason": "",
        })
    idx = tmp_path / "dual_framing_index.parquet"
    pd.DataFrame(rows).to_parquet(idx, index=False)

    result = subprocess.run(
        [sys.executable, "scripts/infer_mid.py",
         "--index", str(idx), "--output-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    mid = pd.read_parquet(tmp_path / "mid_inferences.parquet")
    assert {"review_id", "trial_id", "delta_hat_t", "delta_hat_c", "delta_hat_trial", "model1_mid", "model1_source"} <= set(mid.columns)
    # Model 1 for kccq_os canonical = 5.0.
    assert (mid["model1_mid"] == 5.0).all()
    # Model 2 back-out should be finite per trial.
    assert mid["delta_hat_trial"].notna().all()

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def test_sensitivity_runs_on_minimal_input(tmp_path):
    rows = [
        {"review_id": "R1", "trial_id": "T1", "instrument_id": "body_weight_kg",
         "mean_t": -8.0, "sd_t": 5.0, "n_t": 100, "events_t": 50,
         "mean_c": -2.0, "sd_c": 5.0, "n_c": 100, "events_c": 30,
         "model1_mid": 5.0, "direction": -1, "status": "OK",
         "p_hat_t": 0.7257, "p_hat_c": 0.2742},
    ]
    pd.DataFrame(rows).to_parquet(tmp_path / "reconstructions.parquet", index=False)
    result = subprocess.run([sys.executable, "scripts/run_sensitivity.py",
                            "--reconstructions", str(tmp_path / "reconstructions.parquet"),
                            "--output-dir", str(tmp_path), "--n-draws", "2000"],
                           capture_output=True, text=True, check=True)
    summary = pd.read_parquet(tmp_path / "sensitivity_summary.parquet")
    # Expect 3 dists × 1 instrument
    assert len(summary) == 3
    assert set(summary["dist"]) == {"lognormal_shifted", "beta_bounded", "truncated_normal"}
    assert (summary["median_delta_p"] >= 0).all()

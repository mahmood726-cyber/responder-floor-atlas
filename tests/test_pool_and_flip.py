# tests/test_pool_and_flip.py
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def test_pool_and_flip_computes_per_review_verdict(tmp_path):
    # Build one review with 3 trials; both framings should reach significance.
    rows = []
    for t in ("T1", "T2", "T3"):
        rows.append({
            "review_id": "R001", "trial_id": t,
            "n_t": 100, "n_c": 100, "events_t": 70, "events_c": 40,
            "n_t_dich": 100, "n_c_dich": 100,
            "mean_t": 10, "sd_t": 15, "mean_c": 3, "sd_c": 15,
            "instrument_id": "kccq_os", "model1_mid": 5.0, "direction": 1,
            "log_rr_hat": np.log(0.7 / 0.4), "se_log_rr_hat": 0.15,
            "status": "OK",
        })
    inp = tmp_path / "reconstructions.parquet"
    pd.DataFrame(rows).to_parquet(inp, index=False)

    result = subprocess.run(
        [sys.executable, "scripts/pool_and_flip.py",
         "--reconstructions", str(inp),
         "--output-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    flips = pd.read_parquet(tmp_path / "flip_results.parquet")
    row = flips[flips["review_id"] == "R001"].iloc[0]
    # Both framings significant → no flip.
    assert bool(row["smd_significant"])
    assert bool(row["rr_significant"])
    assert bool(row["framing_flip"]) is False

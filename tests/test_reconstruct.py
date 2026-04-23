"""Test Stage 3 reconstruction (per-trial responder probability + error terms)."""
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_reconstruct_emits_epsilon_per_arm(tmp_path):
    rows = []
    for t in ("T1", "T2", "T3"):
        rows.append({
            "review_id": "R001", "trial_id": t,
            "mean_t": 10, "sd_t": 15, "n_t": 100, "events_t": 63, "n_t_dich": 100,
            "mean_c": 5, "sd_c": 15, "n_c": 100, "events_c": 45, "n_c_dich": 100,
            "instrument_id": "kccq_os", "direction": 1, "model1_mid": 5.0,
            "status": "OK",
        })
    inp = tmp_path / "mid_inferences.parquet"
    pd.DataFrame(rows).to_parquet(inp, index=False)

    result = subprocess.run(
        [sys.executable, "scripts/reconstruct.py",
         "--mid-inferences", str(inp), "--output-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    out = pd.read_parquet(tmp_path / "reconstructions.parquet")
    expected_cols = {"p_hat_t", "p_hat_c", "p_obs_t", "p_obs_c",
                     "epsilon_t", "epsilon_c", "log_rr_hat", "log_rr_obs", "epsilon_log_rr"}
    assert expected_cols <= set(out.columns)
    # For KCCQ d=+1, μ_t=10, σ_t=15, δ=5: p̂_t = Φ(5/15) ≈ 0.6305587; obs = 63/100 = 0.63. ε ≈ 0.0006.
    assert abs(out.iloc[0]["p_hat_t"] - 0.6305587) < 1e-5

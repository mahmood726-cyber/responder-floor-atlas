import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_q4_handles_no_overlap(tmp_path):
    # All trials unique per review
    df = pd.DataFrame([
        {"review_id": f"R{i}", "trial_id": f"S{i}", "instrument_id": "kccq_os",
         "delta_hat_trial": 5.0, "status": "OK"} for i in range(5)
    ])
    df.to_parquet(tmp_path / "reconstructions.parquet", index=False)
    result = subprocess.run([sys.executable, "scripts/exploratory_q4.py",
                            "--reconstructions", str(tmp_path / "reconstructions.parquet"),
                            "--output-dir", str(tmp_path)],
                           capture_output=True, text=True, check=True)
    summary = json.loads((tmp_path / "q4_overlap.json").read_text())
    assert summary["trials_in_multiple_reviews"] == 0
    assert summary["max_review_overlap"] == 1


def test_q4_detects_overlap(tmp_path):
    # Trial S1 appears in 2 reviews under same instrument
    df = pd.DataFrame([
        {"review_id": "R1", "trial_id": "S1|n_t=100|n_c=100", "instrument_id": "kccq_os",
         "delta_hat_trial": 4.5, "status": "OK"},
        {"review_id": "R2", "trial_id": "S1|n_t=120|n_c=120", "instrument_id": "kccq_os",
         "delta_hat_trial": 5.5, "status": "OK"},
    ])
    df.to_parquet(tmp_path / "reconstructions.parquet", index=False)
    subprocess.run([sys.executable, "scripts/exploratory_q4.py",
                   "--reconstructions", str(tmp_path / "reconstructions.parquet"),
                   "--output-dir", str(tmp_path)],
                  capture_output=True, text=True, check=True)
    summary = json.loads((tmp_path / "q4_overlap.json").read_text())
    assert summary["trials_in_multiple_reviews"] == 1

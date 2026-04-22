# tests/test_scan_dual_framing.py
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

FIXTURE = Path("tests/fixtures/synthetic_one_review.rda")


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture not generated")
def test_scan_emits_parquet_with_expected_rows(tmp_path):
    out_dir = tmp_path / "outputs"
    result = subprocess.run(
        [sys.executable, "scripts/scan_dual_framing.py",
         "--corpus", "tests/fixtures",
         "--output-dir", str(out_dir)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    df = pd.read_parquet(out_dir / "dual_framing_index.parquet")
    # Three trials (T1/T2/T3) × 1 review = 3 rows
    assert len(df) == 3
    expected_cols = {
        "review_id", "outcome_group", "trial_id",
        "mean_t", "sd_t", "n_t", "events_t",
        "mean_c", "sd_c", "n_c", "events_c",
        "instrument_id", "status", "reason",
    }
    assert expected_cols <= set(df.columns)
    assert (df["instrument_id"] == "kccq_os").all()
    assert (df["status"] == "OK").all()

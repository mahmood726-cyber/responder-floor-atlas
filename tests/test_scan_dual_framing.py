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
    # fixture_R001: 3 trials (T1/T2/T3); negative_control_kccq: 5 trials (T1-T5) = 8 rows total
    assert len(df) == 8
    expected_cols = {
        "review_id", "outcome_group", "trial_id",
        "mean_t", "sd_t", "n_t", "events_t",
        "mean_c", "sd_c", "n_c", "events_c",
        "instrument_id", "status", "reason",
    }
    assert expected_cols <= set(df.columns)
    assert (df["instrument_id"] == "kccq_os").all()
    assert (df["status"] == "OK").all()

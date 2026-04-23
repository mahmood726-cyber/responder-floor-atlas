import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_audit_emits_audit_md_and_paper_numbers(tmp_path):
    idx = pd.DataFrame([
        {"review_id": "R1", "trial_id": "T1", "instrument_id": "kccq_os", "status": "OK", "reason": ""},
        {"review_id": "R2", "trial_id": "T2", "instrument_id": "sgrq_total", "status": "MISSING_SD", "reason": "sd missing"},
    ])
    idx.to_parquet(tmp_path / "dual_framing_index.parquet", index=False)
    flips = pd.DataFrame([
        {"review_id": "R1", "framing_flip": True, "magnitude_flip": False, "k": 3,
         "smd_significant": True, "rr_significant": False,
         "smd_estimate": 0.3, "rr_estimate": 0.4, "smd_p": 0.01, "rr_p": 0.08}
    ])
    flips.to_parquet(tmp_path / "flip_results.parquet", index=False)
    recon = pd.DataFrame([
        {"instrument_id": "kccq_os", "epsilon_t": 0.01, "epsilon_c": 0.02,
         "delta_hat_trial": 5.0, "review_id": "R1"}
    ])
    recon.to_parquet(tmp_path / "reconstructions.parquet", index=False)

    result = subprocess.run(
        [sys.executable, "scripts/emit_audit.py",
         "--dual-framing-index", str(tmp_path / "dual_framing_index.parquet"),
         "--flips", str(tmp_path / "flip_results.parquet"),
         "--reconstructions", str(tmp_path / "reconstructions.parquet"),
         "--output-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    numbers = json.loads((tmp_path / "paper_numbers.json").read_text())
    audit = (tmp_path / "analysis_audit.md").read_text(encoding="utf-8")
    assert numbers["q1_flip_rate"] == 1.0
    assert "MISSING_SD" in audit

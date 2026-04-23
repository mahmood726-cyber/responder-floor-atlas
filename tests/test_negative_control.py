# tests/test_negative_control.py
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

FIXTURE = Path("tests/fixtures/kccq_stable_cluster.rda")
CORPUS = FIXTURE.parent  # tests/fixtures contains BOTH synthetic_one_review.rda AND kccq_stable_cluster.rda


@pytest.mark.skipif(not FIXTURE.exists(), reason="kccq_stable_cluster.rda not generated")
def test_reconstruction_epsilon_tight_on_stable_cluster(tmp_path):
    out = tmp_path / "outputs"
    subprocess.run([sys.executable, "scripts/scan_dual_framing.py",
                    "--corpus", str(CORPUS), "--output-dir", str(out)], check=True, capture_output=True)
    subprocess.run([sys.executable, "scripts/infer_mid.py",
                    "--index", str(out / "dual_framing_index.parquet"), "--output-dir", str(out)],
                   check=True, capture_output=True)
    subprocess.run([sys.executable, "scripts/reconstruct.py",
                    "--mid-inferences", str(out / "mid_inferences.parquet"), "--output-dir", str(out)],
                   check=True, capture_output=True)
    recon = pd.read_parquet(out / "reconstructions.parquet")
    nc = recon[recon["review_id"] == "negative_control_kccq"]
    assert len(nc) == 5, f"expected 5 negative-control trials, got {len(nc)}"
    all_eps = pd.concat([nc["epsilon_t"], nc["epsilon_c"]])
    # Analytically-generated → rounding error only. Expect ε < 0.01 for ≥80% of 10 arms.
    tight = (all_eps < 0.01).mean()
    assert tight >= 0.8, (
        f"negative control failed: only {tight:.0%} of arms have ε < 0.01; "
        f"all ε values: {all_eps.tolist()}"
    )

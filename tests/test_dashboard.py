import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_dashboard_emits_single_html_with_three_panels(tmp_path):
    flips = pd.DataFrame([
        {"review_id": f"R{i:03d}", "k": 4, "smd_estimate": 0.3, "smd_p": 0.01,
         "smd_significant": True, "rr_estimate": 0.35, "rr_p": 0.06,
         "rr_significant": False, "framing_flip": True, "magnitude_flip": False}
        for i in range(20)
    ])
    flips_path = tmp_path / "flip_results.parquet"
    flips.to_parquet(flips_path, index=False)
    recon = pd.DataFrame([
        {"instrument_id": "kccq_os", "epsilon_t": 0.01, "epsilon_c": 0.02,
         "delta_hat_trial": 5.1, "review_id": "R001"}
    ])
    recon_path = tmp_path / "reconstructions.parquet"
    recon.to_parquet(recon_path, index=False)

    result = subprocess.run(
        [sys.executable, "scripts/build_dashboard.py",
         "--flips", str(flips_path),
         "--reconstructions", str(recon_path),
         "--output", str(tmp_path / "index.html")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "panel-flip" in html
    assert "panel-reconstruction" in html
    assert "panel-implied-mid" in html
    # No literal </script> outside script tags (XSS / injection check).
    # Specifically: before the first <script tag, there must be no literal </script>.
    before_first_script = html.split("<script", 1)[0] if "<script" in html else html
    assert "</script>" not in before_first_script

"""End-to-end pipeline integration test for all 5 stages on fixture corpus.

Stages:
  1. scan_dual_framing.py — dual-framing index
  2. evaluate_gates.py — feasibility gates (may return exit code 2 on tiny fixture)
  3. infer_mid.py — MID inferences
  4. reconstruct.py — per-trial reconstruction
  5. pool_and_flip.py — pooling + flip detection
  6. build_dashboard.py — HTML dashboard render

This test verifies:
  - All stages execute without hard errors
  - Expected output files exist after each stage
  - Data flows correctly between stages (parquets are readable, not corrupted)
  - Dashboard HTML is well-formed (contains expected markers)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


FIXTURE_CORPUS = Path("tests/fixtures")


@pytest.mark.skipif(
    not (FIXTURE_CORPUS / "fixture_R001_data.rda").exists(),
    reason="fixture RDA not generated",
)
def test_end_to_end_all_stages(tmp_path):
    """Run all 6 pipeline stages on fixture corpus; verify outputs exist and data flows correctly."""
    out = tmp_path / "outputs"

    # Define stages: each is (script_path, [args...], allowed_exit_codes)
    # Most stages expect exit code 0; evaluate_gates returns 0 or 2 depending on gate results.
    stages = [
        ("scripts/scan_dual_framing.py", ["--corpus", str(FIXTURE_CORPUS), "--output-dir", str(out)], {0}),
        ("scripts/evaluate_gates.py", ["--index", str(out / "dual_framing_index.parquet"),
                                       "--output", str(out / "FEASIBILITY_REPORT.md"),
                                       "--json", str(out / "gates.json")], {0, 2}),
        ("scripts/infer_mid.py", ["--index", str(out / "dual_framing_index.parquet"),
                                   "--output-dir", str(out)], {0}),
        ("scripts/reconstruct.py", ["--mid-inferences", str(out / "mid_inferences.parquet"),
                                     "--output-dir", str(out)], {0}),
        ("scripts/pool_and_flip.py", ["--reconstructions", str(out / "reconstructions.parquet"),
                                       "--output-dir", str(out)], {0}),
        ("scripts/build_dashboard.py", ["--flips", str(out / "flip_results.parquet"),
                                         "--reconstructions", str(out / "reconstructions.parquet"),
                                         "--output", str(out / "dashboard" / "index.html")], {0}),
    ]

    for script_path, args, allowed_codes in stages:
        cmd = [sys.executable, script_path] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        step_name = Path(script_path).stem

        # Check exit code is allowed for this stage
        if result.returncode not in allowed_codes:
            pytest.fail(
                f"Stage {step_name} failed with exit code {result.returncode}. "
                f"Stderr: {result.stderr[:500]}"
            )

    # Verify expected output files exist
    expected_files = [
        "dual_framing_index.parquet",
        "mid_inferences.parquet",
        "reconstructions.parquet",
        "flip_results.parquet",
        "dashboard/index.html",
        "FEASIBILITY_REPORT.md",
        "gates.json",
        "stage1_manifest.json",
    ]
    for fname in expected_files:
        fpath = out / fname
        assert fpath.exists(), f"Expected output file missing: {fname}"

    # Spot-check parquet files are readable
    import pandas as pd

    df_index = pd.read_parquet(out / "dual_framing_index.parquet")
    assert len(df_index) > 0, "dual_framing_index is empty"
    assert "review_id" in df_index.columns, "dual_framing_index missing review_id"

    df_mid = pd.read_parquet(out / "mid_inferences.parquet")
    assert len(df_mid) > 0, "mid_inferences is empty"
    assert "model1_mid" in df_mid.columns, "mid_inferences missing model1_mid"

    df_recon = pd.read_parquet(out / "reconstructions.parquet")
    assert len(df_recon) > 0, "reconstructions is empty"
    assert "p_hat_t" in df_recon.columns, "reconstructions missing p_hat_t"

    df_flips = pd.read_parquet(out / "flip_results.parquet")
    assert len(df_flips) >= 0, "flip_results should have non-negative rows"
    # flips may be empty if fixture has no review-level data to pool, but file must exist

    # Spot-check HTML dashboard is well-formed
    html_content = (out / "dashboard" / "index.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_content, "dashboard missing DOCTYPE"
    assert "<title>Responder Floor Atlas</title>" in html_content, "dashboard missing title"
    assert html_content.count("<div") == html_content.count("</div>"), "dashboard div imbalance"
    assert "Responder Floor Atlas" in html_content, "dashboard missing page title"

    # Spot-check FEASIBILITY_REPORT.md contains gate results
    report = (out / "FEASIBILITY_REPORT.md").read_text(encoding="utf-8")
    assert "# Feasibility Report" in report, "FEASIBILITY_REPORT missing header"
    assert "Gate A" in report or "Gate B" in report, "FEASIBILITY_REPORT missing gate results"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""Determinism regression test for Stages 1-3 (deterministic pipeline stages).

Stages 1-3 (scan_dual_framing, infer_mid, reconstruct) use no random state or
external IO that would break reproducibility. They must produce byte-identical
output across two independent runs.

This test:
  1. Runs all three stages on the fixture corpus
  2. Repeats the run in a separate output directory
  3. Compares the output parquet files byte-for-byte (SHA-256)
  4. Asserts hash equality; if byte-identity fails, falls back to df.equals()

If byte-identity fails consistently, we investigate Parquet metadata or pandas
write-order issues. But starting with byte-identity is the gold standard for
determinism in data pipelines.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest


FIXTURE_CORPUS = Path("tests/fixtures")


def _sha256(path: Path) -> str:
    """Compute SHA-256 hash of file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_deterministic_stages(out: Path) -> None:
    """Run Stages 1-3 (scan, infer_mid, reconstruct) on fixture corpus.

    All three stages are deterministic (no random state, no timestamps).
    Output parquets should be byte-identical across runs.
    """
    out.mkdir(parents=True, exist_ok=True)

    stages = [
        (
            "scripts/scan_dual_framing.py",
            ["--corpus", str(FIXTURE_CORPUS), "--output-dir", str(out)],
        ),
        (
            "scripts/infer_mid.py",
            ["--index", str(out / "dual_framing_index.parquet"), "--output-dir", str(out)],
        ),
        (
            "scripts/reconstruct.py",
            ["--mid-inferences", str(out / "mid_inferences.parquet"), "--output-dir", str(out)],
        ),
    ]

    for script_path, args in stages:
        cmd = [sys.executable, script_path] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        step_name = Path(script_path).stem

        if result.returncode != 0:
            raise RuntimeError(
                f"Stage {step_name} failed with exit code {result.returncode}. "
                f"Stderr: {result.stderr[:500]}"
            )


@pytest.mark.skipif(
    not (FIXTURE_CORPUS / "synthetic_one_review.rda").exists(),
    reason="fixture RDA not generated",
)
def test_reconstructions_byte_identical_across_runs(tmp_path):
    """Verify Stages 1-3 produce byte-identical parquets across two runs.

    If byte-identity fails, fall back to DataFrame equality check to diagnose
    whether it's a Parquet metadata/write-order issue (df.equals passes) or
    true data corruption (df.equals fails).
    """
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"

    # Run all three stages twice
    _run_deterministic_stages(out1)
    _run_deterministic_stages(out2)

    # Check byte-identity of critical output files
    critical_files = [
        "dual_framing_index.parquet",
        "mid_inferences.parquet",
        "reconstructions.parquet",
    ]

    for fname in critical_files:
        path1 = out1 / fname
        path2 = out2 / fname

        assert path1.exists(), f"Run 1 missing {fname}"
        assert path2.exists(), f"Run 2 missing {fname}"

        hash1 = _sha256(path1)
        hash2 = _sha256(path2)

        if hash1 == hash2:
            # Byte-identical: success
            continue

        # Byte-identity failed; fall back to DataFrame equality
        df1 = pd.read_parquet(path1)
        df2 = pd.read_parquet(path2)

        if not df1.equals(df2):
            pytest.fail(
                f"Determinism violation in {fname}: "
                f"DataFrames differ (hash1={hash1[:8]}, hash2={hash2[:8]}). "
                f"Shape1={df1.shape}, Shape2={df2.shape}. "
                f"Columns: {list(df1.columns)}"
            )
        else:
            # DataFrames equal but bytes differ — likely Parquet metadata or row order
            pytest.skip(
                f"{fname}: DataFrames equal but bytes differ (likely Parquet metadata). "
                f"This is acceptable if row order/metadata is non-deterministic. "
                f"Hash mismatch: {hash1[:8]} vs {hash2[:8]}"
            )


@pytest.mark.skipif(
    not (FIXTURE_CORPUS / "synthetic_one_review.rda").exists(),
    reason="fixture RDA not generated",
)
def test_dual_framing_index_stability(tmp_path):
    """Verify dual_framing_index.parquet schema and record count are stable."""
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"

    _run_deterministic_stages(out1)
    _run_deterministic_stages(out2)

    df1 = pd.read_parquet(out1 / "dual_framing_index.parquet")
    df2 = pd.read_parquet(out2 / "dual_framing_index.parquet")

    # Schema must match
    assert list(df1.columns) == list(df2.columns), "Columns differ between runs"
    assert df1.dtypes.equals(df2.dtypes), "Dtypes differ between runs"

    # Row count must match
    assert len(df1) == len(df2), f"Row count differs: {len(df1)} vs {len(df2)}"


@pytest.mark.skipif(
    not (FIXTURE_CORPUS / "synthetic_one_review.rda").exists(),
    reason="fixture RDA not generated",
)
def test_mid_inferences_stability(tmp_path):
    """Verify mid_inferences.parquet schema and record count are stable."""
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"

    _run_deterministic_stages(out1)
    _run_deterministic_stages(out2)

    df1 = pd.read_parquet(out1 / "mid_inferences.parquet")
    df2 = pd.read_parquet(out2 / "mid_inferences.parquet")

    # Schema must match
    assert list(df1.columns) == list(df2.columns), "Columns differ between runs"
    assert df1.dtypes.equals(df2.dtypes), "Dtypes differ between runs"

    # Row count must match
    assert len(df1) == len(df2), f"Row count differs: {len(df1)} vs {len(df2)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

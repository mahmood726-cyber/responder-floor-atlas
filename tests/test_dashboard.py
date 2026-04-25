import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# Shared fixtures helpers
# ---------------------------------------------------------------------------

def _make_flips(tmp_path: Path) -> Path:
    flips = pd.DataFrame([
        {"review_id": f"R{i:03d}", "k": 4, "smd_estimate": 0.3, "smd_p": 0.01,
         "smd_significant": True, "rr_estimate": 0.35, "rr_p": 0.06,
         "rr_significant": False, "framing_flip": True, "magnitude_flip": False}
        for i in range(20)
    ])
    p = tmp_path / "flip_results.parquet"
    flips.to_parquet(p, index=False)
    return p


def _make_recon(tmp_path: Path) -> Path:
    recon = pd.DataFrame([
        {
            "instrument_id": "kccq_os",
            "epsilon_t": 0.01,
            "epsilon_c": 0.02,
            "delta_hat_trial": 5.1,
            "review_id": "R001",
            "trial_id": "Trial_A",
            "status": "OK",
            "p_hat_t": 0.4,
            "p_hat_c": 0.3,
            "p_obs_t": 0.42,
            "p_obs_c": 0.28,
        }
    ])
    p = tmp_path / "reconstructions.parquet"
    recon.to_parquet(p, index=False)
    return p


def _make_mid_bootstrap(tmp_path: Path) -> Path:
    boot = pd.DataFrame([
        {
            "instrument_id": "kccq_os",
            "n_trials": 10,
            "n_reviews": 1,
            "empirical_mid": 6.5,
            "canonical_mid": 5.0,
            "ratio": 1.30,
            "ratio_ci_lower": 1.10,
            "ratio_ci_upper": 1.55,
            "n_boot": 200,
            "status": "OK",
        }
    ])
    p = tmp_path / "mid_bootstrap.parquet"
    boot.to_parquet(p, index=False)
    return p


def _make_q4(tmp_path: Path) -> Path:
    q4 = {
        "total_unique_trials": 10,
        "trials_in_multiple_reviews": 2,
        "trials_in_single_review": 8,
        "max_review_overlap": 2,
    }
    p = tmp_path / "q4_overlap.json"
    p.write_text(json.dumps(q4), encoding="utf-8")
    return p


def _make_sensitivity(tmp_path: Path) -> Path:
    rows = []
    for dist in ["lognormal_shifted", "truncated_normal", "beta_bounded"]:
        rows.append({
            "instrument_id": "kccq_os",
            "dist": dist,
            "n_arms": 100,
            "median_delta_p": 0.03,
            "p95_delta_p": 0.09,
            "max_delta_p": 0.15,
        })
    sens = pd.DataFrame(rows)
    p = tmp_path / "sensitivity_summary.parquet"
    sens.to_parquet(p, index=False)
    return p


# ---------------------------------------------------------------------------
# Test: backward-compatible 3-panel assertion (no new optional inputs)
# ---------------------------------------------------------------------------

def test_dashboard_emits_single_html_with_three_panels(tmp_path):
    """Original smoke test — must pass without optional inputs."""
    flips_path = _make_flips(tmp_path)
    recon_path = _make_recon(tmp_path)

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
    before_first_script = html.split("<script", 1)[0] if "<script" in html else html
    assert "</script>" not in before_first_script


# ---------------------------------------------------------------------------
# Test: all 5 panels when all optional inputs provided
# ---------------------------------------------------------------------------

def test_dashboard_emits_all_five_panels(tmp_path):
    """When all optional inputs are supplied, all 5 panel IDs must appear."""
    flips_path = _make_flips(tmp_path)
    recon_path = _make_recon(tmp_path)
    boot_path = _make_mid_bootstrap(tmp_path)
    q4_path = _make_q4(tmp_path)
    sens_path = _make_sensitivity(tmp_path)

    result = subprocess.run(
        [sys.executable, "scripts/build_dashboard.py",
         "--flips", str(flips_path),
         "--reconstructions", str(recon_path),
         "--mid-bootstrap", str(boot_path),
         "--q4-summary", str(q4_path),
         "--sensitivity-summary", str(sens_path),
         "--output", str(tmp_path / "index.html"),
         "--commit", "abc1234",
         "--date", "2026-04-25"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "panel-flip" in html
    assert "panel-reconstruction" in html
    assert "panel-implied-mid" in html
    assert "panel-q4" in html
    assert "panel-sensitivity" in html
    # commit hash and date embedded
    assert "abc1234" in html
    assert "2026-04-25" in html
    # No script injection
    before_first_script = html.split("<script", 1)[0] if "<script" in html else html
    assert "</script>" not in before_first_script


# ---------------------------------------------------------------------------
# Test: graceful degradation when optional inputs are missing/absent
# ---------------------------------------------------------------------------

def test_dashboard_graceful_when_optional_inputs_absent(tmp_path):
    """Missing optional paths emit '(data not available)' but do not crash."""
    flips_path = _make_flips(tmp_path)
    recon_path = _make_recon(tmp_path)
    nonexistent = tmp_path / "does_not_exist.parquet"

    result = subprocess.run(
        [sys.executable, "scripts/build_dashboard.py",
         "--flips", str(flips_path),
         "--reconstructions", str(recon_path),
         "--mid-bootstrap", str(nonexistent),
         "--q4-summary", str(tmp_path / "nope.json"),
         "--sensitivity-summary", str(nonexistent),
         "--output", str(tmp_path / "index.html")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    # All 5 panel containers still rendered
    assert "panel-flip" in html
    assert "panel-reconstruction" in html
    assert "panel-implied-mid" in html
    assert "panel-q4" in html
    assert "panel-sensitivity" in html
    # Graceful content shown for missing inputs
    assert "data not available" in html


# ---------------------------------------------------------------------------
# Test: SVG elements present when real-ish data supplied
# ---------------------------------------------------------------------------

def test_dashboard_contains_svg_elements(tmp_path):
    """With data that drives all SVG paths, the output must contain <svg tags."""
    flips_path = _make_flips(tmp_path)
    recon_path = _make_recon(tmp_path)
    boot_path = _make_mid_bootstrap(tmp_path)
    q4_path = _make_q4(tmp_path)
    sens_path = _make_sensitivity(tmp_path)

    result = subprocess.run(
        [sys.executable, "scripts/build_dashboard.py",
         "--flips", str(flips_path),
         "--reconstructions", str(recon_path),
         "--mid-bootstrap", str(boot_path),
         "--q4-summary", str(q4_path),
         "--sensitivity-summary", str(sens_path),
         "--output", str(tmp_path / "index.html")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    # Must contain multiple SVG elements (forest, density, BA, flip bar)
    assert html.count("<svg") >= 3
    assert html.count("</svg>") >= 3

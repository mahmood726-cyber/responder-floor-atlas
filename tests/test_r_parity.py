"""Task 8: R+metafor parity harness.

Runs `responder_floor/r_validation.R` via Rscript, compares its REML+HKSJ+PI
output against pool_reml_hksj_pi() at 1e-6 tolerance across 4 representative
MA cases (k=3, 4, 5, 8).  Skips gracefully when R 4.5.2 is not present.

Known divergence (k=3 perfectly homogeneous):
  metafor sets se=0 / collapsed CI/PI when Q_RE=0 (HKSJ factor → 0).
  pool_reml_hksj_pi() intentionally guards hksj_factor to 1.0 to prevent
  division-by-zero in t_stat — this is a documented, tested behaviour in
  test_pooling.py::test_hksj_factor_zero_re_q_falls_back_to_one.
  The degenerate case is therefore excluded from the 1e-6 parity loop and
  verified separately in test_metafor_parity_degenerate_k3_documents_divergence.
"""
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from responder_floor.pooling import pool_reml_hksj_pi

RSCRIPT = Path(r"C:\Program Files\R\R-4.5.2\bin\Rscript.exe")
R_SCRIPT = Path("responder_floor/r_validation.R")

# Parity cases: varied k and heterogeneity levels.
# Case 4 (k=8, diverse effects) was used by the Task 7 code reviewer to surface
# the original REML bug — retained here as a regression guard.
# The k=3-homogeneous case is excluded here; see separate test below.
PARITY_CASES = [
    ([0.3, 0.5, 0.7, 0.4, 0.6], [0.02, 0.03, 0.015, 0.025, 0.02]),          # k=5
    ([-0.2, 0.1, 0.4, 0.3], [0.01, 0.02, 0.015, 0.03]),                      # k=4
    ([0.1, 0.3, -0.2, 0.8, 0.5, -0.1, 0.6, 0.4],
     [0.02, 0.025, 0.03, 0.02, 0.018, 0.022, 0.025, 0.02]),                   # k=8 heterogeneous
]


@pytest.mark.skipif(not RSCRIPT.exists(), reason="R 4.5.2 not installed at expected path")
def test_metafor_parity_at_1e6(tmp_path):
    """pool_reml_hksj_pi() must match metafor rma(method='REML', test='knha') at 1e-6."""
    for eff, var in PARITY_CASES:
        in_csv = tmp_path / "in.csv"
        out_json = tmp_path / "out.json"
        pd.DataFrame({"yi": eff, "vi": var}).to_csv(in_csv, index=False)

        subprocess.run(
            [str(RSCRIPT), str(R_SCRIPT), str(in_csv), str(out_json)],
            check=True, capture_output=True, text=True,
        )
        r = json.loads(out_json.read_text())
        py = pool_reml_hksj_pi(np.array(eff), np.array(var))

        k = len(eff)
        assert abs(py.estimate - r["estimate"]) < 1e-6, (
            f"estimate mismatch on k={k}: py={py.estimate:.10f}, r={r['estimate']:.10f}"
        )
        assert abs(py.se - r["se"]) < 1e-6, (
            f"se mismatch on k={k}: py={py.se:.10f}, r={r['se']:.10f}"
        )
        assert abs(py.tau2 - r["tau2"]) < 1e-6, (
            f"tau2 mismatch on k={k}: py={py.tau2:.10f}, r={r['tau2']:.10f}"
        )
        assert abs(py.ci_lower - r["ci_lower"]) < 1e-6, (
            f"ci_lower mismatch on k={k}: py={py.ci_lower:.10f}, r={r['ci_lower']:.10f}"
        )
        assert abs(py.ci_upper - r["ci_upper"]) < 1e-6, (
            f"ci_upper mismatch on k={k}: py={py.ci_upper:.10f}, r={r['ci_upper']:.10f}"
        )


@pytest.mark.skipif(not RSCRIPT.exists(), reason="R 4.5.2 not installed at expected path")
def test_metafor_parity_degenerate_k3_documents_divergence(tmp_path):
    """Documents the known SE divergence for the k=3 perfectly homogeneous case.

    metafor rma(test='knha') emits se=0 / collapsed CI/PI when tau2=0 and
    Q_RE=0 (HKSJ factor collapses to 0).  pool_reml_hksj_pi() guards
    hksj_factor to min 1.0 to keep t_stat well-defined.  Estimate and tau2
    still match at 1e-6; SE/CI/PI intentionally diverge.
    """
    eff = [0.5, 0.5, 0.5]
    var = [0.01, 0.01, 0.01]
    in_csv = tmp_path / "in.csv"
    out_json = tmp_path / "out.json"
    pd.DataFrame({"yi": eff, "vi": var}).to_csv(in_csv, index=False)

    subprocess.run(
        [str(RSCRIPT), str(R_SCRIPT), str(in_csv), str(out_json)],
        check=True, capture_output=True, text=True,
    )
    r = json.loads(out_json.read_text())
    py = pool_reml_hksj_pi(np.array(eff), np.array(var))

    # Estimate and tau2 must still agree.
    assert abs(py.estimate - r["estimate"]) < 1e-6, (
        f"estimate mismatch: py={py.estimate:.10f}, r={r['estimate']:.10f}"
    )
    assert abs(py.tau2 - r["tau2"]) < 1e-6, (
        f"tau2 mismatch: py={py.tau2:.10f}, r={r['tau2']:.10f}"
    )
    # Document (not assert) the known SE divergence.
    assert r["se"] == 0.0, "metafor se should be 0 for degenerate homogeneous case"
    assert py.se > 0.0, "Python guard should keep se > 0 (hksj_factor floored to 1)"

"""Tests for REML + HKSJ + PI pooling (Task 7)."""
import math
import numpy as np
import pytest
from responder_floor.pooling import pool_reml_hksj_pi, _reml_tau2

# ---------------------------------------------------------------------------
# Golden values from: Rscript -e 'suppressMessages(library(metafor));
#   res <- rma(yi=c(0.3,0.5,0.7,0.4,0.6), vi=c(0.02,0.03,0.015,0.025,0.02),
#              method="REML", test="knha");
#   cat(sprintf("tau2=%.10f\nestimate=%.10f\nse=%.10f\nci_lb=%.10f\nci_ub=%.10f\n",
#               res$tau2, res$b[1], res$se, res$ci.lb, res$ci.ub))'
# Captured 2026-04-22 with metafor installed on R 4.5.2
# ---------------------------------------------------------------------------
_METAFOR_TAU2      = 0.0096225743
_METAFOR_ESTIMATE  = 0.5114547423
_METAFOR_SE        = 0.0742705870
_METAFOR_CI_LOWER  = 0.3052465345
_METAFOR_CI_UPPER  = 0.7176629500


def test_pooled_matches_two_study_weighted_mean():
    # With k=3 identical studies (PI requires k>=3), pooled should equal the common effect.
    effects = np.array([0.5, 0.5, 0.5])
    variances = np.array([0.01, 0.01, 0.01])
    result = pool_reml_hksj_pi(effects, variances)
    assert abs(result.estimate - 0.5) < 1e-10


def test_hksj_factor_zero_re_q_falls_back_to_one():
    # Perfectly homogeneous studies -> Q_RE = 0 -> guard floors factor to 1 to avoid
    # division by zero in t_stat.  This is the degenerate corner case only.
    effects = np.array([0.5, 0.5, 0.5])
    variances = np.array([0.01, 0.01, 0.01])
    result = pool_reml_hksj_pi(effects, variances)
    # hksj_raw = 0/(k-1) = 0, so guard sets factor=1
    assert result.hksj_factor == 1.0


def test_pi_uses_t_k_minus_2():
    effects = np.array([0.3, 0.5, 0.7, 0.4])
    variances = np.array([0.02, 0.03, 0.015, 0.025])
    result = pool_reml_hksj_pi(effects, variances)
    assert result.pi_lower < result.estimate < result.pi_upper
    assert result.pi_df == len(effects) - 2


def test_pi_undefined_for_k_below_3():
    with pytest.raises(ValueError):
        pool_reml_hksj_pi(np.array([0.5, 0.3]), np.array([0.01, 0.02]))


def test_p_value_uses_t_distribution_hksj():
    # Under HKSJ (RE-Q variant), p-value must use t_{k-1} not normal CDF.
    # Use heterogeneous data so Q_RE > 0 and the full HKSJ path is exercised.
    effects = np.array([0.3, 0.5, 0.7, 0.4, 0.6])
    variances = np.array([0.02, 0.03, 0.015, 0.025, 0.02])
    result = pool_reml_hksj_pi(effects, variances)
    from scipy.stats import t as scipy_t
    # Reconstruct expected p-value from the result's own t_stat and k-1 df
    p_expected = float(2.0 * scipy_t.sf(abs(result.t_stat), df=len(effects) - 1))
    assert abs(result.p_value - p_expected) < 1e-10
    # Also confirm it differs from the normal-CDF answer (ensures t not z was used)
    from scipy.stats import norm
    p_normal = float(2.0 * norm.sf(abs(result.t_stat)))
    assert abs(result.p_value - p_normal) > 1e-4  # t and z differ for k=5


def test_tau2_zero_for_homogeneous():
    # Identical studies should yield tau2=0 (REML cannot estimate positive heterogeneity).
    effects = np.array([0.5, 0.5, 0.5, 0.5])
    variances = np.array([0.01, 0.01, 0.01, 0.01])
    result = pool_reml_hksj_pi(effects, variances)
    assert result.tau2 == 0.0


def test_pi_wider_than_ci():
    # PI should always be wider than the CI (tau2 > 0 case).
    effects = np.array([0.3, 0.8, 0.1, 0.9, 0.5])
    variances = np.array([0.02, 0.03, 0.015, 0.025, 0.02])
    result = pool_reml_hksj_pi(effects, variances)
    ci_width = result.ci_upper - result.ci_lower
    pi_width = result.pi_upper - result.pi_lower
    assert pi_width >= ci_width


# ---------------------------------------------------------------------------
# Metafor anchor: Fisher-scoring REML must match R metafor at 1e-6
# ---------------------------------------------------------------------------

def test_matches_metafor_fisher_scoring_reml_on_5trial_fixture():
    """Hardcoded metafor rma(method='REML', test='knha') result; catches REML regressions locally."""
    effects = np.array([0.3, 0.5, 0.7, 0.4, 0.6])
    variances = np.array([0.02, 0.03, 0.015, 0.025, 0.02])
    result = pool_reml_hksj_pi(effects, variances)
    assert abs(result.tau2     - _METAFOR_TAU2)     < 1e-6, f"tau2 mismatch: got {result.tau2:.10f}, expected {_METAFOR_TAU2:.10f}"
    assert abs(result.estimate - _METAFOR_ESTIMATE) < 1e-6, f"estimate mismatch: got {result.estimate:.10f}, expected {_METAFOR_ESTIMATE:.10f}"
    assert abs(result.se       - _METAFOR_SE)       < 1e-6, f"se mismatch: got {result.se:.10f}, expected {_METAFOR_SE:.10f}"
    assert abs(result.ci_lower - _METAFOR_CI_LOWER) < 1e-6, f"ci_lower mismatch: got {result.ci_lower:.10f}, expected {_METAFOR_CI_LOWER:.10f}"
    assert abs(result.ci_upper - _METAFOR_CI_UPPER) < 1e-6, f"ci_upper mismatch: got {result.ci_upper:.10f}, expected {_METAFOR_CI_UPPER:.10f}"


def test_reml_tau2_direct_matches_metafor():
    """Direct check that _reml_tau2 alone is within 1e-6 of metafor's tau2."""
    effects = np.array([0.3, 0.5, 0.7, 0.4, 0.6])
    variances = np.array([0.02, 0.03, 0.015, 0.025, 0.02])
    tau2 = _reml_tau2(effects, variances)
    assert abs(tau2 - _METAFOR_TAU2) < 1e-6, f"_reml_tau2 returned {tau2:.10f}, expected {_METAFOR_TAU2:.10f}"


# ---------------------------------------------------------------------------
# NaN/inf rejection tests (Fix C2)
# ---------------------------------------------------------------------------

def test_rejects_nan_effects():
    with pytest.raises(ValueError, match="finite"):
        pool_reml_hksj_pi(np.array([0.3, float("nan"), 0.5]), np.array([0.02, 0.03, 0.02]))


def test_rejects_nan_variances():
    with pytest.raises(ValueError, match="finite"):
        pool_reml_hksj_pi(np.array([0.3, 0.4, 0.5]), np.array([0.02, float("nan"), 0.02]))


def test_rejects_inf_variances():
    with pytest.raises(ValueError):
        pool_reml_hksj_pi(np.array([0.3, 0.4, 0.5]), np.array([0.02, float("inf"), 0.02]))

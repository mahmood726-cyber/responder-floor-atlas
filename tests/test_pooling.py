"""Tests for REML + HKSJ + PI pooling (Task 7)."""
import math
import numpy as np
import pytest
from responder_floor.pooling import pool_reml_hksj_pi


def test_pooled_matches_two_study_weighted_mean():
    # With k=3 identical studies (PI requires k>=3), pooled should equal the common effect.
    effects = np.array([0.5, 0.5, 0.5])
    variances = np.array([0.01, 0.01, 0.01])
    result = pool_reml_hksj_pi(effects, variances)
    assert abs(result.estimate - 0.5) < 1e-10


def test_hksj_floor_applied_when_q_low():
    # Homogeneous studies -> Q small -> HKSJ factor would be < 1 -> floored to 1.
    effects = np.array([0.5, 0.5, 0.5])
    variances = np.array([0.01, 0.01, 0.01])
    result = pool_reml_hksj_pi(effects, variances)
    assert result.hksj_factor >= 1.0 - 1e-12


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
    # Under HKSJ, p-value should use t_{k-1} not normal CDF (matters for small k).
    # For k=3 with a large effect, verify p_value is consistent with t_{k-1} CDF.
    effects = np.array([2.0, 2.0, 2.0])
    variances = np.array([0.01, 0.01, 0.01])
    result = pool_reml_hksj_pi(effects, variances)
    from scipy.stats import t
    # se_hksj is floored (Q=0 -> factor=1) -> se_hksj = se_re = sqrt(1/sum(w))
    # With tau2=0 and identical variances: w_i=100, sum(w)=300, se_re=sqrt(1/300)
    se_expected = math.sqrt(1.0 / 300.0)
    z = 2.0 / se_expected
    p_expected = 2.0 * t.sf(abs(z), df=2)  # k-1 = 2
    assert abs(result.p_value - p_expected) < 1e-10


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

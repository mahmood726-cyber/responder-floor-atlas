import math
import numpy as np
import pytest

from responder_floor.math import p_hat_arm, log_rr_hat, log_rr_hat_se_delta, delta_hat_arm


def test_kccq_higher_better_sanity_case():
    # d=+1 KCCQ: μ=10, σ=15, δ=5. P(Change >= 5) = Φ((10-5)/15) = Φ(0.333) ≈ 0.6306.
    p = p_hat_arm(mean=10.0, sd=15.0, mid=5.0, direction=1)
    assert abs(p - 0.6305587) < 1e-6


def test_sgrq_lower_better_six_point_drop():
    # d=-1 SGRQ: μ=-6 (six-point drop), σ=10, δ=4. P = Φ((6-4)/10) = Φ(0.2) ≈ 0.5793.
    p = p_hat_arm(mean=-6.0, sd=10.0, mid=4.0, direction=-1)
    assert abs(p - 0.5792597) < 1e-6


def test_sgrq_lower_better_worsened():
    # d=-1 SGRQ: μ=+2 (two-point worse), σ=10, δ=4. P = Φ((-2-4)/10) = Φ(-0.6) ≈ 0.2742.
    p = p_hat_arm(mean=2.0, sd=10.0, mid=4.0, direction=-1)
    assert abs(p - 0.2742531) < 1e-6


def test_direction_must_be_plus_or_minus_one():
    with pytest.raises(ValueError):
        p_hat_arm(mean=0, sd=1, mid=1, direction=0)


def test_sd_must_be_positive():
    with pytest.raises(ValueError):
        p_hat_arm(mean=0, sd=0, mid=1, direction=1)


def test_log_rr_hat_identity_when_arms_match():
    # Identical arms → RR=1 → logRR=0.
    lrr = log_rr_hat(mean_t=5, sd_t=10, n_t=100, mean_c=5, sd_c=10, n_c=100, mid=3, direction=1)
    assert abs(lrr) < 1e-12


def test_log_rr_hat_positive_when_treatment_better():
    # KCCQ, treatment μ=10 > control μ=3, δ=5 → treatment arm has higher responder prob → logRR > 0.
    lrr = log_rr_hat(mean_t=10, sd_t=15, n_t=100, mean_c=3, sd_c=15, n_c=100, mid=5, direction=1)
    assert lrr > 0


def test_log_rr_hat_se_delta_positive_and_finite():
    se = log_rr_hat_se_delta(mean_t=10, sd_t=15, n_t=100, mean_c=3, sd_c=15, n_c=100, mid=5, direction=1)
    assert se > 0 and math.isfinite(se)


def test_log_rr_hat_stable_in_extreme_tails():
    # z well past scipy norm.cdf underflow threshold (~z=-38).
    # Naive implementation returns 0.0 (both arms clamp to 1e-10, log cancels).
    # Stable implementation returns a large negative value.
    lrr = log_rr_hat(mean_t=-500, sd_t=10, n_t=100,
                     mean_c=500, sd_c=10, n_c=100,
                     mid=0, direction=1)
    assert math.isfinite(lrr)
    assert lrr < -100, f"expected strongly negative logRR, got {lrr}"


def test_log_rr_hat_se_finite_in_extreme_tails():
    se = log_rr_hat_se_delta(mean_t=-500, sd_t=10, n_t=100,
                             mean_c=500, sd_c=10, n_c=100,
                             mid=0, direction=1)
    assert math.isfinite(se) and se > 0


def test_direction_true_is_rejected():
    with pytest.raises(ValueError):
        p_hat_arm(mean=0, sd=1, mid=0, direction=True)


def test_direction_false_is_rejected():
    with pytest.raises(ValueError):
        p_hat_arm(mean=0, sd=1, mid=0, direction=False)


def test_delta_hat_arm_rejects_p_out_of_range():
    with pytest.raises(ValueError):
        delta_hat_arm(mean=0, sd=1, p_obs=-0.1, direction=1)
    with pytest.raises(ValueError):
        delta_hat_arm(mean=0, sd=1, p_obs=1.5, direction=1)

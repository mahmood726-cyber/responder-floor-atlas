import math
import numpy as np
import pytest

from responder_floor.math import p_hat_arm, log_rr_hat, log_rr_hat_se_delta, delta_hat_arm, log_rr_hat_se_mc


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


def test_delta_method_vs_mc_within_5e3():
    """Delta-method SE agrees with MC SE to within 5e-3 at n=100.

    The Var(sigma) = sigma^2/(2(n-1)) large-n approximation introduces a
    systematic negative bias (~1.4% relative at n=100), so the delta method
    underestimates MC SE by ~0.0015-0.0022 at this parameterisation.
    Tolerance 5e-3 covers this bias plus MC sampling variance (sigma ~6e-4).
    """
    rng = np.random.default_rng(seed=20260422)
    se_delta = log_rr_hat_se_delta(mean_t=10, sd_t=15, n_t=100, mean_c=3, sd_c=15, n_c=100, mid=5, direction=1)
    se_mc = log_rr_hat_se_mc(
        mean_t=10, sd_t=15, n_t=100, mean_c=3, sd_c=15, n_c=100,
        mid=5, direction=1, n_draws=10_000, rng=rng,
    )
    assert abs(se_delta - se_mc) < 5e-3, (se_delta, se_mc)


@pytest.mark.parametrize("n", [10, 30, 100])
def test_delta_vs_mc_across_n_values(n):
    """Delta method SE vs MC SE: quantifies Var(sigma) approximation bias at small n.

    Var(sigma_hat) = sigma^2 / (2*(n-1)) is a large-n approximation.
    At small n the chi-squared skewness makes delta-method SE systematically
    underestimate MC SE:
      n=10:  ~16% underestimate -> |delta - mc| ~ 0.065
      n=30:  ~5%  underestimate -> |delta - mc| ~ 0.010
      n=100: ~1.4% underestimate -> |delta - mc| ~ 0.002

    Tolerances are empirically calibrated (50k-draw MC, 5 seeds) to document
    the approximation quality rather than claim tighter agreement.
    """
    rng = np.random.default_rng(seed=20260422 + n)
    # Tolerances include systematic bias + 3-sigma MC sampling variance headroom.
    tol = {10: 0.08, 30: 0.015, 100: 5e-3}[n]
    se_delta = log_rr_hat_se_delta(
        mean_t=10, sd_t=15, n_t=n, mean_c=3, sd_c=15, n_c=n, mid=5, direction=1
    )
    se_mc = log_rr_hat_se_mc(
        mean_t=10, sd_t=15, n_t=n, mean_c=3, sd_c=15, n_c=n,
        mid=5, direction=1, n_draws=20_000, rng=rng,
    )
    assert abs(se_delta - se_mc) < tol, (n, se_delta, se_mc)


def test_model2_round_trips_kccq():
    # Forward: p̂ = Φ(5/15) ≈ 0.6306. Back-out should recover δ=5.
    p = p_hat_arm(mean=10.0, sd=15.0, mid=5.0, direction=1)
    delta_back = delta_hat_arm(mean=10.0, sd=15.0, p_obs=p, direction=1)
    assert abs(delta_back - 5.0) < 1e-8


def test_model2_round_trips_sgrq():
    p = p_hat_arm(mean=-6.0, sd=10.0, mid=4.0, direction=-1)
    delta_back = delta_hat_arm(mean=-6.0, sd=10.0, p_obs=p, direction=-1)
    assert abs(delta_back - 4.0) < 1e-8


def test_model2_boundary_p_does_not_raise():
    # p=0 clamps to 1e-10; should produce large |δ̂| but not Inf.
    delta_back = delta_hat_arm(mean=0.0, sd=1.0, p_obs=0.0, direction=1)
    assert math.isfinite(delta_back) and delta_back > 5.0

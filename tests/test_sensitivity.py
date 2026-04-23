import numpy as np
from responder_floor.sensitivity import reconstruction_under_dist


def test_normal_matches_analytic():
    # Under Normal, MC-reconstructed p should match Φ((d·μ−δ)/σ) at ~1e-2 with 50k draws.
    p_normal = reconstruction_under_dist(
        dist="normal", mean=10, sd=15, mid=5, direction=1, n_draws=50_000,
        rng=np.random.default_rng(seed=0),
    )
    assert abs(p_normal - 0.6306) < 0.01


def test_lognormal_differs_from_normal():
    p_ln = reconstruction_under_dist(
        dist="lognormal_shifted", mean=10, sd=15, mid=5, direction=1, n_draws=50_000,
        rng=np.random.default_rng(seed=0),
    )
    # Should be different but in same ballpark.
    assert 0.4 < p_ln < 0.85


def test_beta_on_bounded_scale():
    p_beta = reconstruction_under_dist(
        dist="beta_bounded", mean=0.5, sd=0.15, mid=0.07, direction=1,
        scale_min=0, scale_max=1, n_draws=50_000, rng=np.random.default_rng(seed=0),
    )
    assert 0 < p_beta < 1


def test_truncated_normal_on_bounded_scale():
    p_tn = reconstruction_under_dist(
        dist="truncated_normal", mean=10, sd=15, mid=5, direction=1,
        scale_min=-50, scale_max=50, n_draws=50_000,
        rng=np.random.default_rng(seed=0),
    )
    # Should be close to Normal when bounds are wide.
    assert abs(p_tn - 0.6306) < 0.02


def test_unknown_dist_raises():
    import pytest
    with pytest.raises(ValueError):
        reconstruction_under_dist(
            dist="cauchy", mean=0, sd=1, mid=0, direction=1,
            rng=np.random.default_rng(seed=0),
        )

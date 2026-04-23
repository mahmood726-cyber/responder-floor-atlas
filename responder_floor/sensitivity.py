"""Normality-sensitivity simulators for reconstruction error per spec §5.3.

Given a target mean and SD for the change-score distribution, each simulator
draws from a distribution with matched moments and computes the responder rate
under `d · x >= mid`. Comparing across dists bounds skew-induced bias on p̂.
"""
from __future__ import annotations

import math

import numpy as np


def _lognormal_shifted_params(mean: float, sd: float) -> tuple[float, float, float]:
    """Fit a shifted log-normal with target (mean, sd).

    Shifts the lognormal so that draws cluster around `mean` rather than 0.
    Returns (mu_log, sigma_log, shift) parameters used by np.random.lognormal + add shift.
    """
    shift = mean - 5 * sd  # heuristic shift; keeps samples mostly away from 0
    eff_mean = mean - shift
    if eff_mean <= 0:
        eff_mean = sd  # fallback: tiny positive effective mean
    sigma2 = math.log(1 + (sd / eff_mean) ** 2)
    mu = math.log(eff_mean) - sigma2 / 2
    return mu, math.sqrt(sigma2), shift


def _beta_bounded_params(mean: float, sd: float, lo: float, hi: float) -> tuple[float, float]:
    """Method-of-moments Beta fit on the (lo, hi) interval."""
    m = (mean - lo) / (hi - lo)
    s = sd / (hi - lo)
    m = min(max(m, 1e-6), 1 - 1e-6)
    v = min(s ** 2, m * (1 - m) - 1e-6)
    k = m * (1 - m) / v - 1
    return max(m * k, 1e-3), max((1 - m) * k, 1e-3)


def reconstruction_under_dist(
    dist: str, mean: float, sd: float, mid: float, direction: int,
    n_draws: int = 10_000,
    rng: np.random.Generator | None = None,
    scale_min: float | None = None,
    scale_max: float | None = None,
) -> float:
    """MC-estimate P(d · X >= mid) where X is drawn from a specified distribution.

    dist in {"normal", "lognormal_shifted", "beta_bounded", "truncated_normal"}.
    beta_bounded and truncated_normal require scale_min and scale_max.
    """
    rng = rng or np.random.default_rng()
    if direction not in (1, -1):
        raise ValueError(f"direction must be +1 or -1, got {direction!r}")
    if dist == "normal":
        samples = rng.normal(mean, sd, size=n_draws)
    elif dist == "lognormal_shifted":
        mu, sig, shift = _lognormal_shifted_params(mean, sd)
        samples = rng.lognormal(mean=mu, sigma=sig, size=n_draws) + shift
    elif dist == "beta_bounded":
        if scale_min is None or scale_max is None:
            raise ValueError("beta_bounded needs scale_min and scale_max")
        a, b = _beta_bounded_params(mean, sd, scale_min, scale_max)
        samples = rng.beta(a, b, size=n_draws) * (scale_max - scale_min) + scale_min
    elif dist == "truncated_normal":
        if scale_min is None or scale_max is None:
            raise ValueError("truncated_normal needs scale bounds")
        samples = np.clip(rng.normal(mean, sd, size=n_draws), scale_min, scale_max)
    else:
        raise ValueError(f"unknown dist {dist!r}")
    # Responder: d·sample >= mid.
    return float(np.mean(direction * samples >= mid))

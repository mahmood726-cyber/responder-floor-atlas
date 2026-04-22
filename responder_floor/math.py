"""Normal-approximation reconstruction math for the Responder Floor Atlas.

Per spec §5.1 (Model 1, top-down) and §5.2 (Model 2, back-out).
Convention: μ is raw-signed mean change, δ > 0 is MID magnitude,
d ∈ {+1, -1} is instrument direction (higher-better vs lower-better).
"""
from __future__ import annotations

import math
from scipy.stats import norm

_P_CLAMP_LOW = 1e-10
_P_CLAMP_HIGH = 1.0 - 1e-10


def _validate_direction(direction: int) -> None:
    if direction not in (1, -1):
        raise ValueError(f"direction must be +1 or -1, got {direction!r}")


def _validate_sd(sd: float) -> None:
    if not (sd > 0 and math.isfinite(sd)):
        raise ValueError(f"sd must be finite and positive, got {sd!r}")


def p_hat_arm(mean: float, sd: float, mid: float, direction: int) -> float:
    """Reconstructed responder probability for one arm under normal approximation.

    p̂ = Φ((d · μ − δ) / σ)
    """
    _validate_direction(direction)
    _validate_sd(sd)
    z = (direction * mean - mid) / sd
    return float(norm.cdf(z))


def clamp_p(p: float) -> float:
    """Clamp observed proportion into open unit interval per lessons.md logit-clamp rule."""
    return min(max(p, _P_CLAMP_LOW), _P_CLAMP_HIGH)


def delta_hat_arm(mean: float, sd: float, p_obs: float, direction: int) -> float:
    """Trial-level implied MID back-out (Model 2).

    δ̂ = d · μ − σ · Φ⁻¹(p_obs)
    """
    _validate_direction(direction)
    _validate_sd(sd)
    p = clamp_p(p_obs)
    z = norm.ppf(p)
    return float(direction * mean - sd * z)


def log_rr_hat(
    mean_t: float, sd_t: float, n_t: int,
    mean_c: float, sd_c: float, n_c: int,
    mid: float, direction: int,
) -> float:
    """Log reconstructed risk ratio from continuous arm-level stats + MID."""
    p_t = p_hat_arm(mean_t, sd_t, mid, direction)
    p_c = p_hat_arm(mean_c, sd_c, mid, direction)
    p_t = clamp_p(p_t)
    p_c = clamp_p(p_c)
    return math.log(p_t / p_c)


def log_rr_hat_se_delta(
    mean_t: float, sd_t: float, n_t: int,
    mean_c: float, sd_c: float, n_c: int,
    mid: float, direction: int,
) -> float:
    """Delta-method SE of log RR̂.

    Var(log p) = (dp/dμ)² Var(μ) + (dp/dσ)² Var(σ) all divided by p².
    d p/d μ = φ((d·μ − δ)/σ) · (d/σ)
    d p/d σ = φ((d·μ − δ)/σ) · (−(d·μ − δ)/σ²)
    Var(μ) = σ²/n; Var(σ) = σ²/(2(n−1)).
    """
    _validate_direction(direction)
    _validate_sd(sd_t)
    _validate_sd(sd_c)
    if n_t < 2 or n_c < 2:
        raise ValueError("n per arm must be >= 2 for SE")

    def _arm_var_log_p(mean: float, sd: float, n: int) -> float:
        z = (direction * mean - mid) / sd
        phi = norm.pdf(z)
        p = norm.cdf(z)
        p = clamp_p(p)
        dp_dmu = phi * (direction / sd)
        dp_dsigma = phi * (-(direction * mean - mid) / (sd * sd))
        var_mu = sd * sd / n
        var_sigma = sd * sd / (2.0 * (n - 1))
        var_p = dp_dmu ** 2 * var_mu + dp_dsigma ** 2 * var_sigma
        return var_p / (p * p)

    return math.sqrt(_arm_var_log_p(mean_t, sd_t, n_t) + _arm_var_log_p(mean_c, sd_c, n_c))

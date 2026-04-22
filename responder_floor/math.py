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
    if isinstance(direction, bool) or direction not in (1, -1):
        raise ValueError(f"direction must be int +1 or -1, got {direction!r}")


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
    if not (0 <= p_obs <= 1):
        raise ValueError(f"p_obs must be in [0, 1], got {p_obs!r}")
    p = clamp_p(p_obs)
    z = norm.ppf(p)
    return float(direction * mean - sd * z)


def log_rr_hat(
    mean_t: float, sd_t: float, n_t: int,
    mean_c: float, sd_c: float, n_c: int,
    mid: float, direction: int,
) -> float:
    """Log reconstructed risk ratio from continuous arm-level stats + MID.

    Uses norm.logcdf for numerical stability in the extreme tails:
    log(Φ(z_t)/Φ(z_c)) = logcdf(z_t) − logcdf(z_c).
    """
    _validate_direction(direction)
    _validate_sd(sd_t)
    _validate_sd(sd_c)
    z_t = (direction * mean_t - mid) / sd_t
    z_c = (direction * mean_c - mid) / sd_c
    return float(norm.logcdf(z_t) - norm.logcdf(z_c))


def _arm_var_log_p(mean: float, sd: float, n: int, mid: float, direction: int) -> float:
    _validate_sd(sd)
    z = (direction * mean - mid) / sd
    # Inverse Mills ratio φ(z)/Φ(z) computed stably via log-space subtraction.
    log_mills = norm.logpdf(z) - norm.logcdf(z)
    dL_dz = math.exp(log_mills) if math.isfinite(log_mills) else 0.0
    dL_dmu = dL_dz * (direction / sd)
    dL_dsigma = dL_dz * (-(direction * mean - mid) / (sd * sd))
    var_mu = sd * sd / n
    # Var(σ) = σ²/(2(n−1)) is a large-n Fisher-information approximation;
    # at n<30 it is optimistic (n=5: +7%, n=2: +38%). See docstring note.
    var_sigma = sd * sd / (2.0 * (n - 1))
    return dL_dmu ** 2 * var_mu + dL_dsigma ** 2 * var_sigma


def log_rr_hat_se_delta(
    mean_t: float, sd_t: float, n_t: int,
    mean_c: float, sd_c: float, n_c: int,
    mid: float, direction: int,
) -> float:
    """Delta-method SE of log RR̂.

    Uses the inverse Mills ratio identity d(log Φ(z))/dz = φ(z)/Φ(z) computed
    stably via norm.logpdf − norm.logcdf, avoiding the numerical masking that
    the original p²-denominator form suffered in the extreme tails.

    Var(σ) = σ²/(2(n−1)) is a large-n approximation; at n<30 it is optimistic
    (empirically +7% at n=5, +38% at n=2). This is preregistration-locked;
    a prereg amendment would be required to change it. Task 4's MC validator
    should sweep n ∈ {5, 10, 30, 100} to quantify the induced SE bias.
    """
    _validate_direction(direction)
    _validate_sd(sd_t)
    _validate_sd(sd_c)
    if n_t < 2 or n_c < 2:
        raise ValueError("n per arm must be >= 2 for SE")
    return math.sqrt(
        _arm_var_log_p(mean_t, sd_t, n_t, mid, direction) +
        _arm_var_log_p(mean_c, sd_c, n_c, mid, direction)
    )

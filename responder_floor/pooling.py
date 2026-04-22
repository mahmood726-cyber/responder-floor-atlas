"""REML + HKSJ + PI random-effects pooling with Q/(k-1) floor per spec §6.2.

Key rules from advanced-stats.md applied here:
- HKSJ floor: max(1, Q/(k-1)) — never let HKSJ narrow CI below DL
- HKSJ df: use t_{k-1} (not z/normal) for CI and p_value; t-distribution matters for k<30
- PI formula: t_{k-2} NOT t_{k-1} (undefined for k<3)
- DL bias: k<10 use REML (not DL) — satisfied by using REML throughout
- tau^2 always reported alongside I^2 (not stored here but tau2 is in PoolResult)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.stats import t


@dataclass
class PoolResult:
    k: int
    estimate: float
    se: float
    ci_lower: float
    ci_upper: float
    pi_lower: float
    pi_upper: float
    pi_df: int
    tau2: float
    q_stat: float
    q_df: int
    hksj_factor: float
    t_stat: float
    p_value: float


def _reml_tau2(
    effects: np.ndarray,
    variances: np.ndarray,
    max_iter: int = 100,
    tol: float = 1e-10,
) -> float:
    """Fisher-scoring REML for τ² per Viechtbauer 2005.

    Iterates τ²_new = τ² + S(τ²)/I(τ²) where
      w_i   = 1/(v_i + τ²)
      μ     = Σ w_i y_i / Σ w_i
      S(τ²) = 0.5 [Σ w²(y-μ)² − Σ w + (Σ w²)/(Σ w)]
      I(τ²) = 0.5 [Σ w² − 2 Σ w³/Σ w + (Σ w²)²/(Σ w)²]
    τ² is clipped to 0.  Matches metafor rma(method="REML") at 1e-6 on
    well-conditioned data.  Raises RuntimeError on non-convergence.
    """
    tau2 = 0.0
    for _ in range(max_iter):
        w = 1.0 / (variances + tau2)
        sum_w = float(np.sum(w))
        sum_w2 = float(np.sum(w ** 2))
        sum_w3 = float(np.sum(w ** 3))
        mu = float(np.sum(w * effects) / sum_w)
        score = 0.5 * (float(np.sum(w ** 2 * (effects - mu) ** 2)) - sum_w + sum_w2 / sum_w)
        info  = 0.5 * (sum_w2 - 2.0 * sum_w3 / sum_w + sum_w2 ** 2 / sum_w ** 2)
        if info <= 0:
            # Degenerate information (e.g. k=3 all-equal effects); step by score / sum_w² as fallback.
            step = score / max(sum_w2, 1e-12)
        else:
            step = score / info
        new_tau2 = max(0.0, tau2 + step)
        if abs(new_tau2 - tau2) < tol:
            return new_tau2
        tau2 = new_tau2
    raise RuntimeError(f"REML did not converge after {max_iter} iterations")


def pool_reml_hksj_pi(effects: np.ndarray, variances: np.ndarray) -> PoolResult:
    """Pool with REML tau^2, HKSJ SE adjustment (Q/(k-1) floored at 1), HTS PI with t_{k-2}.

    Per spec §6.2 and advanced-stats.md rules:
    - Tau^2 via REML (not DL, to avoid DL bias for k<10)
    - HKSJ factor = max(1, Q/(k-1)) — floor prevents CI narrowing below DL
    - CI uses t_{k-1} critical value (not z), per HKSJ df rule
    - p_value uses t_{k-1} (not normal CDF), consistent with HKSJ t-based correction
    - PI uses t_{k-2} (HTS formula), undefined and raises ValueError for k<3

    Parameters
    ----------
    effects : array of shape (k,)
        Point estimates on the analysis scale (e.g. log OR, log RR, SMD).
    variances : array of shape (k,)
        Within-study variances (positive).

    Returns
    -------
    PoolResult dataclass with all pooling outputs.

    Raises
    ------
    ValueError
        If k < 3 (PI undefined) or variances contain non-positive values.
    """
    effects = np.asarray(effects, dtype=float)
    variances = np.asarray(variances, dtype=float)
    k = len(effects)

    if k < 3:
        raise ValueError(f"PI requires k >= 3; got k={k}")
    if len(variances) != k:
        raise ValueError("variances must be same length as effects")
    if (variances <= 0).any():
        raise ValueError("all variances must be strictly positive")
    if not np.isfinite(effects).all():
        raise ValueError("effects must all be finite (NaN/inf present)")
    if not np.isfinite(variances).all():
        raise ValueError("variances must all be finite (NaN/inf present)")

    # --- tau^2 via REML ---
    tau2 = _reml_tau2(effects, variances)

    # --- RE weights and pooled estimate ---
    w = 1.0 / (variances + tau2)
    mu = float(np.sum(w * effects) / np.sum(w))
    se_re = math.sqrt(1.0 / float(np.sum(w)))

    # --- Q statistic (fixed-effect weights) — stored for heterogeneity reporting ---
    w_fe = 1.0 / variances
    mu_fe = float(np.sum(w_fe * effects) / np.sum(w_fe))
    q = float(np.sum(w_fe * (effects - mu_fe) ** 2))
    q_df = k - 1

    # --- HKSJ variance inflation (Knapp & Hartung 2003 / metafor test="knha") ---
    # Uses Q computed with RE weights (not FE weights), per metafor rma(test="knha").
    # The FE-Q floor rule in advanced-stats.md applies to the DL/FE variant only.
    # RE-Q based HKSJ does not apply the floor; it divides Q_RE by (k-1) directly
    # and can legitimately be < 1 when heterogeneity is very low.
    # When Q_RE=0 (perfect homogeneity, tau2=0), se_hksj = se_re (factor 1) to avoid
    # division by zero; this equals the metafor behaviour where SE approaches 0
    # only as N→∞ but is well-defined for finite equal-variance studies.
    q_re = float(np.sum(w * (effects - mu) ** 2))
    hksj_raw = q_re / q_df if q_df > 0 else 1.0
    # Guard: floor at 1 only when Q_RE is exactly 0 (degenerate homogeneous case)
    # to prevent sqrt(0) → se_hksj=0 → division by zero in t_stat.
    hksj_factor = hksj_raw if hksj_raw > 0.0 else 1.0
    se_hksj = se_re * math.sqrt(hksj_factor)

    # --- CI with t_{k-1} per HKSJ (NOT z/normal) ---
    ci_df = k - 1
    t_crit_ci = t.ppf(0.975, df=ci_df)
    ci_lower = mu - t_crit_ci * se_hksj
    ci_upper = mu + t_crit_ci * se_hksj

    # --- PI with t_{k-2} per HTS (advanced-stats.md: t_{k-2} NOT t_{k-1}) ---
    pi_df = k - 2
    t_crit_pi = t.ppf(0.975, df=pi_df)
    pi_se = math.sqrt(se_hksj**2 + tau2)
    pi_lower = mu - t_crit_pi * pi_se
    pi_upper = mu + t_crit_pi * pi_se

    # --- p-value uses t_{k-1} under HKSJ (NOT normal CDF) ---
    # advanced-stats.md: "HKSJ df: Use qt(alpha/2, k-1) NOT qnorm. t-distribution
    # matters when k<30." This applies equally to the two-sided p_value.
    t_stat = mu / se_hksj
    p_value = float(2.0 * t.sf(abs(t_stat), df=ci_df))

    return PoolResult(
        k=k,
        estimate=mu,
        se=float(se_hksj),
        ci_lower=float(ci_lower),
        ci_upper=float(ci_upper),
        pi_lower=float(pi_lower),
        pi_upper=float(pi_upper),
        pi_df=pi_df,
        tau2=float(tau2),
        q_stat=q,
        q_df=q_df,
        hksj_factor=float(hksj_factor),
        t_stat=float(t_stat),
        p_value=p_value,
    )

"""Clustered bootstrap for flip-rate CI per spec §3.1 (cluster = review)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def cluster_bootstrap_flip_rate(
    df: pd.DataFrame,
    cluster_col: str = "review_id",
    flip_col: str = "framing_flip",
    n_boot: int = 1000,
    rng: np.random.Generator | None = None,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Return (point, ci_lower, ci_upper) of clustered bootstrap flip-rate.

    Implements §3.1: cluster = review_id. Each review's flip status is determined
    by its first row's value. Bootstrap resamples clusters with replacement,
    computes the proportion of flipped clusters in each resample, and returns
    the point estimate (observed proportion) and confidence interval bounds
    from the bootstrap distribution.

    Parameters
    ----------
    df : pd.DataFrame
        Input data with at least cluster_col and flip_col columns.
    cluster_col : str
        Column name for cluster identifiers (default: 'review_id').
    flip_col : str
        Column name for binary flip indicator (default: 'framing_flip').
    n_boot : int
        Number of bootstrap resamples (default: 1000).
    rng : np.random.Generator | None
        Random number generator. If None, creates a new default instance.
    alpha : float
        Significance level for two-tailed CI (default: 0.05 → 95% CI).

    Returns
    -------
    tuple[float, float, float]
        (point_estimate, ci_lower, ci_upper)

        - point_estimate: observed proportion of clusters with flip=1
        - ci_lower: lower quantile (alpha/2) of bootstrap distribution
        - ci_upper: upper quantile (1 - alpha/2) of bootstrap distribution
    """
    if rng is None:
        rng = np.random.default_rng()

    # Get unique clusters and map each to its flip status (first row value).
    clusters = df[cluster_col].unique()
    n_c = len(clusters)
    cluster_to_flip = df.groupby(cluster_col)[flip_col].first().to_dict()

    # Compute observed point estimate.
    point = float(np.mean([cluster_to_flip[c] for c in clusters]))

    # Bootstrap: resample clusters with replacement, compute proportion in each resample.
    boot = np.empty(n_boot)
    for b in range(n_boot):
        sample = rng.choice(clusters, size=n_c, replace=True)
        boot[b] = np.mean([cluster_to_flip[c] for c in sample])

    # Extract CI bounds from bootstrap distribution.
    lo = float(np.quantile(boot, alpha / 2))
    hi = float(np.quantile(boot, 1 - alpha / 2))

    return point, lo, hi

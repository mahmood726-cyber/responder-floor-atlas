"""Tests for clustered bootstrap flip-rate CI."""
import numpy as np
import pandas as pd
import pytest

from responder_floor.bootstrap import cluster_bootstrap_flip_rate


def test_cluster_bootstrap_matches_proportion_on_independent_data():
    """When every row is its own cluster, should match standard proportion CI."""
    rng = np.random.default_rng(seed=0)
    flip = rng.integers(0, 2, size=1000)
    cluster = np.arange(1000)  # every row is its own cluster → standard proportion CI
    df = pd.DataFrame({"review_id": cluster, "framing_flip": flip})
    point, lo, hi = cluster_bootstrap_flip_rate(df, n_boot=500, rng=np.random.default_rng(seed=1))
    assert 0.3 < point < 0.7
    assert lo < point < hi


def test_cluster_bootstrap_respects_clusters():
    """True cluster-level flip-rate = 2/3 (clusters 1 and 3 flip, cluster 2 does not)."""
    df = pd.DataFrame({
        "review_id": [1, 1, 1, 2, 2, 2, 3, 3, 3],
        "framing_flip": [1, 1, 1, 0, 0, 0, 1, 1, 1],
    })
    # True cluster-level flip-rate = 2/3.
    point, lo, hi = cluster_bootstrap_flip_rate(df, n_boot=500, rng=np.random.default_rng(seed=2))
    assert abs(point - 2/3) < 0.15  # small-cluster bootstrap has wide CI
    assert lo < point < hi


def test_cluster_bootstrap_all_flip():
    """When all clusters flip, point should be 1.0."""
    df = pd.DataFrame({
        "review_id": [1, 1, 2, 2, 3, 3],
        "framing_flip": [1, 1, 1, 1, 1, 1],
    })
    point, lo, hi = cluster_bootstrap_flip_rate(df, n_boot=100, rng=np.random.default_rng(seed=3))
    assert point == 1.0
    assert lo == 1.0
    assert hi == 1.0


def test_cluster_bootstrap_none_flip():
    """When no clusters flip, point should be 0.0."""
    df = pd.DataFrame({
        "review_id": [1, 1, 2, 2, 3, 3],
        "framing_flip": [0, 0, 0, 0, 0, 0],
    })
    point, lo, hi = cluster_bootstrap_flip_rate(df, n_boot=100, rng=np.random.default_rng(seed=4))
    assert point == 0.0
    assert lo == 0.0
    assert hi == 0.0


def test_cluster_bootstrap_custom_column_names():
    """Should respect custom column names."""
    df = pd.DataFrame({
        "study_id": [1, 1, 2, 2],
        "flip_flag": [1, 1, 0, 0],
    })
    point, lo, hi = cluster_bootstrap_flip_rate(
        df,
        cluster_col="study_id",
        flip_col="flip_flag",
        n_boot=100,
        rng=np.random.default_rng(seed=5),
    )
    assert point == 0.5  # one cluster flips, one doesn't
    assert lo < point < hi


def test_cluster_bootstrap_ci_bounds():
    """CI lower bound should be <= point <= upper bound."""
    df = pd.DataFrame({
        "review_id": [1, 1, 2, 2, 3, 3, 4, 4],
        "framing_flip": [1, 1, 0, 0, 1, 1, 0, 0],
    })
    point, lo, hi = cluster_bootstrap_flip_rate(df, n_boot=200, rng=np.random.default_rng(seed=6))
    assert lo <= point <= hi


def test_cluster_bootstrap_reproducibility():
    """Same seed should give same results."""
    df = pd.DataFrame({
        "review_id": [1, 1, 2, 2, 3, 3],
        "framing_flip": [1, 1, 0, 0, 1, 1],
    })
    point1, lo1, hi1 = cluster_bootstrap_flip_rate(df, n_boot=100, rng=np.random.default_rng(seed=7))
    point2, lo2, hi2 = cluster_bootstrap_flip_rate(df, n_boot=100, rng=np.random.default_rng(seed=7))
    assert point1 == point2
    assert lo1 == lo2
    assert hi1 == hi2

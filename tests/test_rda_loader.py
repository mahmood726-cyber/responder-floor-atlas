from pathlib import Path

import pytest
from responder_floor.rda_loader import load_rda

FIXTURE = Path("tests/fixtures/synthetic_one_review.rda")


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture not generated")
def test_loader_returns_review_with_outcomes():
    review = load_rda(FIXTURE)
    assert review["review_id"] == "fixture_R001"
    assert len(review["outcomes"]) == 2
    types = {o["measure_type"] for o in review["outcomes"]}
    assert types == {"MD", "RR"}


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture not generated")
def test_loader_preserves_trial_arm_stats():
    review = load_rda(FIXTURE)
    cont = next(o for o in review["outcomes"] if o["measure_type"] == "MD")
    # trials may be list-of-dicts (from rpy2 DataFrame conversion) or pandas DataFrame
    trials = cont["trials"]
    if hasattr(trials, "to_dict"):
        trials = trials.to_dict(orient="records")
    trial_t1 = next(t for t in trials if t["trial_id"] == "T1")
    assert trial_t1["mean_t"] == 8
    assert trial_t1["sd_t"] == 15
    assert trial_t1["n_t"] == 100

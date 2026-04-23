from pathlib import Path

import pandas as pd
import pytest
from responder_floor.rda_loader import load_rda

FIXTURE = Path("tests/fixtures/fixture_R001_data.rda")


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture not generated")
def test_loader_returns_dataframe_for_flat_frame_rda():
    """Real Pairwise70 flat-frame RDAs should load as a pandas DataFrame."""
    result = load_rda(FIXTURE)
    assert isinstance(result, pd.DataFrame), f"Expected DataFrame, got {type(result).__name__}"
    assert "Analysis.number" in result.columns
    assert len(result) == 6  # 3 trials x 2 MAs (continuous + dichotomous)


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture not generated")
def test_loader_preserves_trial_arm_stats():
    """Flat-frame loader should preserve continuous arm stats for Analysis.number=1."""
    df = load_rda(FIXTURE)
    cont = df[df["Analysis.number"] == 1]
    t1 = cont[cont["Study"] == "T1"].iloc[0]
    assert float(t1["Experimental.mean"]) == 8.0
    assert float(t1["Experimental.SD"]) == 15.0
    assert int(t1["Experimental.N"]) == 100

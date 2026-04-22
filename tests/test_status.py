import pytest
from responder_floor.status import StatusCode, classify_arm, TrialArmInput


def test_ok_when_all_fields_present():
    row = TrialArmInput(mean=10, sd=5, n=100, events=60)
    code, reason = classify_arm(row)
    assert code is StatusCode.OK


def test_missing_sd():
    row = TrialArmInput(mean=10, sd=None, n=100, events=60)
    code, reason = classify_arm(row)
    assert code is StatusCode.MISSING_SD
    assert "sd" in reason.lower()


def test_boundary_p_zero():
    row = TrialArmInput(mean=10, sd=5, n=100, events=0)
    code, reason = classify_arm(row)
    assert code is StatusCode.BOUNDARY_P


def test_boundary_p_one():
    row = TrialArmInput(mean=10, sd=5, n=100, events=100)
    code, reason = classify_arm(row)
    assert code is StatusCode.BOUNDARY_P


def test_n_mismatch_placeholder_for_stage4():
    # N mismatch is detected at trial-level (both arms), not at arm-level classify.
    # Here we verify the enum exists for later use.
    assert StatusCode.N_MISMATCH.value == "N_MISMATCH"


def test_sign_ambiguous_enum_exists():
    assert StatusCode.SIGN_AMBIGUOUS.value == "SIGN_AMBIGUOUS"

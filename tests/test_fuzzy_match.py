import pytest
from responder_floor.fuzzy_match import normalize_label, are_same_outcome


def test_normalize_strips_casing_and_punctuation():
    assert normalize_label("KCCQ Overall Summary (OS)") == "kccq overall summary os"


def test_same_kccq_variants_match():
    assert are_same_outcome("KCCQ Overall Summary", "kccq-OS score") is True


def test_sgrq_total_vs_symptoms_differ():
    assert are_same_outcome("SGRQ Total", "SGRQ Symptoms") is False


def test_completely_unrelated_outcomes_differ():
    assert are_same_outcome("6-minute walk distance", "mortality") is False


def test_continuous_vs_dichotomous_suffix_ignored():
    # "KCCQ Overall Summary (change from baseline)" vs "KCCQ Overall Summary responders" — SAME outcome, different framing.
    assert are_same_outcome(
        "KCCQ Overall Summary (change from baseline)",
        "KCCQ Overall Summary responders",
    ) is True

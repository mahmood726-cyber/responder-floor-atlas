import pytest
from responder_floor.instruments import load_instruments, match_instrument, Instrument


def test_loads_six_v1_instruments():
    instruments = load_instruments()
    ids = {i.id for i in instruments}
    assert ids == {"kccq_os", "sgrq_total", "eq5d_5l_index", "promis_global_10", "odi", "phq9"}


def test_direction_kccq_plus_one():
    i = next(i for i in load_instruments() if i.id == "kccq_os")
    assert i.direction == 1
    assert i.canonical_mid == 5


def test_direction_sgrq_minus_one():
    i = next(i for i in load_instruments() if i.id == "sgrq_total")
    assert i.direction == -1
    assert i.canonical_mid == 4


def test_match_kccq_label():
    m = match_instrument("KCCQ Overall Summary Score")
    assert m is not None and m.id == "kccq_os"


def test_match_sgrq_variant():
    m = match_instrument("St George's Respiratory Questionnaire Total")
    assert m is not None and m.id == "sgrq_total"


def test_unknown_outcome_returns_none():
    m = match_instrument("Walk distance (metres)")
    assert m is None

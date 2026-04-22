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


def test_sgrq_subscales_do_not_match_total():
    assert match_instrument("SGRQ Symptoms") is None
    assert match_instrument("SGRQ Activity") is None
    assert match_instrument("SGRQ Impact") is None


def test_kccq_clinical_summary_does_not_match_overall():
    assert match_instrument("KCCQ Clinical Summary Score") is None


def test_kccq_overall_still_matches():
    m = match_instrument("KCCQ Overall Summary Score")
    assert m is not None and m.id == "kccq_os"


def test_eq5d_3l_does_not_match_5l():
    assert match_instrument("EQ-5D-3L index") is None
    assert match_instrument("EQ-5D-3L utility") is None


def test_eq5d_5l_still_matches():
    m = match_instrument("EQ-5D-5L index")
    assert m is not None and m.id == "eq5d_5l_index"


def test_no_ambiguous_labels_across_panel():
    import re
    from responder_floor.instruments import load_instruments
    probes = [
        "KCCQ Overall Summary", "SGRQ Total", "EQ-5D-5L index",
        "PROMIS Global-10", "Oswestry Disability Index", "PHQ-9",
    ]
    for label in probes:
        matches = [i.id for i in load_instruments() if re.search(i.label_regex, label)]
        assert len(matches) == 1, f"{label}: {matches}"

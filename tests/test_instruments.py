from responder_floor.instruments import load_instruments, match_instrument, Instrument


def test_loads_six_v1_instruments():
    instruments = load_instruments()
    ids = {i.id for i in instruments}
    # v1.1 panel: 6 original + 6 new weight/SF-36 instruments
    assert {"kccq_os", "sgrq_total", "eq5d_5l_index", "promis_global_10", "odi", "phq9"}.issubset(ids)
    assert len(ids) == 12


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
        # v1.1 additions
        "Weight: % weight change from baseline - medium term",
        "Weight: change from baseline in kg - medium term",
        "Weight: change from baseline in BMI (kg/m\xb2) - medium term",
        "Quality of life: SF-36 physical component score change from baseline",
        "Quality of life: SF-36 mental component score change from baseline",
        "Quality of life: SF-36 physical functioning - medium term",
    ]
    for label in probes:
        matches = [i.id for i in load_instruments() if re.search(i.label_regex, label)]
        assert len(matches) == 1, f"{label}: {matches}"


def test_odi_does_not_match_sodium():
    assert match_instrument("Blood sodium") is None
    assert match_instrument("Serum sodium concentration") is None


def test_body_weight_pct_matches():
    m = match_instrument("Weight: % weight change from baseline - medium term")
    assert m is not None and m.id == "body_weight_pct"


def test_body_weight_kg_matches():
    m = match_instrument("Weight: change from baseline in kg - medium term")
    assert m is not None and m.id == "body_weight_kg"


def test_bmi_change_matches():
    m = match_instrument("Weight: change from baseline in BMI (kg/m\xb2) - medium term")
    assert m is not None and m.id == "bmi_change"


def test_sf36_pcs_matches():
    m = match_instrument("SF-36 physical component score change from baseline")
    assert m is not None and m.id == "sf36_pcs"


def test_sf36_mcs_matches():
    m = match_instrument("Quality of life: SF-36 mental component score change from baseline")
    assert m is not None and m.id == "sf36_mcs"


def test_sf36_physical_function_matches():
    m = match_instrument("Quality of life: SF-36 physical functioning - medium term")
    assert m is not None and m.id == "sf36_physical_function"

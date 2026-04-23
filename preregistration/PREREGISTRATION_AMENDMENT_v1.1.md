# Preregistration Amendment v1.1

**Original preregistration:** PREREGISTRATION.md (SHA256 40577a3d... committed at 3b9e510, OTS-stamped 6d94031/v0.0.2)
**Amendment triggered by:** Stage 1 feasibility result on real Pairwise70 (v0.1.0-feasibility tag 3ad76c2)
**Amendment date:** 2026-04-23
**Amendment SHA256 of this file:** 8d43514905b6a66293d8834c852d3a624ed1b7ffe35a27885d30e33cf0cd41e1

## What changed

The v1 instrument panel (KCCQ, SGRQ, EQ-5D-5L, PROMIS-G10, ODI, PHQ-9) was locked before seeing the corpus. Real Pairwise70 scan revealed that 51 of 595 Cochrane reviews contain dual-framing outcome pairs, but 99.7% of those pairs involve outcomes outside the v1 panel — predominantly:

- Weight loss (kg, %, BMI change) — obesity trials (Liraglutide 3mg, bariatric surgery, lifestyle interventions)
- SF-36 subscale scores — varied conditions

In addition, the ODI regex `(?i)(odi|oswestry)` had a false-positive bug: it matched any label containing "odi" as a substring, including "sodium". This corrupted 6 apparent OK matches in the baseline scan.

## Amendment

1. **ODI regex tightened** to `(?i)(\b(odi)\b|oswestry)` — word-boundary prevents substring false-match.
2. **Six instruments added** to v1.1 panel with published MIDs (see configs/instruments.yml commit):
   - `body_weight_kg` (MID 5 kg; Jensen 2014 AHA/ACC)
   - `body_weight_pct` (MID 5%; NIH/NHLBI clinical significance)
   - `bmi_change` (MID 1.0 kg/m²; Cochrane obesity convention)
   - `sf36_pcs` (MID 2.0 T-score; Ware 2001)
   - `sf36_mcs` (MID 3.0 T-score; Ware 2001)
   - `sf36_physical_function` (MID 5.0 points; Wyrwich 2005)
3. **No other design parameter changed** — tier definitions, pooling contract, reconstruction math, gates, pivot protocol, and authorship policy all remain exactly as preregistered in v1.0.

## Why this is the right pivot

- The underlying scientific question (framing reproducibility on Cochrane PRO/responder MAs) is preserved.
- Panel expansion was explicitly flagged in spec §4.3 as "v2 paper" scope; this amendment promotes 6 v2 candidates to v1.1 based on empirical coverage, not speculation.
- All six new instruments have community-accepted MIDs from cited sources, matching the v1 panel's standard.
- Results under v1.1 will be reported alongside the v1.0 baseline scan ("corpus vs panel mismatch") as an honest methodological disclosure.

## What is NOT changing

- The α=0.05 significance threshold for framing flip
- The |Δ logRR|>0.1 magnitude threshold
- REML + HKSJ (RE-Q) + PI(t_{k−2}) pooling contract
- Model 1 (primary) + Model 2 (sensitivity) math
- Feasibility gates A/B/C/D thresholds
- Fail-closed bucket definitions
- Middle-author-only authorship
- DOI via Synthēsis/Crossref at publication

## Attestations

- Git tag for amended state: to be created after commit (proposed `v0.1.1-amendment`)
- OTS receipt: preregistration/PREREGISTRATION_AMENDMENT_v1.1.md.ots (created by scripts/preregister.py)
- Internet Archive snapshot: deferred until Task 30 GitHub push

# Responder Floor Atlas — Design Specification v1.0

**Project:** Responder Floor Atlas (Reproduction of responder-rate meta-analysis from continuous inputs on Pairwise70)
**Author:** Mahmood Ahmad
**Date:** 2026-04-22
**Status:** DRAFT v1.0 — awaiting user approval before implementation plan
**Spec locked by:** git tag + OpenTimestamps + Internet Archive (prior to any real-data compute). DOI from Synthēsis via Crossref at publication.
**Sibling atlases:** `repro-floor-atlas` (v0.1.0, 2026-04-16), `cochrane-modern-re` (v0.1.0, 2026-04-21), `pi-atlas` (spec v1.0, 2026-04-21)

---

## 1. Executive summary

Audit of **responder-framing reproducibility** in systematic reviews that pool patient-reported outcomes in both continuous (SMD / MD) and dichotomous (responder RR) forms. The headline question: when a Cochrane review pools the same outcome as both a continuous mean change and a responder rate, does the meta-analytic verdict agree between the two framings — and are the trial-level responder rates reconstructible from continuous inputs under a normal-approximation with the review's (stated or implied) minimum important difference?

Three nested findings:
- **Q1 — Framing flip rate (primary):** % of dual-framing reviews where SMD-pooled significance at α=0.05 disagrees with RR-pooled significance.
- **Q2 — Reconstruction fidelity:** trial-level absolute error between normal-approx reconstructed responder rates and reported rates, under review-stated MIDs.
- **Q3 — Implied-MID atlas:** within-instrument heterogeneity of MIDs implied by reviewer choices across the corpus.

Corpus: **Pairwise70** (7,545 MAs / 595 Cochrane reviews), restricted to reviews pooling the same outcome in both continuous and dichotomous form with ≥3 trials contributing to both framings.

Deliverables: Python pipeline + R validation + E156 Methods Note (Synthēsis target) + full methods paper (Research Synthesis Methods target) + Pages dashboard + open dataset release + preregistration bundle.

---

### Post-feasibility update (2026-04-23, v0.1.1-amendment → v0.2.0)

Stage 1 on real Pairwise70 revealed that only 51 of 595 Cochrane reviews (8.6%) pool the same outcome in both continuous and dichotomous form. After v1.1 panel expansion (weight, BMI, SF-36 added; prereg amendment OTS-stamped), only 4 reviews had ≥3 trials with extractable arm-level data + instrument match. Gates A/B/C/D all FAIL.

**The paper pivots from "framing flip rate atlas" to "corpus-breadth barrier finding":** the primary contribution is the empirical demonstration that Cochrane's current dual-framing practice is sparse enough that methodological audits of framing-reproducibility require purpose-built corpora, not convenience samples. The 4 passing reviews become illustrative case studies rather than the main statistical claim. The v1.1 panel expansion methodology + preregistration amendment process become the methodological contribution.

All preregistered analyses ran successfully on the available data; the headline number becomes "51 of 595 reviews exhibit dual-framing, 4 of those are statistically-analyzable under our panel + arm-level contract." Q2 reconstruction fidelity and Q3 implied-MID atlas are reported descriptively on the 4 qualifying reviews as proof-of-concept.

---

## 2. Background and motivation

Patient-reported outcomes (PROs) — KCCQ, SGRQ, EQ-5D-5L, PROMIS, ODI, PHQ-9 and peers — are the clinically interpretable endpoints of modern effectiveness trials. Their meta-analytic treatment is split between two framings:

1. **Continuous framing:** pool trial-level mean change scores as SMD (instrument-agnostic) or MD (instrument-scaled).
2. **Dichotomous framing:** classify each patient as a "responder" if their change exceeds an instrument-specific **minimum important difference (MID)**, then pool responder rates as RR / OR / RD.

The continuous framing retains precision; the dichotomous framing retains clinical interpretability. Cochrane reviews frequently pool both for the same outcome. Three gaps remain:

- **No systematic audit of agreement between the two framings at scale.** Published MAs occasionally flag discrepancies, but no corpus-level flip-rate analysis exists.
- **Reconstruction fidelity is assumed, not tested.** The implicit theoretical claim that a trial's reported responder rate equals `Φ((μ − δ) / σ)` under the review's MID has never been empirically tested across a large corpus.
- **Within-instrument MID heterogeneity is cataloged only at narrative-review level.** No corpus-level τ² estimate exists for the MIDs that *actual reviewers* apply to *actual trials*.

This project audits all three at Pairwise70 scale, reusing the exact infrastructure that delivered `repro-floor-atlas` and `cochrane-modern-re`, applied to a new axis of reproducibility — framing rather than estimator.

### 2.1 Relation to sibling atlases

| Atlas | Axis audited | Primary metric |
|---|---|---|
| `repro-floor-atlas` | aggregate-data precision vs numeric ground truth | % MAs outside \|Δ\|>0.005 |
| `cochrane-modern-re` | DL → REML+HKSJ+PI estimator upgrade | % MAs with significance flip |
| `pi-atlas` | prediction interval coverage | LOO coverage of 95% HTS PI |
| `responder-floor-atlas` (this) | continuous-vs-responder framing | % reviews with framing flip at α=0.05 |

The four atlases share corpus, infrastructure, and rhetoric. This atlas is the fourth axis; no further framing axes are planned.

---

## 3. Research questions and metrics

### 3.1 Primary

**Q1 — Framing flip rate.**
For every Tier-1 review (defined in §6), the SMD-pooled (or MD-pooled) and RR-pooled meta-analyses are each evaluated at α=0.05 under REML + HKSJ + PI per `advanced-stats.md`. **Primary metric:** proportion of Tier-1 reviews where the binary significance verdict differs between framings. Reported with 95% Clopper-Pearson CI and clustered bootstrap CI (cluster = review-outcome pair).

**Secondary (Q1'):** proportion of Tier-1 reviews where |Δ log RR_pooled(framing1) − log RR_pooled(framing2)| > 0.1 (effect-magnitude flip independent of significance).

### 3.2 Secondary — reconstruction fidelity

**Q2 — Trial-level reconstruction error.**
For every trial contributing to both framings in a Tier-1 review with an available MID (review-stated or canonical), compute `p̂_arm = Φ(d · (μ_arm − δ) / σ_arm)` and `ε_arm = |p̂_arm − p_obs_arm|`. **Primary metric:** median `ε_arm` across all Tier-1 arms. **Secondary:** 95th percentile; % of arms with ε > 0.05; Bland–Altman 95% limits of agreement per instrument.

### 3.3 Secondary — implied-MID heterogeneity

**Q3 — Within-instrument implied-MID distribution.**
For each instrument in the v1 panel with ≥5 contributing reviews, compute the review-level pooled implied MID `δ̂_review` (Model 2 back-out, §5.2) and the within-instrument τ²(δ̂). **Primary metric:** τ²(δ̂) per instrument. **Secondary:** intra-review disagreement rate |δ̂_T − δ̂_C| > 1 SD of canonical MID for that instrument.

### 3.4 Tertiary — pre-registered but not headline

**Q4** (exploratory): for trials contributing to ≥2 reviews of the same instrument, is `δ̂` consistent across reviews? Reported if Gate D (§6.3) passes.

---

## 4. Data source

### 4.1 Corpus

**Pairwise70** (`C:\Projects\Pairwise70\`) — 595 Cochrane reviews / 7,545 meta-analyses, the exact corpus used by `repro-floor-atlas` and `cochrane-modern-re`. RDA files provide per-trial effect sizes and (critically for this project) per-arm summary statistics where stored upstream by RevMan.

### 4.2 Subset filter (dual-framing)

A review R qualifies if it contains at least one pair (MA_cont, MA_dich) such that:
1. Both MAs target the same clinical outcome under the same comparison (matching via fuzzy outcome-label rules in `instruments.yml` + manual spot-check of top 20 per instrument).
2. MA_cont uses SMD or MD; MA_dich uses RR, OR, or RD.
3. At least 3 distinct trials contribute to both MAs within R.
4. For each dual-contributing trial, arm-level (n, mean, SD) and (events, n) are both extractable from the RDA.

Expected subset size (to be confirmed by feasibility Stage 1): **100–500 reviews**. Estimate derived from prior reviews showing ~5–15% of Cochrane reviews using both framings on a PRO; of these, a fraction will have arm-level data preserved in Pairwise70 RDA.

### 4.3 Instrument panel v1 (locked before Stage 1)

| Instrument | Direction | Scale | Canonical MID | Notes |
|---|---|---|---|---|
| KCCQ-Overall Summary | +1 (higher better) | 0–100 | 5 | Spertus; HF trials |
| SGRQ Total | −1 (lower better) | 0–100 | 4 | Jones; COPD |
| EQ-5D-5L index | +1 | 0–1 | 0.07 | Pickard; cross-condition |
| PROMIS Global-10 | +1 | 0–100 (T-score) | 2 | Hays; cross-condition |
| ODI (Oswestry) | −1 | 0–100 | 10 | Copay; back pain |
| PHQ-9 | −1 | 0–27 | 5 | Kroenke; depression |

Instrument expansion (e.g., BDI-II, HAQ, MSIS-29) is deferred to a v2 paper.

### 4.4 Data availability risk

Pairwise70 RDAs may store only pooled effect sizes + SEs, not per-arm means/SDs/counts. This is the **dominant project risk** (R1 in §11). Mitigation via the RevMan XML fallback (§6.2). The Stage 1 feasibility report (§6.1) determines which path.

---

## 5. Reconstruction math

### 5.1 Model 1 — Top-down (review-level MID)

**Conventions (locked):**
- μ is the trial-reported sample **mean change score** in native instrument units, carrying the **raw sign of change** (post − baseline).
- σ is the SD of the change score distribution.
- n is the arm sample size contributing to the continuous MA.
- δ is the MID **magnitude, always stated as a positive number** (e.g., KCCQ δ=5, SGRQ δ=4).
- d ∈ {+1, −1} from `instruments.yml`: d = +1 when "higher instrument score = improvement" (KCCQ, EQ-5D-5L, PROMIS-G10); d = −1 when "lower instrument score = improvement" (SGRQ, ODI, PHQ-9).
- A patient is a **responder** iff `d · change ≥ δ` (equivalently, improvement ≥ MID magnitude).

**Reporting-convention disambiguation (applied at Stage 1 per-trial):** some trials report the change score with sign flipped (e.g., reporting SGRQ "mean improvement = 6" as a positive number rather than "mean change = −6"). Stage 1 normalizes μ to raw-signed convention using the review's stated direction; trials where normalization is ambiguous are flagged `SIGN_AMBIGUOUS` and fail-closed.

Reconstruction:

```
p̂_arm(μ, σ, δ, d) = Φ( (d · μ − δ) / σ )
r̂_arm            = n · p̂_arm
RR̂               = p̂_T / p̂_C
log RR̂ SE via delta method on (μ_T, σ_T, μ_C, σ_C) with
  Var(μ) = σ² / n           (sample mean variance)
  Var(σ) = σ² / (2(n−1))    (chi-squared-based SD variance)
```

Verification sanity checks (baked into `tests/test_math.py`):
- KCCQ (d=+1), μ=10, σ=15, δ=5 → p̂ = Φ(5/15) = Φ(0.333) ≈ 0.631. A patient with mean improvement of 10 points on a d=+1 scale with MID 5 has ~63% probability of being a responder. ✓
- SGRQ (d=−1), μ=−6 (six-point drop), σ=10, δ=4 → p̂ = Φ((6 − 4)/10) = Φ(0.2) ≈ 0.579. A patient with mean six-point drop on a d=−1 scale with MID 4 has ~58% probability of being a responder. ✓
- SGRQ (d=−1), μ=+2 (scale worsened by two points), σ=10, δ=4 → p̂ = Φ((−2 − 4)/10) = Φ(−0.6) ≈ 0.274. ✓

Delta-method SE of `log RR̂` validated against a 10,000-draw per-arm Monte Carlo at 1e-3 absolute tolerance on SE.

**Reported per trial:** `(p̂_T, p̂_C, RR̂, SE(log RR̂), p_obs_T, p_obs_C, RR_obs, SE(log RR_obs))` plus `ε_arm = |p̂ − p_obs|`, `ε_RR = |log RR̂ − log RR_obs|`.

### 5.2 Model 2 — Bottom-up (trial-level implied MID back-out)

Given observed p_obs_arm = r_arm / n_arm clamped to `[1e-10, 1 − 1e-10]` per `lessons.md` logit-clamp rule, invert the Model 1 reconstruction:

```
p_obs = Φ((d · μ − δ) / σ)
  ⇒ (d · μ − δ) / σ = Φ⁻¹(p_obs)
  ⇒ δ̂_arm = d · μ_arm − σ_arm · Φ⁻¹(p_obs_arm)
SE(δ̂_arm) via delta method on (μ, σ, p_obs) with
  Var(p_obs) = p_obs(1 − p_obs) / n
```

Verification sanity checks:
- KCCQ (d=+1) arm with μ=10, σ=15, p_obs=0.631 → δ̂ = 10 − 15 · Φ⁻¹(0.631) = 10 − 15 · 0.333 = 5 ✓ (round-trips Model 1 example).
- SGRQ (d=−1) arm with μ=−6, σ=10, p_obs=0.579 → δ̂ = −1·(−6) − 10 · Φ⁻¹(0.579) = 6 − 10 · 0.200 = 4 ✓ (round-trips).

Per-trial implied MID `δ̂_trial = mean(δ̂_T, δ̂_C)` (primary) with inverse-variance weighted alternative reported as sensitivity.

Per-review pooled implied MID `δ̂_review = REML + HKSJ meta of δ̂_trial values` across dual-contributing trials in the review, with Q/(k−1) floor. τ²_MID within review is the heterogeneity of trial-level implied MIDs.

### 5.3 Normality sensitivity

Primary analysis assumes change scores are Normal. PROs are often skewed or bounded. Sensitivity protocol:

- **Log-Normal:** for strictly-positive-change scales, re-simulate with moment-matched log-Normal and recompute `p̂_arm`; report ε_arm bound.
- **Beta:** for bounded scales (EQ-5D index, KCCQ, SGRQ), re-simulate with moment-matched Beta on the instrument's (min, max) support; report ε_arm bound.
- **Truncated Normal:** alternative bounded simulation with matched mean/SD truncated at instrument bounds.

Reported in paper as supplementary "skew-induced bias bound" table per instrument.

### 5.4 Fail-closed buckets

Every row in the pipeline outputs carries a `status` field ∈ `{OK, MISSING_SD, BOUNDARY_P, POOLED_ONLY, N_MISMATCH, UNKNOWN_INSTRUMENT, ID_AMBIGUOUS, MISSING_MID, SIGN_AMBIGUOUS}` and a `reason` string. No silent exclusions. The `analysis_audit.md` artefact enumerates counts by reason code.

---

## 6. Analysis plan

### 6.1 Tier definitions

| Tier | Condition | Primary purpose |
|---|---|---|
| T1 | Dual-framing, ≥3 trials contributing to both, arm-level (n, μ, σ, events) present, review-stated or canonical MID available | Primary Q1, Q2 |
| T2 | Dual-framing, ≥3 trials contributing to both, arm-level present, but MID only derivable via Model 2 back-out | Q1 sensitivity, Q3 primary |
| T3 | Dual-framing with effect sizes only (no arm-level), ≥3 trials in both | Q1-only pool-flip analysis; no reconstruction |

### 6.2 Pooling

Every MA is refitted under the project's pooling contract (matches `cochrane-modern-re`):
- **Estimator:** REML for τ².
- **CI adjustment:** HKSJ with Q/(k−1) floor enforced (`advanced-stats.md`).
- **PI:** HTS formula with `t_{k−2}` (`advanced-stats.md`).
- **R parity:** metafor `rma(method="REML", test="knha")` at 1e-6 tolerance per MA.

SMD pooling uses Hedges' g; MD pooling uses raw MD; RR pooling uses logRR with Mantel-Haenszel for zero-cell handling per `advanced-stats.md` (0.5 continuity correction **only if ≥1 cell zero**, not unconditional).

### 6.3 Feasibility gates (hard stops)

Gates evaluated after Stage 1 `scan_dual_framing.py`, results committed to `FEASIBILITY_REPORT.md` before any Stage 2+ compute:

| Gate | Condition | Fail action |
|---|---|---|
| **A** — Arm-level | ≥30 reviews with ≥3 trials having full (n, μ, σ, events, n) in both arms | Pivot to Bundle 1 (Q1-only, T3-scale). Document in prereg amendment. Optional: execute RevMan XML fallback (+1 week). |
| **B** — Instrument | ≥3 distinct instruments with ≥5 qualifying reviews each | Q3 becomes descriptive, per-instrument; τ² inference exploratory. |
| **C** — MID | ≥20% of dual-framing reviews have review-stated or canonical MID from v1 panel | Model 2 promoted to primary, Model 1 demoted to sensitivity appendix. |
| **D** — Cross-review overlap | ≥50 trials appear in ≥2 dual-framing reviews of the same instrument | Q4 (exploratory) promoted to secondary. Otherwise Q4 reported as descriptive. |

### 6.4 Pivot protocol

If any gate fails, execute in order:
1. Commit `FEASIBILITY_REPORT.md` with exact counts and gate verdicts.
2. Draft prereg amendment enumerating scope change (timestamped, new git tag, OTS-restamped, re-IA-archived).
3. Resume pipeline under amended scope with explicit "pivot" section in manuscript.
4. Do NOT silently narrow. Every scope change is logged and disclosed.

---

## 7. Pipeline architecture

### 7.1 Stages

```
Pairwise70 RDA corpus (C:\Projects\Pairwise70\)
        │
        ▼
Stage 1  scan_dual_framing.py    → outputs/dual_framing_index.parquet
        │                         → outputs/FEASIBILITY_REPORT.md
        ▼
[Feasibility gates A, B, C, D evaluated. Prereg amendment if needed.]
        │
        ▼
Stage 2  infer_mid.py             → outputs/mid_inferences.parquet
        │
        ▼
Stage 3  reconstruct.py           → outputs/reconstructions.parquet
        │
        ▼
Stage 4  pool_and_flip.py         → outputs/flip_results.parquet
        │
        ▼
Stage 5  build_dashboard.py       → dashboard/index.html
                                  → outputs/analysis_audit.md
                                  → outputs/paper_numbers.json
```

### 7.2 Supporting modules

- `responder_floor/math.py` — normal-approx reconstruction, delta-method CI, Monte Carlo validator, Φ clamp.
- `responder_floor/pooling.py` — REML + HKSJ wrapper with Q/(k−1) floor.
- `responder_floor/instruments.py` — instrument panel loader, direction resolver, MID lookup.
- `responder_floor/fuzzy_match.py` — outcome-label matcher for dual-framing detection.
- `responder_floor/rda_loader.py` — pyreadr primary, rpy2 fallback for nested S4.
- `responder_floor/r_validation.R` — metafor + custom reconstruction.R parity tests.
- `responder_floor/sentinel_config.yml` — pre-push rule set.
- `scripts/preregister.py` — OpenTimestamps + archive.org stamping (dry-run and live modes). DOI from Synthēsis/Crossref at publication.

### 7.3 Configuration

- `configs/instruments.yml` — v1 panel (§4.3), frozen before Stage 1 real-data run.
- `configs/pipeline.yml` — paths (Pairwise70 location, output dir), seed (xoshiro128** state), tolerance thresholds.
- `configs/prereg.yml` — Q1/Q2/Q3 metric definitions, tier rules, gate thresholds — must match `PREREGISTRATION.md`.

### 7.4 Dashboard

Three panels, single HTML file, inline SVG, zero external dependencies, Pages-ready:
1. **Framing flip-rate panel:** stacked bars T1/T2/T3 × (framing significance flip, magnitude flip), 95% CI via review-clustered bootstrap.
2. **Reconstruction fidelity panel:** density of arm-level |p̂ − p_obs| by instrument; Bland–Altman scatter with 95% limits of agreement per instrument.
3. **Implied-MID atlas panel:** per-instrument forest plot of review-level δ̂ ± CI, ordered by review publication year; overlaid vertical line at canonical MID.

No hardcoded local paths, no BOM, no unicode mojibake. `configs/instruments.yml` canonical MIDs are rendered as data attributes, not hardcoded in HTML.

---

## 8. Preregistration commitments

Locked to git tag + OpenTimestamps + Internet Archive before Stage 1 first real-data run. Committed to git at `v0.0.1` tag. DOI from Synthēsis via Crossref at publication.

**Frozen items:**
- Q1/Q2/Q3/Q4 definitions + metrics table (§3).
- Tier definitions T1/T2/T3 (§6.1).
- Pooling contract: REML + HKSJ + PI, Q/(k−1) floor, metafor parity at 1e-6 (§6.2).
- Primary α=0.05 significance flip; secondary |Δ logRR|>0.1 magnitude flip.
- Model 1 primary / Model 2 sensitivity, with Gate C reversal protocol.
- Instrument panel v1 (§4.3).
- Normality sensitivity protocol (log-Normal, Beta, truncated Normal moment-matched) (§5.3).
- Feasibility gates A/B/C/D (§6.3) and pivot protocol (§6.4).
- Fail-closed buckets (§5.4).
- Authorship: middle-author-only per `feedback_e156_authorship.md`.
- Clustered bootstrap for CIs (cluster = review-outcome pair).
- Seed: xoshiro128** with state committed in `configs/pipeline.yml`.

**Explicitly NOT frozen (analysis freedom retained):**
- Exact fuzzy-match regexes (may tune based on negative controls in Stage 1 dry-run).
- Post-hoc forest plot ordering within panels.
- Paper narrative structure.

---

## 9. Testing strategy

### 9.1 Unit tests

- `tests/test_math.py` — Φ reconstruction, delta-method SE, clamp boundaries, MC validation. Analytic cases at 1e-6; MC at 1e-3.
- `tests/test_instruments.py` — direction resolver, MID lookup, missing-instrument fail-closed.
- `tests/test_fuzzy_match.py` — hand-labeled positive + negative outcome-pair set, precision + recall reported.
- `tests/test_rda_loader.py` — synthetic RDA fixture with nested S4, UTF-8 enforcement.
- `tests/test_pooling.py` — REML + HKSJ + PI + Q/(k−1) floor, metafor parity at 1e-6.
- `tests/test_mid_inference.py` — Model 1 + Model 2 on trials with hand-computed expected δ̂.

### 9.2 Contract tests at module boundaries

Per `feedback_research_methodology.md`:
- Stage 1 → Stage 2: `dual_framing_index.parquet` schema assertion with expected-vs-received key diff on failure.
- Stage 2 → Stage 3: `mid_inferences.parquet` schema assertion.
- Stage 3 → Stage 4: `reconstructions.parquet` schema assertion.
- Stage 4 → Stage 5: `flip_results.parquet` schema assertion.

Silent-failure sentinels (return None / empty DataFrame) BANNED; schema mismatch raises `KeyError` with diff.

### 9.3 Integration tests

- `tests/test_pipeline_e2e.py` — 5-review synthetic fixture with hand-computed expected outputs across all 5 stages.
- `tests/test_negative_control.py` — curated KCCQ trial cluster where continuous-to-responder mapping is stable; pipeline must report tight reconstruction (ε_arm < 0.05 for ≥90% of arms). Broad disagreement fails test.
- `tests/test_boundary_combinatorics.py` — 2³ combinations of {arm-level present/absent × MID present/absent × boundary p}; every combination routes to the correct fail-closed bucket.
- `tests/test_determinism.py` — two pipeline runs produce byte-identical `reconstructions.parquet`.

### 9.4 R parity

- `tests/test_r_parity.R` — 10 canonical reviews, metafor pooling parity at 1e-6; custom `reconstruction.R` parity at 1e-3 (MC tolerance).

### 9.5 Real-data validation

- 3 trials with published MID + continuous summary + reported responder rates (literature search at Stage 1): reconstruction within 5% absolute responder rate OR documented non-normality as explanation.

### 9.6 Regression snapshot

`FEASIBILITY_REPORT.md` counts + primary-metric values locked after first full run. Re-runs must match within tolerance (exact for counts; 1e-6 for deterministic metrics; 3σ for MC-sensitive metrics).

### 9.7 Sentinel + Overmind gates

- Sentinel pre-push: 0 BLOCK required. No `skip-file` markers except in test fixtures with deliberate violations.
- Overmind nightly verify: PASS required before v0.1.0 tag.
- P1-empty-dataframe-access rule respected: no `.iloc[0]` without length check in Stages 4–5.

---

## 10. Deliverables and release plan

### 10.1 Release structure

| Tag | Contents | Gate |
|---|---|---|
| `v0.0.1` | Spec + prereg committed, instrument panel v1 frozen, no real-data compute yet | git tag + OTS + IA stamping before progression |
| `v0.1.0-feasibility` | Stage 1 output, `FEASIBILITY_REPORT.md` public, gate verdicts, prereg amendment (if any) | Gate A/B/C/D resolved |
| `v0.1.0` | Full pipeline run, E156 Methods Note drafted, Pages dashboard live, `analysis_audit.md` published | All tests pass, R parity clean, Sentinel 0 BLOCK, Overmind PASS |
| `v0.2.0` | Post-internal-review edits, full paper draft for RSM | Co-author sign-off |
| `v1.0.0` | Post peer-review edits, DOI from Synthēsis via Crossref at publication | Journal acceptance |

### 10.2 Artefacts

- Code: Python package `responder_floor/` + R scripts + tests + configs.
- Data: `outputs/*.parquet` + `outputs/analysis_audit.md`.
- Dashboard: `dashboard/index.html` (Pages, under `mahmood726-cyber.github.io/responder-floor-atlas/`).
- Paper: `manuscript/e156_methods_note.md` (Synthēsis) + `manuscript/full_paper.md` (RSM).
- Preregistration: `preregistration/PREREGISTRATION.md` + OTS receipt + archive.org URL. Publication DOI from Synthēsis via Crossref.
- Signed release bundle: HMAC via `TRUTHCERT_HMAC_KEY` per `lessons.md` crypto rule; no placeholder signatures.

### 10.3 Authorship

Middle-author-only for Mahmood Ahmad on both papers per `feedback_e156_authorship.md`. First and senior authors TBD; editorial-board COI retired per 2026-04-20 update.

---

## 11. Risk register

| # | Risk | Prob | Impact | Mitigation | Detection |
|---|---|---|---|---|---|
| R1 | Pairwise70 RDA stores effect sizes only (no arm-level μ/σ) | Med | High | RevMan XML fallback documented (+1 week); Gate A pivot to Bundle 1 | Stage 1 FEASIBILITY_REPORT |
| R2 | Outcome-label fuzzy match creates false dual-framing pairs | Med | Med | Top-20-per-instrument hand-review; precision/recall reported; `instruments.yml` regex tightened | Negative control test + spot audit |
| R3 | Normality badly violated for skewed PROs | High | Med | Sensitivity under log-Normal + Beta + truncated Normal; bound reported explicitly in paper | Sensitivity table |
| R4 | R ↔ Python parity fails at 1e-6 | Low | Low | Document tolerance; ship at 1e-5 with audit note; investigate root cause | R parity CI |
| R5 | Prereg locked but feasibility forces scope narrowing | Med | Med | Amendment protocol (§6.4): timestamped, OTS-restamped, re-IA-archived, explicit "pivot" section in paper | Stage 1 gate result |
| R6 | Same-trial multiplicity inflates CI confidence | Med | Med | Clustered bootstrap (cluster = review-outcome pair); reported alongside naive CI | Built into Stage 4 |
| R7 | Instrument panel v1 too narrow, misses coverage | Med | Low | v1 frozen; panel expansion is v2 paper | Post-feasibility count per instrument |
| R8 | Direction-of-benefit misconfigured (silent sign flip per instrument) | Low | High | Contract test: each instrument in yml has a happy-path trial with hand-checked expected RR sign | Negative control |
| R9 | Memory-driven claims (test counts, denominators) drift from reality | High | Med | All paper numbers sourced from live pipeline output + commit hash; no citing MEMORY.md | Review gate before submission |
| R10 | Scope creep ("one more panel", "one more sensitivity") | High | Med | Defer-list file; v2 paper for accepted extensions; PI Atlas-style discipline | Weekly commit audit |
| R11 | MID provenance error (review cites outdated MID literature) | Med | Low | Out-of-scope for v1; flagged as discussion limitation; cite as future work | N/A |
| R12 | Publication-selection bias in Pairwise70 itself | Cert | Med | Acknowledged as known corpus-level limit; disclosure section cites sibling-atlas precedent | Disclosure section |
| R13 | README/paper "Grand Unified" claim drift | Low | High | Static-vs-dynamic hardcode-disclosure table (§12); banned language list | Sentinel + review gate |
| R14 | Dual-framing subset too small to support Q1 + Q2 + Q3 simultaneously | Med | High | Gate-driven bundle pivot (§6.3 A/B/C); transparent scope reduction | Stage 1 |
| R15 | Negative control fails (pipeline shows broad disagreement on known-stable cluster) | Low | High | Pipeline blocked until root cause found; no forward progression | `test_negative_control.py` |

---

## 12. Static-vs-dynamic hardcode disclosure

Per `rules.md` "Ingredient proof and claim discipline":

| Item | Static (hardcoded v1) | Dynamic (pipeline-derived) |
|---|---|---|
| Instrument panel | v1 list in `configs/instruments.yml` (6 instruments) | — |
| Canonical MIDs | v1 values in `configs/instruments.yml` | — |
| Fuzzy-match regexes | Author-tuned against Stage 1 dry-run | — |
| Pairwise70 corpus | Path in `configs/pipeline.yml` | Counts per review / MA — read at runtime |
| Tier thresholds | ≥3 dual-contributing trials, ≥5 reviews per instrument | — |
| Gate thresholds | ≥30 reviews (A), ≥3×5 (B), ≥20% (C), ≥50 trials (D) | — |
| α, magnitude threshold | 0.05, 0.1 | — |
| MC seed | xoshiro128** state committed | — |
| R tolerance | 1e-6 pooling, 1e-3 MC | — |
| Paper numbers | — | All from `outputs/paper_numbers.json` at commit hash |
| Dashboard counts | — | All from `outputs/*.parquet` at commit hash |
| Review flip-rate headline | — | Stage 4 result, committed before publication |

**Banned in README / paper / dashboard copy:** "complete", "global", "full", "grand unified", "comprehensive", "all Cochrane reviews" (without tier qualifier). Claims grounded in the specific qualifying subset only.

---

## 13. Timeline

| Week | Milestone |
|---|---|
| 1, Day 1 | Repo scaffold + `PREREGISTRATION.md` + git tag + OTS + IA stamp → `v0.0.1` |
| 1, Day 2 | `scan_dual_framing.py` + FEASIBILITY_REPORT → `v0.1.0-feasibility` |
| 1, Day 3 | Gate resolution + prereg amendment (if needed) |
| 1, Days 4–5 | `infer_mid.py` + `reconstruct.py` + tests |
| 2, Days 1–2 | `pool_and_flip.py` + R parity |
| 2, Day 3 | `build_dashboard.py` + Pages deploy |
| 2, Day 4 | E156 Methods Note draft |
| 2, Day 5 | RSM full-paper skeleton → `v0.1.0` tag + release bundle |

Total: **2 weeks** under the happy path. Add 1 week if RevMan XML fallback triggers (R1).

---

## 14. Dependencies and Task 0 preflight

Per `lessons.md` "preflight external prereqs before starting a multi-task plan", Task 0 of the implementation plan MUST verify:

- [ ] `C:\Projects\Pairwise70\` exists and contains ≥500 RDA files.
- [ ] `pyreadr` imports cleanly; one test RDA loads.
- [ ] R 4.5.2 at `C:\Program Files\R\R-4.5.2\bin\Rscript.exe` with `metafor` available.
- [ ] OTS binary + archive.org save API functional (reuse from PI Atlas). DOI from Synthēsis/Crossref at publication — no Zenodo token required.
- [ ] `configs/instruments.yml` v1 panel parses and resolves every entry.
- [ ] Sentinel hook installable in this repo.
- [ ] Overmind nightly can enrol this repo.

Failure of any Task 0 item blocks all subsequent tasks with a specific user-action list. No Stage 1 compute begins with missing prereqs.

---

## 15. Open questions — none

All design decisions resolved. Spec is implementation-ready pending user review.

---

## Appendix A — Related work and prior art

- Higgins & Green (2011), Cochrane Handbook §9 — continuous vs dichotomous outcome pooling guidance.
- Guyatt et al. (2013), J Clin Epidemiol — MID concept and anchor-based methods.
- Furukawa et al. (2020), Stat Med — responder analysis vs continuous analysis efficiency.
- HTS (2009), JRSS-A — prediction interval and `t_{k-2}` critical value.
- IntHout et al. (2016), BMJ Open — HKSJ method and small-k behaviour.
- Partlett & Riley (2017), Stat Med — PI coverage under misspecification.
- `repro-floor-atlas` v0.1.0 (Ahmad 2026) — aggregate-data precision floor on Pairwise70.
- `cochrane-modern-re` v0.1.0 (Ahmad 2026) — DL → REML+HKSJ+PI flip-rate on Pairwise70.
- `pi-atlas` spec v1.0 (Ahmad 2026) — prediction interval calibration study on Pairwise70.

## Appendix B — Cross-references within portfolio

- Infrastructure reuse: Sentinel pre-push rules, Overmind verification, Pages deploy, OTS+IA stamper (from PI Atlas; Zenodo dropped per Synthēsis/Crossref DOI policy), xoshiro128** seeded MC (from `ma-workbench/precision-sweep`).
- Methodology reuse: Q/(k−1) HKSJ floor, metafor 1e-6 parity, REML + PI from `cochrane-modern-re`.
- Corpus: Pairwise70 (shared with three sibling atlases).
- Authorship policy: middle-author-only per `feedback_e156_authorship.md`.
- Rhetoric: atlas series positioning; "fourth axis" framing.

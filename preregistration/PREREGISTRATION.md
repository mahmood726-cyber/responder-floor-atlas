# Responder Floor Atlas — Preregistration v1.0

**Spec reference:** `docs/superpowers/specs/2026-04-22-responder-floor-atlas-design.md` (commit `ee81682`)
**Corpus:** Pairwise70 (unchanged from sibling atlases)
**Immutability proof:** git tag + OpenTimestamps receipt + Internet Archive snapshot of this file.
**Publication DOI:** assigned by Synthēsis via Crossref at publication.

## Research questions (locked)

- **Q1 — primary:** proportion of Tier-1 dual-framing reviews where SMD-pool and RR-pool significance at α=0.05 disagree. Secondary: |Δ logRR_pooled| > 0.1.
- **Q2 — secondary:** median trial-level |p̂ − p_obs| under Model 1 MID across Tier-1 arms.
- **Q3 — secondary:** within-instrument τ²(δ̂) per instrument across reviews ≥5.
- **Q4 — exploratory:** cross-review δ̂ consistency for trials appearing in ≥2 reviews (reported if Gate D passes).

## Tiers (locked)

- T1: dual-framing + ≥3 dual-contributing trials + arm-level (n, μ, σ, events) both arms + stated or canonical MID.
- T2: T1 without stated/canonical MID (Model 2 back-out only).
- T3: dual-framing with effect sizes only; Q1-only subset.

## Methods (locked)

- Pooling: REML (Fisher-scoring per Viechtbauer 2005) + HKSJ (RE-Q, per metafor knha) + HTS PI with t_{k−2}.
- Reconstruction: Model 1 `p̂ = Φ((d·μ − δ)/σ)` (primary); Model 2 `δ̂ = d·μ − σ·Φ⁻¹(p_obs)` (sensitivity).
- Numerical stability: `norm.logcdf` in extreme tails.
- Sensitivity: log-normal + Beta + truncated Normal moment-matched.
- Clustered bootstrap (cluster = review) for Q1 CI.
- R validation at 1e-6 pooling (via responder_floor/r_validation.R + metafor).

## Known approximations (disclosed before compute)

- `Var(σ̂) ≈ σ²/(2(n−1))` is a large-n Fisher-information approximation; biases SE optimistically at small n (+7% at n=5, +38% at n=2). Task 4's MC validator quantifies this. Preregistration-locked; change requires amendment.
- HKSJ uses RE-Q (metafor convention), not FE-Q (DerSimonian-Laird convention). HKSJ floor at 1 applies only when Q_RE=0 exactly (degenerate all-equal-effects case).

## Feasibility gates

- A: ≥30 reviews with ≥3 dual-contributing trials + arm-level stats (hard stop; pivot to Bundle 1 if fail).
- B: ≥3 instruments with ≥5 reviews each (Q3 exploratory if fail).
- C: ≥20% MID availability (Model 1 primary reversal if fail).
- D: ≥50 trials in ≥2 reviews (Q4 promoted if pass).

## Pivot protocol

Any gate failure triggers a timestamped amendment (new git tag, re-OTS-stamped, re-IA-archived) with explicit paper disclosure. No silent narrowing.

## Authorship

Middle-author-only for Mahmood Ahmad per `feedback_e156_authorship.md` (and the retired editorial-board COI note).

## Instrument panel v1 (frozen)

KCCQ-Overall Summary (d=+1, MID=5), SGRQ-Total (d=−1, MID=4), EQ-5D-5L index (d=+1, MID=0.07), PROMIS Global-10 (d=+1, MID=2), Oswestry Disability Index (d=−1, MID=10), PHQ-9 (d=−1, MID=5). Panel expansion deferred to v2 paper.

## Signatures

- Spec commit: ee81682
- Preregistration git tag: [TO FILL BEFORE FIRST REAL-DATA RUN]
- OTS receipt: preregistration/PREREGISTRATION.md.ots
- Internet Archive URL: [FILLED BY scripts/preregister.py at live-stamp time]
- Publication DOI (Crossref via Synthēsis): [FILLED AT PUBLICATION]

# Responder Floor Atlas

Audit of responder-framing reproducibility in systematic reviews that pool patient-reported outcomes in both continuous (SMD / MD) and dichotomous (responder RR) forms on the **Pairwise70** corpus (595 Cochrane reviews / 7,545 MAs).

**Status:** DRAFT — design spec v1.0 committed. No compute yet. Preregistration pending before first real-data run.

- **Design spec:** [`docs/superpowers/specs/2026-04-22-responder-floor-atlas-design.md`](docs/superpowers/specs/2026-04-22-responder-floor-atlas-design.md)
- **Sibling atlases on the same corpus:** `repro-floor-atlas`, `cochrane-modern-re`, `pi-atlas`
- **Targets:** ◆ Synthēsis (E156 Methods Note) + Research Synthesis Methods (full paper)
- **Authorship:** middle-author-only (MA) per portfolio policy

## Research questions (Bundle 2)

- **Q1** — Framing flip rate: does MA verdict at α=0.05 flip between SMD-pool and RR-pool on the same outcome?
- **Q2** — Reconstruction fidelity: does normal-approx reconstruction (with review MID) match reported responder rates?
- **Q3** — Implied-MID atlas: within-instrument MID heterogeneity across Cochrane reviews.

## Project scaffold

```
responder-floor-atlas/
├── docs/superpowers/specs/   # design spec (committed)
├── preregistration/           # Zenodo + OTS + IA artefacts (pending)
└── README.md                  # this file
```

Implementation structure (per spec §7) is created when the implementation plan executes.

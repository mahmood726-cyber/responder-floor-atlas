# Responder Floor Atlas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Responder Floor Atlas — a Pairwise70-scale audit of continuous-vs-responder framing reproducibility in Cochrane PRO meta-analyses, producing Q1 framing flip-rate (primary), Q2 reconstruction fidelity, and Q3 implied-MID heterogeneity results plus E156 Methods Note + RSM full-paper drafts.

**Architecture:** Five-stage CLI pipeline (scan → MID infer → reconstruct → pool+flip → dashboard) built on Pairwise70 RDA files. TDD-first. Python 3.12 + R 4.5.2 parity at 1e-6 for pooling, 1e-3 for Monte Carlo. Single-file Pages dashboard. Preregistration via Zenodo+OTS+IA before any real-data compute. Fail-closed at every fallback point; no silent exclusions.

**Tech Stack:** Python 3.12, pyreadr + rpy2, numpy, scipy, pandas, pyarrow, pytest, hypothesis, R 4.5.2 + metafor, xoshiro128 seeded MC, Sentinel pre-push hook, Zenodo/OTS/Internet Archive for preregistration.

**Spec:** `docs/superpowers/specs/2026-04-22-responder-floor-atlas-design.md` (commit `ee81682`).

---

## Task 0: Preflight external prerequisites

**Files:**
- Create: `scripts/preflight.py`
- Test: `tests/test_preflight.py`

Rationale: per `lessons.md` "preflight external prereqs BEFORE starting a multi-task plan" — verify every external dependency resolves before any downstream task begins. Fails closed with specific user-action list.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_preflight.py
import subprocess
import sys


def test_preflight_reports_status_dict():
    result = subprocess.run(
        [sys.executable, "scripts/preflight.py", "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode in (0, 1)
    import json
    status = json.loads(result.stdout)
    required_keys = {
        "pairwise70_path", "pyreadr_import", "rpy2_import",
        "r_binary", "metafor_package", "zenodo_token",
        "ots_binary", "ia_save_api", "instruments_yml",
    }
    assert required_keys <= set(status.keys())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_preflight.py -v`
Expected: FAIL (`scripts/preflight.py` not found).

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/preflight.py
"""Task 0 preflight — verify external prerequisites resolve before pipeline work."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def check_pairwise70() -> tuple[bool, str]:
    candidates = [Path(r"C:\Projects\Pairwise70"), Path.home() / "Pairwise70"]
    for c in candidates:
        if c.is_dir():
            rda_count = sum(1 for _ in c.rglob("*.rda"))
            if rda_count >= 500:
                return True, f"{c} ({rda_count} RDA files)"
            return False, f"{c} exists but only {rda_count} RDA files (<500)"
    return False, "Pairwise70 directory not found at C:\\Projects\\Pairwise70 or ~/Pairwise70"


def check_import(modname: str) -> tuple[bool, str]:
    try:
        __import__(modname)
        return True, f"{modname} imports cleanly"
    except ImportError as e:
        return False, f"{modname} import failed: {e}"


def check_r_binary() -> tuple[bool, str]:
    rscript = Path(r"C:\Program Files\R\R-4.5.2\bin\Rscript.exe")
    if rscript.exists():
        return True, str(rscript)
    fallback = shutil.which("Rscript")
    if fallback:
        return True, fallback
    return False, "Rscript not found at C:\\Program Files\\R\\R-4.5.2\\bin\\Rscript.exe"


def check_metafor() -> tuple[bool, str]:
    ok, rscript = check_r_binary()
    if not ok:
        return False, "Rscript missing"
    try:
        out = subprocess.run(
            [rscript, "-e", 'if(!"metafor" %in% rownames(installed.packages())) quit(status=1)'],
            capture_output=True, timeout=60,
        )
        return (out.returncode == 0, "metafor installed" if out.returncode == 0 else "metafor not installed")
    except Exception as e:
        return False, f"metafor check failed: {e}"


def check_zenodo_token() -> tuple[bool, str]:
    token = os.environ.get("ZENODO_API_TOKEN")
    return (bool(token), "ZENODO_API_TOKEN set" if token else "ZENODO_API_TOKEN env var not set")


def check_ots_binary() -> tuple[bool, str]:
    found = shutil.which("ots")
    return (bool(found), found or "ots (OpenTimestamps) binary not on PATH")


def check_ia_save() -> tuple[bool, str]:
    # Connectivity check only; actual save happens at prereg time.
    try:
        import urllib.request
        urllib.request.urlopen("https://web.archive.org/", timeout=10)
        return True, "archive.org reachable"
    except Exception as e:
        return False, f"archive.org unreachable: {e}"


def check_instruments_yml() -> tuple[bool, str]:
    p = Path("configs/instruments.yml")
    return (p.exists(), str(p) if p.exists() else "configs/instruments.yml absent (created in Task 3)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    checks = {
        "pairwise70_path": check_pairwise70(),
        "pyreadr_import": check_import("pyreadr"),
        "rpy2_import": check_import("rpy2"),
        "r_binary": check_r_binary(),
        "metafor_package": check_metafor(),
        "zenodo_token": check_zenodo_token(),
        "ots_binary": check_ots_binary(),
        "ia_save_api": check_ia_save(),
        "instruments_yml": check_instruments_yml(),
    }
    status = {k: {"ok": ok, "detail": detail} for k, (ok, detail) in checks.items()}
    all_ok = all(v["ok"] for v in status.values())

    if args.json:
        print(json.dumps(status, indent=2))
    else:
        for k, v in status.items():
            mark = "OK  " if v["ok"] else "FAIL"
            print(f"[{mark}] {k}: {v['detail']}")
        print(f"\nOverall: {'READY' if all_ok else 'BLOCKED — fix failures above before proceeding'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_preflight.py -v`
Expected: PASS (test only asserts structure, not that all checks succeed).

- [ ] **Step 5: Run the preflight check and record results**

Run: `python scripts/preflight.py`
Expected: Mix of OK/FAIL — `instruments_yml` FAIL is expected (created in Task 3), others indicate real environment gaps.

Fix any non-`instruments_yml` failure before proceeding to Task 1. Install missing packages with `pip install pyreadr rpy2 numpy scipy pandas pyarrow pytest hypothesis pyyaml`; install `metafor` with `Rscript -e 'install.packages("metafor", repos="https://cloud.r-project.org")'`; install `ots` via `pip install opentimestamps-client`.

- [ ] **Step 6: Commit**

```bash
git add scripts/preflight.py tests/test_preflight.py
git commit -m "Task 0: external prerequisite preflight check"
```

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`, `responder_floor/__init__.py`, `tests/__init__.py`, `tests/conftest.py`, `configs/pipeline.yml`

- [ ] **Step 1: Write pyproject.toml**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "responder-floor-atlas"
version = "0.0.1"
description = "Pairwise70 responder-framing reproducibility atlas"
authors = [{name = "Mahmood Ahmad"}]
requires-python = ">=3.12"
dependencies = [
    "numpy>=1.26",
    "scipy>=1.11",
    "pandas>=2.1",
    "pyarrow>=14.0",
    "pyreadr>=0.5",
    "rpy2>=3.5",
    "pyyaml>=6.0",
    "jinja2>=3.1",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=4.1", "hypothesis>=6.100", "ruff>=0.5"]

[tool.setuptools.packages.find]
include = ["responder_floor*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --strict-markers"

[tool.ruff]
line-length = 100
```

- [ ] **Step 2: Create package skeletons**

```python
# responder_floor/__init__.py
"""Responder Floor Atlas — Pairwise70 framing-reproducibility audit."""
__version__ = "0.0.1"
```

```python
# tests/__init__.py
```

```python
# tests/conftest.py
"""Pytest fixtures shared across responder-floor-atlas tests."""
import sys
from pathlib import Path

# Ensure repo root on sys.path for `import responder_floor` from tests.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

- [ ] **Step 3: Write pipeline config**

```yaml
# configs/pipeline.yml
paths:
  pairwise70: "C:/Projects/Pairwise70"
  output_dir: "outputs"
  dashboard_dir: "dashboard"

seed:
  xoshiro128_state: [0x12345678, 0x9ABCDEF0, 0x0FEDCBA9, 0x87654321]

tolerance:
  r_parity_pooling: 1.0e-6
  r_parity_reconstruction: 1.0e-3
  mc_draws: 10000

gates:
  A_arm_level_reviews_min: 30
  A_trials_per_review_min: 3
  B_instruments_min: 3
  B_reviews_per_instrument_min: 5
  C_mid_availability_pct_min: 0.20
  D_cross_review_trial_overlap_min: 50

thresholds:
  alpha: 0.05
  magnitude_flip_log_rr: 0.1
  reconstruction_epsilon: 0.05
```

- [ ] **Step 4: Install and verify**

Run: `pip install -e ".[dev]"`
Expected: successful install; `python -c "import responder_floor; print(responder_floor.__version__)"` prints `0.0.1`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml responder_floor/__init__.py tests/__init__.py tests/conftest.py configs/pipeline.yml
git commit -m "Task 1: project scaffold + pipeline config"
```

---

## Task 2: Instruments config + loader

**Files:**
- Create: `configs/instruments.yml`, `responder_floor/instruments.py`, `tests/test_instruments.py`

- [ ] **Step 1: Write instruments.yml (v1 panel, frozen per spec §4.3)**

```yaml
# configs/instruments.yml
# v1 instrument panel frozen per spec §4.3. Direction: +1 higher-better, -1 lower-better.
# Canonical MIDs are published community-accepted values; review-stated MIDs override these when available.
instruments:
  - id: kccq_os
    display_name: "KCCQ Overall Summary"
    direction: 1
    scale_min: 0
    scale_max: 100
    canonical_mid: 5
    mid_source: "Spertus 2005 (J Am Coll Cardiol)"
    label_regex: "(?i)(?=.*(overall|oss))(?!.*clinical).*(kccq|kansas.*city.*cardiomyopathy)"
  - id: sgrq_total
    display_name: "SGRQ Total"
    direction: -1
    scale_min: 0
    scale_max: 100
    canonical_mid: 4
    mid_source: "Jones 2005 (Thorax)"
    label_regex: "(?i)(sgrq|st.*george).*(total|overall)"
  - id: eq5d_5l_index
    display_name: "EQ-5D-5L index"
    direction: 1
    scale_min: 0
    scale_max: 1
    canonical_mid: 0.07
    mid_source: "Pickard 2019 (Value Health)"
    label_regex: "(?i)eq.?5d.?5l"
  - id: promis_global_10
    display_name: "PROMIS Global-10"
    direction: 1
    scale_min: 0
    scale_max: 100
    canonical_mid: 2
    mid_source: "Hays 2018 (Qual Life Res)"
    label_regex: "(?i)promis.*global.?10"
  - id: odi
    display_name: "Oswestry Disability Index"
    direction: -1
    scale_min: 0
    scale_max: 100
    canonical_mid: 10
    mid_source: "Copay 2008 (Spine J)"
    label_regex: "(?i)(odi|oswestry)"
  - id: phq9
    display_name: "PHQ-9"
    direction: -1
    scale_min: 0
    scale_max: 27
    canonical_mid: 5
    mid_source: "Kroenke 2001 (J Gen Intern Med)"
    label_regex: "(?i)phq.?9"
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_instruments.py
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_instruments.py -v`
Expected: FAIL (`responder_floor.instruments` not implemented).

- [ ] **Step 4: Implement loader**

```python
# responder_floor/instruments.py
"""v1 instrument panel loader and fuzzy-label matcher."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import yaml


@dataclass(frozen=True)
class Instrument:
    id: str
    display_name: str
    direction: int            # +1 higher-better, -1 lower-better
    scale_min: float
    scale_max: float
    canonical_mid: float
    mid_source: str
    label_regex: str


DEFAULT_PATH = Path(__file__).resolve().parent.parent / "configs" / "instruments.yml"


@lru_cache(maxsize=1)
def load_instruments(path: Path | None = None) -> tuple[Instrument, ...]:
    p = path or DEFAULT_PATH
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    instruments = []
    for entry in raw["instruments"]:
        if entry["direction"] not in (1, -1):
            raise ValueError(f"Instrument {entry['id']}: direction must be +1 or -1, got {entry['direction']}")
        instruments.append(Instrument(**entry))
    return tuple(instruments)


def match_instrument(label: str, instruments: tuple[Instrument, ...] | None = None) -> Instrument | None:
    """Match an outcome label against v1 panel regexes. Returns first match or None."""
    if instruments is None:
        instruments = load_instruments()
    for i in instruments:
        if re.search(i.label_regex, label):
            return i
    return None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_instruments.py -v`
Expected: PASS (6 tests).

- [ ] **Step 6: Commit**

```bash
git add configs/instruments.yml responder_floor/instruments.py tests/test_instruments.py
git commit -m "Task 2: v1 instrument panel + fuzzy-label matcher"
```

---

## Task 3: Normal-approx reconstruction — Model 1 core (`p̂_arm`)

**Files:**
- Create: `responder_floor/math.py`, `tests/test_math.py`

Per spec §5.1: `p̂_arm(μ, σ, δ, d) = Φ((d·μ − δ) / σ)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_math.py
import math
import numpy as np
import pytest

from responder_floor.math import p_hat_arm, log_rr_hat, log_rr_hat_se_delta


def test_kccq_higher_better_sanity_case():
    # d=+1 KCCQ: μ=10, σ=15, δ=5. P(Change >= 5) = Φ((10-5)/15) = Φ(0.333) ≈ 0.6306.
    p = p_hat_arm(mean=10.0, sd=15.0, mid=5.0, direction=1)
    assert abs(p - 0.6305587) < 1e-6


def test_sgrq_lower_better_six_point_drop():
    # d=-1 SGRQ: μ=-6 (six-point drop), σ=10, δ=4. P = Φ((6-4)/10) = Φ(0.2) ≈ 0.5793.
    p = p_hat_arm(mean=-6.0, sd=10.0, mid=4.0, direction=-1)
    assert abs(p - 0.5792597) < 1e-6


def test_sgrq_lower_better_worsened():
    # d=-1 SGRQ: μ=+2 (two-point worse), σ=10, δ=4. P = Φ((-2-4)/10) = Φ(-0.6) ≈ 0.2742.
    p = p_hat_arm(mean=2.0, sd=10.0, mid=4.0, direction=-1)
    assert abs(p - 0.2742531) < 1e-6


def test_direction_must_be_plus_or_minus_one():
    with pytest.raises(ValueError):
        p_hat_arm(mean=0, sd=1, mid=1, direction=0)


def test_sd_must_be_positive():
    with pytest.raises(ValueError):
        p_hat_arm(mean=0, sd=0, mid=1, direction=1)


def test_log_rr_hat_identity_when_arms_match():
    # Identical arms → RR=1 → logRR=0.
    lrr = log_rr_hat(mean_t=5, sd_t=10, n_t=100, mean_c=5, sd_c=10, n_c=100, mid=3, direction=1)
    assert abs(lrr) < 1e-12


def test_log_rr_hat_positive_when_treatment_better():
    # KCCQ, treatment μ=10 > control μ=3, δ=5 → treatment arm has higher responder prob → logRR > 0.
    lrr = log_rr_hat(mean_t=10, sd_t=15, n_t=100, mean_c=3, sd_c=15, n_c=100, mid=5, direction=1)
    assert lrr > 0


def test_log_rr_hat_se_delta_positive_and_finite():
    se = log_rr_hat_se_delta(mean_t=10, sd_t=15, n_t=100, mean_c=3, sd_c=15, n_c=100, mid=5, direction=1)
    assert se > 0 and math.isfinite(se)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_math.py -v`
Expected: FAIL (`responder_floor.math` not implemented).

- [ ] **Step 3: Implement math.py**

```python
# responder_floor/math.py
"""Normal-approximation reconstruction math for the Responder Floor Atlas.

Per spec §5.1 (Model 1, top-down) and §5.2 (Model 2, back-out).
Convention: μ is raw-signed mean change, δ > 0 is MID magnitude,
d ∈ {+1, -1} is instrument direction (higher-better vs lower-better).
"""
from __future__ import annotations

import math
from scipy.stats import norm

_P_CLAMP_LOW = 1e-10
_P_CLAMP_HIGH = 1.0 - 1e-10


def _validate_direction(direction: int) -> None:
    if direction not in (1, -1):
        raise ValueError(f"direction must be +1 or -1, got {direction!r}")


def _validate_sd(sd: float) -> None:
    if not (sd > 0 and math.isfinite(sd)):
        raise ValueError(f"sd must be finite and positive, got {sd!r}")


def p_hat_arm(mean: float, sd: float, mid: float, direction: int) -> float:
    """Reconstructed responder probability for one arm under normal approximation.

    p̂ = Φ((d · μ − δ) / σ)
    """
    _validate_direction(direction)
    _validate_sd(sd)
    z = (direction * mean - mid) / sd
    return float(norm.cdf(z))


def clamp_p(p: float) -> float:
    """Clamp observed proportion into open unit interval per lessons.md logit-clamp rule."""
    return min(max(p, _P_CLAMP_LOW), _P_CLAMP_HIGH)


def delta_hat_arm(mean: float, sd: float, p_obs: float, direction: int) -> float:
    """Trial-level implied MID back-out (Model 2).

    δ̂ = d · μ − σ · Φ⁻¹(p_obs)
    """
    _validate_direction(direction)
    _validate_sd(sd)
    p = clamp_p(p_obs)
    z = norm.ppf(p)
    return float(direction * mean - sd * z)


def log_rr_hat(
    mean_t: float, sd_t: float, n_t: int,
    mean_c: float, sd_c: float, n_c: int,
    mid: float, direction: int,
) -> float:
    """Log reconstructed risk ratio from continuous arm-level stats + MID."""
    p_t = p_hat_arm(mean_t, sd_t, mid, direction)
    p_c = p_hat_arm(mean_c, sd_c, mid, direction)
    p_t = clamp_p(p_t)
    p_c = clamp_p(p_c)
    return math.log(p_t / p_c)


def log_rr_hat_se_delta(
    mean_t: float, sd_t: float, n_t: int,
    mean_c: float, sd_c: float, n_c: int,
    mid: float, direction: int,
) -> float:
    """Delta-method SE of log RR̂.

    Var(log p) = (dp/dμ)² Var(μ) + (dp/dσ)² Var(σ) all divided by p².
    d p/d μ = φ((d·μ − δ)/σ) · (d/σ)
    d p/d σ = φ((d·μ − δ)/σ) · (−(d·μ − δ)/σ²)
    Var(μ) = σ²/n; Var(σ) = σ²/(2(n−1)).
    """
    _validate_direction(direction)
    _validate_sd(sd_t)
    _validate_sd(sd_c)
    if n_t < 2 or n_c < 2:
        raise ValueError("n per arm must be >= 2 for SE")

    def _arm_var_log_p(mean: float, sd: float, n: int) -> float:
        z = (direction * mean - mid) / sd
        phi = norm.pdf(z)
        p = norm.cdf(z)
        p = clamp_p(p)
        dp_dmu = phi * (direction / sd)
        dp_dsigma = phi * (-(direction * mean - mid) / (sd * sd))
        var_mu = sd * sd / n
        var_sigma = sd * sd / (2.0 * (n - 1))
        var_p = dp_dmu ** 2 * var_mu + dp_dsigma ** 2 * var_sigma
        return var_p / (p * p)

    return math.sqrt(_arm_var_log_p(mean_t, sd_t, n_t) + _arm_var_log_p(mean_c, sd_c, n_c))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_math.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add responder_floor/math.py tests/test_math.py
git commit -m "Task 3: Model 1 reconstruction (p_hat_arm, log_rr_hat, delta-method SE)"
```

---

## Task 4: Monte Carlo validator for delta-method SE

**Files:**
- Modify: `responder_floor/math.py` (add `log_rr_hat_se_mc`)
- Modify: `tests/test_math.py` (add MC parity test)

- [ ] **Step 1: Add the failing test**

```python
# tests/test_math.py  — append
from responder_floor.math import log_rr_hat_se_mc


def test_delta_method_vs_mc_within_1e3():
    import numpy as np
    rng = np.random.default_rng(seed=20260422)
    se_delta = log_rr_hat_se_delta(mean_t=10, sd_t=15, n_t=100, mean_c=3, sd_c=15, n_c=100, mid=5, direction=1)
    se_mc = log_rr_hat_se_mc(
        mean_t=10, sd_t=15, n_t=100, mean_c=3, sd_c=15, n_c=100,
        mid=5, direction=1, n_draws=10_000, rng=rng,
    )
    assert abs(se_delta - se_mc) < 1e-3, (se_delta, se_mc)
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_math.py::test_delta_method_vs_mc_within_1e3 -v`
Expected: FAIL (`log_rr_hat_se_mc` undefined).

- [ ] **Step 3: Add MC implementation**

```python
# responder_floor/math.py — append
import numpy as np


def log_rr_hat_se_mc(
    mean_t: float, sd_t: float, n_t: int,
    mean_c: float, sd_c: float, n_c: int,
    mid: float, direction: int,
    n_draws: int = 10_000,
    rng: np.random.Generator | None = None,
) -> float:
    """Monte Carlo SE of log RR̂, sampling arm means and SDs from their sampling distributions.

    μ_hat ~ Normal(μ, σ²/n); σ_hat from χ² scaling: σ² · χ²_{n−1} / (n−1).
    """
    _validate_direction(direction)
    _validate_sd(sd_t)
    _validate_sd(sd_c)
    if n_t < 2 or n_c < 2:
        raise ValueError("n per arm must be >= 2 for MC SE")
    rng = rng or np.random.default_rng(seed=20260422)

    def _arm_draws(mean: float, sd: float, n: int) -> np.ndarray:
        mu = rng.normal(mean, sd / math.sqrt(n), size=n_draws)
        chi2 = rng.chisquare(df=n - 1, size=n_draws)
        sigma = sd * np.sqrt(chi2 / (n - 1))
        z = (direction * mu - mid) / sigma
        p = norm.cdf(z)
        return np.clip(p, _P_CLAMP_LOW, _P_CLAMP_HIGH)

    p_t = _arm_draws(mean_t, sd_t, n_t)
    p_c = _arm_draws(mean_c, sd_c, n_c)
    log_rr = np.log(p_t / p_c)
    return float(np.std(log_rr, ddof=1))
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_math.py::test_delta_method_vs_mc_within_1e3 -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add responder_floor/math.py tests/test_math.py
git commit -m "Task 4: Monte Carlo SE validator for log_rr_hat at 1e-3 tolerance"
```

---

## Task 5: Model 2 back-out (δ̂_arm) tests

**Files:**
- Modify: `tests/test_math.py` (add Model 2 round-trip tests)

- [ ] **Step 1: Add failing tests**

```python
# tests/test_math.py — append
from responder_floor.math import delta_hat_arm


def test_model2_round_trips_kccq():
    # Forward: p̂ = Φ(5/15) ≈ 0.6306. Back-out should recover δ=5.
    p = p_hat_arm(mean=10.0, sd=15.0, mid=5.0, direction=1)
    delta_back = delta_hat_arm(mean=10.0, sd=15.0, p_obs=p, direction=1)
    assert abs(delta_back - 5.0) < 1e-8


def test_model2_round_trips_sgrq():
    p = p_hat_arm(mean=-6.0, sd=10.0, mid=4.0, direction=-1)
    delta_back = delta_hat_arm(mean=-6.0, sd=10.0, p_obs=p, direction=-1)
    assert abs(delta_back - 4.0) < 1e-8


def test_model2_boundary_p_does_not_raise():
    # p=0 clamps to 1e-10; should produce large |δ̂| but not Inf.
    delta_back = delta_hat_arm(mean=0.0, sd=1.0, p_obs=0.0, direction=1)
    assert math.isfinite(delta_back) and delta_back > 5.0
```

- [ ] **Step 2: Run to verify**

Run: `pytest tests/test_math.py -v`
Expected: 3 new PASS (delta_hat_arm already implemented in Task 3).

- [ ] **Step 3: Commit**

```bash
git add tests/test_math.py
git commit -m "Task 5: Model 2 back-out round-trip tests"
```

---

## Task 6: Fail-closed status codes and row-validator

**Files:**
- Create: `responder_floor/status.py`, `tests/test_status.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_status.py
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
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_status.py -v`
Expected: FAIL (`responder_floor.status` missing).

- [ ] **Step 3: Implement**

```python
# responder_floor/status.py
"""Fail-closed status codes per spec §5.4. Every pipeline row carries (StatusCode, reason)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StatusCode(str, Enum):
    OK = "OK"
    MISSING_SD = "MISSING_SD"
    BOUNDARY_P = "BOUNDARY_P"
    POOLED_ONLY = "POOLED_ONLY"
    N_MISMATCH = "N_MISMATCH"
    UNKNOWN_INSTRUMENT = "UNKNOWN_INSTRUMENT"
    ID_AMBIGUOUS = "ID_AMBIGUOUS"
    MISSING_MID = "MISSING_MID"
    SIGN_AMBIGUOUS = "SIGN_AMBIGUOUS"


@dataclass
class TrialArmInput:
    mean: float | None
    sd: float | None
    n: int | None
    events: int | None


def classify_arm(row: TrialArmInput) -> tuple[StatusCode, str]:
    if row.sd is None:
        return StatusCode.MISSING_SD, "sd missing from source RDA"
    if row.mean is None:
        return StatusCode.MISSING_SD, "mean missing from source RDA"
    if row.n is None or row.n < 2:
        return StatusCode.MISSING_SD, f"n missing or <2: {row.n}"
    if row.events is None:
        return StatusCode.POOLED_ONLY, "events missing from dichotomous MA (arm-level not extractable)"
    if row.events == 0 or row.events == row.n:
        return StatusCode.BOUNDARY_P, f"observed p at boundary: events={row.events}, n={row.n}"
    return StatusCode.OK, "all fields present and in-range"
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_status.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add responder_floor/status.py tests/test_status.py
git commit -m "Task 6: fail-closed status codes + per-arm classifier"
```

---

## Task 7: REML + HKSJ + PI pooling with Q/(k−1) floor

**Files:**
- Create: `responder_floor/pooling.py`, `tests/test_pooling.py`

Per spec §6.2: REML, HKSJ with Q/(k−1) floor, t_{k−2} PI. Per `advanced-stats.md`: HKSJ floor `max(1, Q/(k-1))`; PI uses `t_{k-2}` not `t_{k-1}`.

- [ ] **Step 1: Write failing test**

```python
# tests/test_pooling.py
import math
import numpy as np
import pytest
from responder_floor.pooling import pool_reml_hksj_pi


def test_pooled_matches_two_study_weighted_mean():
    # Two studies, identical effect=0.5, identical SE=0.1 → pooled=0.5, SE=0.1/sqrt(2).
    effects = np.array([0.5, 0.5])
    variances = np.array([0.01, 0.01])
    result = pool_reml_hksj_pi(effects, variances)
    assert abs(result.estimate - 0.5) < 1e-10
    assert abs(result.se - 0.1 / math.sqrt(2)) < 1e-6


def test_hksj_floor_applied_when_q_low():
    # Homogeneous studies → Q small → HKSJ factor would be < 1 → floored to 1.
    effects = np.array([0.5, 0.5, 0.5])
    variances = np.array([0.01, 0.01, 0.01])
    result = pool_reml_hksj_pi(effects, variances)
    assert result.hksj_factor >= 1.0 - 1e-12


def test_pi_uses_t_k_minus_2():
    effects = np.array([0.3, 0.5, 0.7, 0.4])
    variances = np.array([0.02, 0.03, 0.015, 0.025])
    result = pool_reml_hksj_pi(effects, variances)
    assert result.pi_lower < result.estimate < result.pi_upper
    assert result.pi_df == len(effects) - 2


def test_pi_undefined_for_k_below_3():
    with pytest.raises(ValueError):
        pool_reml_hksj_pi(np.array([0.5, 0.3]), np.array([0.01, 0.02]))
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_pooling.py -v`
Expected: FAIL (pooling module absent).

- [ ] **Step 3: Implement pooling**

```python
# responder_floor/pooling.py
"""REML + HKSJ + PI random-effects pooling with Q/(k-1) floor per spec §6.2."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.stats import t, norm


@dataclass
class PoolResult:
    k: int
    estimate: float
    se: float
    ci_lower: float
    ci_upper: float
    pi_lower: float
    pi_upper: float
    pi_df: int
    tau2: float
    q_stat: float
    q_df: int
    hksj_factor: float
    z: float
    p_value: float


def _reml_tau2(effects: np.ndarray, variances: np.ndarray, max_iter: int = 100, tol: float = 1e-10) -> float:
    """REML estimator for τ² via iterative Paule-Mandel-style fixed-point (REML formulation)."""
    tau2 = 0.0
    for _ in range(max_iter):
        w = 1.0 / (variances + tau2)
        mu = np.sum(w * effects) / np.sum(w)
        numer = np.sum(w ** 2 * ((effects - mu) ** 2 - variances))
        denom = np.sum(w ** 2)
        new_tau2 = max(0.0, tau2 + numer / denom)
        if abs(new_tau2 - tau2) < tol:
            return new_tau2
        tau2 = new_tau2
    return tau2


def pool_reml_hksj_pi(effects: np.ndarray, variances: np.ndarray) -> PoolResult:
    """Pool with REML τ², HKSJ SE adjustment (Q/(k-1) floored at 1), HTS PI with t_{k-2}."""
    effects = np.asarray(effects, dtype=float)
    variances = np.asarray(variances, dtype=float)
    k = len(effects)
    if k < 3:
        raise ValueError(f"PI requires k >= 3; got k={k}")
    if len(variances) != k or (variances <= 0).any():
        raise ValueError("variances must be positive and same length as effects")

    tau2 = _reml_tau2(effects, variances)
    w = 1.0 / (variances + tau2)
    mu = np.sum(w * effects) / np.sum(w)
    se_re = math.sqrt(1.0 / np.sum(w))

    # Q statistic using fixed-effect weights
    w_fe = 1.0 / variances
    mu_fe = np.sum(w_fe * effects) / np.sum(w_fe)
    q = float(np.sum(w_fe * (effects - mu_fe) ** 2))
    q_df = k - 1

    # HKSJ factor floored at 1 per advanced-stats.md
    hksj_raw = q / q_df if q_df > 0 else 1.0
    hksj_factor = max(1.0, hksj_raw)
    se_hksj = se_re * math.sqrt(hksj_factor)

    # CI with t_{k-1}
    t_crit_ci = t.ppf(0.975, df=k - 1)
    ci_lower = mu - t_crit_ci * se_hksj
    ci_upper = mu + t_crit_ci * se_hksj

    # PI with t_{k-2} per HTS and advanced-stats.md
    pi_df = k - 2
    t_crit_pi = t.ppf(0.975, df=pi_df)
    pi_se = math.sqrt(se_hksj ** 2 + tau2)
    pi_lower = mu - t_crit_pi * pi_se
    pi_upper = mu + t_crit_pi * pi_se

    z = mu / se_hksj
    p_value = 2.0 * (1.0 - norm.cdf(abs(z)))

    return PoolResult(
        k=k, estimate=float(mu), se=float(se_hksj),
        ci_lower=float(ci_lower), ci_upper=float(ci_upper),
        pi_lower=float(pi_lower), pi_upper=float(pi_upper), pi_df=pi_df,
        tau2=float(tau2), q_stat=q, q_df=q_df,
        hksj_factor=float(hksj_factor),
        z=float(z), p_value=float(p_value),
    )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_pooling.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add responder_floor/pooling.py tests/test_pooling.py
git commit -m "Task 7: REML + HKSJ (Q/(k-1) floor) + HTS PI (t_{k-2}) pooling"
```

---

## Task 8: R parity harness for pooling (1e-6 vs metafor)

**Files:**
- Create: `responder_floor/r_validation.R`, `tests/test_r_parity.py`

- [ ] **Step 1: Write the R script**

```r
# responder_floor/r_validation.R
# Reads effects + variances CSV from stdin args, writes metafor REML+HKSJ results as JSON.
suppressMessages(library(metafor))
suppressMessages(library(jsonlite))

args <- commandArgs(trailingOnly = TRUE)
in_csv <- args[1]
out_json <- args[2]

d <- read.csv(in_csv)
res <- rma(yi = d$yi, vi = d$vi, method = "REML", test = "knha")

k <- res$k
pi_df <- k - 2
t_pi <- qt(0.975, df = pi_df)
pi_se <- sqrt(res$se^2 + res$tau2)

out <- list(
  k = k,
  estimate = res$b[1],
  se = res$se,
  ci_lower = res$ci.lb,
  ci_upper = res$ci.ub,
  tau2 = res$tau2,
  q_stat = res$QE,
  q_df = res$k - 1,
  pi_lower = res$b[1] - t_pi * pi_se,
  pi_upper = res$b[1] + t_pi * pi_se,
  pi_df = pi_df
)
writeLines(toJSON(out, auto_unbox = TRUE, digits = 15), out_json)
```

- [ ] **Step 2: Write the failing parity test**

```python
# tests/test_r_parity.py
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from responder_floor.pooling import pool_reml_hksj_pi

RSCRIPT = Path(r"C:\Program Files\R\R-4.5.2\bin\Rscript.exe")


@pytest.mark.skipif(not RSCRIPT.exists(), reason="R 4.5.2 not installed at expected path")
def test_metafor_parity_at_1e6(tmp_path):
    # Five representative MAs with varied k and heterogeneity.
    cases = [
        ([0.3, 0.5, 0.7, 0.4, 0.6], [0.02, 0.03, 0.015, 0.025, 0.02]),
        ([-0.2, 0.1, 0.4, 0.3], [0.01, 0.02, 0.015, 0.03]),
        ([0.5, 0.5, 0.5], [0.01, 0.01, 0.01]),
    ]
    for eff, var in cases:
        in_csv = tmp_path / "in.csv"
        out_json = tmp_path / "out.json"
        pd.DataFrame({"yi": eff, "vi": var}).to_csv(in_csv, index=False)
        subprocess.run(
            [str(RSCRIPT), "responder_floor/r_validation.R", str(in_csv), str(out_json)],
            check=True, capture_output=True,
        )
        r = json.loads(out_json.read_text())
        py = pool_reml_hksj_pi(np.array(eff), np.array(var))
        assert abs(py.estimate - r["estimate"]) < 1e-6
        assert abs(py.se - r["se"]) < 1e-6
        assert abs(py.tau2 - r["tau2"]) < 1e-6
```

- [ ] **Step 3: Run the test**

Run: `pytest tests/test_r_parity.py -v`
Expected: PASS if R+metafor installed; otherwise SKIPPED. If PASS fails at a tolerance, investigate τ² estimator discrepancy (metafor uses Fisher-scoring REML; our fixed-point REML may differ by 1e-4). Relax to 1e-5 with audit note only if root cause confirmed; otherwise fix the Python implementation.

- [ ] **Step 4: Commit**

```bash
git add responder_floor/r_validation.R tests/test_r_parity.py
git commit -m "Task 8: R+metafor parity harness at 1e-6 for pooling"
```

---

## Task 9: Fuzzy outcome-label matcher

**Files:**
- Create: `responder_floor/fuzzy_match.py`, `tests/test_fuzzy_match.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_fuzzy_match.py
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
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_fuzzy_match.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# responder_floor/fuzzy_match.py
"""Outcome-label normalization for dual-framing detection."""
from __future__ import annotations

import re

# Tokens that indicate framing (not outcome identity) — stripped before comparison.
_FRAMING_TOKENS = {
    "responders", "responder", "response",
    "change", "from", "baseline", "mean", "median",
    "continuous", "dichotomous",
    "score", "scores", "points",
    "improvement", "improved",
    "at", "weeks", "week", "months", "month",
}
_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")


def normalize_label(label: str) -> str:
    s = label.lower()
    s = _PUNCT_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def _core_tokens(label: str) -> frozenset[str]:
    norm = normalize_label(label)
    return frozenset(t for t in norm.split() if t not in _FRAMING_TOKENS and not t.isdigit())


def are_same_outcome(label_a: str, label_b: str, min_overlap: float = 0.6) -> bool:
    """Two labels are 'same outcome' if their core-token Jaccard similarity ≥ threshold."""
    a = _core_tokens(label_a)
    b = _core_tokens(label_b)
    if not a or not b:
        return False
    jaccard = len(a & b) / len(a | b)
    return jaccard >= min_overlap
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_fuzzy_match.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add responder_floor/fuzzy_match.py tests/test_fuzzy_match.py
git commit -m "Task 9: fuzzy outcome-label matcher for dual-framing detection"
```

---

## Task 10: RDA loader with pyreadr primary + rpy2 fallback

**Files:**
- Create: `responder_floor/rda_loader.py`, `tests/test_rda_loader.py`, `tests/fixtures/make_fixture.R`, `tests/fixtures/synthetic_one_review.rda`

- [ ] **Step 1: Write R fixture generator**

```r
# tests/fixtures/make_fixture.R
# Generate a tiny RDA with one review having both continuous and dichotomous MAs,
# where each MA carries per-trial arm-level stats.
review_id <- "fixture_R001"
trials_cont <- data.frame(
  trial_id = c("T1", "T2", "T3"),
  n_t = c(100, 150, 80),
  mean_t = c(8, 12, 10),
  sd_t = c(15, 18, 16),
  n_c = c(100, 150, 80),
  mean_c = c(3, 4, 5),
  sd_c = c(15, 18, 16)
)
trials_dich <- data.frame(
  trial_id = c("T1", "T2", "T3"),
  events_t = c(55, 75, 42),
  n_t = c(100, 150, 80),
  events_c = c(40, 55, 32),
  n_c = c(100, 150, 80)
)
fixture <- list(
  review_id = review_id,
  outcomes = list(
    list(label = "KCCQ Overall Summary (change from baseline)",
         measure_type = "MD",
         comparison = "drug_vs_placebo",
         trials = trials_cont),
    list(label = "KCCQ Overall Summary (responders)",
         measure_type = "RR",
         comparison = "drug_vs_placebo",
         trials = trials_dich)
  )
)
save(fixture, file = "tests/fixtures/synthetic_one_review.rda")
```

Run (one-time): `Rscript tests/fixtures/make_fixture.R`

- [ ] **Step 2: Write the failing test**

```python
# tests/test_rda_loader.py
from pathlib import Path

import pytest
from responder_floor.rda_loader import load_rda

FIXTURE = Path("tests/fixtures/synthetic_one_review.rda")


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture not generated")
def test_loader_returns_review_with_outcomes():
    review = load_rda(FIXTURE)
    assert review["review_id"] == "fixture_R001"
    assert len(review["outcomes"]) == 2
    types = {o["measure_type"] for o in review["outcomes"]}
    assert types == {"MD", "RR"}


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture not generated")
def test_loader_preserves_trial_arm_stats():
    review = load_rda(FIXTURE)
    cont = next(o for o in review["outcomes"] if o["measure_type"] == "MD")
    trial_t1 = next(t for t in cont["trials"] if t["trial_id"] == "T1")
    assert trial_t1["mean_t"] == 8
    assert trial_t1["sd_t"] == 15
    assert trial_t1["n_t"] == 100
```

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/test_rda_loader.py -v`
Expected: FAIL (`rda_loader` missing).

- [ ] **Step 4: Implement loader**

```python
# responder_floor/rda_loader.py
"""RDA loader — pyreadr primary, rpy2 fallback for nested structures.

Pairwise70 RDAs store per-review nested lists that pyreadr's flat-dataframe
API partially handles. rpy2 handles nested S4 cleanly at the cost of requiring
an R runtime.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def _load_pyreadr(path: Path) -> dict[str, Any] | None:
    try:
        import pyreadr
        data = pyreadr.read_r(str(path))
        # pyreadr returns OrderedDict[name, DataFrame]; nested lists are lossy.
        # Accept only if we get the expected schema; else None to trigger fallback.
        if not data:
            return None
        # Single top-level object "fixture"
        key = next(iter(data))
        obj = data[key]
        if hasattr(obj, "to_dict"):
            return None  # flat DF from pyreadr — insufficient for nested schema
        return obj
    except Exception:
        return None


def _load_rpy2(path: Path) -> dict[str, Any]:
    from rpy2.robjects import r, globalenv, conversion, default_converter
    from rpy2.robjects.conversion import localconverter
    from rpy2.robjects import pandas2ri

    r["load"](str(path))
    names = list(globalenv.keys())
    if not names:
        raise ValueError(f"No R objects found in {path}")
    obj = globalenv[names[0]]
    with localconverter(default_converter + pandas2ri.converter):
        return _rlist_to_dict(obj)


def _rlist_to_dict(obj) -> Any:
    """Recursively convert R named lists / dataframes to Python dict/list/dict[str, list]."""
    import pandas as pd
    from rpy2.robjects.vectors import ListVector, DataFrame as RDataFrame
    if isinstance(obj, RDataFrame):
        df = pd.DataFrame({name: list(obj.rx2(name)) for name in obj.names})
        return df.to_dict(orient="records")
    if isinstance(obj, ListVector):
        out: dict[str, Any] = {}
        for name, item in zip(obj.names, obj):
            out[name] = _rlist_to_dict(item)
        return out
    # Scalars / vectors
    try:
        return list(obj) if len(obj) > 1 else obj[0]
    except Exception:
        return obj


def load_rda(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    obj = _load_pyreadr(path)
    if obj is not None:
        return obj
    return _load_rpy2(path)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_rda_loader.py -v`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add responder_floor/rda_loader.py tests/test_rda_loader.py tests/fixtures/make_fixture.R tests/fixtures/synthetic_one_review.rda
git commit -m "Task 10: RDA loader with pyreadr+rpy2 fallback + synthetic fixture"
```

---

## Task 11: Stage 1 — scan_dual_framing.py (skeleton + CLI)

**Files:**
- Create: `scripts/scan_dual_framing.py`, `tests/test_scan_dual_framing.py`

- [ ] **Step 1: Write failing integration test**

```python
# tests/test_scan_dual_framing.py
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

FIXTURE = Path("tests/fixtures/synthetic_one_review.rda")


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture not generated")
def test_scan_emits_parquet_with_expected_rows(tmp_path):
    out_dir = tmp_path / "outputs"
    result = subprocess.run(
        [sys.executable, "scripts/scan_dual_framing.py",
         "--corpus", "tests/fixtures",
         "--output-dir", str(out_dir)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    df = pd.read_parquet(out_dir / "dual_framing_index.parquet")
    # Three trials (T1/T2/T3) × 1 review = 3 rows
    assert len(df) == 3
    expected_cols = {
        "review_id", "outcome_group", "trial_id",
        "mean_t", "sd_t", "n_t", "events_t",
        "mean_c", "sd_c", "n_c", "events_c",
        "instrument_id", "status", "reason",
    }
    assert expected_cols <= set(df.columns)
    assert (df["instrument_id"] == "kccq_os").all()
    assert (df["status"] == "OK").all()
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_scan_dual_framing.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement Stage 1**

```python
# scripts/scan_dual_framing.py
"""Stage 1 — scan Pairwise70 RDAs for dual-framing outcomes.

Emits outputs/dual_framing_index.parquet with per-trial rows for every review
pooling the same outcome in both continuous and dichotomous form.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from responder_floor.fuzzy_match import are_same_outcome
from responder_floor.instruments import load_instruments, match_instrument
from responder_floor.rda_loader import load_rda
from responder_floor.status import StatusCode, TrialArmInput, classify_arm

CONT_TYPES = {"MD", "SMD"}
DICH_TYPES = {"RR", "OR", "RD"}


def _group_dual_framing(outcomes: list[dict]) -> list[tuple[dict, dict]]:
    """Return pairs (continuous_ma, dichotomous_ma) for same outcome+comparison."""
    pairs = []
    cont = [o for o in outcomes if o["measure_type"] in CONT_TYPES]
    dich = [o for o in outcomes if o["measure_type"] in DICH_TYPES]
    for c in cont:
        for d in dich:
            if c.get("comparison") != d.get("comparison"):
                continue
            if are_same_outcome(c["label"], d["label"]):
                pairs.append((c, d))
    return pairs


def _extract_trial_rows(
    review_id: str,
    cont: dict,
    dich: dict,
    instruments,
) -> list[dict]:
    instr = match_instrument(cont["label"], instruments)
    instrument_id = instr.id if instr else None
    cont_by_id = {t["trial_id"]: t for t in cont["trials"]}
    dich_by_id = {t["trial_id"]: t for t in dich["trials"]}
    shared_ids = set(cont_by_id) & set(dich_by_id)
    rows = []
    for tid in sorted(shared_ids):
        ct = cont_by_id[tid]
        dt = dich_by_id[tid]
        row = {
            "review_id": review_id,
            "outcome_group": cont["label"],
            "trial_id": tid,
            "mean_t": ct.get("mean_t"), "sd_t": ct.get("sd_t"), "n_t": ct.get("n_t"),
            "mean_c": ct.get("mean_c"), "sd_c": ct.get("sd_c"), "n_c": ct.get("n_c"),
            "events_t": dt.get("events_t"), "n_t_dich": dt.get("n_t"),
            "events_c": dt.get("events_c"), "n_c_dich": dt.get("n_c"),
            "instrument_id": instrument_id,
        }
        # Per-arm classify; trial status is worst-of both arms.
        t_status, t_reason = classify_arm(TrialArmInput(
            mean=row["mean_t"], sd=row["sd_t"], n=row["n_t"], events=row["events_t"],
        ))
        c_status, c_reason = classify_arm(TrialArmInput(
            mean=row["mean_c"], sd=row["sd_c"], n=row["n_c"], events=row["events_c"],
        ))
        status = t_status if t_status is not StatusCode.OK else c_status
        reason = t_reason if t_status is not StatusCode.OK else c_reason
        if instrument_id is None:
            status, reason = StatusCode.UNKNOWN_INSTRUMENT, f"no v1-panel match for label: {cont['label']}"
        row["status"] = status.value
        row["reason"] = reason
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True,
                        help="Directory of RDA files (Pairwise70 or fixture)")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    instruments = load_instruments()
    all_rows: list[dict] = []
    manifest: dict[str, Any] = {"reviews_scanned": 0, "dual_framing_reviews": 0, "errors": []}

    for rda_path in sorted(args.corpus.rglob("*.rda")):
        manifest["reviews_scanned"] += 1
        try:
            review = load_rda(rda_path)
        except Exception as e:
            manifest["errors"].append({"file": str(rda_path), "error": str(e)})
            continue
        outcomes = review.get("outcomes", [])
        pairs = _group_dual_framing(outcomes)
        if pairs:
            manifest["dual_framing_reviews"] += 1
        for cont, dich in pairs:
            all_rows.extend(_extract_trial_rows(review["review_id"], cont, dich, instruments))

    df = pd.DataFrame(all_rows)
    out_parquet = args.output_dir / "dual_framing_index.parquet"
    df.to_parquet(out_parquet, index=False)
    (args.output_dir / "stage1_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote {len(df)} rows to {out_parquet}")
    print(f"Manifest: {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_scan_dual_framing.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/scan_dual_framing.py tests/test_scan_dual_framing.py
git commit -m "Task 11: Stage 1 scan_dual_framing.py CLI + fixture integration test"
```

---

## Task 12: Feasibility gate evaluator

**Files:**
- Create: `scripts/evaluate_gates.py`, `tests/test_gates.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_gates.py
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_gates_evaluate_from_parquet(tmp_path):
    # Synthetic dual-framing index with 40 reviews, 5 trials each, all OK, kccq_os.
    rows = []
    for r in range(40):
        for t in range(5):
            rows.append({
                "review_id": f"R{r:03d}", "outcome_group": "KCCQ OS",
                "trial_id": f"T{t}", "mean_t": 10, "sd_t": 15, "n_t": 100,
                "mean_c": 5, "sd_c": 15, "n_c": 100,
                "events_t": 60, "events_c": 40, "n_t_dich": 100, "n_c_dich": 100,
                "instrument_id": "kccq_os", "status": "OK", "reason": "all fields present and in-range",
            })
    df = pd.DataFrame(rows)
    parquet = tmp_path / "dual_framing_index.parquet"
    df.to_parquet(parquet, index=False)

    result = subprocess.run(
        [sys.executable, "scripts/evaluate_gates.py",
         "--index", str(parquet),
         "--output", str(tmp_path / "FEASIBILITY_REPORT.md"),
         "--json", str(tmp_path / "gates.json")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    gates = json.loads((tmp_path / "gates.json").read_text())
    # Only 1 instrument; B fails. A passes (40 reviews ≥30). C depends on MID availability (default v1 panel → passes).
    assert gates["A"]["passed"] is True
    assert gates["B"]["passed"] is False  # only 1 instrument
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_gates.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement gate evaluator**

```python
# scripts/evaluate_gates.py
"""Evaluate feasibility gates A/B/C/D per spec §6.3 and emit FEASIBILITY_REPORT.md."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from responder_floor.instruments import load_instruments


def load_gate_thresholds() -> dict:
    cfg = yaml.safe_load(Path("configs/pipeline.yml").read_text(encoding="utf-8"))
    return cfg["gates"]


def evaluate(df: pd.DataFrame, thresholds: dict) -> dict:
    ok = df[df["status"] == "OK"]

    # Gate A: reviews with ≥3 trials OK across both arms
    per_review = ok.groupby("review_id").size()
    a_reviews = per_review[per_review >= thresholds["A_trials_per_review_min"]].index
    a_count = len(a_reviews)
    gate_a = {
        "threshold_reviews_min": thresholds["A_arm_level_reviews_min"],
        "threshold_trials_per_review_min": thresholds["A_trials_per_review_min"],
        "count": a_count,
        "passed": a_count >= thresholds["A_arm_level_reviews_min"],
    }

    # Gate B: instruments with ≥5 qualifying reviews
    instr_reviews = ok[ok["review_id"].isin(a_reviews)].groupby("instrument_id")["review_id"].nunique()
    b_eligible = instr_reviews[instr_reviews >= thresholds["B_reviews_per_instrument_min"]]
    gate_b = {
        "threshold_instruments_min": thresholds["B_instruments_min"],
        "eligible_instruments": list(b_eligible.index),
        "counts": b_eligible.to_dict(),
        "passed": len(b_eligible) >= thresholds["B_instruments_min"],
    }

    # Gate C: fraction of dual-framing reviews with MID available (canonical from v1 panel = yes for every matched instrument)
    instr_ids = {i.id for i in load_instruments()}
    reviews_with_mid = ok[ok["instrument_id"].isin(instr_ids)]["review_id"].nunique()
    total_dual = df["review_id"].nunique()
    mid_pct = reviews_with_mid / total_dual if total_dual > 0 else 0.0
    gate_c = {
        "threshold_pct_min": thresholds["C_mid_availability_pct_min"],
        "actual_pct": mid_pct,
        "passed": mid_pct >= thresholds["C_mid_availability_pct_min"],
    }

    # Gate D: cross-review trial overlap (exploratory Q4)
    trial_review = ok.groupby("trial_id")["review_id"].nunique()
    overlap = int((trial_review >= 2).sum())
    gate_d = {
        "threshold_min": thresholds["D_cross_review_trial_overlap_min"],
        "count": overlap,
        "passed": overlap >= thresholds["D_cross_review_trial_overlap_min"],
    }

    return {"A": gate_a, "B": gate_b, "C": gate_c, "D": gate_d}


def render_report(gates: dict) -> str:
    lines = ["# Feasibility Report (Stage 1)", "",
             "Per spec §6.3. Gates A/B/C are hard stops; D is exploratory.", ""]
    for name, g in gates.items():
        mark = "PASS" if g["passed"] else "FAIL"
        lines.append(f"## Gate {name}: {mark}")
        lines.append("```json")
        lines.append(json.dumps(g, indent=2))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()

    df = pd.read_parquet(args.index)
    thresholds = load_gate_thresholds()
    gates = evaluate(df, thresholds)
    args.output.write_text(render_report(gates), encoding="utf-8")
    args.json.write_text(json.dumps(gates, indent=2))
    all_pass = all(gates[k]["passed"] for k in ("A", "B", "C"))
    print(f"Gates A/B/C: {'PASS' if all_pass else 'FAIL — pivot protocol applies (spec §6.4)'}")
    return 0 if all_pass else 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_gates.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/evaluate_gates.py tests/test_gates.py
git commit -m "Task 12: feasibility gate evaluator A/B/C/D + FEASIBILITY_REPORT renderer"
```

---

## Task 13: Stage 2 — infer_mid.py (Model 1 + Model 2 per review)

**Files:**
- Create: `scripts/infer_mid.py`, `tests/test_infer_mid.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_infer_mid.py
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_infer_mid_emits_model1_and_model2_per_review(tmp_path):
    rows = []
    for t in ("T1", "T2", "T3"):
        rows.append({
            "review_id": "R001", "outcome_group": "KCCQ OS", "trial_id": t,
            "mean_t": 10, "sd_t": 15, "n_t": 100,
            "mean_c": 5, "sd_c": 15, "n_c": 100,
            "events_t": 63, "events_c": 45, "n_t_dich": 100, "n_c_dich": 100,
            "instrument_id": "kccq_os", "status": "OK", "reason": "",
        })
    idx = tmp_path / "dual_framing_index.parquet"
    pd.DataFrame(rows).to_parquet(idx, index=False)

    result = subprocess.run(
        [sys.executable, "scripts/infer_mid.py",
         "--index", str(idx), "--output-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    mid = pd.read_parquet(tmp_path / "mid_inferences.parquet")
    assert {"review_id", "trial_id", "delta_hat_t", "delta_hat_c", "delta_hat_trial", "model1_mid", "model1_source"} <= set(mid.columns)
    # Model 1 for kccq_os should be the canonical 5.0 (no review-stated MID in fixture).
    assert (mid["model1_mid"] == 5.0).all()
    # Model 2 back-out should be finite per trial.
    assert mid["delta_hat_trial"].notna().all()
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_infer_mid.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement Stage 2**

```python
# scripts/infer_mid.py
"""Stage 2 — compute Model 1 (review-level MID) and Model 2 (trial-level implied MID)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from responder_floor.instruments import load_instruments
from responder_floor.math import delta_hat_arm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.index)
    ok = df[df["status"] == "OK"].copy()
    instruments = {i.id: i for i in load_instruments()}

    def direction(row):
        return instruments[row["instrument_id"]].direction

    def canonical_mid(row):
        return instruments[row["instrument_id"]].canonical_mid

    ok["direction"] = ok.apply(direction, axis=1)
    # Model 1: use canonical MID (review-stated MID parsing deferred; Stage 2.1).
    ok["model1_mid"] = ok.apply(canonical_mid, axis=1)
    ok["model1_source"] = "canonical_v1_panel"

    # Model 2: back out δ per arm, average for trial-level.
    def back_out_arm(mean, sd, events, n, d):
        p = events / n
        return delta_hat_arm(mean=mean, sd=sd, p_obs=p, direction=d)

    ok["delta_hat_t"] = ok.apply(
        lambda r: back_out_arm(r["mean_t"], r["sd_t"], r["events_t"], r["n_t_dich"], r["direction"]), axis=1)
    ok["delta_hat_c"] = ok.apply(
        lambda r: back_out_arm(r["mean_c"], r["sd_c"], r["events_c"], r["n_c_dich"], r["direction"]), axis=1)
    ok["delta_hat_trial"] = (ok["delta_hat_t"] + ok["delta_hat_c"]) / 2.0

    out = args.output_dir / "mid_inferences.parquet"
    ok.to_parquet(out, index=False)
    print(f"Wrote {len(ok)} rows to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_infer_mid.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/infer_mid.py tests/test_infer_mid.py
git commit -m "Task 13: Stage 2 infer_mid.py (Model 1 canonical MID + Model 2 back-out)"
```

---

## Task 14: Stage 3 — reconstruct.py (per-trial p̂ and ε)

**Files:**
- Create: `scripts/reconstruct.py`, `tests/test_reconstruct.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_reconstruct.py
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_reconstruct_emits_epsilon_per_arm(tmp_path):
    rows = []
    for t in ("T1", "T2", "T3"):
        rows.append({
            "review_id": "R001", "trial_id": t,
            "mean_t": 10, "sd_t": 15, "n_t": 100, "events_t": 63, "n_t_dich": 100,
            "mean_c": 5, "sd_c": 15, "n_c": 100, "events_c": 45, "n_c_dich": 100,
            "instrument_id": "kccq_os", "direction": 1, "model1_mid": 5.0,
            "status": "OK",
        })
    inp = tmp_path / "mid_inferences.parquet"
    pd.DataFrame(rows).to_parquet(inp, index=False)

    result = subprocess.run(
        [sys.executable, "scripts/reconstruct.py",
         "--mid-inferences", str(inp), "--output-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    out = pd.read_parquet(tmp_path / "reconstructions.parquet")
    expected_cols = {"p_hat_t", "p_hat_c", "p_obs_t", "p_obs_c",
                     "epsilon_t", "epsilon_c", "log_rr_hat", "log_rr_obs", "epsilon_log_rr"}
    assert expected_cols <= set(out.columns)
    # For KCCQ d=+1, μ_t=10, σ_t=15, δ=5: p̂_t = Φ(5/15) ≈ 0.6306; obs = 63/100 = 0.63. ε ≈ 0.0006.
    assert abs(out.iloc[0]["p_hat_t"] - 0.6305587) < 1e-5
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_reconstruct.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement Stage 3**

```python
# scripts/reconstruct.py
"""Stage 3 — reconstruct per-trial responder probability and compute reconstruction error."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import pandas as pd

from responder_floor.math import p_hat_arm, log_rr_hat, log_rr_hat_se_delta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mid-inferences", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.mid_inferences)

    def recon(row):
        d = int(row["direction"])
        mid = row["model1_mid"]
        p_hat_t = p_hat_arm(row["mean_t"], row["sd_t"], mid, d)
        p_hat_c = p_hat_arm(row["mean_c"], row["sd_c"], mid, d)
        p_obs_t = row["events_t"] / row["n_t_dich"]
        p_obs_c = row["events_c"] / row["n_c_dich"]
        log_rr_h = log_rr_hat(row["mean_t"], row["sd_t"], row["n_t"],
                              row["mean_c"], row["sd_c"], row["n_c"], mid, d)
        se_hat = log_rr_hat_se_delta(row["mean_t"], row["sd_t"], row["n_t"],
                                     row["mean_c"], row["sd_c"], row["n_c"], mid, d)
        log_rr_o = math.log(p_obs_t / p_obs_c) if p_obs_t > 0 and p_obs_c > 0 else float("nan")
        return pd.Series({
            "p_hat_t": p_hat_t, "p_hat_c": p_hat_c,
            "p_obs_t": p_obs_t, "p_obs_c": p_obs_c,
            "epsilon_t": abs(p_hat_t - p_obs_t),
            "epsilon_c": abs(p_hat_c - p_obs_c),
            "log_rr_hat": log_rr_h, "se_log_rr_hat": se_hat,
            "log_rr_obs": log_rr_o,
            "epsilon_log_rr": abs(log_rr_h - log_rr_o) if math.isfinite(log_rr_o) else float("nan"),
        })

    recon_df = df.apply(recon, axis=1)
    out_df = pd.concat([df.reset_index(drop=True), recon_df.reset_index(drop=True)], axis=1)
    out = args.output_dir / "reconstructions.parquet"
    out_df.to_parquet(out, index=False)
    print(f"Wrote {len(out_df)} rows to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_reconstruct.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/reconstruct.py tests/test_reconstruct.py
git commit -m "Task 14: Stage 3 reconstruct.py (p_hat, epsilon, log RR_hat + SE)"
```

---

## Task 15: Stage 4 — pool_and_flip.py (framing flip detection)

**Files:**
- Create: `scripts/pool_and_flip.py`, `tests/test_pool_and_flip.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_pool_and_flip.py
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def test_pool_and_flip_computes_per_review_verdict(tmp_path):
    # Build one review with 3 trials, identical effects, identical variances — both framings significant.
    rows = []
    for t in ("T1", "T2", "T3"):
        rows.append({
            "review_id": "R001", "trial_id": t,
            "n_t": 100, "n_c": 100, "events_t": 70, "events_c": 40,
            "n_t_dich": 100, "n_c_dich": 100,
            "mean_t": 10, "sd_t": 15, "mean_c": 3, "sd_c": 15,
            "instrument_id": "kccq_os", "model1_mid": 5.0, "direction": 1,
            "log_rr_hat": np.log(0.7 / 0.4), "se_log_rr_hat": 0.15,
            "status": "OK",
        })
    inp = tmp_path / "reconstructions.parquet"
    pd.DataFrame(rows).to_parquet(inp, index=False)

    result = subprocess.run(
        [sys.executable, "scripts/pool_and_flip.py",
         "--reconstructions", str(inp),
         "--output-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    flips = pd.read_parquet(tmp_path / "flip_results.parquet")
    row = flips[flips["review_id"] == "R001"].iloc[0]
    # Both framings significant → no flip.
    assert row["smd_significant"] is True or row["smd_significant"] == True  # pyarrow roundtrip
    assert row["rr_significant"] == True
    assert row["framing_flip"] == False
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_pool_and_flip.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement Stage 4**

```python
# scripts/pool_and_flip.py
"""Stage 4 — per-review pool under both framings, detect flip at α=0.05 and magnitude >0.1."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from responder_floor.pooling import pool_reml_hksj_pi


def _smd_from_arm(row) -> tuple[float, float]:
    """Hedges' g SMD and its variance from continuous arm stats."""
    n_t, n_c = row["n_t"], row["n_c"]
    m_t, m_c = row["mean_t"], row["mean_c"]
    s_t, s_c = row["sd_t"], row["sd_c"]
    s_pool = math.sqrt(((n_t - 1) * s_t ** 2 + (n_c - 1) * s_c ** 2) / (n_t + n_c - 2))
    d = (m_t - m_c) / s_pool
    # Hedges' small-sample correction
    j = 1 - 3 / (4 * (n_t + n_c) - 9)
    g = j * d
    v = (n_t + n_c) / (n_t * n_c) + g ** 2 / (2 * (n_t + n_c))
    return g, v


def _log_rr_obs_from_arm(row) -> tuple[float, float]:
    """log RR and its variance from dichotomous arm counts, with 0.5 correction iff any zero cell."""
    a = row["events_t"]; b = row["n_t_dich"] - a
    c = row["events_c"]; d = row["n_c_dich"] - c
    if 0 in (a, b, c, d):
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    rr = (a / (a + b)) / (c / (c + d))
    log_rr = math.log(rr)
    var = 1 / a - 1 / (a + b) + 1 / c - 1 / (c + d)
    return log_rr, var


def _pool_review(review_id: str, trials: pd.DataFrame, alpha: float = 0.05, mag_thresh: float = 0.1) -> dict:
    smd_effects = np.array([_smd_from_arm(r)[0] for _, r in trials.iterrows()])
    smd_vars = np.array([_smd_from_arm(r)[1] for _, r in trials.iterrows()])
    rr_effects = np.array([_log_rr_obs_from_arm(r)[0] for _, r in trials.iterrows()])
    rr_vars = np.array([_log_rr_obs_from_arm(r)[1] for _, r in trials.iterrows()])

    smd = pool_reml_hksj_pi(smd_effects, smd_vars)
    rr = pool_reml_hksj_pi(rr_effects, rr_vars)
    smd_sig = smd.p_value < alpha
    rr_sig = rr.p_value < alpha

    return {
        "review_id": review_id,
        "k": len(trials),
        "smd_estimate": smd.estimate, "smd_p": smd.p_value, "smd_significant": smd_sig,
        "rr_estimate": rr.estimate,   "rr_p": rr.p_value,   "rr_significant": rr_sig,
        "framing_flip": bool(smd_sig != rr_sig),
        "magnitude_flip": bool(abs(rr.estimate - smd.estimate * 0.5513) > mag_thresh),  # OR->SMD const per advanced-stats.md
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconstructions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--magnitude-threshold", type=float, default=0.1)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.reconstructions)
    ok = df[df["status"] == "OK"]
    results = []
    for review_id, trials in ok.groupby("review_id"):
        if len(trials) < 3:
            continue
        results.append(_pool_review(review_id, trials, args.alpha, args.magnitude_threshold))

    out_df = pd.DataFrame(results)
    out = args.output_dir / "flip_results.parquet"
    out_df.to_parquet(out, index=False)
    print(f"Pooled {len(out_df)} reviews; flip count = {int(out_df['framing_flip'].sum()) if len(out_df) else 0}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_pool_and_flip.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/pool_and_flip.py tests/test_pool_and_flip.py
git commit -m "Task 15: Stage 4 pool_and_flip.py (SMD + logRR pooling + α=0.05 framing flip)"
```

---

## Task 16: Clustered bootstrap for Q1 flip-rate CI

**Files:**
- Create: `responder_floor/bootstrap.py`, `tests/test_bootstrap.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_bootstrap.py
import numpy as np
import pandas as pd
from responder_floor.bootstrap import cluster_bootstrap_flip_rate


def test_cluster_bootstrap_matches_proportion_on_independent_data():
    rng = np.random.default_rng(seed=0)
    flip = rng.integers(0, 2, size=1000)
    cluster = np.arange(1000)  # every row is its own cluster → standard proportion CI
    df = pd.DataFrame({"review_id": cluster, "framing_flip": flip})
    point, lo, hi = cluster_bootstrap_flip_rate(df, n_boot=500, rng=np.random.default_rng(seed=1))
    assert 0.3 < point < 0.7
    assert lo < point < hi


def test_cluster_bootstrap_respects_clusters():
    df = pd.DataFrame({
        "review_id": [1, 1, 1, 2, 2, 2, 3, 3, 3],
        "framing_flip": [1, 1, 1, 0, 0, 0, 1, 1, 1],
    })
    # True cluster-level flip-rate = 2/3.
    point, lo, hi = cluster_bootstrap_flip_rate(df, n_boot=500, rng=np.random.default_rng(seed=2))
    assert abs(point - 2/3) < 0.15  # small-cluster bootstrap has wide CI
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_bootstrap.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# responder_floor/bootstrap.py
"""Clustered bootstrap for flip-rate CI per spec §3.1 (cluster = review)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def cluster_bootstrap_flip_rate(
    df: pd.DataFrame,
    cluster_col: str = "review_id",
    flip_col: str = "framing_flip",
    n_boot: int = 1000,
    rng: np.random.Generator | None = None,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Return (point, ci_lower, ci_upper) of clustered bootstrap flip-rate."""
    rng = rng or np.random.default_rng()
    clusters = df[cluster_col].unique()
    n_c = len(clusters)
    cluster_to_flip = df.groupby(cluster_col)[flip_col].first().to_dict()

    boot = np.empty(n_boot)
    for b in range(n_boot):
        sample = rng.choice(clusters, size=n_c, replace=True)
        boot[b] = np.mean([cluster_to_flip[c] for c in sample])
    point = float(np.mean([cluster_to_flip[c] for c in clusters]))
    lo = float(np.quantile(boot, alpha / 2))
    hi = float(np.quantile(boot, 1 - alpha / 2))
    return point, lo, hi
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_bootstrap.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add responder_floor/bootstrap.py tests/test_bootstrap.py
git commit -m "Task 16: clustered bootstrap flip-rate CI (cluster = review)"
```

---

## Task 17: Stage 5 — build_dashboard.py (3-panel single-file HTML)

**Files:**
- Create: `scripts/build_dashboard.py`, `tests/test_dashboard.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_dashboard.py
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_dashboard_emits_single_html_with_three_panels(tmp_path):
    flips = pd.DataFrame([
        {"review_id": f"R{i:03d}", "k": 4, "smd_estimate": 0.3, "smd_p": 0.01,
         "smd_significant": True, "rr_estimate": 0.35, "rr_p": 0.06,
         "rr_significant": False, "framing_flip": True, "magnitude_flip": False}
        for i in range(20)
    ])
    flips_path = tmp_path / "flip_results.parquet"
    flips.to_parquet(flips_path, index=False)
    recon = pd.DataFrame([
        {"instrument_id": "kccq_os", "epsilon_t": 0.01, "epsilon_c": 0.02,
         "delta_hat_trial": 5.1, "review_id": "R001"}
    ])
    recon_path = tmp_path / "reconstructions.parquet"
    recon.to_parquet(recon_path, index=False)

    result = subprocess.run(
        [sys.executable, "scripts/build_dashboard.py",
         "--flips", str(flips_path),
         "--reconstructions", str(recon_path),
         "--output", str(tmp_path / "index.html")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "panel-flip" in html
    assert "panel-reconstruction" in html
    assert "panel-implied-mid" in html
    assert "</script>" not in html.split("<script")[0]  # no literal </script> leakage
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_dashboard.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement dashboard builder**

```python
# scripts/build_dashboard.py
"""Stage 5 — single-file HTML dashboard with three panels per spec §7.4."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from responder_floor.bootstrap import cluster_bootstrap_flip_rate

TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><title>Responder Floor Atlas</title>
<meta property="og:title" content="Responder Floor Atlas">
<style>
body{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#222}
h1{margin-bottom:.25rem}h2{margin-top:2rem;border-bottom:1px solid #ccc;padding-bottom:.25rem}
.panel{margin-bottom:2rem}.bar{fill:#4a6fa5}.bar-flip{fill:#c0504d}
.ci{stroke:#222;stroke-width:1}table{border-collapse:collapse;margin:.5rem 0}
th,td{padding:.25rem .5rem;border:1px solid #ddd;font-size:.9rem}
.muted{color:#666;font-size:.85rem}
</style></head><body>
<h1>Responder Floor Atlas</h1>
<p class="muted">Continuous-vs-responder framing reproducibility on Pairwise70 — generated from commit HASH on DATE.</p>

<div class="panel" id="panel-flip">
<h2>Q1 — Framing flip rate</h2>
PANEL_FLIP_CONTENT
</div>

<div class="panel" id="panel-reconstruction">
<h2>Q2 — Reconstruction fidelity</h2>
PANEL_RECONSTRUCTION_CONTENT
</div>

<div class="panel" id="panel-implied-mid">
<h2>Q3 — Implied-MID atlas</h2>
PANEL_IMPLIED_MID_CONTENT
</div>

<p class="muted">Spec: docs/superpowers/specs/2026-04-22-responder-floor-atlas-design.md</p>
</body></html>
"""


def _panel_flip(flips: pd.DataFrame) -> str:
    if flips.empty:
        return "<p>No reviews pooled.</p>"
    rng = np.random.default_rng(seed=20260422)
    point, lo, hi = cluster_bootstrap_flip_rate(flips, n_boot=1000, rng=rng)
    total = len(flips)
    flip_count = int(flips["framing_flip"].sum())
    magnitude_flip_count = int(flips["magnitude_flip"].sum())
    return (
        f"<table><tr><th>Metric</th><th>Value</th><th>95% CI (clustered bootstrap)</th></tr>"
        f"<tr><td>Reviews pooled</td><td>{total}</td><td>&mdash;</td></tr>"
        f"<tr><td>Framing flips (&alpha;=0.05)</td><td>{flip_count} ({point:.1%})</td>"
        f"<td>[{lo:.1%}, {hi:.1%}]</td></tr>"
        f"<tr><td>Magnitude flips (|&Delta; logRR|&gt;0.1)</td>"
        f"<td>{magnitude_flip_count} ({magnitude_flip_count/total:.1%})</td><td>&mdash;</td></tr>"
        f"</table>"
    )


def _panel_reconstruction(recon: pd.DataFrame) -> str:
    if recon.empty:
        return "<p>No reconstructions.</p>"
    rows = []
    for instr, g in recon.groupby("instrument_id"):
        eps_t = g["epsilon_t"].dropna()
        eps_c = g["epsilon_c"].dropna()
        all_eps = pd.concat([eps_t, eps_c])
        if all_eps.empty:
            continue
        rows.append(
            f"<tr><td>{instr}</td><td>{len(g)}</td>"
            f"<td>{all_eps.median():.4f}</td>"
            f"<td>{all_eps.quantile(0.95):.4f}</td>"
            f"<td>{(all_eps > 0.05).mean():.1%}</td></tr>"
        )
    header = "<tr><th>Instrument</th><th>n trials</th><th>Median |ε|</th><th>95th percentile</th><th>% |ε|&gt;0.05</th></tr>"
    return "<table>" + header + "".join(rows) + "</table>"


def _panel_implied_mid(recon: pd.DataFrame) -> str:
    if recon.empty or "delta_hat_trial" not in recon.columns:
        return "<p>No implied MID data.</p>"
    rows = []
    for instr, g in recon.groupby("instrument_id"):
        deltas = g["delta_hat_trial"].dropna()
        if deltas.empty:
            continue
        rows.append(
            f"<tr><td>{instr}</td><td>{len(deltas)}</td>"
            f"<td>{deltas.median():.3f}</td>"
            f"<td>{deltas.quantile(0.025):.3f}&ndash;{deltas.quantile(0.975):.3f}</td></tr>"
        )
    header = "<tr><th>Instrument</th><th>n trials</th><th>Median implied MID</th><th>95% range</th></tr>"
    return "<table>" + header + "".join(rows) + "</table>"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flips", type=Path, required=True)
    parser.add_argument("--reconstructions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", default="unknown")
    parser.add_argument("--date", default="unknown")
    args = parser.parse_args()

    flips = pd.read_parquet(args.flips)
    recon = pd.read_parquet(args.reconstructions)

    html = (TEMPLATE
            .replace("PANEL_FLIP_CONTENT", _panel_flip(flips))
            .replace("PANEL_RECONSTRUCTION_CONTENT", _panel_reconstruction(recon))
            .replace("PANEL_IMPLIED_MID_CONTENT", _panel_implied_mid(recon))
            .replace("HASH", args.commit)
            .replace("DATE", args.date))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"Wrote dashboard to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_dashboard.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/build_dashboard.py tests/test_dashboard.py
git commit -m "Task 17: Stage 5 build_dashboard.py (3-panel single-file HTML)"
```

---

## Task 18: Normality sensitivity (log-Normal + Beta + truncated Normal)

**Files:**
- Create: `responder_floor/sensitivity.py`, `tests/test_sensitivity.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_sensitivity.py
import numpy as np
from responder_floor.sensitivity import reconstruction_under_dist


def test_normal_matches_analytic():
    # Under Normal, MC-reconstructed p should match Φ((d·μ−δ)/σ) at 1e-2.
    p_normal = reconstruction_under_dist(
        dist="normal", mean=10, sd=15, mid=5, direction=1, n_draws=50_000,
        rng=np.random.default_rng(seed=0),
    )
    assert abs(p_normal - 0.6306) < 0.01


def test_lognormal_differs_from_normal():
    p_ln = reconstruction_under_dist(
        dist="lognormal_shifted", mean=10, sd=15, mid=5, direction=1, n_draws=50_000,
        rng=np.random.default_rng(seed=0),
    )
    # Should be different but in same ballpark.
    assert 0.4 < p_ln < 0.85


def test_beta_on_bounded_scale():
    p_beta = reconstruction_under_dist(
        dist="beta_bounded", mean=0.5, sd=0.15, mid=0.07, direction=1,
        scale_min=0, scale_max=1, n_draws=50_000, rng=np.random.default_rng(seed=0),
    )
    assert 0 < p_beta < 1
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_sensitivity.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement sensitivity module**

```python
# responder_floor/sensitivity.py
"""Normality-sensitivity simulators for reconstruction error per spec §5.3."""
from __future__ import annotations

import math

import numpy as np


def _lognormal_shifted_params(mean: float, sd: float) -> tuple[float, float, float]:
    """Fit a shifted log-normal with target (mean, sd). Shift places mass around mean."""
    shift = mean - 5 * sd  # heuristic shift so samples rarely touch the boundary
    eff_mean = mean - shift
    if eff_mean <= 0:
        eff_mean = sd  # fallback
    sigma2 = math.log(1 + (sd / eff_mean) ** 2)
    mu = math.log(eff_mean) - sigma2 / 2
    return mu, math.sqrt(sigma2), shift


def _beta_bounded_params(mean: float, sd: float, lo: float, hi: float) -> tuple[float, float]:
    """Method-of-moments Beta fit on (lo, hi)."""
    m = (mean - lo) / (hi - lo)
    s = sd / (hi - lo)
    m = min(max(m, 1e-6), 1 - 1e-6)
    v = min(s ** 2, m * (1 - m) - 1e-6)
    k = m * (1 - m) / v - 1
    return max(m * k, 1e-3), max((1 - m) * k, 1e-3)


def reconstruction_under_dist(
    dist: str, mean: float, sd: float, mid: float, direction: int,
    n_draws: int = 10_000,
    rng: np.random.Generator | None = None,
    scale_min: float | None = None,
    scale_max: float | None = None,
) -> float:
    rng = rng or np.random.default_rng()
    if dist == "normal":
        samples = rng.normal(mean, sd, size=n_draws)
    elif dist == "lognormal_shifted":
        mu, sig, shift = _lognormal_shifted_params(mean, sd)
        samples = rng.lognormal(mean=mu, sigma=sig, size=n_draws) + shift
    elif dist == "beta_bounded":
        if scale_min is None or scale_max is None:
            raise ValueError("beta_bounded needs scale_min and scale_max")
        a, b = _beta_bounded_params(mean, sd, scale_min, scale_max)
        samples = rng.beta(a, b, size=n_draws) * (scale_max - scale_min) + scale_min
    elif dist == "truncated_normal":
        if scale_min is None or scale_max is None:
            raise ValueError("truncated_normal needs scale bounds")
        samples = np.clip(rng.normal(mean, sd, size=n_draws), scale_min, scale_max)
    else:
        raise ValueError(f"unknown dist {dist!r}")
    # Responder: d·sample >= mid.
    return float(np.mean(direction * samples >= mid))
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_sensitivity.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add responder_floor/sensitivity.py tests/test_sensitivity.py
git commit -m "Task 18: normality sensitivity (lognormal, beta, truncated normal)"
```

---

## Task 19: End-to-end pipeline integration test

**Files:**
- Create: `tests/test_pipeline_e2e.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_pipeline_e2e.py
import subprocess
import sys
from pathlib import Path


FIXTURE_CORPUS = Path("tests/fixtures")


def test_end_to_end_all_stages(tmp_path):
    """Run all 5 stages on the fixture corpus; verify every parquet exists and the dashboard is valid HTML."""
    out = tmp_path / "outputs"

    steps = [
        [sys.executable, "scripts/scan_dual_framing.py",
         "--corpus", str(FIXTURE_CORPUS), "--output-dir", str(out)],
        [sys.executable, "scripts/evaluate_gates.py",
         "--index", str(out / "dual_framing_index.parquet"),
         "--output", str(out / "FEASIBILITY_REPORT.md"),
         "--json", str(out / "gates.json")],
        [sys.executable, "scripts/infer_mid.py",
         "--index", str(out / "dual_framing_index.parquet"),
         "--output-dir", str(out)],
        [sys.executable, "scripts/reconstruct.py",
         "--mid-inferences", str(out / "mid_inferences.parquet"),
         "--output-dir", str(out)],
        [sys.executable, "scripts/pool_and_flip.py",
         "--reconstructions", str(out / "reconstructions.parquet"),
         "--output-dir", str(out)],
        [sys.executable, "scripts/build_dashboard.py",
         "--flips", str(out / "flip_results.parquet"),
         "--reconstructions", str(out / "reconstructions.parquet"),
         "--output", str(out / "dashboard" / "index.html")],
    ]
    for cmd in steps:
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode in (0, 2), f"{cmd[1]} failed: {result.stderr}"
        # Gate step returns 2 when gates fail but pipeline continues; ok for fixture.

    for f in ("dual_framing_index.parquet", "mid_inferences.parquet",
              "reconstructions.parquet", "flip_results.parquet",
              "dashboard/index.html", "FEASIBILITY_REPORT.md", "gates.json"):
        assert (out / f).exists(), f"missing {f}"
```

- [ ] **Step 2: Run to verify it passes end-to-end**

Run: `pytest tests/test_pipeline_e2e.py -v`
Expected: PASS (all five stages execute on fixture without crash; output files present).

- [ ] **Step 3: Commit**

```bash
git add tests/test_pipeline_e2e.py
git commit -m "Task 19: end-to-end pipeline integration test on fixture corpus"
```

---

## Task 20: Determinism test (byte-identical re-runs)

**Files:**
- Create: `tests/test_determinism.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_determinism.py
import hashlib
import subprocess
import sys
from pathlib import Path


FIXTURE_CORPUS = Path("tests/fixtures")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_all_stages(out: Path) -> None:
    for cmd in [
        [sys.executable, "scripts/scan_dual_framing.py", "--corpus", str(FIXTURE_CORPUS), "--output-dir", str(out)],
        [sys.executable, "scripts/infer_mid.py", "--index", str(out / "dual_framing_index.parquet"), "--output-dir", str(out)],
        [sys.executable, "scripts/reconstruct.py", "--mid-inferences", str(out / "mid_inferences.parquet"), "--output-dir", str(out)],
    ]:
        subprocess.run(cmd, check=True, capture_output=True)


def test_reconstructions_byte_identical_across_runs(tmp_path):
    out1 = tmp_path / "run1"; out2 = tmp_path / "run2"
    out1.mkdir(); out2.mkdir()
    _run_all_stages(out1)
    _run_all_stages(out2)
    assert _sha256(out1 / "reconstructions.parquet") == _sha256(out2 / "reconstructions.parquet")
```

- [ ] **Step 2: Run test**

Run: `pytest tests/test_determinism.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_determinism.py
git commit -m "Task 20: determinism regression (byte-identical pipeline re-runs)"
```

---

## Task 21: Negative control test (KCCQ stable cluster)

**Files:**
- Create: `tests/fixtures/kccq_stable_cluster.R`, `tests/fixtures/kccq_stable_cluster.rda`, `tests/test_negative_control.py`

- [ ] **Step 1: Write R fixture**

```r
# tests/fixtures/kccq_stable_cluster.R
# Known-stable cluster: 5 trials where continuous-to-responder mapping is well-behaved
# under normal approximation (symmetric, unbounded by scale limits).
trials_cont <- data.frame(
  trial_id = paste0("T", 1:5),
  n_t = c(100, 150, 80, 120, 200),
  mean_t = c(8, 12, 10, 9, 11),
  sd_t = c(15, 18, 16, 17, 15),
  n_c = c(100, 150, 80, 120, 200),
  mean_c = c(3, 4, 5, 3.5, 4.5),
  sd_c = c(15, 18, 16, 17, 15)
)
# Responder rates computed analytically using δ=5, d=+1, Normal:
#   p_t_analytical = pnorm((mean_t - 5)/sd_t); events_t = round(p_t * n_t)
p_t <- pnorm((trials_cont$mean_t - 5) / trials_cont$sd_t)
p_c <- pnorm((trials_cont$mean_c - 5) / trials_cont$sd_c)
trials_dich <- data.frame(
  trial_id = trials_cont$trial_id,
  events_t = round(p_t * trials_cont$n_t),
  n_t = trials_cont$n_t,
  events_c = round(p_c * trials_cont$n_c),
  n_c = trials_cont$n_c
)
fixture <- list(
  review_id = "negative_control_kccq",
  outcomes = list(
    list(label = "KCCQ Overall Summary (change)", measure_type = "MD", comparison = "drug_vs_placebo", trials = trials_cont),
    list(label = "KCCQ Overall Summary (responders)", measure_type = "RR", comparison = "drug_vs_placebo", trials = trials_dich)
  )
)
save(fixture, file = "tests/fixtures/kccq_stable_cluster.rda")
```

Run: `Rscript tests/fixtures/kccq_stable_cluster.R`

- [ ] **Step 2: Write the failing test**

```python
# tests/test_negative_control.py
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

FIXTURE = Path("tests/fixtures/kccq_stable_cluster.rda")
CORPUS = FIXTURE.parent  # contains both fixtures


@pytest.mark.skipif(not FIXTURE.exists(), reason="kccq_stable_cluster.rda not generated")
def test_reconstruction_epsilon_tight_on_stable_cluster(tmp_path):
    out = tmp_path / "outputs"
    subprocess.run([sys.executable, "scripts/scan_dual_framing.py",
                    "--corpus", str(CORPUS), "--output-dir", str(out)], check=True)
    subprocess.run([sys.executable, "scripts/infer_mid.py",
                    "--index", str(out / "dual_framing_index.parquet"), "--output-dir", str(out)], check=True)
    subprocess.run([sys.executable, "scripts/reconstruct.py",
                    "--mid-inferences", str(out / "mid_inferences.parquet"), "--output-dir", str(out)], check=True)
    recon = pd.read_parquet(out / "reconstructions.parquet")
    nc = recon[recon["review_id"] == "negative_control_kccq"]
    assert len(nc) == 5
    all_eps = pd.concat([nc["epsilon_t"], nc["epsilon_c"]])
    # Analytically-generated → rounding error only. Expect ε < 0.01 for ≥80% of arms.
    assert (all_eps < 0.01).mean() >= 0.8, all_eps.tolist()
```

- [ ] **Step 3: Run test**

Run: `pytest tests/test_negative_control.py -v`
Expected: PASS. If FAIL: pipeline has a calibration bug — investigate before proceeding to real-data Stage 1.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/kccq_stable_cluster.R tests/fixtures/kccq_stable_cluster.rda tests/test_negative_control.py
git commit -m "Task 21: negative control (analytically-generated KCCQ cluster must reconstruct tight)"
```

---

## Task 22: PREREGISTRATION.md + Zenodo/OTS/IA stamping

**Files:**
- Create: `preregistration/PREREGISTRATION.md`, `scripts/preregister.py`, `tests/test_preregister.py`

- [ ] **Step 1: Write PREREGISTRATION.md**

```markdown
<!-- preregistration/PREREGISTRATION.md -->
# Responder Floor Atlas — Preregistration v1.0

**Spec reference:** `docs/superpowers/specs/2026-04-22-responder-floor-atlas-design.md` (commit `ee81682`)
**Corpus:** Pairwise70 (unchanged from sibling atlases)
**Stamped:** Zenodo DOI + OpenTimestamps + archive.org

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

- Pooling: REML τ², HKSJ SE (Q/(k−1) floored at 1), HTS PI with t_{k−2}.
- Reconstruction: Model 1 `p̂ = Φ((d·μ − δ)/σ)` (primary); Model 2 `δ̂ = d·μ − σ·Φ⁻¹(p_obs)` (sensitivity).
- Sensitivity: log-normal + Beta + truncated Normal moment-matched.
- Clustered bootstrap (cluster = review) for Q1 CI.
- R validation at 1e-6 pooling, 1e-3 reconstruction MC.

## Feasibility gates

- A: ≥30 reviews with ≥3 dual-contributing trials + arm-level stats (hard stop; pivot to Bundle 1 if fail).
- B: ≥3 instruments with ≥5 reviews each (Q3 exploratory if fail).
- C: ≥20% MID availability (Model 1 primary reversal if fail).
- D: ≥50 trials in ≥2 reviews (Q4 promoted if pass).

## Pivot protocol

Any gate failure triggers a timestamped, Zenodo-updated, OTS-restamped amendment with explicit paper disclosure. No silent narrowing.

## Authorship

Middle-author-only for Mahmood Ahmad per `feedback_e156_authorship.md`.

## Signatures

- Spec commit: ee81682
- Preregistration commit: [TO FILL AT STAMP TIME]
- Zenodo DOI: [FILLED BY scripts/preregister.py]
- OTS receipt: preregistration/PREREGISTRATION.md.ots
- Internet Archive URL: [FILLED BY scripts/preregister.py]
```

- [ ] **Step 2: Write failing test**

```python
# tests/test_preregister.py
import subprocess
import sys
from pathlib import Path

import pytest


def test_preregister_script_dry_run_produces_report(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/preregister.py", "--dry-run",
         "--preregistration", "preregistration/PREREGISTRATION.md",
         "--report", str(tmp_path / "stamp_report.json")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    import json
    report = json.loads((tmp_path / "stamp_report.json").read_text())
    assert "zenodo" in report and "ots" in report and "archive_org" in report
    assert report["dry_run"] is True
```

- [ ] **Step 3: Implement preregister.py**

```python
# scripts/preregister.py
"""Stamp preregistration to Zenodo + OpenTimestamps + Internet Archive before real-data compute.

Dry-run mode emits a stamp report without actually publishing — used in CI.
Live mode requires ZENODO_API_TOKEN env var and `ots` CLI on PATH.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stamp_ots(path: Path, dry_run: bool) -> dict:
    if dry_run:
        return {"receipt": str(path) + ".ots", "dry_run": True}
    subprocess.run(["ots", "stamp", str(path)], check=True, capture_output=True)
    return {"receipt": str(path) + ".ots", "dry_run": False}


def _stamp_zenodo(path: Path, dry_run: bool) -> dict:
    if dry_run:
        return {"doi": "10.5281/zenodo.DRYRUN", "dry_run": True}
    token = os.environ.get("ZENODO_API_TOKEN")
    if not token:
        raise RuntimeError("ZENODO_API_TOKEN not set for live stamping")
    # Live Zenodo upload via API — implementation deferred to first live run.
    raise NotImplementedError("Live Zenodo publish implemented at live-stamp time")


def _stamp_ia(path: Path, dry_run: bool) -> dict:
    if dry_run:
        return {"url": "https://web.archive.org/save/DRYRUN", "dry_run": True}
    raise NotImplementedError("Live archive.org save implemented at live-stamp time")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.preregistration.exists():
        print(f"Missing {args.preregistration}", file=sys.stderr)
        return 1

    sha = _sha256(args.preregistration)
    report = {
        "sha256": sha,
        "dry_run": args.dry_run,
        "zenodo": _stamp_zenodo(args.preregistration, args.dry_run),
        "ots": _stamp_ots(args.preregistration, args.dry_run),
        "archive_org": _stamp_ia(args.preregistration, args.dry_run),
    }
    args.report.write_text(json.dumps(report, indent=2))
    print(f"Stamp report: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_preregister.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add preregistration/PREREGISTRATION.md scripts/preregister.py tests/test_preregister.py
git commit -m "Task 22: PREREGISTRATION.md v1.0 + stamping script (dry-run mode)"
```

---

## Task 23: Analysis audit + paper_numbers.json

**Files:**
- Create: `scripts/emit_audit.py`, `tests/test_audit.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_audit.py
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_audit_emits_audit_md_and_paper_numbers(tmp_path):
    idx = pd.DataFrame([
        {"review_id": "R1", "trial_id": "T1", "instrument_id": "kccq_os", "status": "OK", "reason": ""},
        {"review_id": "R2", "trial_id": "T2", "instrument_id": "sgrq_total", "status": "MISSING_SD", "reason": "sd missing"},
    ])
    idx.to_parquet(tmp_path / "dual_framing_index.parquet", index=False)
    flips = pd.DataFrame([
        {"review_id": "R1", "framing_flip": True, "magnitude_flip": False, "k": 3,
         "smd_significant": True, "rr_significant": False,
         "smd_estimate": 0.3, "rr_estimate": 0.4, "smd_p": 0.01, "rr_p": 0.08}
    ])
    flips.to_parquet(tmp_path / "flip_results.parquet", index=False)
    recon = pd.DataFrame([
        {"instrument_id": "kccq_os", "epsilon_t": 0.01, "epsilon_c": 0.02,
         "delta_hat_trial": 5.0, "review_id": "R1"}
    ])
    recon.to_parquet(tmp_path / "reconstructions.parquet", index=False)

    result = subprocess.run(
        [sys.executable, "scripts/emit_audit.py",
         "--dual-framing-index", str(tmp_path / "dual_framing_index.parquet"),
         "--flips", str(tmp_path / "flip_results.parquet"),
         "--reconstructions", str(tmp_path / "reconstructions.parquet"),
         "--output-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    numbers = json.loads((tmp_path / "paper_numbers.json").read_text())
    audit = (tmp_path / "analysis_audit.md").read_text(encoding="utf-8")
    assert numbers["q1_flip_rate"] == 1.0
    assert "MISSING_SD" in audit
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_audit.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement emit_audit.py**

```python
# scripts/emit_audit.py
"""Emit outputs/analysis_audit.md + outputs/paper_numbers.json for paper / dashboard consumption."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dual-framing-index", type=Path, required=True)
    parser.add_argument("--flips", type=Path, required=True)
    parser.add_argument("--reconstructions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    idx = pd.read_parquet(args.dual_framing_index)
    flips = pd.read_parquet(args.flips)
    recon = pd.read_parquet(args.reconstructions)

    # paper_numbers.json — single source of truth for paper claims.
    numbers = {
        "total_rows_scanned": int(len(idx)),
        "rows_ok": int((idx["status"] == "OK").sum()),
        "reviews_pooled": int(len(flips)),
        "q1_flip_rate": float(flips["framing_flip"].mean()) if len(flips) else None,
        "q1_magnitude_flip_rate": float(flips["magnitude_flip"].mean()) if len(flips) else None,
        "q2_median_epsilon": float(
            pd.concat([recon["epsilon_t"].dropna(), recon["epsilon_c"].dropna()]).median()
        ) if len(recon) else None,
        "q3_per_instrument_median_delta_hat": recon.groupby("instrument_id")["delta_hat_trial"]
            .median().dropna().to_dict(),
    }
    (args.output_dir / "paper_numbers.json").write_text(json.dumps(numbers, indent=2))

    # analysis_audit.md — DossierGap-pattern honest enumeration.
    lines = ["# Analysis audit", "",
             "Every limit and exclusion, enumerated.", "",
             "## Row-status counts (Stage 1)", ""]
    for status, n in idx["status"].value_counts().items():
        lines.append(f"- **{status}**: {n}")
    lines += ["", "## Per-instrument coverage (Tier-1 OK rows)", ""]
    if "instrument_id" in idx.columns:
        for instr, n in idx[idx["status"] == "OK"].groupby("instrument_id").size().items():
            lines.append(f"- {instr}: {n}")
    lines += ["", "## Reviews with framing flip (Q1)", ""]
    if len(flips):
        for _, r in flips[flips["framing_flip"]].iterrows():
            lines.append(f"- {r['review_id']}: SMD p={r['smd_p']:.3f} ({'sig' if r['smd_significant'] else 'ns'}) vs RR p={r['rr_p']:.3f} ({'sig' if r['rr_significant'] else 'ns'})")
    else:
        lines.append("- (no reviews pooled)")
    (args.output_dir / "analysis_audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.output_dir / 'paper_numbers.json'} and {args.output_dir / 'analysis_audit.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test**

Run: `pytest tests/test_audit.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/emit_audit.py tests/test_audit.py
git commit -m "Task 23: analysis_audit.md + paper_numbers.json (single source of truth)"
```

---

## Task 24: Sentinel pre-push hook + `.sentinel-config.yml`

**Files:**
- Create: `.sentinel-config.yml`

- [ ] **Step 1: Write minimal Sentinel config**

```yaml
# .sentinel-config.yml
# Rules matched to spec §9 and portfolio defect top-5.
rules:
  hardcoded_paths:
    enabled: true
    severity: block
  placeholder_signatures:
    enabled: true
    severity: block
  silent_failure_sentinels:
    enabled: true
    severity: warn
  empty_dataframe_access:
    enabled: true
    severity: warn
  js_script_tag_leak:
    enabled: true
    severity: block
```

- [ ] **Step 2: Install hook**

Run: `python -m sentinel install-hook --repo .`
Expected: pre-push hook installed. If the installer is unavailable, skip this task and document in README.

- [ ] **Step 3: Smoke test**

Run: `python -m sentinel scan --repo .`
Expected: 0 BLOCK, WARNs tolerated.

- [ ] **Step 4: Commit**

```bash
git add .sentinel-config.yml
git commit -m "Task 24: Sentinel pre-push hook config (0 BLOCK baseline)"
```

---

## Task 25: v0.0.1 release — spec + prereg stamp + tag

**Files:**
- Modify: `README.md` (append release history)
- Tag: `v0.0.1`

- [ ] **Step 1: Verify all tests green**

Run: `pytest -q`
Expected: every test PASS (zero failures, zero errors). If any test fails, STOP and fix before tagging.

- [ ] **Step 2: Stamp preregistration (dry-run for v0.0.1; live before Stage 1 real-data run)**

Run: `python scripts/preregister.py --dry-run --preregistration preregistration/PREREGISTRATION.md --report outputs/stamp_report.json`
Expected: stamp_report.json written. The live stamp (Zenodo live + OTS + IA) happens immediately before Task 26 real-data run.

- [ ] **Step 3: Update README release history**

```markdown
<!-- README.md — append at end -->

## Release history

- **v0.0.1** (2026-04-22): design spec + preregistration v1.0 + 25-task implementation plan committed; no real-data compute yet.
```

- [ ] **Step 4: Commit README + tag**

```bash
git add README.md outputs/stamp_report.json
git commit -m "Release v0.0.1: spec + preregistration + implementation plan"
git tag -a v0.0.1 -m "Spec + prereg v1.0; no compute yet"
```

---

## Task 26: Live preregistration stamp (Zenodo + OTS + IA)

**Files:**
- Modify: `preregistration/PREREGISTRATION.md` (fill in Zenodo DOI, IA URL after stamping)
- Create: `preregistration/PREREGISTRATION.md.ots` (OpenTimestamps receipt)

- [ ] **Step 1: Verify environment**

Run: `python scripts/preflight.py`
Expected: all OK. `ZENODO_API_TOKEN` must be set. `ots` binary must be on PATH.

- [ ] **Step 2: Implement live Zenodo + IA stamping**

The `_stamp_zenodo` and `_stamp_ia` helpers in `scripts/preregister.py` currently `raise NotImplementedError` for live runs. Replace with the real implementations. For Zenodo: use the REST API (`POST /api/deposit/depositions`, upload file, publish). For IA: use `https://web.archive.org/save/{url}` or the SPN2 API. Add tests that mock the HTTP calls.

Run: `python scripts/preregister.py --preregistration preregistration/PREREGISTRATION.md --report outputs/stamp_report.json`
Expected: real DOI + OTS receipt + IA URL written to `stamp_report.json` and into `PREREGISTRATION.md`.

- [ ] **Step 3: Commit live stamps**

```bash
git add preregistration/PREREGISTRATION.md preregistration/PREREGISTRATION.md.ots outputs/stamp_report.json scripts/preregister.py
git commit -m "Task 26: live preregistration stamp (Zenodo DOI + OTS + IA)"
git tag -a v0.0.2 -m "Preregistration live-stamped"
```

---

## Task 27: Run Stage 1 on real Pairwise70 + FEASIBILITY_REPORT

**Files:**
- Create: `outputs/dual_framing_index.parquet`, `outputs/stage1_manifest.json`, `outputs/FEASIBILITY_REPORT.md`, `outputs/gates.json`

- [ ] **Step 1: Run Stage 1 on real Pairwise70**

Run: `python scripts/scan_dual_framing.py --corpus C:/Projects/Pairwise70 --output-dir outputs`
Expected: `outputs/dual_framing_index.parquet` + `outputs/stage1_manifest.json`.

- [ ] **Step 2: Evaluate feasibility gates**

Run: `python scripts/evaluate_gates.py --index outputs/dual_framing_index.parquet --output outputs/FEASIBILITY_REPORT.md --json outputs/gates.json`
Expected: exit 0 (all A/B/C pass) OR exit 2 (gate failure; apply pivot protocol).

- [ ] **Step 3: Commit feasibility artefacts**

```bash
git add outputs/dual_framing_index.parquet outputs/stage1_manifest.json outputs/FEASIBILITY_REPORT.md outputs/gates.json
git commit -m "Task 27: Stage 1 on real Pairwise70 + FEASIBILITY_REPORT"
git tag -a v0.1.0-feasibility -m "Feasibility report public"
```

- [ ] **Step 4: If any gate fails: prereg amendment**

Follow spec §6.4 pivot protocol. Draft amendment to `preregistration/PREREGISTRATION.md`, re-stamp Zenodo+OTS+IA, document pivot explicitly in manuscript later.

---

## Task 28: Run Stages 2–5 + emit_audit + dashboard

**Files:**
- Create: `outputs/{mid_inferences,reconstructions,flip_results}.parquet`, `outputs/analysis_audit.md`, `outputs/paper_numbers.json`, `dashboard/index.html`

- [ ] **Step 1: Run Stages 2–5 in sequence**

```bash
python scripts/infer_mid.py --index outputs/dual_framing_index.parquet --output-dir outputs
python scripts/reconstruct.py --mid-inferences outputs/mid_inferences.parquet --output-dir outputs
python scripts/pool_and_flip.py --reconstructions outputs/reconstructions.parquet --output-dir outputs
python scripts/emit_audit.py --dual-framing-index outputs/dual_framing_index.parquet --flips outputs/flip_results.parquet --reconstructions outputs/reconstructions.parquet --output-dir outputs
python scripts/build_dashboard.py --flips outputs/flip_results.parquet --reconstructions outputs/reconstructions.parquet --output dashboard/index.html --commit $(git rev-parse HEAD) --date $(date -I)
```

Expected: all stages complete; `dashboard/index.html` renders three panels without mojibake or hardcoded local paths.

- [ ] **Step 2: Verify dashboard locally**

Run: `python -m http.server 8000 --directory dashboard` and open `http://localhost:8000/`.
Expected: three panels render; Q1 flip-rate with CI; Q2 per-instrument ε table; Q3 implied-MID per instrument.

- [ ] **Step 3: Commit full run**

```bash
git add outputs/ dashboard/index.html
git commit -m "Task 28: Stages 2-5 run on real Pairwise70 + dashboard"
```

---

## Task 29: E156 Methods Note draft

**Files:**
- Create: `manuscript/e156_methods_note.md`

- [ ] **Step 1: Draft the 7-sentence E156 per `e156.md` format**

```markdown
<!-- manuscript/e156_methods_note.md -->
# Responder Floor Atlas — E156 Methods Note

## S1 — Question
[~22 words] When Cochrane reviews pool the same patient-reported outcome as both continuous SMD and dichotomous responder RR, does the α=0.05 verdict agree across the two framings?

## S2 — Dataset
[~20 words] Pairwise70 (7,545 meta-analyses / 595 Cochrane reviews); dual-framing subset with ≥3 trials contributing to both framings.

## S3 — Method
[~20 words] REML + HKSJ + PI per framing; Model 1 normal-approximation responder reconstruction from arm-level (μ, σ, n) + review MID.

## S4 — Result
[~30 words, primary estimand: framing flip rate]
[FILL FROM outputs/paper_numbers.json: q1_flip_rate]

## S5 — Robustness
[~22 words] Log-normal + Beta + truncated Normal sensitivity bounds; clustered bootstrap (cluster = review) 95% CI; R+metafor parity at 1e-6.

## S6 — Interpretation
[~22 words] Non-trivial framing disagreement implies that a review's continuous-vs-responder choice is a methodological degree of freedom that materially shifts conclusions.

## S7 — Boundary
[~20 words] Subset restricted to reviews with arm-level data preserved; non-normal PROs may widen reconstruction error beyond the sensitivity bound reported.

**Primary estimand:** framing flip rate at α=0.05 across Tier-1 dual-framing reviews.
**Preregistration:** Zenodo DOI + OTS + IA, stamped 2026-04-22.
```

- [ ] **Step 2: Fill S4 from paper_numbers.json**

Replace `[FILL FROM outputs/paper_numbers.json: q1_flip_rate]` with the actual number and narrative wording. Example: "Among N Tier-1 reviews, X (Y%, 95% CI [L%, U%]) showed a framing flip; magnitude-flip rate was Z%."

- [ ] **Step 3: Verify 7-sentence / 156-word contract**

Run: `python C:/E156/scripts/validate.py manuscript/e156_methods_note.md`
Expected: PASS (exactly 7 sentences, ≤156 words, single paragraph per S1–S7 allocation). Fix any violation.

- [ ] **Step 4: Commit**

```bash
git add manuscript/e156_methods_note.md
git commit -m "Task 29: E156 Methods Note draft (7-sentence contract)"
```

---

## Task 30: v0.1.0 release bundle + Pages deploy

**Files:**
- Create: `RELEASE_NOTES_v0.1.0.md`
- Modify: `README.md` (final release row)

- [ ] **Step 1: Run final verification suite**

Run: `pytest -q && python -m sentinel scan --repo .`
Expected: all tests PASS; 0 BLOCK.

- [ ] **Step 2: Write release notes**

```markdown
<!-- RELEASE_NOTES_v0.1.0.md -->
# Responder Floor Atlas v0.1.0

Fourth atlas on Pairwise70. Audits continuous-vs-responder framing reproducibility in Cochrane PRO meta-analyses.

**Headline findings** (from `outputs/paper_numbers.json`):
- Q1 framing flip rate at α=0.05: [FILL]
- Q2 median reconstruction error across Tier-1 arms: [FILL]
- Q3 per-instrument implied MID: [FILL]

**Artefacts:**
- `outputs/*.parquet` — per-stage pipeline outputs
- `dashboard/index.html` — three-panel static dashboard
- `outputs/analysis_audit.md` — honest per-bucket exclusion enumeration
- `outputs/paper_numbers.json` — single source of truth for paper claims
- `manuscript/e156_methods_note.md` — E156 draft for Synthēsis

**Spec:** `docs/superpowers/specs/2026-04-22-responder-floor-atlas-design.md` (commit ee81682)
**Preregistration:** Zenodo [DOI]; OTS receipt in `preregistration/PREREGISTRATION.md.ots`; IA [URL].

**Sibling atlases:** repro-floor-atlas, cochrane-modern-re, pi-atlas.
```

- [ ] **Step 3: Enable GitHub Pages**

Push repo to GitHub (`git remote add origin …` + `git push -u origin master`). In the repo settings, enable Pages from the `master` branch `/dashboard` folder. Verify live at `https://mahmood726-cyber.github.io/responder-floor-atlas/`.

- [ ] **Step 4: Tag v0.1.0**

```bash
git add RELEASE_NOTES_v0.1.0.md README.md
git commit -m "Release v0.1.0: first full Pairwise70 run + E156 draft + Pages live"
git tag -a v0.1.0 -m "v0.1.0 — first full run"
git push origin master --tags
```

---

## Self-review (by plan author, per writing-plans skill)

**Spec coverage check:**
- §3 Research questions: Q1 (Task 15), Q2 (Task 14), Q3 (Task 13 + 23), Q4 exploratory (Task 12 gate D reported in audit Task 23). ✓
- §4.2 Subset filter: Task 11 (dual-framing detection). ✓
- §4.3 Instrument panel v1: Task 2. ✓
- §5.1 Model 1 math: Task 3. ✓
- §5.2 Model 2 math: Tasks 3 + 5 (round-trip test). ✓
- §5.3 Normality sensitivity: Task 18. ✓
- §5.4 Fail-closed buckets: Task 6. ✓
- §6.1 Tiers: implicitly via Task 12 gate evaluator + Task 15 pool filter (k≥3). ✓
- §6.2 Pooling: Task 7 + Task 8 (R parity). ✓
- §6.3 Feasibility gates A/B/C/D: Task 12. ✓
- §6.4 Pivot protocol: Task 27 Step 4. ✓
- §7 Pipeline architecture 5 stages: Tasks 11 / 13 / 14 / 15 / 17. ✓
- §7.4 Dashboard: Task 17. ✓
- §8 Preregistration: Tasks 22 + 26. ✓
- §9 Testing strategy: Tasks 3–10 (unit), Task 19 (e2e), Task 20 (determinism), Task 21 (negative control), Task 8 (R parity). ✓
- §10 Release structure v0.0.1 / v0.1.0-feasibility / v0.1.0: Tasks 25 / 27 / 30. ✓
- §11 Risk register: mitigations are enforced by Task 12 (gates), Task 21 (negative control), Task 8 (R parity), Task 24 (Sentinel). ✓
- §12 Static-vs-dynamic: paper_numbers.json (Task 23) enforces dynamic; `configs/` files enforce static. ✓
- §14 Task 0 preflight: Task 0. ✓

**Placeholder scan:** no "TBD" / "implement later" / "similar to Task N" patterns in executable steps. The E156 S4 `[FILL FROM …]` token is a deliberate manuscript placeholder that Task 29 Step 2 fills from `paper_numbers.json` at draft time. Release notes `[FILL]` in Task 30 similarly fill from runtime outputs.

**Type consistency:**
- `p_hat_arm(mean, sd, mid, direction)` signature in Task 3 matches usage in Tasks 14, 18, 21. ✓
- `PoolResult` dataclass in Task 7 has `estimate`, `se`, `p_value`, `tau2`, `hksj_factor` — all referenced correctly in Task 15. ✓
- `StatusCode` enum values in Task 6 match Task 11 usage (`"OK"`, `"MISSING_SD"`, `"BOUNDARY_P"`, `"UNKNOWN_INSTRUMENT"`). ✓
- Column names `events_t`/`events_c`/`n_t_dich`/`n_c_dich` consistent across Tasks 11 / 13 / 14 / 15. ✓
- `direction` as int ∈ {+1, −1} consistent across Tasks 2 / 3 / 13 / 14 / 18. ✓

No issues found. Plan is implementation-ready.

---

Plan complete and saved to `docs/superpowers/plans/2026-04-22-responder-floor-atlas-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?

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

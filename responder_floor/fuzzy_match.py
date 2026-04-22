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

# Tokens that distinguish subscales or sub-outcomes — disagreement blocks match.
_DISTINGUISHING_TOKENS = {
    "total", "overall", "summary", "symptoms", "activity", "impact",
    "clinical", "physical", "social",
}

_PUNCT_RE = re.compile(r"[^\w\s]")
_WS_RE = re.compile(r"\s+")


def normalize_label(label: str) -> str:
    """Normalize label: lowercase, remove punctuation, collapse whitespace."""
    s = label.lower()
    s = _PUNCT_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def _core_tokens(label: str) -> frozenset[str]:
    """Extract core tokens: drop framing tokens and digits."""
    norm = normalize_label(label)
    return frozenset(
        t for t in norm.split()
        if t not in _FRAMING_TOKENS and not t.isdigit()
    )


def are_same_outcome(
    label_a: str,
    label_b: str,
    min_overlap: float = 0.25,
) -> bool:
    """
    Two labels are 'same outcome' if their core-token Jaccard similarity >= threshold
    AND they do not have contradicting distinguishing tokens.

    Distinguishing-token disagreement (e.g., one has 'total' and the other 'symptoms')
    always returns False, regardless of Jaccard overlap.
    """
    a = _core_tokens(label_a)
    b = _core_tokens(label_b)
    if not a or not b:
        return False

    # Distinguishing-token disagreement → not same outcome.
    a_dist = a & _DISTINGUISHING_TOKENS
    b_dist = b & _DISTINGUISHING_TOKENS
    if a_dist and b_dist and a_dist != b_dist:
        return False

    jaccard = len(a & b) / len(a | b)
    return jaccard >= min_overlap

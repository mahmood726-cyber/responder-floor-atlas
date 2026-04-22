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


@lru_cache(maxsize=4)
def load_instruments(path: Path | None = None) -> tuple[Instrument, ...]:
    p = (path or DEFAULT_PATH).resolve()
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "instruments" not in raw:
        raise ValueError(f"{p}: expected top-level 'instruments:' key")
    instruments = []
    for entry in raw["instruments"]:
        if entry["direction"] not in (1, -1):
            raise ValueError(f"Instrument {entry['id']}: direction must be +1 or -1, got {entry['direction']}")
        if not (entry["scale_min"] < entry["scale_max"]):
            raise ValueError(f"{entry['id']}: scale_min must be < scale_max")
        scale_range = entry["scale_max"] - entry["scale_min"]
        if not (0 < entry["canonical_mid"] <= scale_range):
            raise ValueError(f"{entry['id']}: canonical_mid {entry['canonical_mid']} outside (0, {scale_range}]")
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

"""RDA loader — pyreadr primary, rpy2 secondary, R-subprocess fallback.

Supports two RDA layouts:
  - Flat data.frame (real Pairwise70 schema): pyreadr returns a DataFrame
    directly.  load_rda() returns that DataFrame.
  - Nested list (legacy fixture schema): pyreadr returns empty; rpy2 or
    Rscript/jsonlite deserialise to a Python dict.  load_rda() returns dict.

Strategy order (first success wins):
  1. pyreadr  — zero overhead, works for flat/dataframe RDAs; returns DataFrame.
  2. rpy2     — works when `libR.so`/`R.dll` is a shared library; returns dict.
  3. Rscript subprocess + jsonlite  — works whenever `Rscript` is on PATH or
     R_HOME is set; no compile-time R headers required; returns dict.

Note: rpy2 is declared as an optional extra (r_bridge) since it fails to
install on Windows without R dev headers.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

# Path to the bundled R helper script (sits next to this module).
_R_SCRIPT_HELPER = Path(__file__).parent / "_rda_to_json.R"


# ---------------------------------------------------------------------------
# Strategy 1: pyreadr
# ---------------------------------------------------------------------------

def _load_pyreadr(path: Path):
    """Try pyreadr; return DataFrame, dict, or None.

    pyreadr's read_r returns an OrderedDict whose values are DataFrames.
    - Flat data.frame RDA (real Pairwise70): returns the DataFrame directly.
    - Nested R list structures produce an *empty* OrderedDict — return None
      to signal "need fallback".
    - If the value is already a dict-like structure (unusual), return it.
    """
    try:
        import pyreadr

        data = pyreadr.read_r(str(path))
        if not data:
            return None
        key = next(iter(data))
        obj = data[key]
        # Flat data.frame → return the DataFrame directly (new Pairwise70 schema)
        if hasattr(obj, "to_dict"):
            return obj
        # If it's already a dict-like structure, return it.
        if isinstance(obj, dict):
            return obj
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Strategy 2: rpy2
# ---------------------------------------------------------------------------

def _load_rpy2(path: Path) -> dict[str, Any] | None:
    """Try rpy2; return None if import fails or R shared library is absent."""
    try:
        from rpy2.robjects import globalenv, r  # noqa: F401 — side-effect import
        from rpy2.robjects.vectors import DataFrame as RDataFrame, ListVector
    except Exception:
        return None

    try:
        r["load"](str(path))
        names = list(globalenv.keys())
        if not names:
            return None
        obj = globalenv[names[0]]
        return _rlist_to_dict(obj)
    except Exception:
        return None


def _rlist_to_dict(obj: Any) -> Any:
    """Recursively convert R named lists / DataFrames to Python dicts/lists."""
    try:
        from rpy2.robjects.vectors import DataFrame as RDataFrame, ListVector
    except ImportError:
        raise RuntimeError("rpy2 not available")

    if isinstance(obj, RDataFrame):
        col_names = list(obj.names)
        col_data = {name: list(obj.rx2(name)) for name in col_names}
        n_rows = len(next(iter(col_data.values()))) if col_data else 0
        return [{col: col_data[col][i] for col in col_names} for i in range(n_rows)]
    if isinstance(obj, ListVector):
        out: dict[str, Any] = {}
        for name, item in zip(obj.names, obj):
            out[name] = _rlist_to_dict(item)
        return out
    # Scalars / atomic vectors
    try:
        lst = list(obj)
        return lst[0] if len(lst) == 1 else lst
    except Exception:
        return obj


# ---------------------------------------------------------------------------
# Strategy 3: Rscript subprocess + jsonlite
# ---------------------------------------------------------------------------

def _find_rscript() -> str | None:
    """Locate the Rscript executable via PATH, R_HOME, or common Windows paths."""
    # 1. On PATH?
    found = shutil.which("Rscript")
    if found:
        return found

    # 2. R_HOME env var
    r_home = os.environ.get("R_HOME")
    if r_home:
        candidate = Path(r_home) / "bin" / "Rscript.exe"
        if candidate.exists():
            return str(candidate)
        candidate = Path(r_home) / "bin" / "Rscript"
        if candidate.exists():
            return str(candidate)

    # 3. Common Windows install locations
    for root in (Path("C:/Program Files/R"), Path("C:/Program Files (x86)/R")):
        if root.is_dir():
            # Pick the highest-version subdirectory
            candidates = sorted(root.iterdir(), reverse=True)
            for d in candidates:
                exe = d / "bin" / "Rscript.exe"
                if exe.exists():
                    return str(exe)

    return None


def _load_rscript(path: Path) -> dict[str, Any]:
    """Shell out to Rscript with the bundled helper; parse the JSON output."""
    rscript = _find_rscript()
    if rscript is None:
        raise RuntimeError(
            f"Cannot load nested RDA '{path}': pyreadr returned empty result, "
            "rpy2 is unavailable, and Rscript was not found.  "
            "Install R and ensure Rscript is on PATH, or set R_HOME."
        )

    if not _R_SCRIPT_HELPER.exists():
        raise FileNotFoundError(
            f"Bundled R helper script not found: {_R_SCRIPT_HELPER}.  "
            "Re-install the responder-floor-atlas package."
        )

    result = subprocess.run(
        [rscript, str(_R_SCRIPT_HELPER), str(path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Rscript helper failed (exit {result.returncode}) for '{path}':\n"
            f"{result.stderr.strip()}"
        )
    stdout = result.stdout.strip()
    if not stdout:
        raise ValueError(
            f"Rscript helper produced no output for '{path}'.  "
            f"stderr: {result.stderr.strip()}"
        )
    return json.loads(stdout)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_rda(path: Path | str):
    """Load an RDA file.

    Tries pyreadr first (zero-overhead, handles flat DataFrames), then rpy2
    (handles nested S4, needs R shared library), then falls back to an Rscript
    subprocess that serialises via jsonlite.

    Parameters
    ----------
    path:
        Path to the ``.rda`` / ``.RData`` file.

    Returns
    -------
    pandas.DataFrame
        For flat data.frame RDAs (real Pairwise70 schema) — returned by
        pyreadr directly.
    dict
        For nested-list RDAs (legacy fixture schema) — returned by rpy2 or
        Rscript/jsonlite.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    RuntimeError
        If all three loading strategies fail.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    # Strategy 1
    obj = _load_pyreadr(path)
    if obj is not None:
        return obj

    # Strategy 2
    obj = _load_rpy2(path)
    if obj is not None:
        return obj

    # Strategy 3 (may raise on failure)
    return _load_rscript(path)

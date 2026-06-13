"""Pytest fixtures shared across responder-floor-atlas tests."""
import os
import sys
from pathlib import Path

# Ensure repo root on sys.path for `import responder_floor` from tests.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, _REPO_ROOT)

# Tests that invoke pipeline scripts via subprocess inherit os.environ but not
# the in-process sys.path insertion above. Prepend the repo root to PYTHONPATH so
# those subprocesses can `import responder_floor` without an editable install.
_existing = os.environ.get("PYTHONPATH", "")
if _REPO_ROOT not in _existing.split(os.pathsep):
    os.environ["PYTHONPATH"] = (
        _REPO_ROOT + (os.pathsep + _existing if _existing else "")
    )

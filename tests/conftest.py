"""Pytest fixtures shared across responder-floor-atlas tests."""
import sys
from pathlib import Path

# Ensure repo root on sys.path for `import responder_floor` from tests.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# tests/test_preregister.py
import json
import subprocess
import sys
from pathlib import Path


def test_preregister_dry_run_produces_report(tmp_path):
    # Create a minimal temporary preregistration file for the dry run
    prereg = tmp_path / "prereg.md"
    prereg.write_text("# test prereg\n")
    result = subprocess.run(
        [sys.executable, "scripts/preregister.py", "--dry-run",
         "--preregistration", str(prereg),
         "--report", str(tmp_path / "stamp_report.json")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "stamp_report.json").read_text())
    assert "sha256" in report
    assert "ots" in report
    assert "archive_org" in report
    assert report["dry_run"] is True
    assert "zenodo" not in report  # explicit — Zenodo removed


def test_preregister_real_file_exists():
    # Smoke check that the actual preregistration file is present in the repo.
    p = Path("preregistration/PREREGISTRATION.md")
    assert p.exists(), "preregistration/PREREGISTRATION.md must be committed"
    body = p.read_text(encoding="utf-8")
    assert "Zenodo" not in body, "Preregistration must not reference Zenodo (Crossref via Synthēsis)"
    assert "Crossref" in body
    assert "OpenTimestamps" in body or "OTS" in body
    assert "Internet Archive" in body

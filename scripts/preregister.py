# scripts/preregister.py
"""Stamp preregistration to OpenTimestamps + Internet Archive before real-data compute.

DOI comes from Synthēsis via Crossref at publication time — Zenodo is not used.
The immutability proof for the preregistration itself is: (a) git tag on the
signed commit, (b) OTS receipt embedded in the repo, (c) Internet Archive
snapshot of the GitHub-rendered markdown.

Dry-run mode emits a stamp report without actually publishing — used in CI.
Live mode requires the `ots` CLI on PATH and network access to archive.org.
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


def _stamp_ia(path: Path, dry_run: bool) -> dict:
    if dry_run:
        return {"url": "https://web.archive.org/save/DRYRUN", "dry_run": True}
    raise NotImplementedError(
        "Live archive.org save implemented at live-stamp time; requires "
        "GitHub-rendered URL, not local path."
    )


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
        "ots": _stamp_ots(args.preregistration, args.dry_run),
        "archive_org": _stamp_ia(args.preregistration, args.dry_run),
        "notes": "Zenodo intentionally omitted: DOI via Synthēsis+Crossref at publication.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2))
    print(f"Stamp report: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# scripts/preregister.py
"""Stamp preregistration to OpenTimestamps + Internet Archive before real-data compute.

DOI comes from Synthēsis via Crossref at publication time — Zenodo is not used.
The immutability proof for the preregistration itself is: (a) git tag on the
signed commit, (b) OTS receipt embedded in the repo, (c) Internet Archive
snapshot of the GitHub-rendered markdown.

Dry-run mode emits a stamp report without actually publishing — used in CI.
Live mode uses the opentimestamps Python API directly (no CLI dependency) and
defers Internet Archive until Task 30 when a public GitHub Pages URL exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path
from queue import Empty, Queue


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# OTS stamping — uses the opentimestamps Python API directly.
# The `ots` CLI is *not* used because python-bitcoinlib fails to load libssl
# on Python 3.13/Windows (TypeError: argument of type 'NoneType' is not iterable
# in bitcoin/core/key.py). The calendar submission path in the library itself
# works fine without bitcoin.rpc.
# ---------------------------------------------------------------------------

OTS_CALENDARS = [
    "https://a.pool.opentimestamps.org",
    "https://b.pool.opentimestamps.org",
    "https://a.pool.eternitywall.com",
]
OTS_USER_AGENT = "responder-floor-atlas-preregister/0.0.2"
OTS_TIMEOUT = 30  # seconds per calendar request
OTS_NEEDED = 1    # minimum calendar responses required


def _ots_stamp_via_python_api(path: Path) -> Path:
    """Stamp *path* using the opentimestamps Python library.

    Returns the Path of the written .ots receipt file.
    Raises RuntimeError if fewer than OTS_NEEDED attestations are received.
    """
    from opentimestamps.calendar import RemoteCalendar
    from opentimestamps.core.op import OpAppend, OpSHA256
    from opentimestamps.core.serialize import StreamSerializationContext
    from opentimestamps.core.timestamp import DetachedTimestampFile, make_merkle_tree

    with path.open("rb") as fd:
        file_ts = DetachedTimestampFile.from_fd(OpSHA256(), fd)

    nonce_stamp = file_ts.timestamp.ops.add(OpAppend(os.urandom(16)))
    merkle_root = nonce_stamp.ops.add(OpSHA256())
    merkle_tip = make_merkle_tree([merkle_root])

    q: Queue = Queue()

    def _submit(url: str, msg: bytes) -> None:
        try:
            cal = RemoteCalendar(url, user_agent=OTS_USER_AGENT)
            result = cal.submit(msg, timeout=OTS_TIMEOUT)
            q.put(result)
        except Exception as exc:  # noqa: BLE001
            q.put(exc)

    for url in OTS_CALENDARS:
        t = threading.Thread(target=_submit, args=(url, merkle_tip.msg), daemon=True)
        t.start()

    start = time.time()
    merged = 0
    for _ in range(len(OTS_CALENDARS)):
        remaining = max(0.5, OTS_TIMEOUT - (time.time() - start))
        try:
            result = q.get(block=True, timeout=remaining)
        except Empty:
            break
        if hasattr(result, "msg"):  # is a Timestamp
            merkle_tip.merge(result)
            merged += 1
            if merged >= OTS_NEEDED:
                break
        else:
            print(f"[ots] calendar error: {result}", file=sys.stderr)

    if merged < OTS_NEEDED:
        raise RuntimeError(
            f"OTS: only {merged}/{OTS_NEEDED} calendar attestation(s) received "
            f"within {OTS_TIMEOUT}s timeout."
        )

    ots_path = Path(str(path) + ".ots")
    with ots_path.open("xb") as f:
        ctx = StreamSerializationContext(f)
        file_ts.serialize(ctx)

    return ots_path


def _stamp_ots(path: Path, dry_run: bool) -> dict:
    if dry_run:
        return {"receipt": str(path) + ".ots", "dry_run": True}

    # Overwrite-safe: remove existing receipt so we don't hit FileExistsError on 'xb'
    ots_path = Path(str(path) + ".ots")
    if ots_path.exists():
        ots_path.unlink()

    receipt = _ots_stamp_via_python_api(path)

    # Confirm the receipt is readable and carries at least one attestation
    from opentimestamps.core.serialize import StreamDeserializationContext
    from opentimestamps.core.timestamp import DetachedTimestampFile as _DTF

    with receipt.open("rb") as f:
        ctx = StreamDeserializationContext(f)
        loaded = _DTF.deserialize(ctx)
    attestations = list(loaded.timestamp.all_attestations())
    attestation_labels = [type(a).__name__ for _, a in attestations]

    return {
        "receipt": str(receipt),
        "dry_run": False,
        "attestations": attestation_labels,
        "note": (
            "PendingAttestation is normal immediately after stamping. "
            "Bitcoin confirmation arrives within a few hours."
        ),
    }


# ---------------------------------------------------------------------------
# Internet Archive — deferred until a public GitHub Pages URL exists (Task 30)
# ---------------------------------------------------------------------------


def _stamp_ia(path: Path, dry_run: bool) -> dict:  # noqa: ARG001
    if dry_run:
        return {"url": "https://web.archive.org/save/DRYRUN", "dry_run": True}
    # No public URL yet — GitHub remote + Pages created at Task 30.
    return {
        "status": "deferred_until_github_push",
        "reason": (
            "No public URL yet: GitHub remote and Pages will be created at Task 30. "
            "IA save will target the github.io page URL at that point."
        ),
    }


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
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Stamp report: {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

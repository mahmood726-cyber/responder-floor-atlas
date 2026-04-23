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
    """Discover Pairwise70 root from PAIRWISE70_ROOT env var, then configs/pipeline.yml, then fallback candidates."""
    candidates: list[Path] = []

    # 1. Check PAIRWISE70_ROOT env var
    env_path = os.environ.get("PAIRWISE70_ROOT")
    if env_path:
        candidates.append(Path(env_path))

    # 2. Check configs/pipeline.yml
    try:
        import yaml
        cfg_path = Path(__file__).resolve().parent.parent / "configs" / "pipeline.yml"
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        cfg_pairwise = cfg.get("paths", {}).get("pairwise70")
        if cfg_pairwise:
            candidates.append(Path(cfg_pairwise))
    except Exception:
        pass

    # 3. Fallback candidates
    candidates.append(Path.home() / "Pairwise70")

    for c in candidates:
        if c.is_dir():
            rda_count = sum(1 for _ in c.rglob("*.rda"))
            if rda_count >= 500:
                return True, f"{c} ({rda_count} RDA files)"
            return False, f"{c} exists but only {rda_count} RDA files (<500)"
    return False, f"Pairwise70 not found (tried: {', '.join(str(c) for c in candidates)})"


def check_import(modname: str) -> tuple[bool, str]:
    try:
        __import__(modname)
        return True, f"{modname} imports cleanly"
    except ModuleNotFoundError as e:
        return False, f"{modname} not installed: {e}"
    except Exception as e:
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
            capture_output=True, timeout=20,
        )
        return (out.returncode == 0, "metafor installed" if out.returncode == 0 else "metafor not installed")
    except subprocess.TimeoutExpired:
        return False, "metafor check timed out after 20s"
    except Exception as e:
        return False, f"metafor check failed: {e}"


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
    p = Path(__file__).resolve().parent.parent / "configs" / "instruments.yml"
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
        print(f"\nOverall: {'READY' if all_ok else 'BLOCKED -- fix failures above before proceeding'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

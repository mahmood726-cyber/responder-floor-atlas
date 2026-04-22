import subprocess
import sys


def test_preflight_reports_status_dict():
    result = subprocess.run(
        [sys.executable, "scripts/preflight.py", "--json"],
        capture_output=True, text=True,
    )
    assert result.returncode in (0, 1)
    import json
    status = json.loads(result.stdout)
    required_keys = {
        "pairwise70_path", "pyreadr_import", "rpy2_import",
        "r_binary", "metafor_package", "zenodo_token",
        "ots_binary", "ia_save_api", "instruments_yml",
    }
    assert required_keys <= set(status.keys())

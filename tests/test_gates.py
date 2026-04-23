import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


def test_gates_evaluate_from_parquet(tmp_path):
    # Synthetic dual-framing index with 40 reviews, 5 trials each, all OK, kccq_os.
    rows = []
    for r in range(40):
        for t in range(5):
            rows.append({
                "review_id": f"R{r:03d}", "outcome_group": "KCCQ OS",
                "trial_id": f"T{t}", "mean_t": 10, "sd_t": 15, "n_t": 100,
                "mean_c": 5, "sd_c": 15, "n_c": 100,
                "events_t": 60, "events_c": 40, "n_t_dich": 100, "n_c_dich": 100,
                "instrument_id": "kccq_os", "status": "OK", "reason": "all fields present and in-range",
            })
    df = pd.DataFrame(rows)
    parquet = tmp_path / "dual_framing_index.parquet"
    df.to_parquet(parquet, index=False)

    result = subprocess.run(
        [sys.executable, "scripts/evaluate_gates.py",
         "--index", str(parquet),
         "--output", str(tmp_path / "FEASIBILITY_REPORT.md"),
         "--json", str(tmp_path / "gates.json")],
        capture_output=True, text=True,
    )
    assert result.returncode in (0, 2), result.stderr
    gates = json.loads((tmp_path / "gates.json").read_text())
    # Only 1 instrument; B fails. A passes (40 reviews ≥30). C depends on MID availability (default v1 panel → passes).
    assert gates["A"]["passed"] is True
    assert gates["B"]["passed"] is False  # only 1 instrument

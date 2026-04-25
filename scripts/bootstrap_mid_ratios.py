"""CLI: emit outputs/mid_bootstrap.parquet from outputs/reconstructions.parquet."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from responder_floor.mid_bootstrap import bootstrap_mid_ratios


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--reconstructions", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--n-boot", type=int, default=2000)
    p.add_argument("--seed", type=int, default=20260425)
    a = p.parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(a.reconstructions)
    result = bootstrap_mid_ratios(df, n_boot=a.n_boot, rng=np.random.default_rng(seed=a.seed))
    out = a.output_dir / "mid_bootstrap.parquet"
    result.to_parquet(out, index=False)
    print(f"Wrote {len(result)} rows to {out}")
    for _, r in result.iterrows():
        print(f"  {r['instrument_id']}: empirical={r['empirical_mid']:.3f} canonical={r['canonical_mid']:.3f} "
              f"ratio={r['ratio']:.2f} 95%CI=[{r['ratio_ci_lower']:.2f}, {r['ratio_ci_upper']:.2f}] "
              f"(n_reviews={r['n_reviews']}, n_trials={r['n_trials']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

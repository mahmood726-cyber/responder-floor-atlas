"""Stage 5 -- single-file HTML dashboard with three panels per spec §7.4.

No external dependencies (no CDN), inline SVG only. Commits hash + date into
the top of the page so any divergence between report and code is attributable.
"""
from __future__ import annotations

import argparse
import html as html_mod
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from responder_floor.bootstrap import cluster_bootstrap_flip_rate

TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><title>Responder Floor Atlas</title>
<meta property="og:title" content="Responder Floor Atlas">
<style>
body{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#222}
h1{margin-bottom:.25rem}h2{margin-top:2rem;border-bottom:1px solid #ccc;padding-bottom:.25rem}
.panel{margin-bottom:2rem}
.muted{color:#666;font-size:.85rem}
table{border-collapse:collapse;margin:.5rem 0}
th,td{padding:.25rem .5rem;border:1px solid #ddd;font-size:.9rem;text-align:left}
</style></head><body>
<h1>Responder Floor Atlas</h1>
<p class="muted">Continuous-vs-responder framing reproducibility on Pairwise70 &mdash; generated from commit HASH on DATE.</p>

<div class="panel" id="panel-flip">
<h2>Q1 &mdash; Framing flip rate</h2>
PANEL_FLIP_CONTENT
</div>

<div class="panel" id="panel-reconstruction">
<h2>Q2 &mdash; Reconstruction fidelity</h2>
PANEL_RECONSTRUCTION_CONTENT
</div>

<div class="panel" id="panel-implied-mid">
<h2>Q3 &mdash; Implied-MID atlas</h2>
PANEL_IMPLIED_MID_CONTENT
</div>

<p class="muted">Spec: docs/superpowers/specs/2026-04-22-responder-floor-atlas-design.md</p>
</body></html>
"""


def _panel_flip(flips: pd.DataFrame) -> str:
    if flips.empty:
        return "<p>No reviews pooled.</p>"
    # Guard against all-None framing_flip column (fail-closed pooling results)
    valid = flips.dropna(subset=["framing_flip"])
    if valid.empty:
        return "<p>No reviews with successful pooling.</p>"
    rng = np.random.default_rng(seed=20260422)
    # cluster_bootstrap_flip_rate wants review_id column; ensure boolean framing_flip
    point, lo, hi = cluster_bootstrap_flip_rate(
        valid.assign(framing_flip=valid["framing_flip"].astype(bool)),
        n_boot=1000,
        rng=rng,
    )
    total = len(valid)
    flip_count = int(valid["framing_flip"].fillna(False).astype(bool).sum())
    magnitude_flip_count = int(
        valid.get("magnitude_flip", pd.Series([False] * total))
        .fillna(False)
        .astype(bool)
        .sum()
    )
    return (
        f"<table><tr><th>Metric</th><th>Value</th><th>95% CI (clustered bootstrap)</th></tr>"
        f"<tr><td>Reviews pooled</td><td>{total}</td><td>&mdash;</td></tr>"
        f"<tr><td>Framing flips (&alpha;=0.05)</td><td>{flip_count} ({point:.1%})</td>"
        f"<td>[{lo:.1%}, {hi:.1%}]</td></tr>"
        f"<tr><td>Magnitude flips (|&Delta; logRR|&gt;0.1)</td>"
        f"<td>{magnitude_flip_count} ({magnitude_flip_count/total:.1%})</td><td>&mdash;</td></tr>"
        f"</table>"
    )


def _panel_reconstruction(recon: pd.DataFrame) -> str:
    if recon.empty:
        return "<p>No reconstructions.</p>"
    rows_html = []
    for instr, g in recon.groupby("instrument_id"):
        eps_t = g["epsilon_t"].dropna()
        eps_c = g["epsilon_c"].dropna()
        all_eps = pd.concat([eps_t, eps_c])
        if all_eps.empty:
            continue
        rows_html.append(
            f"<tr><td>{html_mod.escape(str(instr))}</td><td>{len(g)}</td>"
            f"<td>{all_eps.median():.4f}</td>"
            f"<td>{all_eps.quantile(0.95):.4f}</td>"
            f"<td>{(all_eps > 0.05).mean():.1%}</td></tr>"
        )
    header = (
        "<tr><th>Instrument</th><th>n trials</th><th>Median |&epsilon;|</th>"
        "<th>95th percentile</th><th>% |&epsilon;|&gt;0.05</th></tr>"
    )
    return "<table>" + header + "".join(rows_html) + "</table>"


def _panel_implied_mid(recon: pd.DataFrame) -> str:
    if recon.empty or "delta_hat_trial" not in recon.columns:
        return "<p>No implied MID data.</p>"
    rows_html = []
    for instr, g in recon.groupby("instrument_id"):
        deltas = g["delta_hat_trial"].dropna()
        if deltas.empty:
            continue
        rows_html.append(
            f"<tr><td>{html_mod.escape(str(instr))}</td><td>{len(deltas)}</td>"
            f"<td>{deltas.median():.3f}</td>"
            f"<td>{deltas.quantile(0.025):.3f}&ndash;{deltas.quantile(0.975):.3f}</td></tr>"
        )
    header = (
        "<tr><th>Instrument</th><th>n trials</th>"
        "<th>Median implied MID</th><th>95% range</th></tr>"
    )
    return "<table>" + header + "".join(rows_html) + "</table>"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flips", type=Path, required=True)
    parser.add_argument("--reconstructions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", default="unknown")
    parser.add_argument("--date", default="unknown")
    args = parser.parse_args()

    flips = pd.read_parquet(args.flips)
    recon = pd.read_parquet(args.reconstructions)

    html = (
        TEMPLATE.replace("PANEL_FLIP_CONTENT", _panel_flip(flips))
        .replace("PANEL_RECONSTRUCTION_CONTENT", _panel_reconstruction(recon))
        .replace("PANEL_IMPLIED_MID_CONTENT", _panel_implied_mid(recon))
        .replace("HASH", html_mod.escape(args.commit))
        .replace("DATE", html_mod.escape(args.date))
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(f"Wrote dashboard to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

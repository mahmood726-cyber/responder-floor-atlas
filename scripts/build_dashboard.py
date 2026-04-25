"""Stage 5 -- single-file HTML dashboard with five panels per spec §7.4.

No external dependencies (no CDN), inline SVG only. Commits hash + date into
the top of the page so any divergence between report and code is attributable.

v0.3.0: real inline-SVG plots — forest (Panel 3), density + Bland-Altman
(Panel 2), plus new Panel 4 (Q4 overlap) and Panel 5 (sensitivity bounds).
"""
from __future__ import annotations

import argparse
import html as html_mod
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from responder_floor.bootstrap import cluster_bootstrap_flip_rate

# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><title>Responder Floor Atlas</title>
<meta property="og:title" content="Responder Floor Atlas">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#222}
h1{margin-bottom:.25rem}h2{margin-top:2rem;border-bottom:1px solid #ccc;padding-bottom:.25rem}
.panel{margin-bottom:2rem}
.muted{color:#666;font-size:.85rem}
table{border-collapse:collapse;margin:.5rem 0}
th,td{padding:.25rem .5rem;border:1px solid #ddd;font-size:.9rem;text-align:left}
svg{display:block;margin:.75rem 0}
.stoplight-row{display:flex;align-items:center;gap:1rem;margin:.5rem 0}
.stoplight-dot{width:18px;height:18px;border-radius:50%;flex-shrink:0}
.dot-flip{background:#e05c5c}
.dot-ok{background:#5caa5c}
.panel-cols{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem;align-items:start}
@media(max-width:700px){.panel-cols{grid-template-columns:1fr}}
</style></head><body>
<h1>Responder Floor Atlas</h1>
<p class="muted">Continuous-vs-responder framing reproducibility on Pairwise70 &mdash;
generated from commit HASH on DATE.</p>

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

<div class="panel" id="panel-q4">
<h2>Q4 &mdash; Cross-review trial overlap</h2>
PANEL_Q4_CONTENT
</div>

<div class="panel" id="panel-sensitivity">
<h2>Q5 &mdash; Sensitivity: implied MID under alternative distributional assumptions</h2>
PANEL_SENSITIVITY_CONTENT
</div>

<p class="muted">Spec: docs/superpowers/specs/2026-04-22-responder-floor-atlas-design.md</p>
</body></html>
"""

# ---------------------------------------------------------------------------
# SVG helpers — all return plain strings; no HTML escaping needed inside
# numerical/coordinate contexts, but all label text is escaped.
# ---------------------------------------------------------------------------

_INSTRUMENTS_SHORT: dict[str, str] = {
    "bmi_change": "BMI change",
    "body_weight_kg": "Weight (kg)",
    "body_weight_pct": "Weight (%)",
    "sf36_mcs": "SF-36 MCS",
    "sf36_pcs": "SF-36 PCS",
    "sf36_physical_function": "SF-36 PF",
}


def _short(instr: str) -> str:
    return html_mod.escape(_INSTRUMENTS_SHORT.get(str(instr), str(instr)))


def _svg_forest(boot_df: pd.DataFrame, width: int = 700, row_h: int = 38, margin_l: int = 110,
                margin_r: int = 210, margin_top: int = 30, margin_bot: int = 30) -> str:
    """Vertical forest plot: one row per instrument.

    X-axis: implied-MID absolute value.
    Each row: dashed vertical canonical-MID reference line, whisker (CI), square (point estimate).
    Right label: ratio [CI_lower – CI_upper].
    """
    if boot_df is None or boot_df.empty:
        return "<p>No bootstrap CI data available.</p>"

    # Absolute implied MID = ratio * canonical_mid
    boot_df = boot_df.copy()
    boot_df["emp_abs"] = boot_df["empirical_mid"].abs()
    boot_df["ci_lo_abs"] = boot_df["ratio_ci_lower"] * boot_df["canonical_mid"]
    boot_df["ci_hi_abs"] = boot_df["ratio_ci_upper"] * boot_df["canonical_mid"]
    boot_df["canon_abs"] = boot_df["canonical_mid"].abs()

    x_max = float(max(
        boot_df["ci_hi_abs"].max(),
        boot_df["emp_abs"].max(),
        boot_df["canon_abs"].max(),
    ) * 1.08)
    x_min = 0.0

    inner_w = width - margin_l - margin_r
    n = len(boot_df)
    height = margin_top + n * row_h + margin_bot

    def tx(v: float) -> float:
        return margin_l + (v - x_min) / (x_max - x_min) * inner_w

    lines = [
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="Forest plot of implied MID per instrument">',
    ]

    # X-axis line
    ax_y = height - margin_bot
    lines.append(
        f'<line x1="{margin_l}" y1="{ax_y}" x2="{margin_l + inner_w}" y2="{ax_y}" '
        f'stroke="#888" stroke-width="1"/>'
    )

    # X-axis ticks + labels: ~5 ticks
    n_ticks = 5
    for ti in range(n_ticks + 1):
        v = x_min + (x_max - x_min) * ti / n_ticks
        xp = tx(v)
        lines.append(
            f'<line x1="{xp:.1f}" y1="{ax_y}" x2="{xp:.1f}" y2="{ax_y + 4}" '
            f'stroke="#888" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{xp:.1f}" y="{ax_y + 14}" text-anchor="middle" '
            f'font-size="10" fill="#555">{v:.1f}</text>'
        )
    lines.append(
        f'<text x="{margin_l + inner_w // 2}" y="{ax_y + 26}" text-anchor="middle" '
        f'font-size="11" fill="#444">Implied MID (absolute)</text>'
    )

    # One row per instrument
    for i, (_, row) in enumerate(boot_df.iterrows()):
        cy = margin_top + i * row_h + row_h // 2
        lbl = _short(row["instrument_id"])
        emp = float(row["emp_abs"])
        lo = float(row["ci_lo_abs"])
        hi = float(row["ci_hi_abs"])
        canon = float(row["canon_abs"])
        ratio = float(row["ratio"])
        rlo = float(row["ratio_ci_lower"])
        rhi = float(row["ratio_ci_upper"])

        # Instrument label (left)
        lines.append(
            f'<text x="{margin_l - 6}" y="{cy + 4}" text-anchor="end" '
            f'font-size="11" fill="#222">{lbl}</text>'
        )

        # Canonical MID vertical dashed reference line
        cx_canon = tx(canon)
        lines.append(
            f'<line x1="{cx_canon:.1f}" y1="{margin_top}" x2="{cx_canon:.1f}" y2="{ax_y}" '
            f'stroke="#bbb" stroke-width="1" stroke-dasharray="4,3"/>'
        )

        # CI whisker
        x_lo = tx(max(lo, x_min))
        x_hi = tx(min(hi, x_max))
        lines.append(
            f'<line x1="{x_lo:.1f}" y1="{cy}" x2="{x_hi:.1f}" y2="{cy}" '
            f'stroke="#222" stroke-width="1.5"/>'
        )
        # End caps
        for xep in (x_lo, x_hi):
            lines.append(
                f'<line x1="{xep:.1f}" y1="{cy - 4}" x2="{xep:.1f}" y2="{cy + 4}" '
                f'stroke="#222" stroke-width="1.5"/>'
            )

        # Point-estimate square
        x_emp = tx(emp)
        sq = 6
        lines.append(
            f'<rect x="{x_emp - sq / 2:.1f}" y="{cy - sq / 2:.1f}" '
            f'width="{sq}" height="{sq}" fill="#1a6faf" stroke="#124e7c" stroke-width="1"/>'
        )

        # Right label
        rtext = f"ratio = {ratio:.2f} [{rlo:.2f}–{rhi:.2f}]"
        rx = margin_l + inner_w + 8
        lines.append(
            f'<text x="{rx}" y="{cy + 4}" text-anchor="start" '
            f'font-size="10" fill="#333">{html_mod.escape(rtext)}</text>'
        )

    # Legend
    leg_x = margin_l + 4
    leg_y = margin_top - 12
    lines.append(
        f'<line x1="{leg_x}" y1="{leg_y}" x2="{leg_x + 28}" y2="{leg_y}" '
        f'stroke="#bbb" stroke-width="1" stroke-dasharray="4,3"/>'
    )
    lines.append(
        f'<text x="{leg_x + 32}" y="{leg_y + 4}" font-size="10" fill="#666">'
        f'canonical MID</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


def _svg_density(recon: pd.DataFrame, width: int = 680, height: int = 180) -> str:
    """Small-multiples histogram: one panel per instrument, |epsilon| distribution.

    Uses log10(|eps|+1e-4) x-axis to spread the near-zero mass.
    """
    if recon is None or recon.empty:
        return "<p>No reconstruction data for density plot.</p>"

    instruments = sorted(recon["instrument_id"].dropna().unique())
    n_instr = len(instruments)
    if n_instr == 0:
        return "<p>No instruments found.</p>"

    panel_w = width // n_instr
    margin_l = 8
    margin_r = 4
    margin_top = 22
    margin_bot = 24
    n_bins = 18

    # Global log10 range across all instruments
    all_eps: list[float] = []
    for instr in instruments:
        g = recon[recon["instrument_id"] == instr]
        eps = pd.concat([g["epsilon_t"].dropna(), g["epsilon_c"].dropna()])
        all_eps.extend(eps.tolist())
    if not all_eps:
        return "<p>No epsilon data.</p>"

    arr = np.array(all_eps, dtype=float)
    log_min = float(np.log10(max(arr.min(), 1e-5)))
    log_max = float(np.log10(arr.max() + 1e-9)) + 0.01
    bin_edges = np.linspace(log_min, log_max, n_bins + 1)

    inner_w = panel_w - margin_l - margin_r
    inner_h = height - margin_top - margin_bot

    lines = [
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="Density plots of reconstruction error by instrument">',
    ]

    for pi, instr in enumerate(instruments):
        ox = pi * panel_w  # panel origin x
        g = recon[recon["instrument_id"] == instr]
        eps = pd.concat([g["epsilon_t"].dropna(), g["epsilon_c"].dropna()])
        if eps.empty:
            continue
        log_eps = np.log10(np.clip(eps.values, 1e-5, None))
        counts, _ = np.histogram(log_eps, bins=bin_edges)
        max_count = max(counts.max(), 1)
        bar_w = inner_w / n_bins

        # Title
        lines.append(
            f'<text x="{ox + panel_w // 2}" y="{margin_top - 8}" '
            f'text-anchor="middle" font-size="9" fill="#333">{_short(instr)}</text>'
        )

        # Axis bottom
        ax_y = margin_top + inner_h
        lines.append(
            f'<line x1="{ox + margin_l}" y1="{ax_y}" '
            f'x2="{ox + margin_l + inner_w}" y2="{ax_y}" stroke="#aaa" stroke-width="0.8"/>'
        )

        # Bars
        for bi, cnt in enumerate(counts):
            bh = int(cnt / max_count * inner_h)
            bx = ox + margin_l + bi * bar_w
            by = margin_top + inner_h - bh
            lines.append(
                f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w - 0.5:.1f}" height="{bh}" '
                f'fill="#1a6faf" opacity="0.75"/>'
            )

        # X-axis tick labels (log10 values → original scale labels)
        for tv, tlabel in [
            (log_min + (log_max - log_min) * 0.0, f"{10**log_min:.3f}"),
            (log_min + (log_max - log_min) * 0.5, f"{10**(log_min+(log_max-log_min)*0.5):.2f}"),
            (log_max, f"{10**log_max:.1f}"),
        ]:
            txp = ox + margin_l + (tv - log_min) / (log_max - log_min) * inner_w
            lines.append(
                f'<text x="{txp:.1f}" y="{ax_y + 11}" text-anchor="middle" '
                f'font-size="8" fill="#666">{html_mod.escape(tlabel)}</text>'
            )

    # X-axis global label
    lines.append(
        f'<text x="{width // 2}" y="{height - 2}" text-anchor="middle" '
        f'font-size="9" fill="#555">|&#x03B5;| (arm-level reconstruction error)</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


def _svg_bland_altman(recon: pd.DataFrame, width: int = 500, height: int = 280,
                      max_pts: int = 200, seed: int = 20260422) -> str:
    """Bland-Altman scatter: x = mean(p_hat, p_obs), y = p_hat - p_obs.

    Samples up to max_pts rows for size control; draws 95% LoA dashed lines.
    """
    if recon is None or recon.empty:
        return "<p>No reconstruction data for Bland-Altman plot.</p>"

    needed = ["p_hat_t", "p_hat_c", "p_obs_t", "p_obs_c"]
    for col in needed:
        if col not in recon.columns:
            return "<p>Missing columns for Bland-Altman.</p>"

    # Combine treatment and control arms
    arms = pd.concat([
        recon[["p_hat_t", "p_obs_t"]].rename(columns={"p_hat_t": "p_hat", "p_obs_t": "p_obs"}),
        recon[["p_hat_c", "p_obs_c"]].rename(columns={"p_hat_c": "p_hat", "p_obs_c": "p_obs"}),
    ]).dropna()

    if len(arms) > max_pts:
        arms = arms.sample(max_pts, random_state=seed)

    arms = arms.copy()
    arms["x"] = (arms["p_hat"] + arms["p_obs"]) / 2.0
    arms["y"] = arms["p_hat"] - arms["p_obs"]

    y_mean = float(arms["y"].mean())
    y_sd = float(arms["y"].std())
    loa_hi = y_mean + 1.96 * y_sd
    loa_lo = y_mean - 1.96 * y_sd

    margin_l = 42
    margin_r = 14
    margin_top = 16
    margin_bot = 36

    inner_w = width - margin_l - margin_r
    inner_h = height - margin_top - margin_bot

    x_min, x_max = 0.0, 1.0
    y_pad = max(abs(loa_hi), abs(loa_lo)) * 1.15
    y_lo_ax = -y_pad
    y_hi_ax = y_pad

    def tx(v: float) -> float:
        return margin_l + (v - x_min) / (x_max - x_min) * inner_w

    def ty(v: float) -> float:
        return margin_top + (1.0 - (v - y_lo_ax) / (y_hi_ax - y_lo_ax)) * inner_h

    lines = [
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="Bland-Altman plot of reconstructed vs observed responder proportions">',
    ]

    ax_y = ty(0.0)

    # Plot area border
    lines.append(
        f'<rect x="{margin_l}" y="{margin_top}" width="{inner_w}" height="{inner_h}" '
        f'fill="#fafafa" stroke="#ccc" stroke-width="0.5"/>'
    )

    # Zero line
    lines.append(
        f'<line x1="{margin_l}" y1="{ax_y:.1f}" x2="{margin_l + inner_w}" y2="{ax_y:.1f}" '
        f'stroke="#aaa" stroke-width="0.8"/>'
    )

    # LoA lines (dashed)
    for loa_v, loa_lbl in [(loa_hi, f"+1.96SD={loa_hi:.3f}"), (loa_lo, f"−1.96SD={loa_lo:.3f}")]:
        ly = ty(loa_v)
        if margin_top <= ly <= margin_top + inner_h:
            lines.append(
                f'<line x1="{margin_l}" y1="{ly:.1f}" '
                f'x2="{margin_l + inner_w}" y2="{ly:.1f}" '
                f'stroke="#e05c5c" stroke-width="1" stroke-dasharray="5,3"/>'
            )
            lines.append(
                f'<text x="{margin_l + inner_w - 2}" y="{ly - 3:.1f}" '
                f'text-anchor="end" font-size="9" fill="#c04040">'
                f'{html_mod.escape(loa_lbl)}</text>'
            )

    # Bias line
    bias_y = ty(y_mean)
    if margin_top <= bias_y <= margin_top + inner_h:
        lines.append(
            f'<line x1="{margin_l}" y1="{bias_y:.1f}" '
            f'x2="{margin_l + inner_w}" y2="{bias_y:.1f}" '
            f'stroke="#888" stroke-width="0.8" stroke-dasharray="3,2"/>'
        )
        lines.append(
            f'<text x="{margin_l + 3}" y="{bias_y - 3:.1f}" '
            f'font-size="9" fill="#666">mean={y_mean:.3f}</text>'
        )

    # Scatter dots
    for _, row in arms.iterrows():
        xp = tx(float(row["x"]))
        yp = ty(float(row["y"]))
        if margin_l <= xp <= margin_l + inner_w and margin_top <= yp <= margin_top + inner_h:
            lines.append(
                f'<circle cx="{xp:.1f}" cy="{yp:.1f}" r="2.2" '
                f'fill="#1a6faf" opacity="0.35"/>'
            )

    # Y-axis ticks + labels
    for yv in [y_lo_ax, y_lo_ax / 2, 0, y_hi_ax / 2, y_hi_ax]:
        yp = ty(yv)
        if margin_top <= yp <= margin_top + inner_h:
            lines.append(
                f'<line x1="{margin_l - 3}" y1="{yp:.1f}" x2="{margin_l}" y2="{yp:.1f}" '
                f'stroke="#888" stroke-width="0.8"/>'
            )
            lines.append(
                f'<text x="{margin_l - 5}" y="{yp + 3:.1f}" '
                f'text-anchor="end" font-size="9" fill="#555">{yv:.2f}</text>'
            )

    # X-axis ticks + labels
    ax_bottom = margin_top + inner_h
    for xv in [0.0, 0.25, 0.5, 0.75, 1.0]:
        xp = tx(xv)
        lines.append(
            f'<line x1="{xp:.1f}" y1="{ax_bottom}" x2="{xp:.1f}" y2="{ax_bottom + 3}" '
            f'stroke="#888" stroke-width="0.8"/>'
        )
        lines.append(
            f'<text x="{xp:.1f}" y="{ax_bottom + 12}" text-anchor="middle" '
            f'font-size="9" fill="#555">{xv:.2f}</text>'
        )

    # Axis labels
    lines.append(
        f'<text x="{margin_l + inner_w // 2}" y="{height - 2}" text-anchor="middle" '
        f'font-size="10" fill="#444">Mean of p&#x0302; and p_obs</text>'
    )
    # Y label (rotated)
    cy_label = margin_top + inner_h // 2
    lines.append(
        f'<text transform="rotate(-90,10,{cy_label})" x="10" y="{cy_label}" '
        f'text-anchor="middle" font-size="10" fill="#444">'
        f'p&#x0302; &#x2212; p_obs</text>'
    )

    # Caption (sample size)
    lines.append(
        f'<text x="{margin_l}" y="{margin_top + inner_h - 3}" '
        f'font-size="9" fill="#666">n = {len(arms)} (sampled)</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Panel builders
# ---------------------------------------------------------------------------

def _bar_svg_flip(flip_count: int, total: int, lo: float, hi: float,
                  width: int = 280, height: int = 56) -> str:
    """Horizontal bar: flip vs no-flip with bootstrap-CI whisker."""
    if total == 0:
        return ""
    bar_w = 220
    margin_l = 36
    margin_top = 16
    bar_h = 18
    scale = bar_w / total

    x_flip = flip_count * scale
    x_lo = lo * total * scale
    x_hi = hi * total * scale

    cy = margin_top + bar_h // 2

    lines = [
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="Flip count bar chart">',
        # Background bar (no-flip)
        f'<rect x="{margin_l}" y="{margin_top}" width="{bar_w}" height="{bar_h}" '
        f'fill="#d9ead3" rx="2"/>',
        # Flip bar
        f'<rect x="{margin_l}" y="{margin_top}" width="{x_flip:.1f}" height="{bar_h}" '
        f'fill="#e05c5c" rx="2"/>',
        # 95% CI whisker on the flip proportion
        f'<line x1="{margin_l + x_lo:.1f}" y1="{cy}" x2="{margin_l + x_hi:.1f}" y2="{cy}" '
        f'stroke="#222" stroke-width="1.5"/>',
        # End caps
        f'<line x1="{margin_l + x_lo:.1f}" y1="{cy - 4}" '
        f'x2="{margin_l + x_lo:.1f}" y2="{cy + 4}" stroke="#222" stroke-width="1.5"/>',
        f'<line x1="{margin_l + x_hi:.1f}" y1="{cy - 4}" '
        f'x2="{margin_l + x_hi:.1f}" y2="{cy + 4}" stroke="#222" stroke-width="1.5"/>',
        # Labels
        f'<text x="{margin_l - 2}" y="{margin_top + bar_h + 10}" font-size="9" '
        f'text-anchor="end" fill="#555">0</text>',
        f'<text x="{margin_l + bar_w}" y="{margin_top + bar_h + 10}" font-size="9" '
        f'text-anchor="start" fill="#555" dx="2">{total}</text>',
        f'<text x="{margin_l + x_flip / 2:.0f}" y="{margin_top + bar_h // 2 + 4}" '
        f'text-anchor="middle" font-size="9" fill="white" font-weight="bold">'
        f'{flip_count} flip{"s" if flip_count != 1 else ""}</text>',
        "</svg>",
    ]
    return "\n".join(lines)


def _stoplight_html(flip_count: int, total: int) -> str:
    """Row of coloured dots, one per review (red = flip, green = no-flip)."""
    dots = []
    dot_labels = []
    # We don't know which specific review is which without the row data here,
    # so we generate flip_count red dots then (total - flip_count) green dots.
    for i in range(total):
        cls = "dot-flip" if i < flip_count else "dot-ok"
        lbl = "flip" if i < flip_count else "no flip"
        dots.append(
            f'<div class="stoplight-dot {cls}" title="{html_mod.escape(lbl)}"></div>'
        )
        dot_labels.append(lbl)
    return (
        '<div class="stoplight-row">'
        + "".join(dots)
        + f'<span class="muted">{flip_count} of {total} reviews flipped</span>'
        + "</div>"
    )


def _panel_flip(flips: pd.DataFrame) -> str:
    if flips.empty:
        return "<p>No reviews pooled.</p>"
    valid = flips.dropna(subset=["framing_flip"])
    if valid.empty:
        return "<p>No reviews with successful pooling.</p>"
    rng = np.random.default_rng(seed=20260422)
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

    table = (
        f"<table><tr><th>Metric</th><th>Value</th><th>95% CI (clustered bootstrap)</th></tr>"
        f"<tr><td>Reviews pooled</td><td>{total}</td><td>&mdash;</td></tr>"
        f"<tr><td>Framing flips (&alpha;=0.05)</td><td>{flip_count} ({point:.1%})</td>"
        f"<td>[{lo:.1%}, {hi:.1%}]</td></tr>"
        f"<tr><td>Magnitude flips (|&Delta; logRR|&gt;0.1)</td>"
        f"<td>{magnitude_flip_count} ({magnitude_flip_count / total:.1%})</td><td>&mdash;</td></tr>"
        f"</table>"
    )

    bar_svg = _bar_svg_flip(flip_count, total, lo, hi)
    stoplight = _stoplight_html(flip_count, total)

    return table + "\n" + bar_svg + "\n" + stoplight


def _panel_reconstruction(recon: pd.DataFrame) -> str:
    if recon is None or recon.empty:
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
    summary_table = "<table>" + header + "".join(rows_html) + "</table>"

    density_svg = _svg_density(recon)
    ba_svg = _svg_bland_altman(recon)

    return (
        summary_table
        + "\n<h3>Distribution of |&epsilon;| by instrument</h3>\n"
        + density_svg
        + "\n<h3>Bland&ndash;Altman: reconstructed vs observed responder proportions</h3>\n"
        + ba_svg
    )


def _panel_implied_mid(recon: pd.DataFrame, boot_df: pd.DataFrame | None) -> str:
    if recon is None or recon.empty or "delta_hat_trial" not in recon.columns:
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
    ratio_table = "<table>" + header + "".join(rows_html) + "</table>"

    forest_svg = ""
    if boot_df is not None and not boot_df.empty:
        forest_svg = "\n<h3>Bootstrap CIs on implied-MID ratio (empirical / canonical)</h3>\n"
        forest_svg += _svg_forest(boot_df)

    return ratio_table + forest_svg


def _panel_q4(q4_data: dict | None, recon: pd.DataFrame | None) -> str:
    if q4_data is None:
        return "<p>(data not available)</p>"

    total = q4_data.get("total_unique_trials", "?")
    multi = q4_data.get("trials_in_multiple_reviews", 0)
    single = q4_data.get("trials_in_single_review", "?")
    max_overlap = q4_data.get("max_review_overlap", "?")

    summary = (
        f"<p>Of <strong>{total}</strong> unique trial-instrument combinations, "
        f"<strong>{multi}</strong> appeared in &#x2265;2 reviews "
        f"(max overlap = {max_overlap} reviews). "
        f"{single} were unique to a single review.</p>"
    )

    # Build overlap detail table from reconstructions if available
    overlap_table = ""
    if recon is not None and not recon.empty and multi > 0:
        ok = recon[recon["status"] == "OK"].copy()
        ok["bare_study"] = ok["trial_id"].astype(str).str.split("|", n=1).str[0]
        overlap = ok.groupby(["instrument_id", "bare_study"]).agg(
            n_reviews=("review_id", "nunique"),
            delta_hats=("delta_hat_trial", list),
            review_ids=("review_id", lambda s: sorted(s.unique().tolist())),
        ).reset_index()
        overlapping = overlap[overlap["n_reviews"] >= 2].copy()
        if not overlapping.empty:
            overlapping["delta_range"] = overlapping["delta_hats"].apply(
                lambda lst: max(lst) - min(lst)
            )
            overlapping["delta_min"] = overlapping["delta_hats"].apply(min)
            overlapping["delta_max"] = overlapping["delta_hats"].apply(max)

            rows = []
            for _, row in overlapping.iterrows():
                reviews_str = ", ".join(
                    html_mod.escape(str(r)) for r in row["review_ids"]
                )
                rows.append(
                    f"<tr>"
                    f"<td>{html_mod.escape(str(row['instrument_id']))}</td>"
                    f"<td>{html_mod.escape(str(row['bare_study']))}</td>"
                    f"<td>{int(row['n_reviews'])}</td>"
                    f"<td>{reviews_str}</td>"
                    f"<td>{row['delta_range']:.3f}</td>"
                    f"<td>{row['delta_min']:.3f}&ndash;{row['delta_max']:.3f}</td>"
                    f"</tr>"
                )
            header = (
                "<tr><th>Instrument</th><th>Trial</th><th>Reviews (n)</th>"
                "<th>Review IDs</th><th>&delta;&#x302; range</th>"
                "<th>&delta;&#x302; min&ndash;max</th></tr>"
            )
            overlap_table = "<table>" + header + "".join(rows) + "</table>"
        else:
            overlap_table = "<p>No overlapping trial details found in reconstruction data.</p>"

    return summary + "\n" + overlap_table


def _panel_sensitivity(sens_df: pd.DataFrame | None) -> str:
    if sens_df is None or sens_df.empty:
        return "<p>(data not available)</p>"

    # Pivot: rows = instrument, cols = distribution × metric
    rows_html = []
    for instr, g in sens_df.groupby("instrument_id"):
        dist_cells = ""
        for dist in ["lognormal_shifted", "truncated_normal", "beta_bounded"]:
            row = g[g["dist"] == dist]
            if row.empty:
                dist_cells += "<td>&mdash;</td><td>&mdash;</td><td>&mdash;</td>"
            else:
                r = row.iloc[0]  # sentinel:skip-line — guarded by `if row.empty` two lines above
                dist_cells += (
                    f"<td>{r['median_delta_p']:.4f}</td>"
                    f"<td>{r['p95_delta_p']:.4f}</td>"
                    f"<td>{r['max_delta_p']:.4f}</td>"
                )
        rows_html.append(
            f"<tr><td>{html_mod.escape(str(instr))}</td>{dist_cells}</tr>"
        )

    header = (
        "<tr>"
        "<th rowspan='2'>Instrument</th>"
        "<th colspan='3'>Log-normal</th>"
        "<th colspan='3'>Truncated-Normal</th>"
        "<th colspan='3'>Beta</th>"
        "</tr>"
        "<tr>"
        "<th>Median &Delta;p</th><th>P95</th><th>Max</th>"
        "<th>Median &Delta;p</th><th>P95</th><th>Max</th>"
        "<th>Median &Delta;p</th><th>P95</th><th>Max</th>"
        "</tr>"
    )
    return "<table>" + header + "".join(rows_html) + "</table>"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Build Responder Floor Atlas dashboard.")
    parser.add_argument("--flips", type=Path, required=True)
    parser.add_argument("--reconstructions", type=Path, required=True)
    parser.add_argument("--mid-bootstrap", type=Path, default=None,
                        dest="mid_bootstrap")
    parser.add_argument("--q4-summary", type=Path, default=None,
                        dest="q4_summary")
    parser.add_argument("--sensitivity-summary", type=Path, default=None,
                        dest="sensitivity_summary")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", default="unknown")
    parser.add_argument("--date", default="unknown")
    args = parser.parse_args()

    flips = pd.read_parquet(args.flips)
    recon = pd.read_parquet(args.reconstructions)

    boot_df: pd.DataFrame | None = None
    if args.mid_bootstrap is not None and args.mid_bootstrap.exists():
        boot_df = pd.read_parquet(args.mid_bootstrap)
    elif args.mid_bootstrap is not None:
        print(f"[warn] --mid-bootstrap not found: {args.mid_bootstrap}", file=sys.stderr)

    q4_data: dict | None = None
    if args.q4_summary is not None and args.q4_summary.exists():
        with open(args.q4_summary, encoding="utf-8") as fh:
            q4_data = json.load(fh)
    elif args.q4_summary is not None:
        print(f"[warn] --q4-summary not found: {args.q4_summary}", file=sys.stderr)

    sens_df: pd.DataFrame | None = None
    if args.sensitivity_summary is not None and args.sensitivity_summary.exists():
        sens_df = pd.read_parquet(args.sensitivity_summary)
    elif args.sensitivity_summary is not None:
        print(f"[warn] --sensitivity-summary not found: {args.sensitivity_summary}",
              file=sys.stderr)

    html = (
        TEMPLATE
        .replace("PANEL_FLIP_CONTENT", _panel_flip(flips))
        .replace("PANEL_RECONSTRUCTION_CONTENT", _panel_reconstruction(recon))
        .replace("PANEL_IMPLIED_MID_CONTENT", _panel_implied_mid(recon, boot_df))
        .replace("PANEL_Q4_CONTENT", _panel_q4(q4_data, recon))
        .replace("PANEL_SENSITIVITY_CONTENT", _panel_sensitivity(sens_df))
        .replace("HASH", html_mod.escape(args.commit))
        .replace("DATE", html_mod.escape(args.date))
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    size_kb = args.output.stat().st_size / 1024
    print(f"Wrote dashboard to {args.output} ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

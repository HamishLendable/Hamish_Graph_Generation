"""Regenerate fixture CSVs for batch 5b-b (multi_lines styles).

Deterministic — uses seeded numpy RNGs so the CSVs are stable across runs.
Run::

    poetry run python tests/fixtures/_regen_5b_b.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

FIXTURES = Path(__file__).parent

INTRODUCERS = [
    "Aggregator",
    "Broker - Dealer led",
    "Broker - Online led",
    "Dealer",
    "Direct",
    "Unknown introducer",
]


def _lines_1x2_funnel_by_introducer() -> pd.DataFrame:
    rng = np.random.default_rng(101)
    months = pd.date_range("2024-01-01", periods=15, freq="MS").strftime("%Y-%m")
    rows = []
    # Each introducer has its own baseline quote/sale rate plus mild drift.
    baselines = {
        "Aggregator":          (0.32, 0.085),
        "Broker - Dealer led": (0.28, 0.072),
        "Broker - Online led": (0.41, 0.110),
        "Dealer":              (0.55, 0.180),
        "Direct":              (0.46, 0.140),
        "Unknown introducer":  (0.22, 0.050),
    }
    for intro in INTRODUCERS:
        q_base, s_base = baselines[intro]
        drift_q = np.linspace(-0.02, 0.03, len(months))
        drift_s = np.linspace(-0.005, 0.015, len(months))
        for j, m in enumerate(months):
            q = q_base + drift_q[j] + rng.uniform(-0.01, 0.01)
            s = s_base + drift_s[j] + rng.uniform(-0.004, 0.004)
            n = int(rng.integers(180, 900))
            rows.append({
                "month": m,
                "introducer": intro,
                "quote_rate": round(float(max(0.0, q)), 5),
                "sale_rate": round(float(max(0.0, s)), 5),
                "n": n,
            })
    return pd.DataFrame(rows)


def _lines_with_overall_highlight() -> pd.DataFrame:
    rng = np.random.default_rng(202)
    months = pd.date_range("2024-01-01", periods=15, freq="MS").strftime("%Y-%m")
    grades = ["A", "B", "C", "D", "E", "F"]
    rows = []
    # Base 90+@9 rate per grade — increasing with risk.
    base_rates = {g: 0.012 + 0.008 * i for i, g in enumerate(grades)}
    overall_traj = np.zeros(len(months))
    for g in grades:
        b = base_rates[g]
        trajectory = b + np.linspace(-0.003, 0.005, len(months)) + rng.uniform(
            -0.002, 0.002, len(months)
        )
        n_per = rng.integers(300, 1200, len(months))
        for j, m in enumerate(months):
            rows.append({
                "month": m,
                "segment": g,
                "rate": round(float(max(0.0, trajectory[j])), 5),
                "n": int(n_per[j]),
            })
            overall_traj[j] += trajectory[j] * n_per[j]
        overall_traj /= 1  # placeholder, recomputed below
    # Recompute Overall as £-weighted mean across grades (approximated by n-weighted).
    weights_by_month = {m: 0.0 for m in months}
    num_by_month = {m: 0.0 for m in months}
    for row in rows:
        m = row["month"]
        weights_by_month[m] += row["n"]
        num_by_month[m] += row["rate"] * row["n"]
    for m in months:
        overall_rate = num_by_month[m] / weights_by_month[m]
        rows.append({
            "month": m,
            "segment": "Overall",
            "rate": round(float(overall_rate), 5),
            "n": int(weights_by_month[m]),
        })
    return pd.DataFrame(rows)


def _segment_compare_2x2_with_gap() -> pd.DataFrame:
    """Two-segment compare fixture. Defaults shape it like 'BEV vs Rest of book':
    segment A runs hotter than segment B, mix-adjustment closes ~40% of the gap,
    and A has a heavier F+ mix (segment B has more A-E loans)."""
    rng = np.random.default_rng(303)
    months = pd.date_range("2024-01-01", periods=18, freq="MS").strftime("%Y-%m")
    rows = []
    for j, m in enumerate(months):
        b = 0.022 + 0.0008 * j + rng.uniform(-0.0015, 0.0015)
        a = b + 0.006 + rng.uniform(-0.002, 0.002)
        b_adj = b + 0.0035 + rng.uniform(-0.001, 0.001)
        n = int(rng.integers(400, 1500))
        # Grade mix: A has heavier F+ exposure (60% A-E / 40% F+), B is cleaner
        # (78% A-E / 22% F+). Both drift slightly month-on-month.
        a_good_share = 0.60 + rng.uniform(-0.03, 0.03)
        b_good_share = 0.78 + rng.uniform(-0.03, 0.03)
        rows.append({
            "month": m,
            "a": round(float(a), 5),
            "b": round(float(b), 5),
            "b_adj": round(float(b_adj), 5),
            "gap": round(float((a - b) * 100), 4),
            "a_good_share": round(float(a_good_share), 4),
            "b_good_share": round(float(b_good_share), 4),
            "n": n,
        })
    return pd.DataFrame(rows)


def _lines_funnel_by_introducer_1x1() -> pd.DataFrame:
    rng = np.random.default_rng(404)
    months = pd.date_range("2024-01-01", periods=15, freq="MS").strftime("%Y-%m")
    rows = []
    baselines = {
        "Aggregator":          0.085,
        "Broker - Dealer led": 0.072,
        "Broker - Online led": 0.110,
        "Dealer":              0.180,
        "Direct":              0.140,
        "Unknown introducer":  0.050,
    }
    for intro in INTRODUCERS:
        base = baselines[intro]
        drift = np.linspace(-0.005, 0.012, len(months))
        for j, m in enumerate(months):
            r = base + drift[j] + rng.uniform(-0.005, 0.005)
            n = int(rng.integers(120, 800))
            rows.append({
                "month": m,
                "introducer": intro,
                "rate": round(float(max(0.0, r)), 5),
                "n": n,
            })
    return pd.DataFrame(rows)


def _line_with_ci_band() -> pd.DataFrame:
    rng = np.random.default_rng(505)
    months = pd.date_range("2024-01-01", periods=15, freq="MS").strftime("%Y-%m")
    groups = ["BEV", "Carrera", "Torino"]
    base_rates = {"BEV": 0.025, "Carrera": 0.018, "Torino": 0.032}
    rows = []
    for g in groups:
        base = base_rates[g]
        trajectory = base + np.linspace(-0.002, 0.004, len(months)) + rng.uniform(
            -0.001, 0.001, len(months)
        )
        n_per = rng.integers(200, 1500, len(months))
        for j, m in enumerate(months):
            r = float(max(0.0, trajectory[j]))
            n = int(n_per[j])
            # Wilson-ish half-width ≈ 1.96 * sqrt(p(1-p)/n).
            half = 1.96 * np.sqrt(max(r * (1 - r), 1e-6) / max(n, 1))
            rows.append({
                "month": m,
                "group": g,
                "rate": round(r, 5),
                "ci_lower": round(float(max(0.0, r - half)), 5),
                "ci_upper": round(float(r + half), 5),
                "n": n,
            })
    return pd.DataFrame(rows)


SPECS = {
    "lines_1x2_funnel_by_introducer.csv": _lines_1x2_funnel_by_introducer,
    "lines_with_overall_highlight.csv": _lines_with_overall_highlight,
    "segment_compare_2x2_with_gap.csv": _segment_compare_2x2_with_gap,
    "lines_funnel_by_introducer_1x1.csv": _lines_funnel_by_introducer_1x1,
    "line_with_ci_band.csv": _line_with_ci_band,
}


def main() -> None:
    for name, fn in SPECS.items():
        df = fn()
        path = FIXTURES / name
        df.to_csv(path, index=False)
        print(f"wrote {path} ({len(df)} rows)")


if __name__ == "__main__":
    main()

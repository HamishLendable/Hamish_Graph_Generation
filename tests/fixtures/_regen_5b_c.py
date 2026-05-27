"""Regenerate fixture CSVs for Batch 5b-c (4 additional bar styles).

Deterministic — uses seeded numpy RNGs so the CSVs are stable across runs.
Run::

    poetry run python tests/fixtures/_regen_5b_c.py
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


def _stacked_bar_volume_2x2_with_rate_line() -> pd.DataFrame:
    rng = np.random.default_rng(20260526)
    months = pd.date_range("2024-01-01", periods=12, freq="MS").strftime("%Y-%m")
    # Per-month book-level rates
    quote_rates = 0.32 + rng.uniform(-0.05, 0.05, len(months))
    sale_rates = quote_rates * (0.55 + rng.uniform(-0.05, 0.05, len(months)))

    rows = []
    for j, m in enumerate(months):
        # Generate a per-introducer mix that sums to a sensible monthly total
        raw_mix = rng.uniform(0.05, 1.0, len(INTRODUCERS))
        mix = raw_mix / raw_mix.sum()
        monthly_count_total = int(rng.integers(800, 1800))
        avg_loan_amount = float(rng.uniform(11_000, 14_000))
        # Quoted volume is bigger than originated (sale rate < 1)
        monthly_quote_total = int(monthly_count_total / max(0.15, float(sale_rates[j])))
        for i, intro in enumerate(INTRODUCERS):
            count_i = int(round(mix[i] * monthly_count_total))
            amount_i = float(count_i * avg_loan_amount * (0.85 + rng.uniform(0, 0.3)))
            quoted_i = int(round(mix[i] * monthly_quote_total))
            rows.append(
                {
                    "month": m,
                    "introducer": intro,
                    "count": count_i,
                    "amount": round(amount_i, 2),
                    "quoted_count": quoted_i,
                    "quote_rate": round(float(quote_rates[j]), 4),
                    "sale_rate": round(float(sale_rates[j]), 4),
                }
            )
    return pd.DataFrame(rows)


def _bar_horizontal_top_n() -> pd.DataFrame:
    rng = np.random.default_rng(515)
    # 14 categories so top_n=10 truncates meaningfully
    categories = [f"Introducer {chr(65 + i)}" for i in range(14)]
    # Long-tailed distribution
    values = np.sort(rng.gamma(shape=2.0, scale=1_500_000, size=len(categories)))[::-1]
    ns = rng.integers(40, 1800, len(categories))
    # Shuffle order so the chart has to sort itself
    order = rng.permutation(len(categories))
    rows = []
    for idx in order:
        rows.append(
            {
                "category": categories[idx],
                "value": round(float(values[idx]), 2),
                "n": int(ns[idx]),
            }
        )
    return pd.DataFrame(rows)


def _bar_plus_line_share_top_n() -> pd.DataFrame:
    rng = np.random.default_rng(8742)
    categories = [f"Introducer {chr(65 + i)}" for i in range(12)]
    amount_raw = rng.gamma(shape=2.0, scale=1.0, size=len(categories))
    count_raw = amount_raw * rng.uniform(0.6, 1.6, len(categories))
    amount_share = amount_raw / amount_raw.sum()
    count_share = count_raw / count_raw.sum()
    ns = rng.integers(80, 2500, len(categories))
    rows = []
    for cat, a, c, nn in zip(categories, amount_share, count_share, ns, strict=False):
        rows.append(
            {
                "category": cat,
                "amount_share": round(float(a), 5),
                "count_share": round(float(c), 5),
                "n": int(nn),
            }
        )
    return pd.DataFrame(rows)


def _waterfall_components_by_grade() -> pd.DataFrame:
    rng = np.random.default_rng(33333)
    grade_groups = ["A-B", "C-E", "F+"]
    # Component order is preserved by the function via first-appearance.
    components = [
        ("gross yield", 1400, 200),
        ("loss", -450, 250),
        ("VT", -90, 60),
        ("commission", -180, 40),
        ("servicing", -110, 25),
        ("net IRR", 570, 180),
    ]
    rows = []
    for gi, gg in enumerate(grade_groups):
        risk_factor = 1.0 + 0.4 * gi  # higher-risk groups have bigger losses/yields
        for comp, base, spread in components:
            # Gross yield scales up with risk; losses scale up too.
            scale = risk_factor if comp in ("gross yield", "loss", "VT") else 1.0
            v = base * scale + rng.uniform(-spread, spread)
            # Net IRR is approx gross - losses - costs; let it stay synthetic.
            if comp == "net IRR":
                v = base - 80 * gi + rng.uniform(-spread, spread)
            rows.append(
                {
                    "grade_group": gg,
                    "component": comp,
                    "value": round(float(v), 2),
                }
            )
    return pd.DataFrame(rows)


SPECS = {
    "stacked_bar_volume_2x2_with_rate_line.csv": _stacked_bar_volume_2x2_with_rate_line,
    "bar_horizontal_top_n.csv": _bar_horizontal_top_n,
    "bar_plus_line_share_top_n.csv": _bar_plus_line_share_top_n,
    "waterfall_components_by_grade.csv": _waterfall_components_by_grade,
}


def main() -> None:
    for name, fn in SPECS.items():
        df = fn()
        path = FIXTURES / name
        df.to_csv(path, index=False)
        print(f"wrote {path} ({len(df)} rows)")


if __name__ == "__main__":
    main()

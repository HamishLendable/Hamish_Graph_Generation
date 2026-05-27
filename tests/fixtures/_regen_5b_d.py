"""Regenerate fixture CSVs for batch 5b_d distribution + specialised styles.

Deterministic — uses seeded numpy RNG so the CSVs are stable across runs. Run::

    poetry run python tests/fixtures/_regen_5b_d.py

Generates 5 CSVs in tests/fixtures/:
    violin_grouped.csv
    box_quantile.csv
    histogram_by_grade.csv
    cohort_grid_grade_x_period.csv
    funnel_horizontal.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

FIXTURES = Path(__file__).parent


def _violin_grouped() -> pd.DataFrame:
    """One row per observation; categories = risk grades; value = LTV."""
    rng = np.random.default_rng(101)
    grades = ["A", "B", "C", "D", "E", "F"]
    # Each grade has a different LTV distribution
    means = [0.55, 0.62, 0.68, 0.74, 0.80, 0.86]
    spreads = [0.08, 0.09, 0.10, 0.11, 0.12, 0.14]
    sizes = [800, 1200, 1500, 900, 500, 250]
    rows = []
    for g, mu, sd, n in zip(grades, means, spreads, sizes, strict=False):
        vals = np.clip(rng.normal(mu, sd, n), 0.05, 1.20)
        for v in vals:
            rows.append({"category": g, "value": round(float(v), 4), "n": n})
    return pd.DataFrame(rows)


def _box_quantile() -> pd.DataFrame:
    """One row per observation; categories = introducer channels; value = APR."""
    rng = np.random.default_rng(202)
    channels = [
        "Aggregator",
        "Broker - Dealer led",
        "Broker - Online led",
        "Dealer",
        "Direct",
    ]
    # APR distributions (decimal): centre + lognormal-ish skew
    centres = [0.075, 0.092, 0.085, 0.110, 0.068]
    spreads = [0.015, 0.020, 0.018, 0.025, 0.012]
    sizes = [700, 900, 850, 1100, 400]
    rows = []
    for ch, mu, sd, n in zip(channels, centres, spreads, sizes, strict=False):
        # Add slight skew via mix of normal + exponential tail
        normal_part = rng.normal(mu, sd, n)
        skew_part = rng.exponential(sd * 0.5, n) - sd * 0.5
        vals = np.clip(normal_part + skew_part * 0.3, 0.02, 0.30)
        for v in vals:
            rows.append({"category": ch, "value": round(float(v), 5), "n": n})
    return pd.DataFrame(rows)


def _histogram_by_grade() -> pd.DataFrame:
    """One row per observation; value = origination score; grade = risk grade."""
    rng = np.random.default_rng(303)
    grades = ["A", "B", "C", "D", "E", "F"]
    # Score distributions: higher score → safer grade
    centres = [780, 720, 660, 600, 540, 480]
    spreads = [25, 28, 32, 35, 38, 42]
    sizes = [1500, 1800, 2000, 1200, 700, 300]
    rows = []
    for g, mu, sd, n in zip(grades, centres, spreads, sizes, strict=False):
        vals = np.clip(rng.normal(mu, sd, n), 300, 850).astype(int)
        for v in vals:
            rows.append({"value": int(v), "grade": g, "n": n})
    return pd.DataFrame(rows)


def _cohort_grid_grade_x_period() -> pd.DataFrame:
    """Per (grade, period, MOB) row with actual/model + pre-computed dev text."""
    rng = np.random.default_rng(404)
    grades = ["A", "B", "C", "D", "E"]
    periods = ["2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4"]
    mobs = np.arange(0, 13)

    rows = []
    base_rates = {"A": 0.012, "B": 0.020, "C": 0.030, "D": 0.045, "E": 0.062}
    for g in grades:
        base = base_rates[g]
        for p in periods:
            # Model curve: smooth ramp
            model_curve = base * (1 - np.exp(-mobs / 5))
            # Actual: model + per-cohort drift
            drift = rng.uniform(-0.4, 0.4)
            noise = rng.normal(0, base * 0.05, len(mobs))
            actual_curve = model_curve * (1 + drift) + noise
            # Deviation at final MOB
            dev_pct = (actual_curve[-1] - model_curve[-1]) / model_curve[-1] * 100
            sign = "+" if dev_pct >= 0 else ""
            dev_text = f"Dev: {sign}{dev_pct:.1f}%"
            n_cell = int(rng.integers(120, 800))
            for m, a, mod in zip(mobs, actual_curve, model_curve, strict=False):
                rows.append(
                    {
                        "grade": g,
                        "period": p,
                        "mob": int(m),
                        "actual": round(float(max(0.0, a)), 5),
                        "model": round(float(mod), 5),
                        "deviation_text": dev_text,
                        "n": n_cell,
                    }
                )
    return pd.DataFrame(rows)


def _funnel_horizontal() -> pd.DataFrame:
    """Stage × count rows in funnel order (top wider, bottom narrower)."""
    stages = [
        ("Applications", 12_500),
        ("Quoted", 8_800),
        ("Accepted", 5_400),
        ("Documents complete", 3_700),
        ("Originated", 2_950),
    ]
    rows = [{"stage": s, "count": c, "n": c} for s, c in stages]
    return pd.DataFrame(rows)


SPECS = {
    "violin_grouped.csv": _violin_grouped,
    "box_quantile.csv": _box_quantile,
    "histogram_by_grade.csv": _histogram_by_grade,
    "cohort_grid_grade_x_period.csv": _cohort_grid_grade_x_period,
    "funnel_horizontal.csv": _funnel_horizontal,
}


def main() -> None:
    for name, fn in SPECS.items():
        df = fn()
        path = FIXTURES / name
        df.to_csv(path, index=False)
        print(f"wrote {path} ({len(df)} rows)")


if __name__ == "__main__":
    main()

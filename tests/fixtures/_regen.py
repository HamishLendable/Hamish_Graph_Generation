"""Regenerate the 6 v0.1 fixture CSVs from synthetic distributions.

Deterministic — uses seeded numpy RNG so the CSVs are stable across runs.
Run::

    poetry run python tests/fixtures/_regen.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

FIXTURES = Path(__file__).parent


def _dq_2x2() -> pd.DataFrame:
    rng = np.random.default_rng(99)
    cohorts = pd.date_range("2024-01-01", periods=15, freq="MS").strftime("%Y-%m")
    metrics = [
        ("30+ DPD at MOB 1", 0.018),
        ("30+ DPD at MOB 3", 0.035),
        ("60+ DPD at MOB 6", 0.022),
        ("90+ DPD at MOB 9", 0.028),
    ]
    rows = []
    for met, base in metrics:
        actual = base + rng.uniform(-0.005, 0.005, len(cohorts))
        # taper last 3 (immature)
        actual[-3:] = actual[-3:] * np.linspace(0.7, 0.4, 3)
        n_per = rng.integers(150, 600, len(cohorts))
        for c, a, nn in zip(cohorts, actual, n_per, strict=False):
            rows.append({"cohort": c, "metric": met, "actual": round(float(a), 5),
                          "expected": base, "n": int(nn)})
    return pd.DataFrame(rows)


def _cohort_lines() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    cohorts = pd.date_range("2024-01-01", periods=12, freq="MS").strftime("%Y-%m")
    mobs = np.arange(0, 25)
    rows = []
    expected_curve = 0.04 * (1 - np.exp(-mobs / 8))
    for i, c in enumerate(cohorts):
        peak = 0.04 + rng.uniform(-0.005, 0.005)
        curve = peak * (1 - np.exp(-mobs / 8))
        max_mob = max(2, 24 - i * 2)
        n_size = int(rng.integers(300, 900))
        for m, r, exp in zip(mobs, curve, expected_curve, strict=False):
            if m <= max_mob:
                rows.append({"cohort": c, "mob": int(m), "rate": round(float(r), 5),
                              "expected": round(float(exp), 5), "n": n_size})
    return pd.DataFrame(rows)


def _grouped_bars() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    grades = ["A", "B", "C", "D", "E", "F", "F*", "F**"]
    bev = 0.01 + 0.005 * np.arange(len(grades)) + rng.uniform(-0.005, 0.005, len(grades))
    rob = bev * 0.85 + rng.uniform(-0.003, 0.003, len(grades))
    n_bev = rng.integers(100, 500, len(grades))
    n_rob = rng.integers(800, 2000, len(grades))
    rows = []
    for g, b, r_, nb, nr in zip(grades, bev, rob, n_bev, n_rob, strict=False):
        rows.append({"grade": g, "series": "BEV", "rate": round(float(b), 5), "n": int(nb)})
        rows.append({"grade": g, "series": "Rest of book", "rate": round(float(r_), 5), "n": int(nr)})
    return pd.DataFrame(rows)


def _stacked_100pct() -> pd.DataFrame:
    rng = np.random.default_rng(13)
    months = pd.date_range("2024-01-01", periods=18, freq="MS").strftime("%Y-%m")
    categories = [
        "Aggregator", "Broker - Dealer led", "Broker - Online led",
        "Dealer", "Direct", "Unknown introducer",
    ]
    raw = rng.uniform(0.1, 1.0, (len(categories), len(months)))
    shares = raw / raw.sum(axis=0, keepdims=True) * 100
    ns = rng.integers(500, 2500, len(months))
    rows = []
    for i, cat in enumerate(categories):
        for j, m in enumerate(months):
            rows.append({"month": m, "category": cat, "share": round(float(shares[i, j]), 2),
                          "n": int(ns[j])})
    return pd.DataFrame(rows)


def _swap_matrix() -> pd.DataFrame:
    rng = np.random.default_rng(2024)
    grades = ["A", "B", "C", "D", "E", "F"]
    rows = []
    for i, gx in enumerate(grades):
        for j, gy in enumerate(grades):
            # Stronger diagonal weight, weaker off-diagonal
            d = abs(i - j)
            base = max(50, 600 - 90 * d)
            count = int(rng.integers(int(base * 0.7), int(base * 1.3)))
            pct_amount = round(rng.uniform(0.1, 4.0), 1)
            rows.append({"x_grade": gx, "y_grade": gy, "count": count, "pct_amount": pct_amount})
    return pd.DataFrame(rows)


def _calibration_scatter() -> pd.DataFrame:
    rng = np.random.default_rng(314)
    rows = []
    for i in range(10):
        expected = 0.005 + i * 0.01 + rng.uniform(-0.001, 0.001)
        actual = expected + rng.uniform(-0.004, 0.006)
        n = int(rng.integers(80, 700))
        rows.append({"bucket": f"B{i + 1}", "expected_pd": round(float(expected), 5),
                      "actual_default": round(float(max(0.0, actual)), 5), "n": n})
    return pd.DataFrame(rows)


SPECS = {
    "dq_2x2.csv": _dq_2x2,
    "cohort_lines.csv": _cohort_lines,
    "grouped_bars_by_grade.csv": _grouped_bars,
    "stacked_100pct.csv": _stacked_100pct,
    "swap_matrix.csv": _swap_matrix,
    "calibration_scatter.csv": _calibration_scatter,
}


def main() -> None:
    for name, fn in SPECS.items():
        df = fn()
        path = FIXTURES / name
        df.to_csv(path, index=False)
        print(f"wrote {path} ({len(df)} rows)")

    # Auto-discover and run sibling regen modules (_regen_5b_*.py and any future _regen_*.py).
    import importlib.util

    for path in sorted(FIXTURES.glob("_regen_5b_*.py")):
        print(f"-- {path.name} --")
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()


if __name__ == "__main__":
    main()

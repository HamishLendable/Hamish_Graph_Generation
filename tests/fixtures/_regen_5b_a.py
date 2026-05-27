"""Regenerate the 5 batch-5b-a fixture CSVs from synthetic distributions.

Deterministic — seeded numpy RNGs so CSVs are stable across runs.
Run::

    poetry run python tests/fixtures/_regen_5b_a.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

FIXTURES = Path(__file__).parent


def _dq_2x2_with_n_annotated() -> pd.DataFrame:
    """4 metrics × 15 cohorts. n spans <50, 50-200, ≥200 to exercise fade/suppress."""
    rng = np.random.default_rng(101)
    cohorts = pd.date_range("2024-01-01", periods=15, freq="MS").strftime("%Y-%m")
    metrics = [
        ("30+ DPD at MOB 1", 0.018),
        ("30+ DPD at MOB 3", 0.035),
        ("60+ DPD at MOB 6", 0.022),
        ("90+ DPD at MOB 9", 0.028),
    ]
    # Engineered n distribution per metric:
    #  - first 9 cohorts: large n (>=200) for mature
    #  - cohorts 9..11 (immature): medium 50<=n<200 → faded
    #  - cohorts 12..14 (very immature): tiny n<50 → suppressed
    rows = []
    for met, base in metrics:
        actual = base + rng.uniform(-0.005, 0.005, len(cohorts))
        actual[-3:] = actual[-3:] * np.linspace(0.7, 0.4, 3)
        ns = np.empty(len(cohorts), dtype=int)
        ns[:9] = rng.integers(250, 600, 9)
        ns[9:12] = rng.integers(60, 180, 3)
        ns[12:] = rng.integers(15, 45, 3)
        for c, a, nn in zip(cohorts, actual, ns, strict=False):
            rows.append({
                "cohort": c,
                "metric": met,
                "actual": round(float(a), 5),
                "expected": base,
                "n": int(nn),
            })
    return pd.DataFrame(rows)


def _regression_validation_1x3() -> pd.DataFrame:
    """3 metrics × 12 cohorts. actual vs predicted."""
    rng = np.random.default_rng(202)
    cohorts = pd.date_range("2024-01-01", periods=12, freq="MS").strftime("%Y-%m")
    metrics = [
        ("30+ DPD at MOB 3", 0.030),
        ("60+ DPD at MOB 6", 0.022),
        ("90+ DPD at MOB 9", 0.028),
    ]
    rows = []
    for met, base in metrics:
        predicted = base + rng.uniform(-0.001, 0.001, len(cohorts))
        actual = predicted + rng.uniform(-0.005, 0.005, len(cohorts))
        actual[-2:] = actual[-2:] * np.linspace(0.7, 0.5, 2)
        ns = rng.integers(200, 800, len(cohorts))
        for c, a, p, nn in zip(cohorts, actual, predicted, ns, strict=False):
            rows.append({
                "cohort": c,
                "metric": met,
                "actual": round(float(max(0.0, a)), 5),
                "predicted": round(float(p), 5),
                "n": int(nn),
            })
    return pd.DataFrame(rows)


def _cohort_lines_1x3_by_grade_group() -> pd.DataFrame:
    """8 cohorts × MOB 0..18 × 3 grade groups. Single expected curve per group."""
    rng = np.random.default_rng(303)
    cohorts = pd.date_range("2024-01-01", periods=8, freq="MS").strftime("%Y-%m")
    mobs = np.arange(0, 19)
    grade_groups = [
        ("A-B", 0.020),
        ("C-E", 0.045),
        ("F+",  0.085),
    ]
    rows = []
    for g, base in grade_groups:
        expected_curve = base * (1 - np.exp(-mobs / 8))
        for i, c in enumerate(cohorts):
            peak = base + rng.uniform(-0.005, 0.005)
            curve = peak * (1 - np.exp(-mobs / 8))
            max_mob = max(2, 18 - i * 2)
            n_size = int(rng.integers(300, 900))
            for m, r, exp in zip(mobs, curve, expected_curve, strict=False):
                if m <= max_mob:
                    rows.append({
                        "cohort": c,
                        "mob": int(m),
                        "grade_group": g,
                        "rate": round(float(r), 5),
                        "expected": round(float(exp), 5),
                        "n": n_size,
                    })
    return pd.DataFrame(rows)


def _cohort_lines_1x3_paired_expected() -> pd.DataFrame:
    """8 cohorts × MOB 0..18 × 3 grade groups. Per-cohort expected curve."""
    rng = np.random.default_rng(404)
    cohorts = pd.date_range("2024-01-01", periods=8, freq="MS").strftime("%Y-%m")
    mobs = np.arange(0, 19)
    grade_groups = [
        ("A-B", 0.020),
        ("C-E", 0.045),
        ("F+",  0.085),
    ]
    rows = []
    for g, base in grade_groups:
        for i, c in enumerate(cohorts):
            # Per-cohort expected (planned at origination)
            expected_peak = base + rng.uniform(-0.003, 0.003)
            expected_curve = expected_peak * (1 - np.exp(-mobs / 8))
            # Actual drift: cohort i drifts by a noisy multiplier vs its own plan
            drift = 1.0 + rng.uniform(-0.10, 0.20)
            actual_curve = expected_peak * drift * (1 - np.exp(-mobs / 8))
            max_mob = max(2, 18 - i * 2)
            n_size = int(rng.integers(300, 900))
            for m, a, exp in zip(mobs, actual_curve, expected_curve, strict=False):
                if m <= max_mob:
                    rows.append({
                        "cohort": c,
                        "mob": int(m),
                        "grade_group": g,
                        "actual": round(float(a), 5),
                        "expected": round(float(exp), 5),
                        "n": n_size,
                    })
    return pd.DataFrame(rows)


def _roll_rate_dual_axis_lines() -> pd.DataFrame:
    """18 months × 4 series. One small-scale roll, three large-scale rolls.

    Series:
        early_roll          (LEFT axis, ~0.4-0.8%)  — solid blue
        mid_roll            (RIGHT axis, ~1-2%)     — solid orange
        late_roll           (RIGHT axis, ~2-3.5%)   — solid green
        late_roll_improved  (RIGHT axis, dashed)    — counterfactual indicator
    """
    rng = np.random.default_rng(505)
    months = pd.date_range("2024-01-01", periods=18, freq="MS").strftime("%Y-%m")
    early = 0.005 + rng.uniform(-0.001, 0.003, len(months))
    mid = 0.015 + rng.uniform(-0.003, 0.005, len(months))
    late = 0.028 + rng.uniform(-0.004, 0.007, len(months))
    late_improved = late * 0.75  # always lower than the actual late_roll
    n_totals = rng.integers(800, 2500, len(months))
    rows = []
    for m, e, mi, la, lai, nn in zip(months, early, mid, late, late_improved, n_totals, strict=False):
        rows.append({
            "month": m,
            "early_roll": round(float(max(0.0, e)), 5),
            "mid_roll": round(float(max(0.0, mi)), 5),
            "late_roll": round(float(max(0.0, la)), 5),
            "late_roll_improved": round(float(max(0.0, lai)), 5),
            "n": int(nn),
        })
    return pd.DataFrame(rows)


SPECS = {
    "dq_2x2_with_n_annotated.csv": _dq_2x2_with_n_annotated,
    "regression_validation_1x3.csv": _regression_validation_1x3,
    "cohort_lines_1x3_by_grade_group.csv": _cohort_lines_1x3_by_grade_group,
    "cohort_lines_1x3_paired_expected.csv": _cohort_lines_1x3_paired_expected,
    "roll_rate_dual_axis_lines.csv": _roll_rate_dual_axis_lines,
}


def main() -> None:
    for name, fn in SPECS.items():
        df = fn()
        path = FIXTURES / name
        df.to_csv(path, index=False)
        print(f"wrote {path} ({len(df)} rows)")


if __name__ == "__main__":
    main()

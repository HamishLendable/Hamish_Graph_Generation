"""Tests for motor_graphs.recipes.risk (Batch 5h).

Snowflake is mocked at the data layer via
``monkeypatch.setattr(snowflake, "run_query", ...)`` so these tests never
touch a live warehouse.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from motor_graphs.data import snowflake
from motor_graphs.recipes import risk

# ----------------------------------------------------------------- pd_calibration_irr


def _fake_calibration_df(n_buckets: int = 10) -> pd.DataFrame:
    """Fake calibration aggregate matching the recipe's SQL output."""
    return pd.DataFrame(
        {
            "bucket": list(range(1, n_buckets + 1)),
            "expected_pd": [0.01 + i * 0.02 for i in range(n_buckets)],
            "actual_default": [0.012 + i * 0.022 for i in range(n_buckets)],
            "n": [500 - i * 10 for i in range(n_buckets)],
        }
    )


def test_pd_calibration_irr_returns_figure(monkeypatch):
    fake = _fake_calibration_df(10)
    monkeypatch.setattr(snowflake, "run_query", lambda sql: fake)

    fig = risk.pd_calibration_irr("2023-01-01", "2024-01-01")

    assert isinstance(fig, go.Figure)
    # Two traces: y=x diagonal + points.
    assert len(fig.data) == 2
    # Bucket labels should have been rewritten "B1", "B2", ...
    points = fig.data[1]
    assert points.text is not None
    assert list(points.text) == [f"B{i}" for i in range(1, 11)]
    # Default title uses the cohort range.
    assert "2023-01-01" in fig.layout.title.text
    assert "2024-01-01" in fig.layout.title.text


def test_pd_calibration_irr_validates_dates():
    with pytest.raises(ValueError):
        risk.pd_calibration_irr("2024-04-01", "2024-01-01")
    with pytest.raises(ValueError):
        risk.pd_calibration_irr("2024-04-01", "2024-04-01")


# ---------------------------------------------------- segment_compare_dealer_vs_nondealer


def _fake_segment_compare_df() -> pd.DataFrame:
    """Fake (month, is_dealer, raw_grade) aggregate.

    Designed so that:
        * dealer has more F+ (risky) loans than non-dealer per month → mix
          counterfactual should pull the non-dealer rate UP.
        * non-dealer per-grade rates differ across A / C / F so the mix
          adjustment has signal.
    """
    rows = []
    for month in ("2024-01", "2024-02", "2024-03"):
        # Dealer rows — heavier on the F+ end.
        rows.extend(
            [
                {"month": month, "is_dealer": 1, "raw_grade": "A", "n_loans": 50, "n_dq": 2},
                {"month": month, "is_dealer": 1, "raw_grade": "C", "n_loans": 100, "n_dq": 10},
                {"month": month, "is_dealer": 1, "raw_grade": "F", "n_loans": 150, "n_dq": 45},
            ]
        )
        # Non-dealer rows — heavier on the A end.
        rows.extend(
            [
                {"month": month, "is_dealer": 0, "raw_grade": "A", "n_loans": 200, "n_dq": 4},
                {"month": month, "is_dealer": 0, "raw_grade": "C", "n_loans": 100, "n_dq": 8},
                {"month": month, "is_dealer": 0, "raw_grade": "F", "n_loans": 50, "n_dq": 10},
            ]
        )
    return pd.DataFrame(rows)


def test_segment_compare_dealer_vs_nondealer_returns_figure(monkeypatch):
    fake = _fake_segment_compare_df()
    monkeypatch.setattr(snowflake, "run_query", lambda sql: fake)

    fig = risk.segment_compare_dealer_vs_nondealer("2024-01-01", "2024-04-01")

    assert isinstance(fig, go.Figure)
    # Style guarantees 7 traces: 3 rate lines + 1 gap bar + 2 mix bars + 1 adjusted line.
    assert len(fig.data) == 7
    # Default title mentions the DQ column + cohort range.
    title = fig.layout.title.text
    assert "DQ_90_BY_9" in title
    assert "2024-01-01" in title
    assert "2024-04-01" in title


def test_segment_compare_dealer_vs_nondealer_mix_adjusted_computed(monkeypatch):
    """Sanity-check the mix-adjustment: b_adj must lie within the per-grade-group
    range of non-dealer rates (i.e. it's a convex combination of those rates).
    """
    fake = _fake_segment_compare_df()
    monkeypatch.setattr(snowflake, "run_query", lambda sql: fake)

    captured: dict[str, pd.DataFrame] = {}

    def spy_style(df, **kwargs):
        captured["df"] = df.copy()
        # Return any Figure so the recipe returns successfully.
        return go.Figure()

    monkeypatch.setattr(
        "motor_graphs.styles.segment_compare_2x2_with_gap", spy_style
    )
    # The recipe imports the style via ``motor_graphs.styles.<...>``; patching the
    # attribute on the package is sufficient because risk.py looks it up as
    # ``styles.segment_compare_2x2_with_gap``.
    import motor_graphs.recipes.risk as risk_mod

    monkeypatch.setattr(
        risk_mod.styles, "segment_compare_2x2_with_gap", spy_style
    )

    risk.segment_compare_dealer_vs_nondealer("2024-01-01", "2024-04-01")

    df = captured["df"]
    # Non-dealer per-grade rates (constant across months in the fixture):
    #   A: 4/200 = 0.020
    #   C: 8/100 = 0.080
    #   F: 10/50 = 0.200
    nondealer_rates = [4 / 200, 8 / 100, 10 / 50]
    lo = min(nondealer_rates)
    hi = max(nondealer_rates)

    assert len(df) == 3
    for _, row in df.iterrows():
        assert lo - 1e-9 <= row["b_adj"] <= hi + 1e-9, (
            f"b_adj={row['b_adj']} outside non-dealer per-grade range "
            f"[{lo}, {hi}] for month={row['month']}"
        )
        # And b_adj should be > b (raw non-dealer rate) because dealer mix is
        # skewed toward F+ which has the worst per-group rate.
        assert row["b_adj"] > row["b"], (
            f"Dealer mix is heavier on F+, so b_adj ({row['b_adj']}) should "
            f"exceed b ({row['b']}) for month={row['month']}"
        )

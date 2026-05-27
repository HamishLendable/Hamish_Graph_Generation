"""Mocked tests for motor_graphs.recipes.funnel_distributions (Batch 5g)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from motor_graphs.recipes import funnel_distributions

# ---------------------------------------------------------------- fixtures ----


def _fake_funnel_df() -> pd.DataFrame:
    """Mimic what run_query returns for the funnel SQL (lowercased columns)."""
    return pd.DataFrame(
        {
            "stage": [
                "Applications",
                "Quoted",
                "Bureau passed",
                "Affordability",
                "Contract signed",
                "Originated",
            ],
            "stage_order": [1, 2, 3, 4, 5, 6],
            "cnt": [10000, 7500, 6000, 4500, 2000, 1500],
        }
    )


def _fake_score_df() -> pd.DataFrame:
    """Mimic what run_query returns for the score-distribution SQL."""
    return pd.DataFrame(
        {
            "value": [600, 620, 640, 660, 680, 700, 720, 740, 760, 780],
            "raw_grade": ["A^", "A", "B^", "B", "C", "D^", "E", "F", "F*", "F**"],
        }
    )


# ---------------------------------------------------------------- funnel ----


def test_funnel_app_to_originated_returns_figure(monkeypatch):
    captured_sql: dict[str, str] = {}

    def fake_run_query(sql: str) -> pd.DataFrame:
        captured_sql["sql"] = sql
        return _fake_funnel_df()

    monkeypatch.setattr(funnel_distributions, "run_query", fake_run_query)

    fig = funnel_distributions.funnel_app_to_originated("2024-01-01", "2024-02-01")
    assert isinstance(fig, go.Figure)
    # exactly one Funnel trace
    assert len(fig.data) == 1
    assert fig.data[0].type == "funnel"
    # SQL was executed and includes the cohort dates
    assert "2024-01-01" in captured_sql["sql"]
    assert "2024-02-01" in captured_sql["sql"]
    assert "PRS__APPLICATION__MOTOR" in captured_sql["sql"]


def test_funnel_app_to_originated_stages_in_order(monkeypatch):
    monkeypatch.setattr(funnel_distributions, "run_query", lambda sql: _fake_funnel_df())

    fig = funnel_distributions.funnel_app_to_originated(
        "2024-01-01", "2024-02-01", title="My funnel"
    )
    # Funnel y-axis carries the stage labels in order
    y_labels = list(fig.data[0].y)
    assert y_labels == [
        "Applications",
        "Quoted",
        "Bureau passed",
        "Affordability",
        "Contract signed",
        "Originated",
    ]
    # Counts strictly decreasing through the funnel (sanity-check from the fixture)
    counts = list(fig.data[0].x)
    assert counts == sorted(counts, reverse=True)
    assert fig.layout.title.text == "My funnel"


# ---------------------------------------------------------------- score dist ----


def test_score_distribution_by_grade_returns_figure(monkeypatch):
    captured_sql: dict[str, str] = {}

    def fake_run_query(sql: str) -> pd.DataFrame:
        captured_sql["sql"] = sql
        return _fake_score_df()

    monkeypatch.setattr(funnel_distributions, "run_query", fake_run_query)

    fig = funnel_distributions.score_distribution_by_grade(
        "2024-01-01", "2024-02-01", score_col="DELPHI_SCORE", nbins=20
    )
    assert isinstance(fig, go.Figure)
    # one Histogram trace per simplified grade present
    assert len(fig.data) >= 1
    for tr in fig.data:
        assert tr.type == "histogram"
    # The score column name appears in the SQL and is used as xlabel
    assert "DELPHI_SCORE" in captured_sql["sql"]
    assert "ORIGINATION_SIMPLIFIED_RISK_GRADE" in captured_sql["sql"]
    assert "PRS__APPLICATION__MOTOR" in captured_sql["sql"]
    assert fig.layout.xaxis.title.text == "DELPHI_SCORE"


def test_score_distribution_by_grade_rejects_invalid_score_col(monkeypatch):
    # Stub run_query so a leak past validation would be obvious in the message.
    monkeypatch.setattr(
        funnel_distributions,
        "run_query",
        lambda sql: pytest.fail("run_query should not be called for invalid score_col"),
    )
    with pytest.raises(ValueError, match="score_col"):
        funnel_distributions.score_distribution_by_grade(
            "2024-01-01", "2024-02-01", score_col="HACKED"
        )

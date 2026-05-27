"""Tests for motor_graphs.recipes.dq — DQ recipes (Batch 5e).

All tests mock motor_graphs.data.snowflake.run_query so no live Snowflake.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import pytest

from motor_graphs.data import snowflake
from motor_graphs.recipes import dq

# ----------------------------------------------------------- dq_aging_by_grade ----


def test_dq_aging_by_grade_returns_figure(monkeypatch):
    """Recipe returns a plotly Figure when run_query is mocked with a small DF."""
    # Three grade groups (A→A-B, C→C-E, F→F+) so the 1x3 style finds exactly 3.
    fake = pd.DataFrame(
        {
            "cohort":    ["2024-01", "2024-01", "2024-01", "2024-02", "2024-02", "2024-02"],
            "mob":       [3,         6,         9,         3,         6,         9],
            "raw_grade": ["A",       "C",       "F",       "A",       "C",       "F"],
            "n_at_mob":  [100,       80,        50,        120,       90,        60],
            "n_dq_30":   [2,         5,         8,         3,         6,         9],
        }
    )

    monkeypatch.setattr(snowflake, "run_query", lambda sql: fake)

    fig = dq.dq_aging_by_grade("2024-01-01", "2024-04-01")
    assert isinstance(fig, go.Figure)
    assert hasattr(fig, "data")
    # Title was auto-built from the cohort range
    assert "2024-01-01" in fig.layout.title.text
    assert "2024-04-01" in fig.layout.title.text


def test_dq_aging_by_grade_validates_dates():
    """Passing cohort_start >= cohort_end must raise ValueError."""
    with pytest.raises(ValueError):
        dq.dq_aging_by_grade("2024-04-01", "2024-01-01")
    with pytest.raises(ValueError):
        dq.dq_aging_by_grade("2024-04-01", "2024-04-01")


# ----------------------------------------------------------- dq_2x2_recent_book ----


def test_dq_2x2_recent_book_returns_figure(monkeypatch):
    """Recipe returns a plotly Figure when run_query is mocked with a small DF."""
    fake = pd.DataFrame(
        {
            "cohort": ["2024-01", "2024-02", "2024-03"],
            "n":      [500,       600,       550],
            "n_30_1": [10,        14,        12],
            "n_30_3": [18,        22,        20],
            "n_60_6": [11,        13,        12],
            "n_90_9": [12,        15,        14],
        }
    )

    monkeypatch.setattr(snowflake, "run_query", lambda sql: fake)

    fig = dq.dq_2x2_recent_book("2024-01-01", "2024-04-01")
    assert isinstance(fig, go.Figure)
    assert hasattr(fig, "data")
    # 4 metrics × 2 series (actual + expected) = 8 traces
    assert len(fig.data) == 8


def test_dq_2x2_recent_book_custom_title(monkeypatch):
    """The title kwarg should propagate through to the resulting Figure."""
    fake = pd.DataFrame(
        {
            "cohort": ["2024-01", "2024-02"],
            "n":      [500,       600],
            "n_30_1": [10,        14],
            "n_30_3": [18,        22],
            "n_60_6": [11,        13],
            "n_90_9": [12,        15],
        }
    )

    monkeypatch.setattr(snowflake, "run_query", lambda sql: fake)

    custom = "Custom DQ Title — Q1 2024"
    fig = dq.dq_2x2_recent_book("2024-01-01", "2024-04-01", title=custom)
    assert fig.layout.title.text == custom

"""Tests for motor_graphs.recipes.volume (Batch 5f).

Snowflake is mocked at the data layer via
``monkeypatch.setattr(snowflake, "run_query", ...)`` so these tests never
touch a live warehouse.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from motor_graphs.data import snowflake
from motor_graphs.recipes import volume

# ---------------------------------------------------------------- league table ----


def _fake_league_df(n_rows: int) -> pd.DataFrame:
    """Return a fake league-table DataFrame matching the recipe's SQL output."""
    return pd.DataFrame(
        {
            "category": [f"Introducer {i}" for i in range(n_rows)],
            "value": [1_000_000.0 - i * 50_000.0 for i in range(n_rows)],
            "n": [200 - i * 5 for i in range(n_rows)],
        }
    )


def test_introducer_volume_league_table_returns_figure(monkeypatch):
    fake = _fake_league_df(12)
    monkeypatch.setattr(snowflake, "run_query", lambda sql: fake)

    fig = volume.introducer_volume_league_table("2024-01-01", "2024-04-01")

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    # Default top_n=10 → expect 10 bars on the single horizontal Bar trace.
    assert len(fig.data[0].y) == 10
    # Title uses date range when none passed.
    assert "2024-01-01" in fig.layout.title.text
    assert "2024-04-01" in fig.layout.title.text


def test_introducer_volume_league_table_respects_top_n(monkeypatch):
    fake = _fake_league_df(12)
    monkeypatch.setattr(snowflake, "run_query", lambda sql: fake)

    fig = volume.introducer_volume_league_table(
        "2024-01-01", "2024-04-01", top_n=5, title="Custom title"
    )

    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    # top_n=5 → only 5 bars rendered.
    assert len(fig.data[0].y) == 5
    assert fig.layout.title.text == "Custom title"


# ---------------------------------------------------------------- monthly mix ----


def _fake_monthly_mix_df() -> pd.DataFrame:
    """Return a fake monthly-mix DataFrame matching the recipe's SQL output."""
    rows = []
    for month in ("2024-01", "2024-02", "2024-03"):
        rows.extend(
            [
                {"month": month, "introducer": "Carwow Aggregator", "amount": 1_000_000.0, "n": 50},
                {"month": month, "introducer": "Acme Broker Dealer led", "amount": 500_000.0, "n": 30},
                {"month": month, "introducer": "OnlineCo Broker Online led", "amount": 250_000.0, "n": 20},
                {"month": month, "introducer": "MainStreet Dealer", "amount": 750_000.0, "n": 40},
                {"month": month, "introducer": "Lendable Direct", "amount": 100_000.0, "n": 10},
            ]
        )
    return pd.DataFrame(rows)


def test_introducer_volume_mix_monthly_returns_figure(monkeypatch):
    fake = _fake_monthly_mix_df()
    monkeypatch.setattr(snowflake, "run_query", lambda sql: fake)

    fig = volume.introducer_volume_mix_monthly("2024-01-01", "2024-04-01")

    assert isinstance(fig, go.Figure)
    # 5 stacked categories → 5 Bar traces.
    assert len(fig.data) == 5
    trace_names = {t.name for t in fig.data}
    assert trace_names == {
        "Aggregator",
        "Broker - Dealer led",
        "Broker - Online led",
        "Dealer",
        "Direct",
    }
    # Title uses date range when none passed.
    assert "2024-01-01" in fig.layout.title.text
    assert "2024-04-01" in fig.layout.title.text


def test_introducer_volume_mix_monthly_custom_title(monkeypatch):
    fake = _fake_monthly_mix_df()
    monkeypatch.setattr(snowflake, "run_query", lambda sql: fake)

    fig = volume.introducer_volume_mix_monthly(
        "2024-01-01", "2024-04-01", title="My custom mix title"
    )

    assert isinstance(fig, go.Figure)
    assert fig.layout.title.text == "My custom mix title"

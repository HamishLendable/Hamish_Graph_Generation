"""Introducer volume recipes (Batch 5f).

Thin Snowflake-aware wrappers that pull originated-loan volume from
``PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR``, reshape, and hand off to a
chart style from :mod:`motor_graphs.styles`.

Recipes
-------
* :func:`introducer_volume_league_table` — Top-N introducers by originated £.
* :func:`introducer_volume_mix_monthly`  — Monthly 100%-stacked mix across the
  5-category introducer taxonomy (Aggregator / Broker - Dealer led /
  Broker - Online led / Dealer / Direct).

Notes
-----
The richer 5-category taxonomy is applied **in-recipe** off the raw
``INTRODUCER`` column rather than relying on the pandas-side
``normalize_introducer_category`` helper (which collapses everything to
Broker / Aggregator / Direct). See ``docs/discovery/snowflake_conventions.md``
for the column reference.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from motor_graphs import styles
from motor_graphs.data import snowflake

from ._shared import validate_cohort_range

# ----------------------------------------------------------------------------- helpers


def _categorise_introducer(name: object) -> str:
    """Map a raw ``INTRODUCER`` string to one of the 5 EV-chart categories.

    Categories (in priority order):
        ``Aggregator``, ``Broker - Dealer led``, ``Broker - Online led``,
        ``Dealer``, ``Direct``, ``Unknown introducer``.
    """
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return "Unknown introducer"
    n = str(name).lower().strip()
    if not n:
        return "Unknown introducer"
    if "aggregator" in n:
        return "Aggregator"
    if "dealer led" in n:
        return "Broker - Dealer led"
    if "online led" in n:
        return "Broker - Online led"
    if "dealer" in n:
        return "Dealer"
    if "direct" in n:
        return "Direct"
    return "Unknown introducer"


# ----------------------------------------------------------------------------- recipes


def introducer_volume_league_table(
    cohort_start: date | str,
    cohort_end: date | str,
    *,
    top_n: int = 10,
    title: Optional[str] = None,
) -> go.Figure:
    """Top-N introducers by £ originated volume in the cohort window.

    Use this when:
        - You need a league-table view of which introducers wrote the most
          originated volume in a given cohort window.
        - You want to spot concentration risk in a small number of partners.

    Snowflake tables used:
        - ``PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR`` (filtered on
          ``APPLICATION_CREATED_DATETIME`` half-open + originated flag).

    Parameters:
        cohort_start: inclusive lower bound for ``APPLICATION_CREATED_DATETIME``.
        cohort_end:   exclusive upper bound for ``APPLICATION_CREATED_DATETIME``.
        top_n: number of introducers to retain (default 10).
        title: optional override; default uses the date range.

    Returns:
        ``plotly.graph_objects.Figure`` from
        :func:`motor_graphs.styles.bar_horizontal_top_n`.

    Example:
        >>> fig = introducer_volume_league_table("2024-01-01", "2024-04-01", top_n=10)
    """
    start, end = validate_cohort_range(cohort_start, cohort_end)

    sql = f"""
        SELECT
          a.INTRODUCER AS category,
          SUM(a.FINAL_GROSS_AMOUNT) AS value,
          COUNT(DISTINCT a.LOAN_ID) AS n
        FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR a
        WHERE a.APPLICATION_CREATED_DATETIME >= '{start}'
          AND a.APPLICATION_CREATED_DATETIME <  '{end}'
          AND COALESCE(a.FLAG_ORIGINATED_AND_NOT_CANCELLED, a.FLAG_ORIGINATED) = TRUE
          AND a.INTRODUCER IS NOT NULL
        GROUP BY 1
        ORDER BY value DESC
        LIMIT {top_n}
    """

    df = snowflake.run_query(sql)

    return styles.bar_horizontal_top_n(
        df,
        category="category",
        value="value",
        n="n",
        top_n=top_n,
        value_fmt="£,.0f",
        title=title or f"Top-{top_n} introducers by £ volume — {start} to {end}",
        xlabel="£ originated",
    )


def introducer_volume_mix_monthly(
    cohort_start: date | str,
    cohort_end: date | str,
    *,
    title: Optional[str] = None,
) -> go.Figure:
    """Monthly 100%-stacked originated-volume mix across the 5 introducer categories.

    Use this when:
        - You need to track how monthly £-originated mix splits across
          Aggregator / Broker - Dealer led / Broker - Online led / Dealer /
          Direct over time.
        - You want to spot channel regime shifts (e.g. Aggregator growing).

    Snowflake tables used:
        - ``PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR`` (filtered on
          ``ORIGINATION_DATETIME`` half-open + originated flag).

    Notes:
        The richer 5-category taxonomy is built in-recipe from the raw
        ``INTRODUCER`` string — ``normalize_introducer_category`` would
        collapse this to 3 categories which loses the Dealer-led vs
        Online-led split.

    Parameters:
        cohort_start: inclusive lower bound for ``ORIGINATION_DATETIME``.
        cohort_end:   exclusive upper bound for ``ORIGINATION_DATETIME``.
        title: optional override; default uses the date range.

    Returns:
        ``plotly.graph_objects.Figure`` from
        :func:`motor_graphs.styles.stacked_bar_100pct_monthly_2x2`
        (single panel — no ``facet``).

    Example:
        >>> fig = introducer_volume_mix_monthly("2024-01-01", "2024-07-01")
    """
    start, end = validate_cohort_range(cohort_start, cohort_end)

    sql = f"""
        SELECT
          TO_CHAR(DATE_TRUNC('month', a.ORIGINATION_DATETIME), 'YYYY-MM') AS month,
          a.INTRODUCER AS introducer,
          SUM(a.FINAL_GROSS_AMOUNT) AS amount,
          COUNT(DISTINCT a.LOAN_ID) AS n
        FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR a
        WHERE a.ORIGINATION_DATETIME >= '{start}'
          AND a.ORIGINATION_DATETIME <  '{end}'
          AND COALESCE(a.FLAG_ORIGINATED_AND_NOT_CANCELLED, a.FLAG_ORIGINATED) = TRUE
        GROUP BY 1, 2
        ORDER BY 1, 2
    """

    raw = snowflake.run_query(sql)

    # Map raw introducer → 5-category taxonomy.
    raw = raw.copy()
    raw["category"] = raw["introducer"].map(_categorise_introducer)

    # Aggregate £ amount and n per (month, category).
    grouped = (
        raw.groupby(["month", "category"], as_index=False)
        .agg(amount=("amount", "sum"), n=("n", "sum"))
    )

    # Share as % of monthly total amount (0-100, not decimal — chart expects pct).
    month_totals = grouped.groupby("month")["amount"].transform("sum")
    grouped["share"] = (grouped["amount"] / month_totals.replace(0, pd.NA)) * 100.0
    grouped["share"] = grouped["share"].fillna(0.0)

    # n column for the chart is the per-month total loan count, broadcast onto every row.
    month_n = grouped.groupby("month")["n"].transform("sum")
    df = grouped.assign(n=month_n)[["month", "category", "share", "n"]]

    return styles.stacked_bar_100pct_monthly_2x2(
        df,
        month="month",
        category="category",
        share="share",
        n="n",
        title=title or f"Originated volume mix by introducer — {start} to {end}",
    )

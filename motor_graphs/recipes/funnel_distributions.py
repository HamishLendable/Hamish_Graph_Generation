"""MoTa recipes — application funnel + bureau-score distribution by grade.

Thin Snowflake-aware wrappers that build canonical SQL against
``PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR``, execute via
``motor_graphs.data.snowflake.run_query``, reshape, and call a chart style.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import plotly.graph_objects as go

from motor_graphs import styles
from motor_graphs.data.snowflake import run_query

from ._shared import ORIGINATED_FLAG_PREDICATE, simplify_risk_grade, validate_cohort_range

# Allow-list of bureau-score columns we will interpolate into SQL.
# Hard-coded to prevent f-string injection in score_distribution_by_grade.
_ALLOWED_SCORE_COLS = frozenset({"DELPHI_SCORE", "GAUGE_SCORE2"})


def funnel_app_to_originated(
    cohort_start: date | str,
    cohort_end: date | str,
    *,
    title: Optional[str] = None,
) -> go.Figure:
    """Application → quote → bureau → affordability → contract → originated funnel.

    Use this when:
        - You want a single horizontal funnel showing how many motor applications
          made it through each gate in a cohort window.
        - You want to spot where the largest drop-offs sit (e.g. bureau vs
          affordability vs contract).

    Snowflake tables used:
        - ``PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR`` (one row per application)
          Cohort filter: ``APPLICATION_CREATED_DATETIME >= start AND
          APPLICATION_CREATED_DATETIME <  end`` (half-open).

    Stages (in order, widest at top):
        1. Applications     — all rows in the cohort window
        2. Quoted           — ``FLAG_QUOTED = 1``
        3. Bureau passed    — ``FLAG_EXPERIAN_CREDIT_CHECK_PASSED = 1`` OR (Experian
           null AND ``FLAG_TRANSUNION_CREDIT_CHECK_PASSED = 1``). Captures apps
           that route via TransUnion when Experian is unavailable.
        4. Affordability    — ``FLAG_AFFORDABILITY_CHECK_PASSED_ANY_QUOTE = 1``
        5. Contract signed  — ``FLAG_LOAN_CONTRACT_ACCEPTED = 1``
        6. Originated       — ``COALESCE(FLAG_ORIGINATED_AND_NOT_CANCELLED,
           FLAG_ORIGINATED) = TRUE`` (the canonical originated predicate).

    Parameters:
        cohort_start: inclusive lower bound (date | datetime | 'YYYY-MM-DD').
        cohort_end:   exclusive upper bound (date | datetime | 'YYYY-MM-DD').
        title: optional figure title.

    Returns:
        plotly.graph_objects.Figure — a horizontal funnel via
        ``styles.funnel_horizontal``.

    Example:
        >>> from motor_graphs.recipes.funnel_distributions import funnel_app_to_originated
        >>> fig = funnel_app_to_originated("2024-01-01", "2024-02-01")
        >>> fig.show()
    """
    start, end = validate_cohort_range(cohort_start, cohort_end)

    bureau_predicate = (
        "(FLAG_EXPERIAN_CREDIT_CHECK_PASSED = 1 "
        "OR (FLAG_EXPERIAN_CREDIT_CHECK_PASSED IS NULL "
        "AND FLAG_TRANSUNION_CREDIT_CHECK_PASSED = 1))"
    )

    sql = f"""
    SELECT 'Applications' AS stage, 1 AS stage_order, COUNT(*) AS cnt
    FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR
    WHERE APPLICATION_CREATED_DATETIME >= '{start}'
      AND APPLICATION_CREATED_DATETIME <  '{end}'
    UNION ALL
    SELECT 'Quoted', 2, COUNT(*)
    FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR
    WHERE APPLICATION_CREATED_DATETIME >= '{start}'
      AND APPLICATION_CREATED_DATETIME <  '{end}'
      AND FLAG_QUOTED = 1
    UNION ALL
    SELECT 'Bureau passed', 3, COUNT(*)
    FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR
    WHERE APPLICATION_CREATED_DATETIME >= '{start}'
      AND APPLICATION_CREATED_DATETIME <  '{end}'
      AND {bureau_predicate}
    UNION ALL
    SELECT 'Affordability', 4, COUNT(*)
    FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR
    WHERE APPLICATION_CREATED_DATETIME >= '{start}'
      AND APPLICATION_CREATED_DATETIME <  '{end}'
      AND FLAG_AFFORDABILITY_CHECK_PASSED_ANY_QUOTE = 1
    UNION ALL
    SELECT 'Contract signed', 5, COUNT(*)
    FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR
    WHERE APPLICATION_CREATED_DATETIME >= '{start}'
      AND APPLICATION_CREATED_DATETIME <  '{end}'
      AND FLAG_LOAN_CONTRACT_ACCEPTED = 1
    UNION ALL
    SELECT 'Originated', 6, COUNT(*)
    FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR
    WHERE APPLICATION_CREATED_DATETIME >= '{start}'
      AND APPLICATION_CREATED_DATETIME <  '{end}'
      AND {ORIGINATED_FLAG_PREDICATE}
    ORDER BY stage_order
    """.strip()

    df = run_query(sql)
    # run_query lowercases columns; rename `cnt` -> `count` for the style.
    df = df.rename(columns={"cnt": "count"})
    df = df.sort_values("stage_order").reset_index(drop=True)

    return styles.funnel_horizontal(
        df,
        stage="stage",
        count="count",
        title=title or f"Application → originated funnel — {start} to {end}",
    )


def score_distribution_by_grade(
    cohort_start: date | str,
    cohort_end: date | str,
    *,
    score_col: str = "DELPHI_SCORE",
    nbins: int = 30,
    title: Optional[str] = None,
    normalised: bool = False,
) -> go.Figure:
    """Bureau-score distribution by simplified risk grade — for originated loans.

    Use this when:
        - You want to see how a bureau score (Delphi or Gauge) is distributed
          across risk grades for originations in a cohort window.
        - You want to verify that the grade segmentation actually separates the
          underlying score distribution.

    Snowflake tables used:
        - ``PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR``. Cohort filter on
          ``APPLICATION_CREATED_DATETIME``; originated filter via
          ``COALESCE(FLAG_ORIGINATED_AND_NOT_CANCELLED, FLAG_ORIGINATED) = TRUE``.
          Pulls one row per application with the requested score column and
          ``ORIGINATION_SIMPLIFIED_RISK_GRADE``.

    Parameters:
        cohort_start: inclusive lower bound (date | datetime | 'YYYY-MM-DD').
        cohort_end:   exclusive upper bound (date | datetime | 'YYYY-MM-DD').
        score_col:    bureau-score column to plot. Must be one of
                      ``{"DELPHI_SCORE", "GAUGE_SCORE2"}`` — the allow-list
                      prevents SQL injection via the f-string. ValueError on
                      anything else.
        nbins:        histogram bin count (default 30).
        title:        optional figure title.
        normalised:   if True, use ``histnorm='percent'`` so bars sum to 100%
                      per bin instead of raw counts.

    Returns:
        plotly.graph_objects.Figure — stacked histogram per grade via
        ``styles.histogram_by_grade``.

    Example:
        >>> from motor_graphs.recipes.funnel_distributions import (
        ...     score_distribution_by_grade,
        ... )
        >>> fig = score_distribution_by_grade(
        ...     "2024-01-01", "2024-02-01", score_col="DELPHI_SCORE",
        ... )
        >>> fig.show()
    """
    if score_col not in _ALLOWED_SCORE_COLS:
        raise ValueError(
            f"score_col must be one of {sorted(_ALLOWED_SCORE_COLS)}; got {score_col!r}"
        )
    start, end = validate_cohort_range(cohort_start, cohort_end)

    sql = f"""
    SELECT
        {score_col} AS value,
        ORIGINATION_SIMPLIFIED_RISK_GRADE AS raw_grade
    FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR
    WHERE APPLICATION_CREATED_DATETIME >= '{start}'
      AND APPLICATION_CREATED_DATETIME <  '{end}'
      AND {ORIGINATED_FLAG_PREDICATE}
      AND {score_col} IS NOT NULL
      AND ORIGINATION_SIMPLIFIED_RISK_GRADE IS NOT NULL
    """.strip()

    df = run_query(sql)
    # run_query lowercases the columns -> value, raw_grade.
    df["grade"] = df["raw_grade"].map(simplify_risk_grade)
    df = df.dropna(subset=["grade"]).copy()
    # histogram_by_grade aggregates raw observations directly — n=1 per row
    # lets it produce a per-grade total automatically via _per_category_n
    # (falling back to len(sub) when n is missing). Drop raw_grade.
    df = df[["value", "grade"]].reset_index(drop=True)
    df["n"] = 1

    return styles.histogram_by_grade(
        df,
        value="value",
        grade="grade",
        n="n",
        nbins=nbins,
        normalised=normalised,
        title=title or f"{score_col} distribution by risk grade — {start} to {end}",
        xlabel=score_col,
    )

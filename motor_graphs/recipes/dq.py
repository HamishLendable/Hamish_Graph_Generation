"""Delinquency (DQ) recipes — Snowflake-aware wrappers for MoTa DQ charts.

Each recipe:
    1. Validates the cohort date range.
    2. Builds canonical SQL against PROD.PRS_MOTOR / PROD.MRT_MOTOR / PROD.INT_MOTOR.
    3. Executes via ``motor_graphs.data.snowflake.run_query``.
    4. Reshapes the result into the tidy DataFrame expected by a chart style.
    5. Calls the chart style and returns the resulting plotly Figure.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from motor_graphs import styles
from motor_graphs.data import snowflake

from ._shared import grade_to_group, validate_cohort_range

# Hardcoded expected/benchmark rates for the four "recent book" DQ metrics.
# v0.1: keep these inline so the recipe runs without loading expectations.yaml.
EXPECTED_RATES: dict[str, float] = {
    "30+ DPD at MOB 1": 0.018,
    "30+ DPD at MOB 3": 0.035,
    "60+ DPD at MOB 6": 0.022,
    "90+ DPD at MOB 9": 0.028,
}


def dq_aging_by_grade(
    cohort_start: date | str,
    cohort_end: date | str,
    *,
    mob_max: int = 18,
    title: Optional[str] = None,
) -> go.Figure:
    """30+ DQ aging curves by cohort, faceted into 3 grade-group panels.

    Use this when:
        - You want to see how cumulative 30+@MOB delinquency ages across
          monthly cohorts that originated in the given window, segmented into
          A-B / C-E / F+ grade groups so each panel has its own y-scale.

    Snowflake tables used:
        - PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR — origination master, provides
          ORIGINATION_DATETIME (cohort source) and ORIGINATION_SIMPLIFIED_RISK_GRADE.
        - PROD.INT_MOTOR.INT__CONTRACTUAL_PAYMENTARREARS__MOTOR — per-loan per-MOB
          arrears spine, provides MONTH_INDEX (= MOB) and MONTHS_IN_ARREARS.

    Returns:
        plotly.graph_objects.Figure (via styles.cohort_lines_1x3_by_grade_group).

    Example:
        >>> from datetime import date
        >>> fig = dq_aging_by_grade(date(2024, 1, 1), date(2024, 4, 1))
    """
    start, end = validate_cohort_range(cohort_start, cohort_end)

    sql = f"""
SELECT
    TO_CHAR(DATE_TRUNC('month', a.ORIGINATION_DATETIME), 'YYYY-MM') AS cohort,
    arr.MONTH_INDEX AS mob,
    a.ORIGINATION_SIMPLIFIED_RISK_GRADE AS raw_grade,
    COUNT(DISTINCT a.LOAN_ID) AS n_at_mob,
    SUM(IFF(arr.MONTHS_IN_ARREARS >= 1, 1, 0)) AS n_dq_30
FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR a
INNER JOIN PROD.INT_MOTOR.INT__CONTRACTUAL_PAYMENTARREARS__MOTOR arr
    ON a.LOAN_ID = arr.LOAN_ID
WHERE a.APPLICATION_CREATED_DATETIME >= '{start}'
    AND a.APPLICATION_CREATED_DATETIME <  '{end}'
    AND COALESCE(a.FLAG_ORIGINATED_AND_NOT_CANCELLED, a.FLAG_ORIGINATED) = TRUE
    AND arr.MONTH_INDEX BETWEEN 0 AND {mob_max}
GROUP BY 1, 2, 3
""".strip()

    raw = snowflake.run_query(sql)

    # run_query lowercases columns — work in lowercase from here.
    if raw.empty:
        # Empty result: produce an empty 3-panel figure rather than blowing up
        # in the style on a unique() check. We still need 3 groups, so emit a
        # zero-row frame that has the expected schema.
        df = pd.DataFrame(
            {
                "cohort": pd.Series(dtype="object"),
                "mob": pd.Series(dtype="int64"),
                "grade_group": pd.Series(dtype="object"),
                "rate": pd.Series(dtype="float64"),
                "n_at_mob": pd.Series(dtype="int64"),
            }
        )
    else:
        df = raw.copy()
        df["grade_group"] = df["raw_grade"].map(grade_to_group)
        df = df.dropna(subset=["grade_group"])

        # Aggregate to (cohort, grade_group, mob) — collapsing the raw_grade dim.
        df = (
            df.groupby(["cohort", "grade_group", "mob"], as_index=False)[
                ["n_at_mob", "n_dq_30"]
            ]
            .sum()
        )
        df["rate"] = df["n_dq_30"] / df["n_at_mob"].where(df["n_at_mob"] > 0)
        df = df.dropna(subset=["rate"])

    return styles.cohort_lines_1x3_by_grade_group(
        df,
        cohort="cohort",
        mob="mob",
        grade_group="grade_group",
        y="rate",
        expected=None,
        n="n_at_mob",
        title=title or f"30+ DQ aging by grade group — {start} to {end}",
        ylabel="30+ DQ rate",
    )


def dq_2x2_recent_book(
    cohort_start: date | str,
    cohort_end: date | str,
    *,
    title: Optional[str] = None,
) -> go.Figure:
    """2x2 of 30+@1 / 30+@3 / 60+@6 / 90+@9 DQ — actual vs benchmark per metric.

    Use this when:
        - You want a quick four-metric scan of recent-book DQ for monthly
          cohorts in the window: 30+@MOB1, 30+@MOB3, 60+@MOB6, 90+@MOB9,
          with each panel comparing the actual rate to a benchmark.

    Snowflake tables used:
        - PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR — origination master, provides
          ORIGINATION_DATETIME (cohort source) and the originated filter.
        - PROD.MRT_MOTOR.MRT__DELINQUENCY_FLAGS_BY_MONTH__MOTOR — per-loan
          DQ flags (DQ_30_1, DQ_30_3, DQ_60_6, DQ_90_BY_9).

    Returns:
        plotly.graph_objects.Figure (via styles.dq_2x2_actual_vs_expected).

    Example:
        >>> from datetime import date
        >>> fig = dq_2x2_recent_book(date(2024, 1, 1), date(2024, 12, 1))
    """
    start, end = validate_cohort_range(cohort_start, cohort_end)

    sql = f"""
SELECT
    TO_CHAR(DATE_TRUNC('month', a.ORIGINATION_DATETIME), 'YYYY-MM') AS cohort,
    COUNT(DISTINCT a.LOAN_ID) AS n,
    SUM(IFF(dq.DQ_30_1    = TRUE, 1, 0)) AS n_30_1,
    SUM(IFF(dq.DQ_30_3    = TRUE, 1, 0)) AS n_30_3,
    SUM(IFF(dq.DQ_60_6    = TRUE, 1, 0)) AS n_60_6,
    SUM(IFF(dq.DQ_90_BY_9 = TRUE, 1, 0)) AS n_90_9
FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR a
INNER JOIN PROD.MRT_MOTOR.MRT__DELINQUENCY_FLAGS_BY_MONTH__MOTOR dq
    ON a.LOAN_ID = dq.LOAN_ID
WHERE a.APPLICATION_CREATED_DATETIME >= '{start}'
    AND a.APPLICATION_CREATED_DATETIME <  '{end}'
    AND COALESCE(a.FLAG_ORIGINATED_AND_NOT_CANCELLED, a.FLAG_ORIGINATED) = TRUE
GROUP BY 1
""".strip()

    raw = snowflake.run_query(sql)

    # run_query lowercases columns.
    metric_columns = {
        "30+ DPD at MOB 1": "n_30_1",
        "30+ DPD at MOB 3": "n_30_3",
        "60+ DPD at MOB 6": "n_60_6",
        "90+ DPD at MOB 9": "n_90_9",
    }

    rows: list[dict] = []
    if not raw.empty:
        wide = raw.copy()
        for metric_label, count_col in metric_columns.items():
            for _, r in wide.iterrows():
                n = int(r["n"]) if pd.notna(r["n"]) else 0
                num = int(r[count_col]) if pd.notna(r[count_col]) else 0
                rate = (num / n) if n > 0 else 0.0
                rows.append(
                    {
                        "cohort": r["cohort"],
                        "metric": metric_label,
                        "actual": rate,
                        "expected": EXPECTED_RATES[metric_label],
                        "n": n,
                    }
                )
    else:
        # No rows — still emit one synthetic zero-row per metric so the style
        # sees exactly 4 metrics (it asserts this). Use a placeholder cohort.
        for metric_label in metric_columns:
            rows.append(
                {
                    "cohort": start[:7],
                    "metric": metric_label,
                    "actual": 0.0,
                    "expected": EXPECTED_RATES[metric_label],
                    "n": 0,
                }
            )

    df = pd.DataFrame(rows)

    return styles.dq_2x2_actual_vs_expected(
        df,
        cohort="cohort",
        metric="metric",
        actual="actual",
        expected="expected",
        n="n",
        title=title or f"Recent-book DQ vs benchmark — {start} to {end}",
    )

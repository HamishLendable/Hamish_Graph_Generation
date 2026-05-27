"""Risk recipes (Batch 5h).

Thin Snowflake-aware wrappers covering two MoTa risk views:

* :func:`pd_calibration_irr` — IRR-implied 90+@9 vs realised 90+@9 calibration
  scatter (the MoTa analogue of a PD calibration plot, since
  ``PRS__APPLICATION__MOTOR`` has no ``ORIGINATION_PD`` column).
* :func:`segment_compare_dealer_vs_nondealer` — 2x2 monthly comparison of the
  dealer channel vs the rest of the book, with a mix-adjusted counterfactual
  that re-weights non-dealer per-grade performance onto the dealer grade mix.

Both recipes pull from canonical Snowflake objects (see
``docs/discovery/snowflake_conventions.md``) and reshape the result before
calling a chart style from :mod:`motor_graphs.styles`.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from motor_graphs import styles
from motor_graphs.data import snowflake

from ._shared import (
    ORIGINATED_FLAG_PREDICATE,
    grade_to_group,
    validate_cohort_range,
)

# ----------------------------------------------------------------------------- recipe 1


def pd_calibration_irr(
    cohort_start: date | str,
    cohort_end: date | str,
    *,
    mob: int = 9,
    n_buckets: int = 10,
    title: Optional[str] = None,
) -> go.Figure:
    """IRR-implied 90+@9 vs realised 90+@9 calibration scatter (decile buckets).

    Use this when:
        - You want to check whether the IRR model's ``input_90_in_9``
          expectation is calibrated against realised ``DQ_90_BY_9`` outcomes
          on originated loans.
        - You need the MoTa equivalent of a PD calibration plot — the
          application table does not expose an ``ORIGINATION_PD`` column, so
          ``input_90_in_9`` from
          ``STG__FULL_LOAN_METRICS__MOTOR_IRR`` is used as the PD substitute.

    Snowflake tables used:
        - ``PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR`` (cohort filter, originated
          predicate).
        - ``PROD.STG_MOTOR_LENDABLE.STG__FULL_LOAN_METRICS__MOTOR_IRR`` (joined
          on ``loan_id`` + ``mob`` to pick up ``input_90_in_9``).
        - ``PROD.MRT_MOTOR.MRT__DELINQUENCY_FLAGS_BY_MONTH__MOTOR`` (joined on
          ``LOAN_ID`` to pick up ``DQ_90_BY_9``).

    Parameters:
        cohort_start: inclusive lower bound for ``APPLICATION_CREATED_DATETIME``.
        cohort_end:   exclusive upper bound for ``APPLICATION_CREATED_DATETIME``.
        mob: month-on-book to align the IRR row on (default 9 to match
            ``input_90_in_9``).
        n_buckets: number of equal-population buckets along the expected axis
            (default 10 — deciles).
        title: optional override; default uses the date range.

    Returns:
        ``plotly.graph_objects.Figure`` from
        :func:`motor_graphs.styles.scatter_calibration`. One marker per bucket,
        bubble area proportional to bucket size, with a y=x diagonal so under-
        or over-calibration is immediately visible.

    Example:
        >>> fig = pd_calibration_irr("2023-01-01", "2024-01-01")
        >>> fig = pd_calibration_irr("2023-01-01", "2024-01-01", n_buckets=20)
    """
    start, end = validate_cohort_range(cohort_start, cohort_end)

    sql = f"""
        WITH joined AS (
          SELECT
            a.LOAN_ID,
            i.input_90_in_9 AS expected,
            IFF(dq.DQ_90_BY_9 = 1, 1, 0) AS actual
          FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR a
          INNER JOIN PROD.STG_MOTOR_LENDABLE.STG__FULL_LOAN_METRICS__MOTOR_IRR i
            ON a.LOAN_ID = i.loan_id AND i.mob = {mob}
          INNER JOIN PROD.MRT_MOTOR.MRT__DELINQUENCY_FLAGS_BY_MONTH__MOTOR dq
            ON a.LOAN_ID = dq.LOAN_ID
          WHERE a.APPLICATION_CREATED_DATETIME >= '{start}'
            AND a.APPLICATION_CREATED_DATETIME <  '{end}'
            AND {ORIGINATED_FLAG_PREDICATE}
            AND i.input_90_in_9 IS NOT NULL
            AND dq.DQ_90_BY_9 IS NOT NULL
        ),
        bucketed AS (
          SELECT *, NTILE({n_buckets}) OVER (ORDER BY expected) AS bucket
          FROM joined
        )
        SELECT
          bucket,
          AVG(expected) AS expected_pd,
          AVG(actual)   AS actual_default,
          COUNT(*)      AS n
        FROM bucketed
        GROUP BY bucket
        ORDER BY bucket
    """

    df = snowflake.run_query(sql)

    # Snowflake returns lowercase columns; render bucket as "B1", "B2", ...
    df = df.copy()
    df["bucket"] = df["bucket"].apply(lambda b: f"B{int(b)}")

    return styles.scatter_calibration(
        df,
        expected_pd="expected_pd",
        actual_default="actual_default",
        n="n",
        label="bucket",
        title=title or f"IRR 90+@9 calibration — {start} to {end}",
        xlabel="IRR-implied 90+@9 (input_90_in_9)",
        ylabel="Realised 90+@9",
    )


# ----------------------------------------------------------------------------- recipe 2


# Dealer ``loanproduct_id`` whitelist — see
# ``docs/discovery/snowflake_conventions.md`` (Sample query A).
_DEALER_LOANPRODUCT_IDS = (14, 25, 54, 73, 125, 199, 277)


def _good_share_from_groups(grade_groups: pd.Series, n_loans: pd.Series) -> float:
    """Compute the n-weighted share of "good" (A-B / C-E) grades.

    F+ counts as risky, anything mapping to ``None`` is excluded from the
    denominator so unknown grades don't artificially deflate either share.
    """
    mask_known = grade_groups.isin(["A-B", "C-E", "F+"])
    if not mask_known.any():
        return 0.0
    n = n_loans[mask_known].astype(float)
    g = grade_groups[mask_known].isin(["A-B", "C-E"]).astype(float)
    total = float(n.sum())
    if total <= 0:
        return 0.0
    return float((g * n).sum() / total)


def segment_compare_dealer_vs_nondealer(
    cohort_start: date | str,
    cohort_end: date | str,
    *,
    dq_col: str = "DQ_90_BY_9",
    title: Optional[str] = None,
) -> go.Figure:
    """2x2 monthly compare of dealer vs non-dealer DQ, with a mix-adjusted gap.

    Use this when:
        - You want to understand how dealer-channel originations compare to
          non-dealer on a given DQ flag (default ``DQ_90_BY_9``) over time.
        - You also want to separate "underlying performance" from "grade-mix"
          drivers of the gap.

    Snowflake tables used:
        - ``PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR`` (cohort filter + grade).
        - ``RAW_PRODUCTION.MOTOR_UK_LENDABLE.hirepurchaseloan`` (for
          ``loanproduct_id``, used to derive ``IS_DEALER`` via the canonical
          loan-product whitelist ``{14, 25, 54, 73, 125, 199, 277}``).
        - ``PROD.MRT_MOTOR.MRT__DELINQUENCY_FLAGS_BY_MONTH__MOTOR`` (DQ flag).

    Mix-adjusted calculation (counterfactual direction):
        For each month, per grade group ``g`` in {A-B, C-E, F+}, compute the
        non-dealer per-group DQ rate ``r_nondealer(g, month)`` (loans-weighted
        within the group/month) and the dealer mix share
        ``w_dealer(g, month) = n_dealer(g, month) / n_dealer(month)``.

        ``b_adj`` (column name preserved for compatibility with
        :func:`segment_compare_2x2_with_gap`) is then:

            b_adj(month) = sum_g w_dealer(g, month) * r_nondealer(g, month)

        Read it as: "What would the non-dealer rate look like if the
        non-dealer book had been originated with the dealer's grade mix?"

        Interpretation:
            * ``a - b``     — total raw gap.
            * ``a - b_adj`` — gap that remains AFTER controlling for grade
              mix; this is the "underlying performance" gap.
            * ``b_adj - b`` — the slice of the raw gap that comes purely
              from dealer's mix being skewed vs non-dealer's mix; this is
              the "mix" component.

        Months where the dealer book has no presence in a grade group, or
        where the non-dealer book has no presence in a grade group that the
        dealer book uses, fall back to the overall non-dealer rate for that
        month so the counterfactual stays defined.

    Parameters:
        cohort_start: inclusive lower bound for ``APPLICATION_CREATED_DATETIME``.
        cohort_end:   exclusive upper bound for ``APPLICATION_CREATED_DATETIME``.
        dq_col: DQ flag column on
            ``MRT__DELINQUENCY_FLAGS_BY_MONTH__MOTOR`` (default ``DQ_90_BY_9``;
            also valid: ``DQ_30_1``, ``DQ_30_3``, ``DQ_60_6``).
        title: optional override; default uses the DQ column and date range.

    Returns:
        ``plotly.graph_objects.Figure`` from
        :func:`motor_graphs.styles.segment_compare_2x2_with_gap`.

    Example:
        >>> fig = segment_compare_dealer_vs_nondealer("2023-01-01", "2024-01-01")
        >>> fig = segment_compare_dealer_vs_nondealer(
        ...     "2023-01-01", "2024-01-01", dq_col="DQ_60_6"
        ... )
    """
    start, end = validate_cohort_range(cohort_start, cohort_end)

    sql = f"""
        SELECT
          TO_CHAR(DATE_TRUNC('month', a.ORIGINATION_DATETIME), 'YYYY-MM') AS month,
          IFF(l.loanproduct_id IN {_DEALER_LOANPRODUCT_IDS}, 1, 0) AS is_dealer,
          a.ORIGINATION_SIMPLIFIED_RISK_GRADE AS raw_grade,
          COUNT(*) AS n_loans,
          SUM(IFF(dq.{dq_col} = 1, 1, 0)) AS n_dq
        FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR a
        LEFT JOIN RAW_PRODUCTION.MOTOR_UK_LENDABLE.hirepurchaseloan l
          ON a.LOAN_ID = l.id
        LEFT JOIN PROD.MRT_MOTOR.MRT__DELINQUENCY_FLAGS_BY_MONTH__MOTOR dq
          ON a.LOAN_ID = dq.LOAN_ID
        WHERE a.APPLICATION_CREATED_DATETIME >= '{start}'
          AND a.APPLICATION_CREATED_DATETIME <  '{end}'
          AND {ORIGINATED_FLAG_PREDICATE}
          AND a.ORIGINATION_SIMPLIFIED_RISK_GRADE IS NOT NULL
        GROUP BY 1, 2, 3
    """

    raw = snowflake.run_query(sql)

    if raw.empty:
        raise ValueError(
            "No rows returned for the dealer-vs-nondealer cohort. "
            f"Check the cohort range {start} → {end} and dq_col={dq_col}."
        )

    raw = raw.copy()
    raw["is_dealer"] = raw["is_dealer"].astype(int)
    raw["n_loans"] = raw["n_loans"].astype(float)
    raw["n_dq"] = raw["n_dq"].astype(float)
    raw["grade_group"] = raw["raw_grade"].apply(grade_to_group)
    # Drop rows where the grade could not be mapped — they would have no
    # well-defined mix bucket.
    raw = raw[raw["grade_group"].notna()].reset_index(drop=True)

    # ---- per (month, is_dealer) overall figures ----------------------------
    overall = (
        raw.groupby(["month", "is_dealer"], as_index=False)
        .agg(n_loans=("n_loans", "sum"), n_dq=("n_dq", "sum"))
    )
    overall["rate"] = overall["n_dq"] / overall["n_loans"].replace(0, pd.NA)

    # ---- per (month, is_dealer, grade_group) rates / mix ------------------
    per_group = (
        raw.groupby(["month", "is_dealer", "grade_group"], as_index=False)
        .agg(n_loans=("n_loans", "sum"), n_dq=("n_dq", "sum"))
    )
    per_group["rate"] = per_group["n_dq"] / per_group["n_loans"].replace(0, pd.NA)

    months = sorted(raw["month"].unique())
    records: list[dict] = []

    for month in months:
        d_overall = overall[
            (overall["month"] == month) & (overall["is_dealer"] == 1)
        ]
        nd_overall = overall[
            (overall["month"] == month) & (overall["is_dealer"] == 0)
        ]
        if d_overall.empty or nd_overall.empty:
            # Skip months where either segment is missing — gap is undefined.
            continue

        a_rate = float(d_overall["rate"].iloc[0])
        b_rate = float(nd_overall["rate"].iloc[0])
        n_dealer = float(d_overall["n_loans"].iloc[0])
        n_nondealer = float(nd_overall["n_loans"].iloc[0])

        # --- mix-adjusted ("non-dealer at dealer mix") ---------------------
        d_grp = per_group[(per_group["month"] == month) & (per_group["is_dealer"] == 1)]
        nd_grp = per_group[(per_group["month"] == month) & (per_group["is_dealer"] == 0)]

        dealer_grp_n = dict(zip(d_grp["grade_group"], d_grp["n_loans"].astype(float), strict=False))
        nondealer_grp_rate = dict(
            zip(nd_grp["grade_group"], nd_grp["rate"].astype(float), strict=False)
        )
        dealer_grp_total = float(sum(dealer_grp_n.values()))

        if dealer_grp_total <= 0:
            b_adj = b_rate
        else:
            acc = 0.0
            w_used = 0.0
            for g, n_g in dealer_grp_n.items():
                w = n_g / dealer_grp_total
                if g in nondealer_grp_rate and pd.notna(nondealer_grp_rate[g]):
                    acc += w * float(nondealer_grp_rate[g])
                    w_used += w
            # If we couldn't cover the full dealer mix from non-dealer per-group
            # rates (e.g. non-dealer book is empty in some grade groups the
            # dealer book uses), fall back to the overall non-dealer rate for
            # the missing slice.
            if w_used <= 0:
                b_adj = b_rate
            elif w_used < 1.0:
                acc += (1.0 - w_used) * b_rate
                b_adj = acc
            else:
                b_adj = acc

        # --- "good" share per segment (used by the grade-mix stacked bars) -
        a_good_share = _good_share_from_groups(
            d_grp["grade_group"], d_grp["n_loans"]
        )
        b_good_share = _good_share_from_groups(
            nd_grp["grade_group"], nd_grp["n_loans"]
        )

        records.append(
            {
                "month": month,
                "a": a_rate,
                "b": b_rate,
                "b_adj": float(b_adj),
                "gap": (a_rate - b_rate) * 100.0,  # pp, matches chart style.
                "a_good_share": a_good_share,
                "b_good_share": b_good_share,
                "n": int(n_dealer + n_nondealer),
            }
        )

    df = pd.DataFrame.from_records(records)

    return styles.segment_compare_2x2_with_gap(
        df,
        a_col="a",
        b_col="b",
        adjusted_col="b_adj",
        gap_col="gap",
        a_good_share_col="a_good_share",
        b_good_share_col="b_good_share",
        n="n",
        a_label="Dealer",
        b_label="Non-dealer",
        adjusted_label="Non-dealer at dealer mix",
        title=title or f"Dealer vs non-dealer — {dq_col} — {start} to {end}",
    )

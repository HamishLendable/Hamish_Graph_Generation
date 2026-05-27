"""Backtest the candidate 'new strategy' reject rule on real PROD data.

The rule rejects an applicant if ANY of:
    rev2plus      — any Revolving-17 tradeline with worst_pay_l1m in [2,6]
    ins1plus      — any Instalment-39 tradeline with worst_pay_l1m in [1,6]
    oth2plus      — any Other-55 tradeline   with worst_pay_l1m in [2,6]
    newdef > 1    — more than one tradeline with months_since_default <= 12
                    (all_131 universe)

Produces three diagnostic charts in ``out/rejection_rule_analysis/``:

    01_rejection_signal_breakdown    — applicants per signal (rev / ins / oth / newdef / multiple)
    02_dq_by_grade_rejected_vs_kept  — 90+@9 rate by grade for rule-rejected vs kept
    03_segment_compare_rejected      — 2×2 rate + grade-mix + mix-adjusted gap

Cohort: applications between 24 and 9 months ago (mature enough for 90@9).
Sample: deterministic 100k via HASH(LOANAPPLICATION_ID, 42), restricted to
applicants we have both TU and Experian files for, then narrowed to those
that were originated and have a known origination_simplified_risk_grade.

Run::

    poetry run python scripts/rejection_rule_analysis.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import pandas as pd  # noqa: E402

import motor_graphs  # noqa: E402
from motor_graphs import styles  # noqa: E402
from motor_graphs.data import snowflake  # noqa: E402
from motor_graphs.recipes._shared import grade_to_group, simplify_risk_grade  # noqa: E402

OUT = Path(__file__).parent.parent / "out" / "rejection_rule_analysis"

# ---- The user's SQL with: two typos fixed (truncated table name + missing
# alias), cohort window widened to 24→9 months so 90+@9 is mature, and an
# `app_outcomes` CTE joined to PRS_MOTOR + MRT__DELINQUENCY_FLAGS appended.
SQL = """
WITH
sample_pool AS (
    SELECT m.LOANAPPLICATION_ID, m.CREATED_AT
    FROM PROD.INT_MOTOR.INT__MATRIX_RESULTS__MOTOR m
    INNER JOIN PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR app
        ON m.LOANAPPLICATION_ID = app.APPLICATION_ID
    WHERE m.RANK_NUM_DESC = 1
      AND m.CREATED_AT >= DATEADD('month', -24, CURRENT_DATE())
      AND m.CREATED_AT <  DATEADD('month',  -9, CURRENT_DATE())
      AND m.MATRIX_NAME IN ('transunion credit', 'experian credit')
      AND app.EXPERIAN_FILE_ID IS NOT NULL
      AND app.TU_CREDIT_FILE_ID IS NOT NULL
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY m.LOANAPPLICATION_ID
        ORDER BY m.CREATED_AT DESC
    ) = 1
),
sampled_apps AS (
    SELECT LOANAPPLICATION_ID, CREATED_AT
    FROM sample_pool
    ORDER BY HASH(LOANAPPLICATION_ID, 42)
    LIMIT 100000
),
sampled_apps_tu_files AS (
    SELECT
        sa.LOANAPPLICATION_ID,
        sa.CREATED_AT,
        tca.TU_CREDIT_FILE_ID
    FROM sampled_apps sa
    INNER JOIN PROD.INT_MOTOR.INT__TRANSUNION_CREDIT_REPORT_APPLICATION__MOTOR tca
        ON tca.LOANAPPLICATION_ID = sa.LOANAPPLICATION_ID
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY sa.LOANAPPLICATION_ID
        ORDER BY tca.APPLICATION_SYNCED_AT DESC
    ) = 1
),
history_with_pay_num AS (
    SELECT
        h.ID,
        h.TRADELINE_ID,
        h.HISTORY_MONTH,
        h.PAY,
        CASE
            WHEN h.PAY IN ('0','1','2','3','4','5','6') THEN TO_NUMBER(h.PAY)
            WHEN h.PAY = 'D' THEN 7
            ELSE NULL
        END AS pay_num
    FROM PROD.INT_MOTOR.INT__TRANSUNION_TRADELINE_HISTORY__MOTOR h
    INNER JOIN sampled_apps_tu_files af
        ON h.ID = af.TU_CREDIT_FILE_ID
),
tradeline_panel AS (
    SELECT
        af.LOANAPPLICATION_ID,
        t.TRADELINE_ID,
        t.ACCTYPECODE,
        t.SEARCHDATE,
        MAX(CASE
            WHEN h.HISTORY_MONTH >= TO_CHAR(DATEADD('month', -1, t.SEARCHDATE), 'YYYY-MM')
            THEN h.pay_num
        END) AS worst_pay_l1m,
        DATEDIFF(
            'month',
            TO_DATE(MIN(CASE WHEN h.PAY = 'D' THEN h.HISTORY_MONTH END) || '-01', 'YYYY-MM-DD'),
            t.SEARCHDATE
        ) AS months_since_default
    FROM PROD.INT_MOTOR.INT__TRANSUNION_TRADELINES_PARSED__MOTOR t
    INNER JOIN sampled_apps_tu_files af
        ON t.ID = af.TU_CREDIT_FILE_ID
    LEFT JOIN history_with_pay_num h
        ON h.ID = af.TU_CREDIT_FILE_ID
       AND h.TRADELINE_ID = t.TRADELINE_ID
    WHERE t.JOINT = 0
      AND t.ADDRESSCURRENT = 1
    GROUP BY af.LOANAPPLICATION_ID, t.TRADELINE_ID, t.ACCTYPECODE, t.SEARCHDATE
),
applicant_signals AS (
    SELECT
        p.LOANAPPLICATION_ID,
        MAX(CASE
            WHEN p.ACCTYPECODE IN (
                'BD','BK','CA','CC','CH','CO','CZ','FC','IC','MC',
                'OA','OD','RC','RS','ST','SX','ZC'
            ) AND p.worst_pay_l1m BETWEEN 2 AND 6
            THEN 1 ELSE 0
        END) AS rev2plus,
        MAX(CASE
            WHEN p.ACCTYPECODE IN (
                'AD','AF','BA','BH','BL','BN','BR','CP','CS','CX',
                'CY','DA','DH','DP','ED','EL','FD','FL','FS','HC',
                'HP','IL','LN','LP','LS','ML','OL','PL','RG','SB',
                'SC','SE','SL','SO','TL','UL','WI','ZH','ZL'
            ) AND p.worst_pay_l1m BETWEEN 1 AND 6
            THEN 1 ELSE 0
        END) AS ins1plus,
        MAX(CASE
            WHEN p.ACCTYPECODE IN (
                'AM','AU','BC','BI','BO','BU','BX','CB','CI','CR',
                'CT','DC','DU','EC','EE','EW','FT','GE','GI','HA',
                'HD','HI','HS','HX','IN','IS','LR','LT','MA','MI',
                'MO','MP','MU','OI','OR','PI','PP','PR','PT','QA',
                'QE','QG','QT','QU','QW','RT','SA','SI','SS','TM',
                'TR','TV','UE','UT','VS'
            ) AND p.worst_pay_l1m BETWEEN 2 AND 6
            THEN 1 ELSE 0
        END) AS oth2plus,
        SUM(CASE WHEN p.months_since_default <= 12 THEN 1 ELSE 0 END) AS newdef_all_131
    FROM tradeline_panel p
    GROUP BY p.LOANAPPLICATION_ID
),
app_outcomes AS (
    SELECT
        sa.LOANAPPLICATION_ID,
        sa.CREATED_AT,
        TO_CHAR(DATE_TRUNC('month', sa.CREATED_AT), 'YYYY-MM') AS cohort_month,
        COALESCE(s.rev2plus, 0)        AS rev2plus,
        COALESCE(s.ins1plus, 0)        AS ins1plus,
        COALESCE(s.oth2plus, 0)        AS oth2plus,
        COALESCE(s.newdef_all_131, 0)  AS newdef_all_131,
        CASE WHEN COALESCE(s.rev2plus, 0) = 1
                  OR COALESCE(s.ins1plus, 0) = 1
                  OR COALESCE(s.oth2plus, 0) = 1
                  OR COALESCE(s.newdef_all_131, 0) > 1
             THEN 1 ELSE 0 END AS rejected,
        app.ORIGINATION_SIMPLIFIED_RISK_GRADE AS raw_grade,
        COALESCE(app.FLAG_ORIGINATED_AND_NOT_CANCELLED, app.FLAG_ORIGINATED) AS originated,
        dq.DQ_30_1, dq.DQ_30_3, dq.DQ_60_6, dq.DQ_90_BY_9
    FROM sampled_apps sa
    LEFT JOIN applicant_signals s
        ON sa.LOANAPPLICATION_ID = s.LOANAPPLICATION_ID
    LEFT JOIN PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR app
        ON sa.LOANAPPLICATION_ID = app.APPLICATION_ID
    LEFT JOIN PROD.MRT_MOTOR.MRT__DELINQUENCY_FLAGS_BY_MONTH__MOTOR dq
        ON app.LOAN_ID = dq.LOAN_ID
)
SELECT *
FROM app_outcomes
WHERE originated = TRUE
  AND raw_grade IS NOT NULL
"""


def _signal_breakdown(rejected: pd.DataFrame) -> pd.DataFrame:
    """Decompose the rejected population by which signal(s) fired."""
    rev = rejected["rev2plus"] == 1
    ins = rejected["ins1plus"] == 1
    oth = rejected["oth2plus"] == 1
    nd = rejected["newdef_all_131"] > 1

    n_signals = rev.astype(int) + ins.astype(int) + oth.astype(int) + nd.astype(int)
    rows = [
        {"category": "Rev2+ only", "value": int((rev & ~ins & ~oth & ~nd).sum())},
        {"category": "Ins1+ only", "value": int((ins & ~rev & ~oth & ~nd).sum())},
        {"category": "Oth2+ only", "value": int((oth & ~rev & ~ins & ~nd).sum())},
        {"category": "NewDef>1 only", "value": int((nd & ~rev & ~ins & ~oth).sum())},
        {"category": "Multiple signals", "value": int((n_signals >= 2).sum())},
    ]
    df = pd.DataFrame(rows)
    df["n"] = df["value"]
    return df


def _dq_by_grade(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate 90+@9 rate by (grade, rejected)."""
    df = df.copy()
    df["dq90_9"] = df["dq_90_by_9"].fillna(0).astype(int)
    agg = (
        df.groupby(["grade", "rejected"])
        .agg(n=("dq90_9", "size"), rate=("dq90_9", "mean"))
        .reset_index()
    )
    agg["series"] = agg["rejected"].map({0: "Kept (no rule)", 1: "Rule-rejected"})
    return agg[["grade", "series", "rate", "n"]].copy()


def _segment_compare_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Per-month aggregates for the segment_compare_2x2_with_gap style."""
    df = df.copy()
    df["dq90_9"] = df["dq_90_by_9"].fillna(0).astype(int)
    df["grade_group"] = df["grade"].map(grade_to_group)
    df = df.dropna(subset=["grade_group"])
    df["is_ae"] = df["grade_group"].isin({"A-B", "C-E"}).astype(int)

    rows = []
    for month, gdf in df.groupby("cohort_month"):
        rej = gdf[gdf["rejected"] == 1]
        kep = gdf[gdf["rejected"] == 0]
        if len(rej) < 5 or len(kep) < 5:
            continue
        a = float(rej["dq90_9"].mean())
        b = float(kep["dq90_9"].mean())

        # Counterfactual: "kept rates re-weighted onto rejected's grade mix"
        kep_rates_by_g = kep.groupby("grade_group")["dq90_9"].mean()
        rej_weights_by_g = rej.groupby("grade_group").size() / len(rej)
        b_adj = float(
            sum(
                rej_weights_by_g.get(g, 0.0) * kep_rates_by_g.get(g, b)
                for g in rej_weights_by_g.index
            )
        )
        rows.append(
            {
                "month": month,
                "a": a,
                "b": b,
                "b_adj": b_adj,
                "gap": (a - b) * 100,
                "a_good_share": float(rej["is_ae"].mean()),
                "b_good_share": float(kep["is_ae"].mean()),
                "n": int(len(gdf)),
            }
        )
    return pd.DataFrame(rows).sort_values("month")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("Rejection-rule backtest — running on live Snowflake")
    print("=" * 60)
    print("\n[1/4] Running signal panel + DQ join...", flush=True)
    df = snowflake.run_query(SQL)
    print(f"      {len(df):,} originated loans with known grade + DQ outcomes")

    # Map raw grade → simplified letter; drop unknowns.
    df["grade"] = df["raw_grade"].map(simplify_risk_grade)
    df = df.dropna(subset=["grade"]).reset_index(drop=True)
    n_total = len(df)
    n_rejected = int((df["rejected"] == 1).sum())
    print(f"      {n_rejected:,} rule-rejected ({n_rejected / n_total:.1%} of originated)")

    print("\n[2/4] Rendering signal breakdown (bar_horizontal_top_n)...", flush=True)
    rej = df[df["rejected"] == 1]
    fig1 = styles.bar_horizontal_top_n(
        _signal_breakdown(rej),
        category="category",
        value="value",
        n="n",
        top_n=10,
        value_fmt=",.0f",
        title=(
            f"Which signal fires for each rejected applicant? "
            f"(n={n_rejected:,} of {n_total:,} originated)"
        ),
        xlabel="Applicants",
    )
    motor_graphs.save_figure(fig1, OUT / "01_rejection_signal_breakdown")
    print(f"      ✓ {OUT / '01_rejection_signal_breakdown.png'}")

    print(
        "\n[3/4] Rendering 90+@9 DQ by grade, rejected vs kept "
        "(grouped_bars_by_grade_two_series)...",
        flush=True,
    )
    fig2 = styles.grouped_bars_by_grade_two_series(
        _dq_by_grade(df),
        title="90+@9 DQ rate by grade — rule-rejected vs kept",
        ylabel="90+@9 DQ rate",
        series_order=["Kept (no rule)", "Rule-rejected"],
    )
    motor_graphs.save_figure(fig2, OUT / "02_dq_by_grade_rejected_vs_kept")
    print(f"      ✓ {OUT / '02_dq_by_grade_rejected_vs_kept.png'}")

    print(
        "\n[4/4] Rendering 2×2 segment compare with grade-mix decomposition "
        "(segment_compare_2x2_with_gap)...",
        flush=True,
    )
    monthly = _segment_compare_monthly(df)
    if monthly.empty:
        print("      WARN: not enough monthly data to render segment compare.")
    else:
        fig3 = styles.segment_compare_2x2_with_gap(
            monthly,
            a_label="Rule-rejected",
            b_label="Kept (no rule)",
            adjusted_label="Kept at rejected's grade mix",
            good_band_label="A-E",
            risky_band_label="F+",
            title="Rule-rejected vs kept — 90+@9 rate, grade mix, mix-adjusted gap",
        )
        motor_graphs.save_figure(fig3, OUT / "03_segment_compare_rejected")
        print(f"      ✓ {OUT / '03_segment_compare_rejected.png'}")

    print(f"\nAll outputs in: {OUT}/")
    print("Open the .html files for interactive hover; .png for the static gallery.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

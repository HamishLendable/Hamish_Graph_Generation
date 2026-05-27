"""Regenerate every baseline PNG in tests/baselines/ from the fixture CSVs.

Run::

    poetry run python scripts/refresh_baselines.py

When style code or palette changes intentionally, re-run this and review the
PNG diffs via git before committing.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import motor_graphs
from motor_graphs import styles

REPO = Path(__file__).parent.parent
FIXTURES = REPO / "tests" / "fixtures"
BASELINES = REPO / "tests" / "baselines"

REGISTRY = [
    # (baseline filename, fixture CSV filename, style function, call kwargs)
    (
        "dq_2x2_actual_vs_expected",
        "dq_2x2.csv",
        styles.dq_2x2_actual_vs_expected,
        dict(title="DQ actual vs expected — synthetic"),
    ),
    (
        "cohort_lines_vs_mob",
        "cohort_lines.csv",
        styles.cohort_lines_vs_mob,
        dict(title="Cumulative VT by cohort — synthetic", ylabel="VT rate"),
    ),
    (
        "grouped_bars_by_grade_two_series",
        "grouped_bars_by_grade.csv",
        styles.grouped_bars_by_grade_two_series,
        dict(title="90+@9 DQ by grade — BEV vs ROB", ylabel="90+@9 DQ rate"),
    ),
    (
        "stacked_bar_100pct_monthly_2x2",
        "stacked_100pct.csv",
        styles.stacked_bar_100pct_monthly_2x2,
        dict(title="Originated volume mix by introducer — synthetic"),
    ),
    (
        "heatmap_swap",
        "swap_matrix.csv",
        styles.heatmap_swap,
        dict(title="Swap matrix — synthetic"),
    ),
    (
        "scatter_calibration",
        "calibration_scatter.csv",
        styles.scatter_calibration,
        dict(title="PD calibration: expected vs actual — synthetic"),
    ),
    # --- 5b styles ---
    (
        "dq_2x2_with_n_annotated",
        "dq_2x2_with_n_annotated.csv",
        styles.dq_2x2_with_n_annotated,
        dict(title="DQ 2×2 with EV-style sample-size fade"),
    ),
    (
        "regression_validation_1x3",
        "regression_validation_1x3.csv",
        styles.regression_validation_1x3,
        dict(title="Regression validation: actual vs predicted (1×3)"),
    ),
    (
        "cohort_lines_1x3_by_grade_group",
        "cohort_lines_1x3_by_grade_group.csv",
        styles.cohort_lines_1x3_by_grade_group,
        dict(title="Cohort lines by grade group", ylabel="Rate"),
    ),
    (
        "cohort_lines_1x3_paired_expected",
        "cohort_lines_1x3_paired_expected.csv",
        styles.cohort_lines_1x3_paired_expected,
        dict(title="Cohort lines paired with per-cohort expected", ylabel="Rate"),
    ),
    (
        "roll_rate_dual_axis_lines",
        "roll_rate_dual_axis_lines.csv",
        styles.roll_rate_dual_axis_lines,
        dict(
            title="Roll rate analysis (dual-axis)",
            small_axis_cols=("early_roll",),
            large_axis_cols=("mid_roll", "late_roll", "late_roll_improved"),
            dashed_cols=("late_roll_improved",),
        ),
    ),
    (
        "lines_1x2_funnel_by_introducer",
        "lines_1x2_funnel_by_introducer.csv",
        styles.lines_1x2_funnel_by_introducer,
        dict(title="Funnel: quote rate & quote-to-sale by introducer"),
    ),
    (
        "lines_with_overall_highlight",
        "lines_with_overall_highlight.csv",
        styles.lines_with_overall_highlight,
        dict(title="Rate by segment with Overall overlay"),
    ),
    (
        "segment_compare_2x2_with_gap",
        "segment_compare_2x2_with_gap.csv",
        styles.segment_compare_2x2_with_gap,
        dict(
            title="BEV vs Rest of book — rate, mix, gap",
            a_label="BEV",
            b_label="Rest of book",
            adjusted_label="ROB at BEV mix",
        ),
    ),
    (
        "lines_funnel_by_introducer_1x1",
        "lines_funnel_by_introducer_1x1.csv",
        styles.lines_funnel_by_introducer_1x1,
        dict(title="EV-style funnel rate by introducer"),
    ),
    (
        "line_with_ci_band",
        "line_with_ci_band.csv",
        styles.line_with_ci_band,
        dict(title="Rate with 90% confidence band"),
    ),
    (
        "stacked_bar_volume_2x2_with_rate_line",
        "stacked_bar_volume_2x2_with_rate_line.csv",
        styles.stacked_bar_volume_2x2_with_rate_line,
        dict(title="Volume mix by introducer + book-level rates"),
    ),
    (
        "bar_horizontal_top_n",
        "bar_horizontal_top_n.csv",
        styles.bar_horizontal_top_n,
        dict(title="Top-N volume league table"),
    ),
    (
        "bar_plus_line_share_top_n",
        "bar_plus_line_share_top_n.csv",
        styles.bar_plus_line_share_top_n,
        dict(title="£ share vs count share — top-N introducers"),
    ),
    (
        "waterfall_components_by_grade",
        "waterfall_components_by_grade.csv",
        styles.waterfall_components_by_grade,
        dict(title="Cashflow components by grade group"),
    ),
    (
        "violin_grouped",
        "violin_grouped.csv",
        styles.violin_grouped,
        dict(title="LTV distribution by risk grade", ylabel="LTV"),
    ),
    (
        "box_quantile",
        "box_quantile.csv",
        styles.box_quantile,
        dict(title="APR distribution by introducer channel", ylabel="APR"),
    ),
    (
        "histogram_by_grade",
        "histogram_by_grade.csv",
        styles.histogram_by_grade,
        dict(title="Score distribution by risk grade"),
    ),
    (
        "cohort_grid_grade_x_period",
        "cohort_grid_grade_x_period.csv",
        styles.cohort_grid_grade_x_period,
        dict(title="Cohort grid: actual vs model by grade × period"),
    ),
    (
        "funnel_horizontal",
        "funnel_horizontal.csv",
        styles.funnel_horizontal,
        dict(title="Application → quote → originated funnel"),
    ),
]


def main() -> None:
    BASELINES.mkdir(parents=True, exist_ok=True)
    print(f"Rendering baselines to {BASELINES}/")
    for name, fixture, fn, kwargs in REGISTRY:
        path = FIXTURES / fixture
        if not path.exists():
            raise FileNotFoundError(
                f"Missing fixture {path}. Run `poetry run python tests/fixtures/_regen.py` first."
            )
        df = pd.read_csv(path)
        fig = fn(df, **kwargs)
        motor_graphs.save_figure(fig, BASELINES / name)
        print(f"  ✓ {name}")
    print("Done.")


if __name__ == "__main__":
    main()

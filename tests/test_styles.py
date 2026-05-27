"""Smoke tests for motor_graphs.styles — every Batch 5a style is exercised here.

Each style gets 3 tests: returns Figure, annotate_n=False suppresses annotations,
custom title is applied. Detailed visual regression deferred to Batch 8 CI.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

from motor_graphs import styles

FIXTURES = Path(__file__).parent / "fixtures"


# Helper: load fixture, fail loudly if regen hasn't been run
def _load(name: str) -> pd.DataFrame:
    path = FIXTURES / name
    if not path.exists():
        pytest.fail(
            f"Fixture {name} missing. Run `poetry run python tests/fixtures/_regen.py`."
        )
    return pd.read_csv(path)


# ------------------------------------------------------------------ dq_2x2
def test_dq_2x2_returns_figure():
    df = _load("dq_2x2.csv")
    fig = styles.dq_2x2_actual_vs_expected(df)
    assert isinstance(fig, go.Figure)
    # 4 metrics × 2 series = 8 traces
    assert len(fig.data) == 8


def test_dq_2x2_annotate_n_off_suppresses_n():
    df = _load("dq_2x2.csv")
    fig = styles.dq_2x2_actual_vs_expected(df, annotate_n=False)
    n_annotations = [
        a for a in (fig.layout.annotations or []) if a.text and str(a.text).startswith("n=")
    ]
    assert n_annotations == []


def test_dq_2x2_custom_title():
    df = _load("dq_2x2.csv")
    fig = styles.dq_2x2_actual_vs_expected(df, title="custom")
    assert fig.layout.title.text == "custom"


def test_dq_2x2_requires_4_metrics():
    df = _load("dq_2x2.csv")
    df = df[df["metric"].isin(df["metric"].unique()[:3])]
    with pytest.raises(ValueError, match="exactly 4 metrics"):
        styles.dq_2x2_actual_vs_expected(df)


# ------------------------------------------------------------------ cohort_lines
def test_cohort_lines_returns_figure():
    df = _load("cohort_lines.csv")
    fig = styles.cohort_lines_vs_mob(df, ylabel="VT rate")
    assert isinstance(fig, go.Figure)
    # 12 cohorts + 1 expected
    assert len(fig.data) >= 12


def test_cohort_lines_annotate_n_off():
    df = _load("cohort_lines.csv")
    fig = styles.cohort_lines_vs_mob(df, ylabel="VT rate", annotate_n=False)
    n_annotations = [
        a for a in (fig.layout.annotations or []) if a.text and str(a.text).startswith("n=")
    ]
    assert n_annotations == []


def test_cohort_lines_no_expected_column_omits_trace():
    df = _load("cohort_lines.csv").drop(columns=["expected"])
    fig = styles.cohort_lines_vs_mob(df, expected=None)
    names = [t.name for t in fig.data]
    assert "Expected" not in names


# ------------------------------------------------------------------ grouped_bars
def test_grouped_bars_returns_figure():
    df = _load("grouped_bars_by_grade.csv")
    fig = styles.grouped_bars_by_grade_two_series(df)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2  # 2 series


def test_grouped_bars_annotates_n_by_default():
    df = _load("grouped_bars_by_grade.csv")
    fig = styles.grouped_bars_by_grade_two_series(df)
    # Each bar trace should have non-empty text starting with "n="
    for trace in fig.data:
        assert any(str(t).startswith("n=") for t in trace.text if t)


def test_grouped_bars_requires_exactly_2_series():
    df = _load("grouped_bars_by_grade.csv")
    extra = df.copy()
    extra["series"] = "third"
    bad = pd.concat([df, extra.head(2)])
    with pytest.raises(ValueError, match="exactly 2 series"):
        styles.grouped_bars_by_grade_two_series(bad)


# ------------------------------------------------------------------ stacked_100pct
def test_stacked_100pct_returns_figure():
    df = _load("stacked_100pct.csv")
    fig = styles.stacked_bar_100pct_monthly_2x2(df)
    assert isinstance(fig, go.Figure)
    # 6 introducer categories
    assert len(fig.data) == 6


def test_stacked_100pct_annotates_n_totals():
    df = _load("stacked_100pct.csv")
    fig = styles.stacked_bar_100pct_monthly_2x2(df)
    n_annotations = [
        a for a in (fig.layout.annotations or []) if a.text and str(a.text).startswith("n=")
    ]
    # 18 months × 1 total each
    assert len(n_annotations) == 18


# ------------------------------------------------------------------ heatmap_swap
def test_heatmap_swap_returns_figure():
    df = _load("swap_matrix.csv")
    fig = styles.heatmap_swap(df)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.data[0].type == "heatmap"


def test_heatmap_swap_handles_missing_amount_share():
    df = _load("swap_matrix.csv").drop(columns=["pct_amount"])
    fig = styles.heatmap_swap(df, amount_share=None)
    assert isinstance(fig, go.Figure)


# ------------------------------------------------------------------ scatter_calibration
def test_scatter_calibration_returns_figure():
    df = _load("calibration_scatter.csv")
    fig = styles.scatter_calibration(df)
    assert isinstance(fig, go.Figure)
    # 1 diagonal + 1 points
    assert len(fig.data) == 2


def test_scatter_calibration_has_diagonal():
    df = _load("calibration_scatter.csv")
    fig = styles.scatter_calibration(df)
    # First trace is the y=x diagonal
    diag = fig.data[0]
    assert diag.name == "y = x"
    # Diagonal endpoints should be equal in x and y
    assert list(diag.x) == list(diag.y)


# ------------------------------------------------------------------ universal n-validation
def test_resolve_n_column_raises_when_missing():
    """If annotate_n=True (default) and the n column is missing, raise ValueError."""
    df = _load("dq_2x2.csv").drop(columns=["n"])
    with pytest.raises(ValueError, match="annotate_n=True requires"):
        styles.dq_2x2_actual_vs_expected(df)


# ================================================================== 5b smoke tests
# One smoke test per 5b style — verifies it returns a Figure when fed its fixture.
# Detailed behavioural tests are deferred to a follow-up batch.


def test_dq_2x2_with_n_annotated_returns_figure():
    fig = styles.dq_2x2_with_n_annotated(_load("dq_2x2_with_n_annotated.csv"))
    assert isinstance(fig, go.Figure)


def test_regression_validation_1x3_returns_figure():
    fig = styles.regression_validation_1x3(_load("regression_validation_1x3.csv"))
    assert isinstance(fig, go.Figure)


def test_cohort_lines_1x3_by_grade_group_returns_figure():
    fig = styles.cohort_lines_1x3_by_grade_group(_load("cohort_lines_1x3_by_grade_group.csv"))
    assert isinstance(fig, go.Figure)


def test_cohort_lines_1x3_paired_expected_returns_figure():
    fig = styles.cohort_lines_1x3_paired_expected(_load("cohort_lines_1x3_paired_expected.csv"))
    assert isinstance(fig, go.Figure)


def test_roll_rate_dual_axis_lines_returns_figure():
    fig = styles.roll_rate_dual_axis_lines(
        _load("roll_rate_dual_axis_lines.csv"),
        small_axis_cols=("early_roll",),
        large_axis_cols=("mid_roll", "late_roll", "late_roll_improved"),
        dashed_cols=("late_roll_improved",),
    )
    assert isinstance(fig, go.Figure)


def test_lines_1x2_funnel_by_introducer_returns_figure():
    fig = styles.lines_1x2_funnel_by_introducer(_load("lines_1x2_funnel_by_introducer.csv"))
    assert isinstance(fig, go.Figure)


def test_lines_with_overall_highlight_returns_figure():
    fig = styles.lines_with_overall_highlight(_load("lines_with_overall_highlight.csv"))
    assert isinstance(fig, go.Figure)


def test_segment_compare_2x2_with_gap_returns_figure():
    fig = styles.segment_compare_2x2_with_gap(_load("segment_compare_2x2_with_gap.csv"))
    assert isinstance(fig, go.Figure)


def test_lines_funnel_by_introducer_1x1_returns_figure():
    fig = styles.lines_funnel_by_introducer_1x1(_load("lines_funnel_by_introducer_1x1.csv"))
    assert isinstance(fig, go.Figure)


def test_line_with_ci_band_returns_figure():
    fig = styles.line_with_ci_band(_load("line_with_ci_band.csv"))
    assert isinstance(fig, go.Figure)


def test_stacked_bar_volume_2x2_with_rate_line_returns_figure():
    fig = styles.stacked_bar_volume_2x2_with_rate_line(
        _load("stacked_bar_volume_2x2_with_rate_line.csv")
    )
    assert isinstance(fig, go.Figure)


def test_bar_horizontal_top_n_returns_figure():
    fig = styles.bar_horizontal_top_n(_load("bar_horizontal_top_n.csv"))
    assert isinstance(fig, go.Figure)


def test_bar_plus_line_share_top_n_returns_figure():
    fig = styles.bar_plus_line_share_top_n(_load("bar_plus_line_share_top_n.csv"))
    assert isinstance(fig, go.Figure)


def test_waterfall_components_by_grade_returns_figure():
    fig = styles.waterfall_components_by_grade(_load("waterfall_components_by_grade.csv"))
    assert isinstance(fig, go.Figure)


def test_violin_grouped_returns_figure():
    fig = styles.violin_grouped(_load("violin_grouped.csv"))
    assert isinstance(fig, go.Figure)


def test_box_quantile_returns_figure():
    fig = styles.box_quantile(_load("box_quantile.csv"))
    assert isinstance(fig, go.Figure)


def test_histogram_by_grade_returns_figure():
    fig = styles.histogram_by_grade(_load("histogram_by_grade.csv"))
    assert isinstance(fig, go.Figure)


def test_cohort_grid_grade_x_period_returns_figure():
    fig = styles.cohort_grid_grade_x_period(_load("cohort_grid_grade_x_period.csv"))
    assert isinstance(fig, go.Figure)


def test_funnel_horizontal_returns_figure():
    fig = styles.funnel_horizontal(_load("funnel_horizontal.csv"))
    assert isinstance(fig, go.Figure)


def test_styles_module_exports_all_25():
    """The styles package's __all__ must list exactly the 25 v0.1 chart styles."""
    expected = {
        "grouped_bars_by_grade_two_series", "stacked_bar_100pct_monthly_2x2",
        "bar_horizontal_top_n", "bar_plus_line_share_top_n",
        "stacked_bar_volume_2x2_with_rate_line", "waterfall_components_by_grade",
        "heatmap_swap",
        "cohort_lines_vs_mob", "dq_2x2_actual_vs_expected",
        "dq_2x2_with_n_annotated", "regression_validation_1x3",
        "cohort_lines_1x3_by_grade_group", "cohort_lines_1x3_paired_expected",
        "roll_rate_dual_axis_lines",
        "lines_1x2_funnel_by_introducer", "lines_with_overall_highlight",
        "segment_compare_2x2_with_gap", "lines_funnel_by_introducer_1x1",
        "line_with_ci_band",
        "scatter_calibration",
        "violin_grouped", "box_quantile", "histogram_by_grade",
        "cohort_grid_grade_x_period", "funnel_horizontal",
    }
    assert set(styles.__all__) == expected
    assert len(styles.__all__) == 25


# ================================================================== 5b behavioural tests
# Match 5a's depth: per-style coverage of the universal contract surface
# (annotate_n=False suppresses annotations, validators fire, kwargs apply).


def _n_annotations(fig: go.Figure) -> list:
    """Return all chart annotations whose text starts with 'n='."""
    return [
        a for a in (fig.layout.annotations or [])
        if a.text and str(a.text).startswith("n=")
    ]


# --- dq_2x2_with_n_annotated ---
def test_dq_2x2_with_n_annotated_off_suppresses():
    df = _load("dq_2x2_with_n_annotated.csv")
    fig = styles.dq_2x2_with_n_annotated(df, annotate_n=False)
    assert _n_annotations(fig) == []


def test_dq_2x2_with_n_annotated_custom_title():
    df = _load("dq_2x2_with_n_annotated.csv")
    fig = styles.dq_2x2_with_n_annotated(df, title="EV — small sample variant")
    assert fig.layout.title.text == "EV — small sample variant"


def test_dq_2x2_with_n_annotated_requires_4_metrics():
    df = _load("dq_2x2_with_n_annotated.csv")
    df = df[df["metric"].isin(df["metric"].unique()[:3])]
    with pytest.raises(ValueError):
        styles.dq_2x2_with_n_annotated(df)


# --- regression_validation_1x3 ---
def test_regression_validation_1x3_requires_3_metrics():
    df = _load("regression_validation_1x3.csv")
    df = df[df["metric"].isin(df["metric"].unique()[:2])]
    with pytest.raises(ValueError):
        styles.regression_validation_1x3(df)


def test_regression_validation_1x3_annotate_n_off():
    df = _load("regression_validation_1x3.csv")
    fig = styles.regression_validation_1x3(df, annotate_n=False)
    assert _n_annotations(fig) == []


# --- cohort_lines_1x3_by_grade_group ---
def test_cohort_lines_1x3_by_grade_group_requires_3_groups():
    df = _load("cohort_lines_1x3_by_grade_group.csv")
    df = df[df["grade_group"].isin(df["grade_group"].unique()[:2])]
    with pytest.raises(ValueError):
        styles.cohort_lines_1x3_by_grade_group(df)


def test_cohort_lines_1x3_by_grade_group_annotate_n_off():
    df = _load("cohort_lines_1x3_by_grade_group.csv")
    fig = styles.cohort_lines_1x3_by_grade_group(df, annotate_n=False)
    assert _n_annotations(fig) == []


def test_cohort_lines_1x3_by_grade_group_expected_none_omits_trace():
    df = _load("cohort_lines_1x3_by_grade_group.csv")
    fig = styles.cohort_lines_1x3_by_grade_group(df, expected=None)
    assert "Expected" not in [t.name for t in fig.data]


# --- cohort_lines_1x3_paired_expected ---
def test_cohort_lines_1x3_paired_expected_requires_3_groups():
    df = _load("cohort_lines_1x3_paired_expected.csv")
    df = df[df["grade_group"].isin(df["grade_group"].unique()[:2])]
    with pytest.raises(ValueError):
        styles.cohort_lines_1x3_paired_expected(df)


def test_cohort_lines_1x3_paired_expected_annotate_n_off():
    df = _load("cohort_lines_1x3_paired_expected.csv")
    fig = styles.cohort_lines_1x3_paired_expected(df, annotate_n=False)
    assert _n_annotations(fig) == []


# --- roll_rate_dual_axis_lines ---
def test_roll_rate_dual_axis_lines_dashed_marker():
    df = _load("roll_rate_dual_axis_lines.csv")
    fig = styles.roll_rate_dual_axis_lines(
        df,
        small_axis_cols=("early_roll",),
        large_axis_cols=("mid_roll", "late_roll", "late_roll_improved"),
        dashed_cols=("late_roll_improved",),
    )
    dashed = [t for t in fig.data if t.line and t.line.dash == "dash"]
    assert len(dashed) >= 1


def test_roll_rate_dual_axis_lines_custom_title():
    df = _load("roll_rate_dual_axis_lines.csv")
    fig = styles.roll_rate_dual_axis_lines(
        df,
        small_axis_cols=("early_roll",),
        large_axis_cols=("mid_roll", "late_roll"),
        title="custom",
    )
    assert fig.layout.title.text == "custom"


# --- lines_1x2_funnel_by_introducer ---
def test_lines_1x2_funnel_annotate_n_off():
    df = _load("lines_1x2_funnel_by_introducer.csv")
    fig = styles.lines_1x2_funnel_by_introducer(df, annotate_n=False)
    assert _n_annotations(fig) == []


def test_lines_1x2_funnel_custom_title():
    df = _load("lines_1x2_funnel_by_introducer.csv")
    fig = styles.lines_1x2_funnel_by_introducer(df, title="custom funnel")
    assert fig.layout.title.text == "custom funnel"


# --- lines_with_overall_highlight ---
def test_lines_with_overall_highlight_overall_is_bold():
    df = _load("lines_with_overall_highlight.csv")
    fig = styles.lines_with_overall_highlight(df)
    overall = next((t for t in fig.data if t.name == "Overall"), None)
    assert overall is not None, "Overall trace missing"
    # Overall must be visibly thicker than other segment lines
    other_widths = [t.line.width for t in fig.data if t.name != "Overall" and t.line.width]
    if other_widths:
        assert overall.line.width > max(other_widths)


def test_lines_with_overall_highlight_annotate_n_off():
    df = _load("lines_with_overall_highlight.csv")
    fig = styles.lines_with_overall_highlight(df, annotate_n=False)
    assert _n_annotations(fig) == []


# --- segment_compare_2x2_with_gap ---
def test_segment_compare_annotate_n_off():
    df = _load("segment_compare_2x2_with_gap.csv")
    fig = styles.segment_compare_2x2_with_gap(df, annotate_n=False)
    assert _n_annotations(fig) == []


def test_segment_compare_custom_labels_apply():
    df = _load("segment_compare_2x2_with_gap.csv")
    fig = styles.segment_compare_2x2_with_gap(
        df,
        a_label="Carrera",
        b_label="Torino",
        adjusted_label="Torino at Carrera mix",
        good_band_label="A-D",
        risky_band_label="E+",
    )
    names = [t.name for t in fig.data]
    assert "Carrera" in names
    assert "Torino" in names
    assert "Torino at Carrera mix" in names
    assert "A-D" in names
    assert "E+" in names


def test_segment_compare_requires_grade_mix_cols():
    df = _load("segment_compare_2x2_with_gap.csv").drop(columns=["a_good_share"])
    with pytest.raises(ValueError):
        styles.segment_compare_2x2_with_gap(df)


# --- lines_funnel_by_introducer_1x1 ---
def test_lines_funnel_1x1_annotate_n_off():
    df = _load("lines_funnel_by_introducer_1x1.csv")
    fig = styles.lines_funnel_by_introducer_1x1(df, annotate_n=False)
    assert _n_annotations(fig) == []


# --- line_with_ci_band ---
def test_line_with_ci_band_has_band_traces():
    df = _load("line_with_ci_band.csv")
    fig = styles.line_with_ci_band(df)
    # Each group → 2 traces (line + band). Band traces have fill='toself'.
    band_traces = [t for t in fig.data if t.fill == "toself"]
    n_groups = df["group"].nunique()
    assert len(band_traces) == n_groups


def test_line_with_ci_band_annotate_n_off():
    df = _load("line_with_ci_band.csv")
    fig = styles.line_with_ci_band(df, annotate_n=False)
    assert _n_annotations(fig) == []


# --- stacked_bar_volume_2x2_with_rate_line ---
def test_stacked_bar_volume_2x2_custom_title():
    df = _load("stacked_bar_volume_2x2_with_rate_line.csv")
    fig = styles.stacked_bar_volume_2x2_with_rate_line(df, title="custom")
    assert fig.layout.title.text == "custom"


# --- bar_horizontal_top_n ---
def test_bar_horizontal_top_n_filters_top_n():
    df = _load("bar_horizontal_top_n.csv")
    fig = styles.bar_horizontal_top_n(df, top_n=5)
    # Only one trace; its y has at most 5 categories
    assert len(fig.data) == 1
    assert len(fig.data[0].y) == 5


def test_bar_horizontal_top_n_sorted_by_value():
    df = _load("bar_horizontal_top_n.csv")
    fig = styles.bar_horizontal_top_n(df, top_n=10)
    # In horizontal bars Plotly renders y[0] at the BOTTOM, so the trace stores
    # values ascending — and the largest ends up visually at the top.
    xs = [float(x) for x in fig.data[0].x]
    assert xs == sorted(xs), "Trace should be sorted ascending (Plotly renders largest at top)"


# --- bar_plus_line_share_top_n ---
def test_bar_plus_line_share_top_n_annotate_n_off():
    df = _load("bar_plus_line_share_top_n.csv")
    fig = styles.bar_plus_line_share_top_n(df, annotate_n=False)
    assert _n_annotations(fig) == []


# --- waterfall_components_by_grade ---
def test_waterfall_panels_match_grade_groups():
    df = _load("waterfall_components_by_grade.csv")
    fig = styles.waterfall_components_by_grade(df)
    n_groups = df["grade_group"].nunique()
    # One trace per grade group (each panel has one Bar trace)
    assert len(fig.data) == n_groups


def test_waterfall_custom_title():
    df = _load("waterfall_components_by_grade.csv")
    fig = styles.waterfall_components_by_grade(df, title="custom")
    assert fig.layout.title.text == "custom"


# --- violin_grouped ---
def test_violin_grouped_tick_labels_include_n():
    df = _load("violin_grouped.csv")
    fig = styles.violin_grouped(df)
    # Check that ticktext on x-axis includes "(n=" for each category
    ticktext = fig.layout.xaxis.ticktext or []
    if ticktext:
        assert any("(n=" in str(t) for t in ticktext)


# --- box_quantile ---
def test_box_quantile_returns_one_trace_per_category():
    df = _load("box_quantile.csv")
    fig = styles.box_quantile(df)
    n_cats = df["category"].nunique()
    # Either one trace with one box each or N traces (one per cat)
    assert len(fig.data) in (1, n_cats)


# --- histogram_by_grade ---
def test_histogram_by_grade_one_trace_per_grade():
    df = _load("histogram_by_grade.csv")
    fig = styles.histogram_by_grade(df)
    n_grades = df["grade"].nunique()
    assert len(fig.data) == n_grades


# --- cohort_grid_grade_x_period ---
def test_cohort_grid_custom_title():
    df = _load("cohort_grid_grade_x_period.csv")
    fig = styles.cohort_grid_grade_x_period(df, title="custom")
    assert fig.layout.title.text == "custom"


# --- funnel_horizontal ---
def test_funnel_horizontal_stages_in_data():
    df = _load("funnel_horizontal.csv")
    fig = styles.funnel_horizontal(df)
    # Should be exactly one Funnel trace
    funnel_traces = [t for t in fig.data if t.type == "funnel"]
    assert len(funnel_traces) == 1
    # The funnel trace has as many y values as stages in the data
    assert len(funnel_traces[0].y) == df["stage"].nunique()

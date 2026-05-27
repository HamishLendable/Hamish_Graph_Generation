"""DQ-flavoured subplot chart styles (batch 5b-a).

Five extra primitives that live alongside lines.py / bars.py:

- dq_2x2_with_n_annotated         — 2×2 actual-vs-expected with n= on every point
- regression_validation_1x3       — 1×3 actual-vs-predicted per metric
- cohort_lines_1x3_by_grade_group — 1×3 cohort lines, one panel per grade group
- cohort_lines_1x3_paired_expected— 1×3 cohort lines with paired-colour expected dashes
- roll_rate_dual_axis_lines       — single-panel dual-y-axis lines for roll rates
"""

from __future__ import annotations

from typing import Sequence

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from motor_graphs.style import apply_auto_legend
from motor_graphs.style.palette import (
    ACTUAL,
    ADJUSTED,
    COHORT_COLORS,
    EXPECTED,
    SECONDARY,
)

from ._shared import (
    SmallSampleMode,
    add_pound_weighted_footnote,
    opacity_for_n,
    require_columns,
    resolve_n_column,
)


# --------------------------------------------------------------------------- #
# (a) dq_2x2_with_n_annotated
# --------------------------------------------------------------------------- #
def dq_2x2_with_n_annotated(
    df: pd.DataFrame,
    *,
    cohort: str = "cohort",
    metric: str = "metric",
    actual: str = "actual",
    expected: str = "expected",
    n: str | None = "n",
    title: str | None = None,
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "fade",
) -> go.Figure:
    """2×2 grid of actual-vs-expected lines with n= annotated on EVERY visible point.

    Use this when:
        - You have rate-over-cohort data for exactly 4 DQ metrics and want a
          per-point readout of sample size, not just the most recent one.
        - You want fading on small-n points by default so the eye discounts
          them visually — useful for the very recent / immature MOBs.

    Data shape:
        Long/tidy DataFrame, one row per (cohort, metric):
            cohort   (str or date) — cohort label
            metric   (str)         — exactly 4 distinct values, one per subplot
            actual   (float)       — actual rate (decimal)
            expected (float)       — expected/benchmark rate
            n        (int)         — sample size; required when annotate_n=True.
                                     Some n<50 / 50≤n<200 / n≥200 spreads exercise
                                     the small-sample fade/suppress logic.

    Style:
        2×2 subplots, one per metric (sorted alphabetically). Each subplot:
        - Blue (#1f77b4) solid 2-px line for actual.
        - Red (#d62728) dashed 2-px line for expected.
        - Marker opacity faded per EV thresholds (default
          small_sample_handling="fade": n<200 → 0.35 opacity).
        - n= annotation on EVERY visible actual point (skipped only when
          small_sample_handling="suppress" has dropped the point to 0 opacity).
        - Y-axis as percentages (.1%).

    Parameters:
        df: input DataFrame.
        cohort, metric, actual, expected, n: column names.
        title: figure title (defaults to "DQ actual vs expected (n annotated)").
        annotate_n: if True (default), annotate n= on every visible point.
        small_sample_handling: "show", "fade" (default), or "suppress".

    Returns:
        plotly.graph_objects.Figure with 8 traces (4 metrics × 2 series).

    Example:
        >>> df = pd.read_csv("dq_2x2_with_n_annotated.csv")
        >>> fig = dq_2x2_with_n_annotated(df, title="Motor DQ — full n readout")
    """
    require_columns(df, [cohort, metric, actual, expected], who="dq_2x2_with_n_annotated")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    metrics = sorted(df[metric].unique())
    if len(metrics) != 4:
        raise ValueError(
            f"dq_2x2_with_n_annotated expects exactly 4 metrics, got {len(metrics)}: {metrics}"
        )

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=metrics,
        vertical_spacing=0.20,
        horizontal_spacing=0.08,
    )
    for idx, met in enumerate(metrics):
        r, c = idx // 2 + 1, idx % 2 + 1
        sub = df[df[metric] == met].sort_values(cohort).reset_index(drop=True)
        ns = sub[n_col].tolist() if n_col else None
        opacities = opacity_for_n(ns, mode=small_sample_handling) if ns else [1.0] * len(sub)

        fig.add_trace(
            go.Scatter(
                x=sub[cohort],
                y=sub[actual],
                mode="lines+markers",
                name="Actual",
                line=dict(color=ACTUAL, width=2),
                marker=dict(size=6, opacity=opacities),
                showlegend=(idx == 0),
                customdata=ns if ns else None,
                hovertemplate=(
                    f"<b>{met}</b><br>%{{x}}: %{{y:.2%}}"
                    + (" (n=%{customdata})" if ns else "")
                    + "<extra></extra>"
                ),
            ),
            row=r, col=c,
        )
        fig.add_trace(
            go.Scatter(
                x=sub[cohort],
                y=sub[expected],
                mode="lines",
                name="Expected",
                line=dict(color=EXPECTED, width=2, dash="dash"),
                showlegend=(idx == 0),
                hovertemplate=f"<b>{met}</b><br>Expected: %{{y:.2%}}<extra></extra>",
            ),
            row=r, col=c,
        )
        fig.update_yaxes(tickformat=".1%", row=r, col=c)
        fig.update_xaxes(tickangle=-30, row=r, col=c)

        if annotate_n and n_col and ns:
            for x_val, y_val, n_val, op in zip(
                sub[cohort], sub[actual], ns, opacities, strict=False
            ):
                if op <= 0:
                    continue
                fig.add_annotation(
                    x=x_val,
                    y=y_val,
                    text=f"n={int(n_val)}",
                    showarrow=False,
                    yshift=12,
                    font=dict(size=8, color="grey"),
                    xanchor="center",
                    row=r, col=c,
                )

    fig.update_layout(title=title or "DQ actual vs expected (n annotated)")
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


# --------------------------------------------------------------------------- #
# (b) regression_validation_1x3
# --------------------------------------------------------------------------- #
def regression_validation_1x3(
    df: pd.DataFrame,
    *,
    cohort: str = "cohort",
    metric: str = "metric",
    actual: str = "actual",
    predicted: str = "predicted",
    n: str | None = "n",
    title: str | None = None,
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """1×3 subplot grid — actual vs predicted per regression-validation metric.

    Use this when:
        - You have a regression / forecasting model and want to compare
          realised vs predicted values across exactly 3 validation metrics
          (e.g. 30+@3, 60+@6, 90+@9) side-by-side.
        - The actual/predicted contrast is the focus and a single row makes
          it easy to scan left-to-right.

    Data shape:
        Long/tidy DataFrame, one row per (cohort, metric):
            cohort    (str or date) — cohort label, sorted within each panel
            metric    (str)         — exactly 3 distinct values, one per panel
                                       (panels appear in alphabetical metric order)
            actual    (float)       — realised value (decimal)
            predicted (float)       — model prediction (decimal)
            n         (int, opt)    — sample size; required if annotate_n=True

    Style:
        1×3 subplots. Each panel:
        - Blue (#1f77b4) solid 2-px line for actual.
        - Red (#d62728) dashed 2-px line for predicted.
        - n= annotation on the last actual point per panel.
        - Y-axis as percentages (.1%).

    Parameters:
        df: input DataFrame.
        cohort, metric, actual, predicted, n: column names.
        title: figure title (defaults to "Regression validation — actual vs predicted").
        annotate_n: if True (default), annotate n= on the last actual point per panel.
        small_sample_handling: see dq_2x2_actual_vs_expected.

    Returns:
        plotly.graph_objects.Figure with 6 traces (3 metrics × 2 series).

    Example:
        >>> df = pd.read_csv("regression_validation_1x3.csv")
        >>> fig = regression_validation_1x3(df, title="Validation — H1 2026")
    """
    require_columns(df, [cohort, metric, actual, predicted], who="regression_validation_1x3")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    metrics = sorted(df[metric].unique())
    if len(metrics) != 3:
        raise ValueError(
            f"regression_validation_1x3 expects exactly 3 metrics, got {len(metrics)}: {metrics}"
        )

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=metrics,
        horizontal_spacing=0.08,
    )
    for idx, met in enumerate(metrics):
        c = idx + 1
        sub = df[df[metric] == met].sort_values(cohort).reset_index(drop=True)
        ns = sub[n_col].tolist() if n_col else None
        opacities = opacity_for_n(ns, mode=small_sample_handling) if ns else [1.0] * len(sub)

        fig.add_trace(
            go.Scatter(
                x=sub[cohort],
                y=sub[actual],
                mode="lines+markers",
                name="Actual",
                line=dict(color=ACTUAL, width=2),
                marker=dict(size=6, opacity=opacities),
                showlegend=(idx == 0),
                customdata=ns if ns else None,
                hovertemplate=(
                    f"<b>{met}</b><br>%{{x}}: %{{y:.2%}}"
                    + (" (n=%{customdata})" if ns else "")
                    + "<extra></extra>"
                ),
            ),
            row=1, col=c,
        )
        fig.add_trace(
            go.Scatter(
                x=sub[cohort],
                y=sub[predicted],
                mode="lines",
                name="Predicted",
                line=dict(color=EXPECTED, width=2, dash="dash"),
                showlegend=(idx == 0),
                hovertemplate=f"<b>{met}</b><br>Predicted: %{{y:.2%}}<extra></extra>",
            ),
            row=1, col=c,
        )
        fig.update_yaxes(tickformat=".1%", row=1, col=c)
        fig.update_xaxes(tickangle=-30, row=1, col=c)

        if annotate_n and n_col and ns and opacities[-1] > 0:
            fig.add_annotation(
                x=sub[cohort].iloc[-1],
                y=sub[actual].iloc[-1],
                text=f"n={int(ns[-1])}",
                showarrow=False,
                yshift=14,
                xshift=-2,
                font=dict(size=9, color="grey"),
                xanchor="right",
                row=1, col=c,
            )

    fig.update_layout(title=title or "Regression validation — actual vs predicted")
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


# --------------------------------------------------------------------------- #
# (c) cohort_lines_1x3_by_grade_group
# --------------------------------------------------------------------------- #
def cohort_lines_1x3_by_grade_group(
    df: pd.DataFrame,
    *,
    cohort: str = "cohort",
    mob: str = "mob",
    grade_group: str = "grade_group",
    y: str = "rate",
    expected: str | None = "expected",
    n: str | None = "n",
    title: str | None = None,
    ylabel: str = "Rate",
    y_tickformat: str = ".1%",
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """1×3 cohort-line subplots, one panel per grade group.

    Use this when:
        - You want to compare cumulative rate (VT, default, prepayment) by
          cohort within each of the 3 grade buckets (typically "A-B", "C-E",
          "F+") — keeping each grade group on its own y-scale via separate
          panels.
        - You want a single Expected curve overlaid per panel (red dashed),
          shared across cohorts in that panel.

    Data shape:
        Long/tidy DataFrame, one row per (cohort, mob, grade_group):
            cohort      (str or date) — cohort label
            mob         (int)         — months on book
            grade_group (str)         — exactly 3 distinct values, one per panel
                                         (panels appear in alphabetical group order)
            rate        (float)       — cumulative rate at that MOB (decimal)
            expected    (float, opt)  — single expected curve per (grade_group, mob).
                                         Pass expected=None (or omit column) to
                                         disable the benchmark overlay.
            n           (int, opt)    — cohort size; required if annotate_n=True.
                                         Same value across MOBs for a given cohort.

    Style:
        1×3 subplots (horizontal_spacing=0.06). Each panel:
        - One line per cohort, coloured positionally from COHORT_COLORS.
        - Optional dashed Expected line in red.
        - n= annotation on the last (highest-MOB) point per cohort.
        - Y-axis as percentages by default.

    Parameters:
        df: input DataFrame.
        cohort, mob, grade_group, y, expected, n: column names. `expected=None`
            disables the per-panel benchmark.
        title, ylabel: figure labels.
        y_tickformat: tick format string (default ".1%").
        annotate_n: if True (default), annotate n= on the last cohort point.
        small_sample_handling: see dq_2x2_actual_vs_expected.

    Returns:
        plotly.graph_objects.Figure with one trace per (cohort × panel) plus
        optionally one Expected per panel.

    Example:
        >>> df = pd.read_csv("cohort_lines_1x3_by_grade_group.csv")
        >>> fig = cohort_lines_1x3_by_grade_group(df, ylabel="VT rate")
    """
    require_columns(df, [cohort, mob, grade_group, y], who="cohort_lines_1x3_by_grade_group")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    groups = sorted(df[grade_group].unique())
    if len(groups) != 3:
        raise ValueError(
            f"cohort_lines_1x3_by_grade_group expects exactly 3 grade groups, got {groups}"
        )

    cohorts = list(df[cohort].drop_duplicates())
    show_expected = expected is not None and expected in df.columns

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=groups,
        horizontal_spacing=0.06,
    )

    seen_cohorts: set = set()
    for g_idx, g in enumerate(groups):
        c = g_idx + 1
        g_df = df[df[grade_group] == g]
        for i, coh in enumerate(cohorts):
            sub = g_df[g_df[cohort] == coh].sort_values(mob).reset_index(drop=True)
            if sub.empty:
                continue
            ns = sub[n_col].tolist() if n_col else None
            opacities = (
                opacity_for_n(ns, mode=small_sample_handling) if ns else [1.0] * len(sub)
            )
            color = COHORT_COLORS[i % len(COHORT_COLORS)]
            show_in_legend = coh not in seen_cohorts
            seen_cohorts.add(coh)
            fig.add_trace(
                go.Scatter(
                    x=sub[mob],
                    y=sub[y],
                    mode="lines+markers",
                    name=str(coh),
                    legendgroup=str(coh),
                    line=dict(color=color, width=2),
                    marker=dict(size=4, opacity=opacities),
                    showlegend=show_in_legend,
                    customdata=ns if ns else None,
                    hovertemplate=(
                        f"<b>{coh} — {g}</b><br>MOB %{{x}}: %{{y:{y_tickformat[1:]}}}"
                        + (" (n=%{customdata})" if ns else "")
                        + "<extra></extra>"
                    ),
                ),
                row=1, col=c,
            )

            if annotate_n and n_col and ns and opacities[-1] > 0:
                fig.add_annotation(
                    x=sub[mob].iloc[-1],
                    y=sub[y].iloc[-1],
                    text=f"n={int(ns[-1])}",
                    showarrow=False,
                    yshift=10,
                    xshift=4,
                    font=dict(size=9, color="grey"),
                    xanchor="left",
                    row=1, col=c,
                )

        if show_expected:
            exp_df = (
                g_df.dropna(subset=[expected])
                .drop_duplicates(subset=[mob])
                .sort_values(mob)
            )
            if not exp_df.empty:
                fig.add_trace(
                    go.Scatter(
                        x=exp_df[mob],
                        y=exp_df[expected],
                        mode="lines",
                        name="Expected",
                        legendgroup="Expected",
                        line=dict(color=EXPECTED, width=2, dash="dash"),
                        showlegend=(g_idx == 0),
                        hovertemplate=(
                            f"Expected ({g}) MOB %{{x}}: %{{y:{y_tickformat[1:]}}}<extra></extra>"
                        ),
                    ),
                    row=1, col=c,
                )

        fig.update_yaxes(tickformat=y_tickformat, title=ylabel if g_idx == 0 else None,
                         row=1, col=c)
        fig.update_xaxes(title="MOB", row=1, col=c)

    fig.update_layout(title=title or "Cohort rate vs MOB by grade group")
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


# --------------------------------------------------------------------------- #
# (d) cohort_lines_1x3_paired_expected
# --------------------------------------------------------------------------- #
def cohort_lines_1x3_paired_expected(
    df: pd.DataFrame,
    *,
    cohort: str = "cohort",
    mob: str = "mob",
    grade_group: str = "grade_group",
    actual: str = "actual",
    expected: str = "expected",
    n: str | None = "n",
    title: str | None = None,
    ylabel: str = "Rate",
    y_tickformat: str = ".1%",
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """1×3 cohort lines — per-cohort actual SOLID + per-cohort expected DASHED, same colour.

    Use this when:
        - Each cohort has its OWN expected curve (a per-cohort forecast) and you
          want to spot cohort-level drift from cohort-level expectations.
        - Pairing actual/expected in the same colour per cohort makes the
          divergence within a cohort visually obvious — the dashed line drifts
          away from the solid line of the same colour.

    Data shape:
        Long/tidy DataFrame, one row per (cohort, mob, grade_group):
            cohort      (str or date) — cohort label
            mob         (int)         — months on book
            grade_group (str)         — exactly 3 distinct values, one per panel
            actual      (float)       — realised cumulative rate (decimal)
            expected    (float)       — PER-COHORT expected curve (decimal)
            n           (int, opt)    — cohort size; required if annotate_n=True

    Style:
        1×3 subplots (horizontal_spacing=0.06). Each panel:
        - Per cohort: actual SOLID + expected DASHED in the SAME
          COHORT_COLORS[i] colour (not red).
        - n= annotation on the last actual point per cohort.
        - Y-axis as percentages by default.

    Parameters:
        df: input DataFrame.
        cohort, mob, grade_group, actual, expected, n: column names.
        title, ylabel: figure labels.
        y_tickformat: tick format string (default ".1%").
        annotate_n: if True (default), annotate n= on the last actual point.
        small_sample_handling: see dq_2x2_actual_vs_expected.

    Returns:
        plotly.graph_objects.Figure with two traces per (cohort × panel).

    Example:
        >>> df = pd.read_csv("cohort_lines_1x3_paired_expected.csv")
        >>> fig = cohort_lines_1x3_paired_expected(df, ylabel="Default rate")
    """
    require_columns(
        df, [cohort, mob, grade_group, actual, expected],
        who="cohort_lines_1x3_paired_expected",
    )
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    groups = sorted(df[grade_group].unique())
    if len(groups) != 3:
        raise ValueError(
            f"cohort_lines_1x3_paired_expected expects exactly 3 grade groups, got {groups}"
        )

    cohorts = list(df[cohort].drop_duplicates())

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=groups,
        horizontal_spacing=0.06,
    )

    seen_cohorts: set = set()
    for g_idx, g in enumerate(groups):
        c = g_idx + 1
        g_df = df[df[grade_group] == g]
        for i, coh in enumerate(cohorts):
            sub = g_df[g_df[cohort] == coh].sort_values(mob).reset_index(drop=True)
            if sub.empty:
                continue
            ns = sub[n_col].tolist() if n_col else None
            opacities = (
                opacity_for_n(ns, mode=small_sample_handling) if ns else [1.0] * len(sub)
            )
            color = COHORT_COLORS[i % len(COHORT_COLORS)]
            show_in_legend = coh not in seen_cohorts
            seen_cohorts.add(coh)

            fig.add_trace(
                go.Scatter(
                    x=sub[mob],
                    y=sub[actual],
                    mode="lines+markers",
                    name=str(coh),
                    legendgroup=str(coh),
                    line=dict(color=color, width=2),
                    marker=dict(size=4, opacity=opacities),
                    showlegend=show_in_legend,
                    customdata=ns if ns else None,
                    hovertemplate=(
                        f"<b>{coh} — {g}</b><br>MOB %{{x}}: %{{y:{y_tickformat[1:]}}}"
                        + (" (n=%{customdata})" if ns else "")
                        + "<extra></extra>"
                    ),
                ),
                row=1, col=c,
            )
            fig.add_trace(
                go.Scatter(
                    x=sub[mob],
                    y=sub[expected],
                    mode="lines",
                    name=f"{coh} (expected)",
                    legendgroup=str(coh),
                    line=dict(color=color, width=2, dash="dash"),
                    showlegend=False,
                    hovertemplate=(
                        f"<b>{coh} — {g}</b><br>"
                        f"Expected MOB %{{x}}: %{{y:{y_tickformat[1:]}}}<extra></extra>"
                    ),
                ),
                row=1, col=c,
            )

            if annotate_n and n_col and ns and opacities[-1] > 0:
                fig.add_annotation(
                    x=sub[mob].iloc[-1],
                    y=sub[actual].iloc[-1],
                    text=f"n={int(ns[-1])}",
                    showarrow=False,
                    yshift=10,
                    xshift=4,
                    font=dict(size=9, color="grey"),
                    xanchor="left",
                    row=1, col=c,
                )

        fig.update_yaxes(tickformat=y_tickformat, title=ylabel if g_idx == 0 else None,
                         row=1, col=c)
        fig.update_xaxes(title="MOB", row=1, col=c)

    fig.update_layout(
        title=title or "Cohort actual vs cohort expected — per grade group"
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


# --------------------------------------------------------------------------- #
# (e) roll_rate_dual_axis_lines
# --------------------------------------------------------------------------- #
def roll_rate_dual_axis_lines(
    df: pd.DataFrame,
    *,
    x: str = "month",
    small_axis_cols: Sequence[str] = ("s1",),
    large_axis_cols: Sequence[str] = ("s2", "s3", "s4"),
    dashed_cols: Sequence[str] = (),
    title: str | None = None,
    xlabel: str = "Month",
    small_ylabel: str = "Small-scale rate",
    large_ylabel: str = "Large-scale rate",
    y_tickformat: str = ".1%",
    n: str | None = None,
    annotate_n: bool = False,
) -> go.Figure:
    """Single-panel dual-y-axis line chart for roll rates at different scales.

    Use this when:
        - You have multiple roll-rate series that live at different orders of
          magnitude (e.g. early-stage roll ~0.5% on one axis vs late-stage roll
          ~3% on another) and want them on the same x-axis (monthly).
        - You also want to overlay "counterfactual" / improvement dashed lines.

    Data shape:
        Wide DataFrame, one row per period:
            x                (str/date) — month label
            small_axis_cols  (float)    — series for the LEFT y-axis (low scale)
            large_axis_cols  (float)    — series for the RIGHT y-axis (higher scale)
            n                (int, opt) — total volume for the month (not normally
                                           annotated — annotate_n defaults to False
                                           because the chart is about RATES).

    Style:
        Single panel, secondary-y axis enabled. Colour assignment:
        - First small-axis series → ACTUAL (#1f77b4).
        - First large-axis series → ACTUAL; additional large series → SECONDARY
          (#ff7f0e) then ADJUSTED (#2ca02c), then cycling COHORT_COLORS.
        - Any column listed in dashed_cols is rendered as a 2-px dashed line
          (e.g. EXPECTED-style improvement / counterfactual indicators).
        - The left axis carries small-scale series, the right axis carries
          large-scale series.

    Parameters:
        df: input DataFrame.
        x: x-axis column.
        small_axis_cols, large_axis_cols: column names assigned to each y-axis.
        dashed_cols: any column names rendered with dash="dash".
        title, xlabel, small_ylabel, large_ylabel: labels.
        y_tickformat: applied to both y-axes (default ".1%").
        n, annotate_n: kept for API consistency. n is typically a monthly total
            for a roll-rate chart and is NOT annotated by default.

    Returns:
        plotly.graph_objects.Figure with a secondary-y axis.

    Example:
        >>> df = pd.read_csv("roll_rate_dual_axis_lines.csv")
        >>> fig = roll_rate_dual_axis_lines(
        ...     df,
        ...     small_axis_cols=("early_roll",),
        ...     large_axis_cols=("mid_roll", "late_roll", "late_roll_improved"),
        ...     dashed_cols=("late_roll_improved",),
        ...     title="Roll rates by stage",
        ... )
    """
    require_columns(df, [x, *small_axis_cols, *large_axis_cols], who="roll_rate_dual_axis_lines")
    # annotate_n defaults to False here — only resolve column if user opts in
    n_col = resolve_n_column(df, n, annotate_n=annotate_n) if annotate_n else None

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    df_sorted = df.sort_values(x).reset_index(drop=True)

    # Left axis (small-scale): first gets ACTUAL, additional get SECONDARY/ADJUSTED then cycle
    left_palette = [ACTUAL, SECONDARY, ADJUSTED, *COHORT_COLORS]
    for i, col in enumerate(small_axis_cols):
        color = left_palette[i % len(left_palette)]
        is_dashed = col in dashed_cols
        fig.add_trace(
            go.Scatter(
                x=df_sorted[x],
                y=df_sorted[col],
                mode="lines+markers",
                name=col,
                line=dict(
                    color=EXPECTED if is_dashed else color,
                    width=2,
                    dash="dash" if is_dashed else "solid",
                ),
                marker=dict(size=5),
                hovertemplate=f"<b>{col}</b> %{{x}}: %{{y:{y_tickformat[1:]}}}<extra></extra>",
            ),
            secondary_y=False,
        )

    # Right axis (large-scale): first SECONDARY, then ADJUSTED, then cycle
    right_palette = [SECONDARY, ADJUSTED, *COHORT_COLORS]
    for i, col in enumerate(large_axis_cols):
        color = right_palette[i % len(right_palette)]
        is_dashed = col in dashed_cols
        fig.add_trace(
            go.Scatter(
                x=df_sorted[x],
                y=df_sorted[col],
                mode="lines+markers",
                name=col,
                line=dict(
                    color=EXPECTED if is_dashed else color,
                    width=2,
                    dash="dash" if is_dashed else "solid",
                ),
                marker=dict(size=5),
                hovertemplate=f"<b>{col}</b> %{{x}}: %{{y:{y_tickformat[1:]}}}<extra></extra>",
            ),
            secondary_y=True,
        )

    fig.update_layout(title=title or "Roll rates — dual axis")
    fig.update_xaxes(title=xlabel)
    fig.update_yaxes(title_text=small_ylabel, tickformat=y_tickformat, secondary_y=False)
    fig.update_yaxes(title_text=large_ylabel, tickformat=y_tickformat, secondary_y=True)

    # Optional n annotation (off by default for this chart family).
    if annotate_n and n_col:
        for x_val, n_val in zip(df_sorted[x], df_sorted[n_col], strict=False):
            if pd.isna(n_val):
                continue
            fig.add_annotation(
                x=x_val,
                y=1.02,
                xref="x",
                yref="paper",
                text=f"n={int(n_val)}",
                showarrow=False,
                font=dict(size=8, color="grey"),
            )

    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig

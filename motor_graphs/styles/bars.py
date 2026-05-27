"""Bar-based chart styles."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from motor_graphs.style import apply_auto_legend
from motor_graphs.style.palette import (
    ACTUAL,
    GRADE_COLOURS,
    INTRODUCER_CATEGORY_COLORS,
    SECONDARY,
    UNKNOWN_INTRODUCER_COLOR,
)

from ._shared import (
    SmallSampleMode,
    add_pound_weighted_footnote,
    require_columns,
    resolve_n_column,
)


def grouped_bars_by_grade_two_series(
    df: pd.DataFrame,
    *,
    grade: str = "grade",
    series: str = "series",
    y: str = "rate",
    n: str | None = "n",
    series_order: list[str] | None = None,
    series_colors: dict[str, str] | None = None,
    title: str | None = None,
    xlabel: str = "Risk grade",
    ylabel: str = "Rate",
    y_tickformat: str = ".1%",
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """Grouped vertical bars by risk grade with two side-by-side series.

    Use this when:
        - You want to compare a rate (DQ, FPD, VT, etc.) across risk grades for
          two segments side by side: BEV vs ROB, Carrera vs Torino, dealer vs
          non-dealer.

    Data shape:
        Long/tidy DataFrame, one row per (grade, series):
            grade   (str)   — risk grade label (A, B, ..., F**)
            series  (str)   — exactly 2 distinct values (the two segments)
            rate    (float) — value to plot
            n       (int, opt) — sample size; required if annotate_n=True

    Style:
        Vertical grouped bars. First series in actual blue (#1f77b4),
        second in safety orange (#ff7f0e), unless overridden via series_colors.
        n= annotation above each bar. Grade order: the order they appear in
        GRADE_COLOURS (A, B, C, D, E, F, F*, F**).

    Parameters:
        df: input DataFrame.
        grade, series, y, n: column names.
        series_order: optional explicit order for the two series. Default: order
            of first appearance in df.
        series_colors: optional dict {series_name: hex}. Default: ACTUAL/SECONDARY.
        title, xlabel, ylabel: figure labels.
        y_tickformat: tick format string (default ".1%").
        annotate_n: if True (default), annotate n= above each bar.
        small_sample_handling: see dq_2x2_actual_vs_expected.

    Returns:
        plotly.graph_objects.Figure with 2 bar traces.

    Example:
        >>> df = pd.read_csv("grouped_bars_by_grade.csv")
        >>> fig = grouped_bars_by_grade_two_series(df, ylabel="90+@9 rate")
    """
    require_columns(df, [grade, series, y], who="grouped_bars_by_grade_two_series")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    series_vals = list(df[series].drop_duplicates())
    if len(series_vals) != 2:
        raise ValueError(
            f"grouped_bars_by_grade_two_series needs exactly 2 series, got {series_vals}"
        )
    if series_order:
        series_vals = series_order

    colors = {series_vals[0]: ACTUAL, series_vals[1]: SECONDARY}
    if series_colors:
        colors.update(series_colors)

    grade_order = [g for g in GRADE_COLOURS.keys() if g in df[grade].values]

    fig = go.Figure()
    for s in series_vals:
        sub = (
            df[df[series] == s]
            .set_index(grade)
            .reindex(grade_order)
            .reset_index()
        )
        ns = sub[n_col].tolist() if n_col else None
        fig.add_trace(
            go.Bar(
                x=sub[grade],
                y=sub[y],
                name=str(s),
                marker_color=colors.get(s, ACTUAL),
                text=[f"n={int(v)}" if pd.notna(v) else "" for v in ns] if ns else None,
                textposition="outside",
                customdata=ns if ns else None,
                hovertemplate=(
                    f"<b>{s} %{{x}}</b>: %{{y:{y_tickformat[1:]}}}"
                    + (" (n=%{customdata})" if ns else "")
                    + "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=title or "Rate by risk grade",
        xaxis_title=xlabel,
        yaxis=dict(title=ylabel, tickformat=y_tickformat),
        barmode="group",
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


def stacked_bar_100pct_monthly_2x2(
    df: pd.DataFrame,
    *,
    month: str = "month",
    category: str = "category",
    share: str = "share",
    n: str | None = "n",
    facet: str | None = None,
    category_colors: dict[str, str] | None = None,
    title: str | None = None,
    xlabel: str = "Origination month",
    annotate_n: bool = True,
) -> go.Figure:
    """100%-stacked monthly bars showing category mix over time, optionally faceted 2×2.

    Use this when:
        - You want to track composition (introducer mix, fuel-type mix, LTV-band
          mix, age-band mix) over monthly cohorts.
        - You want to spot regime shifts in volume composition.

    Data shape:
        Long/tidy DataFrame:
            month     (str or date) — origination month label
            category  (str)         — the stacked-band category
            share     (float)       — share in 0-100 (already a percentage, NOT decimal)
            n         (int, opt)    — total sample size at that month (required if annotate_n=True)
            facet     (str, opt)    — if given, the chart is laid out 2×2 with one
                                       panel per distinct facet value (exactly 4 expected)

    Style:
        100%-stacked vertical bars per month. Categories coloured via
        category_colors (or INTRODUCER_CATEGORY_COLORS by default — falls back
        to grey for unmapped categories). n= total annotation above each column.

    Parameters:
        df: input DataFrame.
        month, category, share, n, facet: column names.
        category_colors: dict mapping category → hex. Default: INTRODUCER_CATEGORY_COLORS.
        title, xlabel: figure labels.
        annotate_n: if True (default), annotate the total n above each column.

    Returns:
        plotly.graph_objects.Figure (single panel, or 2×2 if facet is given).

    Example:
        >>> df = pd.read_csv("stacked_100pct.csv")
        >>> fig = stacked_bar_100pct_monthly_2x2(df, title="Introducer mix")
    """
    require_columns(df, [month, category, share], who="stacked_bar_100pct_monthly_2x2")
    if annotate_n:
        resolve_n_column(df, n, annotate_n=True)
    colors = category_colors or INTRODUCER_CATEGORY_COLORS

    if facet:
        require_columns(df, [facet], who="stacked_bar_100pct_monthly_2x2 (facet)")
        facets = sorted(df[facet].unique())
        if len(facets) != 4:
            raise ValueError(
                f"facet must have exactly 4 distinct values for 2×2 layout, got {facets}"
            )
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=facets,
            vertical_spacing=0.18,
            horizontal_spacing=0.10,
        )
        for idx, f in enumerate(facets):
            r, c = idx // 2 + 1, idx % 2 + 1
            sub = df[df[facet] == f]
            _add_stacked_bars(
                fig, sub, month=month, category=category, share=share, n=n,
                colors=colors, annotate_n=annotate_n,
                row=r, col=c, show_legend=(idx == 0),
            )
            fig.update_yaxes(ticksuffix="%", range=[0, 112], row=r, col=c)
    else:
        fig = go.Figure()
        _add_stacked_bars(
            fig, df, month=month, category=category, share=share, n=n,
            colors=colors, annotate_n=annotate_n,
        )
        fig.update_yaxes(ticksuffix="%", range=[0, 112])

    fig.update_layout(
        title=title or "Volume mix over time",
        xaxis_title=xlabel,
        barmode="stack",
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


def _add_stacked_bars(
    fig: go.Figure,
    sub: pd.DataFrame,
    *,
    month: str,
    category: str,
    share: str,
    n: str | None,
    colors: dict[str, str],
    annotate_n: bool,
    row: int | None = None,
    col: int | None = None,
    show_legend: bool = True,
) -> None:
    """Internal helper: add stacked-bar traces and optional n= annotations."""
    cats = list(sub[category].drop_duplicates())
    for cat in cats:
        cat_sub = sub[sub[category] == cat].sort_values(month)
        color = colors.get(cat, UNKNOWN_INTRODUCER_COLOR)
        trace = go.Bar(
            x=cat_sub[month],
            y=cat_sub[share],
            name=str(cat),
            marker_color=color,
            text=[f"{v:.0f}%" if v >= 5 else "" for v in cat_sub[share]],
            textposition="inside",
            showlegend=show_legend,
            hovertemplate=f"<b>{cat}</b> %{{x}}: %{{y:.1f}}%<extra></extra>",
        )
        if row is not None and col is not None:
            fig.add_trace(trace, row=row, col=col)
        else:
            fig.add_trace(trace)

    if annotate_n and n in sub.columns:
        n_per_month = sub.drop_duplicates(subset=[month])[[month, n]].sort_values(month)
        for x_val, n_val in zip(n_per_month[month], n_per_month[n], strict=False):
            kwargs = dict(
                x=x_val, y=104, text=f"n={int(n_val)}",
                showarrow=False, font=dict(size=8, color="#666"),
            )
            if row is not None and col is not None:
                fig.add_annotation(**kwargs, row=row, col=col)
            else:
                fig.add_annotation(**kwargs)

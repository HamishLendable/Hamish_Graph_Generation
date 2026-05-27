"""Specialised chart styles — granular cohort grid + horizontal funnel.

These don't fit cleanly into lines / bars / heatmaps / scatters / distributions
but earn their place in the v0.1 catalogue.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from motor_graphs.style import apply_auto_legend
from motor_graphs.style.palette import ACTUAL, COHORT_COLORS, EXPECTED, GRADE_COLOURS

from ._shared import (
    SmallSampleMode,
    add_pound_weighted_footnote,
    opacity_for_n,
    require_columns,
    resolve_n_column,
)


def cohort_grid_grade_x_period(
    df: pd.DataFrame,
    *,
    grade: str = "grade",
    period: str = "period",
    mob: str = "mob",
    actual: str = "actual",
    model: str = "model",
    deviation_text: str = "deviation_text",
    n: str | None = "n",
    title: str | None = None,
    y_tickformat: str = ".1%",
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """M×N grid of tiny actual-vs-model lines per (grade, period) cell.

    Use this when:
        - You want a single sheet-of-paper view of how every cohort (grade ×
          period) is tracking against the model curve.
        - You need to spot outlier cells quickly — the "Dev: ±X%" annotation
          in the top-right corner of each cell makes deviation scannable.

    Data shape:
        Long/tidy DataFrame, one row per (grade, period, mob):
            grade           (str)   — risk grade label (rows in the grid)
            period          (str)   — period / cohort label (columns in the grid)
            mob             (int)   — months on book (x axis within each cell)
            actual          (float) — actual rate at that MOB (decimal)
            model           (float) — model / expected rate at that MOB (decimal)
            deviation_text  (str)   — pre-computed annotation per cell
                                       (e.g. "Dev: +2.3%"). Same value across MOBs.
            n               (int, opt) — sample size for the cell (required if
                                          annotate_n=True; constant across MOBs).

    Style:
        Row = grade (sorted by GRADE_COLOURS), col = period (sorted ascending).
        Each cell holds a tiny line chart: blue solid actual + red dashed model.
        Top-right of each cell shows the pre-computed `deviation_text`. Bottom-
        right shows "n=…" in small grey font (if annotate_n=True). Subplot
        titles blank to save space; row labels on left, col labels on top.

    Parameters:
        df: input DataFrame.
        grade, period, mob, actual, model, deviation_text, n: column names.
        title: figure title.
        y_tickformat: tick format string (default ".1%").
        annotate_n: if True (default), show n= in bottom-right of each cell.
        small_sample_handling: "show" (default), "fade", or "suppress".

    Returns:
        plotly.graph_objects.Figure with M×N subplots and 2 traces per cell.

    Example:
        >>> df = pd.read_csv("cohort_grid_grade_x_period.csv")
        >>> fig = cohort_grid_grade_x_period(df, title="Cohort grid — VT")
    """
    require_columns(
        df,
        [grade, period, mob, actual, model, deviation_text],
        who="cohort_grid_grade_x_period",
    )
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    # Row order: GRADE_COLOURS order, filtered to those present
    present_grades = set(df[grade].unique())
    grades = [g for g in GRADE_COLOURS.keys() if g in present_grades]
    for g in df[grade].drop_duplicates():
        if g not in grades:
            grades.append(g)
    # Column order: ascending period
    periods = sorted(df[period].drop_duplicates().tolist(), key=str)

    n_rows = len(grades)
    n_cols = len(periods)
    if n_rows == 0 or n_cols == 0:
        raise ValueError(
            f"cohort_grid_grade_x_period needs >=1 grade and >=1 period; "
            f"got {n_rows} grades and {n_cols} periods"
        )

    fig = make_subplots(
        rows=n_rows,
        cols=n_cols,
        shared_xaxes=True,
        shared_yaxes=True,
        vertical_spacing=0.05,
        horizontal_spacing=0.03,
        row_titles=[str(g) for g in grades],
        column_titles=[str(p) for p in periods],
    )

    first_cell = True
    for r, g in enumerate(grades, start=1):
        for c, p in enumerate(periods, start=1):
            sub = df[(df[grade] == g) & (df[period] == p)].sort_values(mob)
            if sub.empty:
                continue
            ns = sub[n_col].tolist() if n_col else None
            opacities = (
                opacity_for_n(ns, mode=small_sample_handling) if ns else [1.0] * len(sub)
            )
            # If all suppressed, skip the cell drawing but still annotate.
            visible = any(o > 0 for o in opacities)

            if visible:
                fig.add_trace(
                    go.Scatter(
                        x=sub[mob],
                        y=sub[actual],
                        mode="lines",
                        name="Actual",
                        line=dict(color=ACTUAL, width=1.5),
                        showlegend=first_cell,
                        hovertemplate=(
                            f"<b>{g} | {p}</b><br>MOB %{{x}}: %{{y:{y_tickformat[1:]}}}"
                            "<extra>Actual</extra>"
                        ),
                    ),
                    row=r,
                    col=c,
                )
                fig.add_trace(
                    go.Scatter(
                        x=sub[mob],
                        y=sub[model],
                        mode="lines",
                        name="Model",
                        line=dict(color=EXPECTED, width=1.5, dash="dash"),
                        showlegend=first_cell,
                        hovertemplate=(
                            f"<b>{g} | {p}</b><br>MOB %{{x}}: %{{y:{y_tickformat[1:]}}}"
                            "<extra>Model</extra>"
                        ),
                    ),
                    row=r,
                    col=c,
                )
                first_cell = False

            # Plotly: subplot index 1 → 'x'/'y'; index N>1 → 'xN'/'yN'.
            idx = (r - 1) * n_cols + c
            xref = f"x{idx} domain" if idx > 1 else "x domain"
            yref = f"y{idx} domain" if idx > 1 else "y domain"

            # Deviation annotation — top-right of each cell
            dev = sub[deviation_text].dropna()
            dev_text = str(dev.iloc[0]) if len(dev) else ""
            if dev_text:
                fig.add_annotation(
                    xref=xref,
                    yref=yref,
                    x=0.98,
                    y=0.98,
                    text=dev_text,
                    showarrow=False,
                    xanchor="right",
                    yanchor="top",
                    font=dict(size=9, color="#333"),
                )

            # n= annotation — bottom-right of each cell
            if annotate_n and n_col and ns:
                fig.add_annotation(
                    xref=xref,
                    yref=yref,
                    x=0.98,
                    y=0.02,
                    text=f"n={int(ns[0])}",
                    showarrow=False,
                    xanchor="right",
                    yanchor="bottom",
                    font=dict(size=8, color="grey"),
                )

            fig.update_yaxes(tickformat=y_tickformat, tickfont=dict(size=8), row=r, col=c)
            fig.update_xaxes(tickfont=dict(size=8), row=r, col=c)

    # Make row / column titles compact
    for ann in fig.layout.annotations:
        if ann.text in [str(g) for g in grades] or ann.text in [str(p) for p in periods]:
            ann.font = dict(size=10, color="#333")

    fig.update_layout(
        title=title or "Cohort grid — grade × period",
        font=dict(size=9),
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


def funnel_horizontal(
    df: pd.DataFrame,
    *,
    stage: str = "stage",
    count: str = "count",
    n: str | None = None,
    title: str | None = None,
    value_fmt: str = ",.0f",
    show_pct_of_top: bool = True,
    show_dropoff: bool = True,
    annotate_n: bool = True,
) -> go.Figure:
    """Horizontal funnel — app → quote → originated stage counts.

    Use this when:
        - You want to visualise how volume drops through a multi-stage
          process (application → underwrite → quote → accepted → originated).
        - You want both the absolute count per stage AND the drop-off
          percentage between adjacent stages.

    Data shape:
        Long/tidy DataFrame, one row per stage (in funnel order, top → bottom):
            stage (str) — stage name (used as the bar label)
            count (int) — count at that stage
            n     (int, opt) — same as count for compatibility; ignored if
                               None (the count column itself is the n).

    Style:
        Horizontal funnel (go.Funnel). Stages stacked descending — top of the
        funnel is the first row (widest bar), bottom is the last (narrowest).
        Each bar labeled with the count (formatted via `value_fmt`). If
        show_pct_of_top, "(X% of top)" is appended. If show_dropoff, "↓ N% drop"
        annotations sit between adjacent stages. Colours: COHORT_COLORS cycle.

    Parameters:
        df: input DataFrame (rows already in funnel order).
        stage, count: column names.
        n: optional duplicate-of-count column name; pass None (default) to
            treat `count` itself as the sample size.
        title: figure title.
        value_fmt: Python format string for count labels (default ",.0f").
        show_pct_of_top: append "(X% of top)" to each stage label.
        show_dropoff: add "↓ N% drop" annotations between adjacent stages.
        annotate_n: if True (default), ensures counts are visible on each bar.

    Returns:
        plotly.graph_objects.Figure with one Funnel trace.

    Example:
        >>> df = pd.read_csv("funnel_horizontal.csv")
        >>> fig = funnel_horizontal(df, title="EV quote → sale funnel")
    """
    require_columns(df, [stage, count], who="funnel_horizontal")
    # n column is optional and treated as the count itself; only resolve if explicit.
    if n is not None and annotate_n:
        resolve_n_column(df, n, annotate_n=True)

    stages = df[stage].astype(str).tolist()
    counts = df[count].astype(float).tolist()
    if not counts:
        raise ValueError("funnel_horizontal needs at least one stage")
    top = counts[0] if counts[0] else 1.0

    # Build per-bar text label
    fmt = "{:" + value_fmt + "}"
    if show_pct_of_top:
        bar_text = [
            f"{fmt.format(c)} ({(c / top * 100):.0f}% of top)" for c in counts
        ]
    else:
        bar_text = [fmt.format(c) for c in counts]

    colors = [COHORT_COLORS[i % len(COHORT_COLORS)] for i in range(len(stages))]

    fig = go.Figure(
        go.Funnel(
            y=stages,
            x=counts,
            text=bar_text,
            textposition="inside",
            textinfo="text",
            marker=dict(color=colors),
            connector=dict(line=dict(color="#999", dash="dot", width=1)),
            hovertemplate="<b>%{y}</b><br>count=%{x}<extra></extra>",
        )
    )

    if show_dropoff and len(counts) > 1:
        for i in range(1, len(counts)):
            prev, cur = counts[i - 1], counts[i]
            drop_pct = (1 - cur / prev) * 100 if prev else 0.0
            # Anchor between the i-1 and i stage rows
            fig.add_annotation(
                xref="paper",
                yref="y",
                x=1.02,
                y=i - 0.5,
                text=f"↓ {drop_pct:.0f}% drop",
                showarrow=False,
                xanchor="left",
                yanchor="middle",
                font=dict(size=10, color="grey"),
            )

    fig.update_layout(
        title=title or "Funnel — stage counts",
        yaxis=dict(autorange="reversed"),
        showlegend=False,
        margin=dict(r=150 if show_dropoff else 80),
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig

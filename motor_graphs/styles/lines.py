"""Line-based chart styles."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from motor_graphs.style import apply_auto_legend
from motor_graphs.style.palette import ACTUAL, COHORT_COLORS, EXPECTED

from ._shared import (
    SmallSampleMode,
    add_pound_weighted_footnote,
    opacity_for_n,
    require_columns,
    resolve_n_column,
)


def dq_2x2_actual_vs_expected(
    df: pd.DataFrame,
    *,
    cohort: str = "cohort",
    metric: str = "metric",
    actual: str = "actual",
    expected: str = "expected",
    n: str | None = "n",
    title: str | None = None,
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """2×2 grid of line subplots — actual vs expected rate per DQ metric.

    Use this when:
        - You have rate-over-cohort data for exactly 4 DQ metrics (30+/60+/90+
          at various MOBs) and want to compare actual vs benchmark per metric.
        - You want a quick visual scan of divergence between blue solid (actual)
          and red dashed (expected) across multiple horizons in one figure.

    Data shape:
        Long/tidy DataFrame, one row per (cohort, metric):
            cohort   (str or date) — the cohort label (e.g. "2024-01", "2024-Q2")
            metric   (str)         — exactly 4 distinct values, one per subplot
            actual   (float)       — actual rate (decimal, e.g. 0.018 for 1.8%)
            expected (float)       — expected/benchmark rate
            n        (int, opt)    — sample size; required if annotate_n=True

    Style:
        2×2 subplots, one per metric (sorted alphabetically). Each subplot:
        - Blue (#1f77b4) solid 2-px line for actual.
        - Red (#d62728) dashed 2-px line for expected.
        - n= annotation on the last actual point (when annotate_n=True).
        - Y-axis as percentages (.1%).

    Parameters:
        df: input DataFrame.
        cohort, metric, actual, expected, n: column names.
        title: figure title (defaults to "DQ actual vs expected").
        annotate_n: if True (default), annotate n= on the last actual point per subplot.
        small_sample_handling: "show" (default), "fade", or "suppress" — fade
            point opacity below n=200 / drop entirely below n=50.

    Returns:
        plotly.graph_objects.Figure with 8 traces (4 metrics × 2 series).

    Example:
        >>> df = pd.read_csv("dq_2x2.csv")
        >>> fig = dq_2x2_actual_vs_expected(df, title="Motor DQ — Apr 2026")
    """
    require_columns(df, [cohort, metric, actual, expected], who="dq_2x2_actual_vs_expected")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    metrics = sorted(df[metric].unique())
    if len(metrics) != 4:
        raise ValueError(
            f"dq_2x2_actual_vs_expected expects exactly 4 metrics, got {len(metrics)}: {metrics}"
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

        if annotate_n and n_col and ns and opacities[-1] > 0:
            fig.add_annotation(
                x=sub[cohort].iloc[-1],
                y=sub[actual].iloc[-1],
                text=f"n={ns[-1]}",
                showarrow=False,
                yshift=14,
                xshift=-2,
                font=dict(size=9, color="grey"),
                xanchor="right",
                row=r, col=c,
            )

    fig.update_layout(title=title or "DQ actual vs expected")
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


def cohort_lines_vs_mob(
    df: pd.DataFrame,
    *,
    cohort: str = "cohort",
    mob: str = "mob",
    y: str = "rate",
    expected: str | None = "expected",
    n: str | None = "n",
    title: str | None = None,
    xlabel: str = "MOB",
    ylabel: str = "Rate",
    y_tickformat: str = ".1%",
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """One coloured line per cohort vs MOB, with optional dashed expected overlay.

    Use this when:
        - You want to track a cumulative rate (VT, prepayment, gross default)
          for each cohort separately, against months-on-book.
        - You want to spot whether more recent cohorts are diverging from older
          ones, and from a benchmark curve.

    Data shape:
        Long/tidy DataFrame, one row per (cohort, mob):
            cohort    (str or date) — cohort label (e.g. "2024-01", "2024-Q2")
            mob       (int)         — months on book, integer
            rate      (float)       — cumulative rate at that MOB (decimal)
            expected  (float, opt)  — single expected curve; same value across cohorts
                                       at a given MOB. Pass expected=None to disable.
            n         (int,   opt)  — cohort size; required if annotate_n=True.
                                       Same value across MOBs for a given cohort.

    Style:
        Single panel. Each cohort gets its next colour in COHORT_COLORS (positional,
        so cohort-N matches across charts). Expected drawn as a red dashed line.
        n= annotation on the last (highest-MOB) point per cohort. Legend
        auto-flips to vertical-right when there are >6 cohorts.

    Parameters:
        df: input DataFrame.
        cohort, mob, y, expected, n: column names. `expected=None` disables benchmark.
        title, xlabel, ylabel: figure labels.
        y_tickformat: tick format string (default ".1%").
        annotate_n: if True (default), annotate n= on the last point per cohort.
        small_sample_handling: see dq_2x2_actual_vs_expected.

    Returns:
        plotly.graph_objects.Figure with one trace per cohort plus optionally one Expected trace.

    Example:
        >>> df = pd.read_csv("cohort_lines.csv")
        >>> fig = cohort_lines_vs_mob(df, ylabel="VT rate", title="Cumulative VT")
    """
    require_columns(df, [cohort, mob, y], who="cohort_lines_vs_mob")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    cohorts = list(df[cohort].drop_duplicates())
    fig = go.Figure()
    for i, c in enumerate(cohorts):
        sub = df[df[cohort] == c].sort_values(mob).reset_index(drop=True)
        ns = sub[n_col].tolist() if n_col else None
        opacities = opacity_for_n(ns, mode=small_sample_handling) if ns else [1.0] * len(sub)
        color = COHORT_COLORS[i % len(COHORT_COLORS)]

        fig.add_trace(
            go.Scatter(
                x=sub[mob],
                y=sub[y],
                mode="lines+markers",
                name=str(c),
                line=dict(color=color, width=2),
                marker=dict(size=4, opacity=opacities),
                customdata=ns if ns else None,
                hovertemplate=(
                    f"<b>{c}</b><br>MOB %{{x}}: %{{y:{y_tickformat[1:]}}}"
                    + (" (n=%{customdata})" if ns else "")
                    + "<extra></extra>"
                ),
            )
        )

        if annotate_n and n_col and ns and opacities[-1] > 0:
            # Stagger yshift across cohorts so labels at the right edge don't overlap
            # when multiple cohorts terminate at the same MOB.
            yshift = 10 + (i % 4) * 7
            fig.add_annotation(
                x=sub[mob].iloc[-1],
                y=sub[y].iloc[-1],
                text=f"n={ns[-1]}",
                showarrow=False,
                yshift=yshift,
                xshift=4,
                font=dict(size=9, color="grey"),
                xanchor="left",
            )

    if expected is not None and expected in df.columns:
        # Expected curve: one row per MOB (we use the first cohort's expected values,
        # since the curve is the same across cohorts in our convention).
        exp_df = df.drop_duplicates(subset=[mob]).sort_values(mob)
        fig.add_trace(
            go.Scatter(
                x=exp_df[mob],
                y=exp_df[expected],
                mode="lines",
                name="Expected",
                line=dict(color=EXPECTED, width=2, dash="dash"),
                hovertemplate=f"Expected MOB %{{x}}: %{{y:{y_tickformat[1:]}}}<extra></extra>",
            )
        )

    fig.update_layout(
        title=title or "Cohort rate vs MOB",
        xaxis_title=xlabel,
        yaxis=dict(title=ylabel, tickformat=y_tickformat),
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig

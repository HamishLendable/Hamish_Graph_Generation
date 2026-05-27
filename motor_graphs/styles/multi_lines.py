"""Multi-line chart styles (batch 5b-b).

Five line-based primitives that extend the v0.1 catalogue:

* ``lines_1x2_funnel_by_introducer``    — 1×2 subplots, one line per introducer
* ``lines_with_overall_highlight``      — multi-line + bold "Overall" overlay
* ``segment_compare_2x2_with_gap``      — 2×2 generic two-segment compare (rate +
  raw gap + grade mix + mix-adjusted gap). Works for BEV-vs-ROB, Carrera-vs-Torino,
  dealer-vs-non-dealer, or any other binary subpopulation cut.
* ``lines_funnel_by_introducer_1x1``    — single-panel variant of #1
* ``line_with_ci_band``                 — line + filled 95% CI band per group
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from motor_graphs.style import apply_auto_legend
from motor_graphs.style.palette import (
    ACTUAL,
    ADJUSTED,
    CI_BAND_OPACITY,
    COHORT_COLORS,
    EXPECTED,
    GRADE_COLOURS,
    INTRODUCER_CATEGORY_COLORS,
    OVERLAY_BLACK,
    SECONDARY,
    UNKNOWN_INTRODUCER_COLOR,
    hex_to_rgba,
)

from ._shared import (
    SmallSampleMode,
    add_pound_weighted_footnote,
    opacity_for_n,
    require_columns,
    resolve_n_column,
)


def _introducer_color(name: str) -> str:
    """Return the palette colour for an introducer name, falling back to grey."""
    return INTRODUCER_CATEGORY_COLORS.get(name, UNKNOWN_INTRODUCER_COLOR)


def _segment_color(name: str, idx: int) -> str:
    """Choose a palette colour for a generic segment.

    If the name matches a known risk grade, use ``GRADE_COLOURS``; if it matches
    a known introducer category, use ``INTRODUCER_CATEGORY_COLORS``; otherwise
    fall back to the positional ``COHORT_COLORS`` cycle.
    """
    if name in GRADE_COLOURS:
        return GRADE_COLOURS[name]
    if name in INTRODUCER_CATEGORY_COLORS:
        return INTRODUCER_CATEGORY_COLORS[name]
    return COHORT_COLORS[idx % len(COHORT_COLORS)]


def lines_1x2_funnel_by_introducer(
    df: pd.DataFrame,
    *,
    month: str = "month",
    introducer: str = "introducer",
    y_left: str = "quote_rate",
    y_right: str = "sale_rate",
    n: str | None = "n",
    title: str | None = None,
    ylabel_left: str = "Quote rate",
    ylabel_right: str = "Quote-to-sale rate",
    y_tickformat: str = ".1%",
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """1×2 line subplots — one line per introducer in each panel.

    Use this when:
        - You want to compare two conversion-funnel rates (e.g. quote rate and
          quote-to-sale rate) across introducer categories over time.
        - You need a side-by-side view so movement in the upstream funnel stage
          can be visually tied to movement in the downstream stage.

    Data shape:
        Long/tidy DataFrame, one row per (month, introducer):
            month       (str or date) — origination month label
            introducer  (str)         — introducer category (matches keys of
                                          INTRODUCER_CATEGORY_COLORS where possible)
            quote_rate  (float)       — left-panel rate (decimal)
            sale_rate   (float)       — right-panel rate (decimal)
            n           (int, opt)    — sample size; required if annotate_n=True

    Style:
        ``rows=1, cols=2`` subplots. One coloured 2-px line per introducer in
        each panel, using ``INTRODUCER_CATEGORY_COLORS`` (falls back to grey).
        n= annotation on the last point per introducer in each panel. Y-axis
        formatted via ``y_tickformat`` (default ".1%").

    Parameters:
        df: input DataFrame.
        month, introducer, y_left, y_right, n: column names.
        title: figure title (defaults to "Funnel rates by introducer").
        ylabel_left, ylabel_right: per-panel y-axis labels.
        y_tickformat: tick format for both y-axes (default ".1%").
        annotate_n: if True (default), annotate n= on the last point per series
            in each panel.
        small_sample_handling: "show" (default), "fade", or "suppress" — fade
            point opacity below n=200 / drop entirely below n=50.

    Returns:
        plotly.graph_objects.Figure with one Scatter trace per introducer per
        panel (2 × number_of_introducers traces).

    Example:
        >>> df = pd.read_csv("lines_1x2_funnel_by_introducer.csv")
        >>> fig = lines_1x2_funnel_by_introducer(df, title="EV funnel")
    """
    require_columns(
        df,
        [month, introducer, y_left, y_right],
        who="lines_1x2_funnel_by_introducer",
    )
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    introducers = list(df[introducer].drop_duplicates())
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(ylabel_left, ylabel_right),
        horizontal_spacing=0.10,
    )

    panels = (
        (1, y_left, y_tickformat, ylabel_left),
        (2, y_right, y_tickformat, ylabel_right),
    )

    for panel_idx, y_col, tickfmt, _label in panels:
        for _i, intro in enumerate(introducers):
            sub = df[df[introducer] == intro].sort_values(month).reset_index(drop=True)
            if sub.empty:
                continue
            ns = sub[n_col].tolist() if n_col else None
            opacities = (
                opacity_for_n(ns, mode=small_sample_handling)
                if ns
                else [1.0] * len(sub)
            )
            color = _introducer_color(str(intro))

            fig.add_trace(
                go.Scatter(
                    x=sub[month],
                    y=sub[y_col],
                    mode="lines+markers",
                    name=str(intro),
                    legendgroup=str(intro),
                    showlegend=(panel_idx == 1),
                    line=dict(color=color, width=2),
                    marker=dict(size=5, opacity=opacities),
                    customdata=ns if ns else None,
                    hovertemplate=(
                        f"<b>{intro}</b><br>%{{x}}: %{{y:{tickfmt[1:]}}}"
                        + (" (n=%{customdata})" if ns else "")
                        + "<extra></extra>"
                    ),
                ),
                row=1,
                col=panel_idx,
            )

            if annotate_n and n_col and ns and opacities[-1] > 0:
                fig.add_annotation(
                    x=sub[month].iloc[-1],
                    y=sub[y_col].iloc[-1],
                    text=f"n={int(ns[-1])}",
                    showarrow=False,
                    yshift=12,
                    xshift=-2,
                    font=dict(size=9, color="grey"),
                    xanchor="right",
                    row=1,
                    col=panel_idx,
                )

        fig.update_yaxes(tickformat=tickfmt, row=1, col=panel_idx)
        fig.update_xaxes(tickangle=-30, row=1, col=panel_idx)

    fig.update_yaxes(title_text=ylabel_left, row=1, col=1)
    fig.update_yaxes(title_text=ylabel_right, row=1, col=2)
    fig.update_layout(title=title or "Funnel rates by introducer")
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


def lines_with_overall_highlight(
    df: pd.DataFrame,
    *,
    x: str = "month",
    group: str = "segment",
    y: str = "rate",
    overall_label: str = "Overall",
    n: str | None = "n",
    title: str | None = None,
    ylabel: str = "Rate",
    y_tickformat: str = ".1%",
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """Multi-line single panel + bold "Overall" portfolio overlay.

    Use this when:
        - You want to plot a rate per segment (grade, channel, vintage) and also
          show the portfolio-wide average prominently as a reference line.
        - The "Overall" series should visually dominate so the reader can
          immediately see whether a segment is above or below the book.

    Data shape:
        Long/tidy DataFrame, one row per (x, group):
            x       (str or date) — typically origination month
            group   (str)         — segment label; one of these MUST match
                                       ``overall_label`` to be drawn bold/black
            rate    (float)       — value to plot (decimal)
            n       (int, opt)    — sample size; required if annotate_n=True

    Style:
        Single panel. Each segment is a 2-px coloured line — colour picked from
        ``GRADE_COLOURS`` / ``INTRODUCER_CATEGORY_COLORS`` if the segment name
        is a known key, else from positional ``COHORT_COLORS``. The "Overall"
        series (group == ``overall_label``) is drawn as a 4-px ``OVERLAY_BLACK``
        line on top, with a slightly larger marker. n= annotation on the last
        point per segment.

    Parameters:
        df: input DataFrame.
        x, group, y, n: column names.
        overall_label: value of ``group`` that identifies the bold overlay.
        title: figure title (defaults to "Rate by segment vs Overall").
        ylabel: y-axis label.
        y_tickformat: tick format string (default ".1%").
        annotate_n: if True (default), annotate n= on the last point per segment.
        small_sample_handling: see ``lines_1x2_funnel_by_introducer``.

    Returns:
        plotly.graph_objects.Figure — one Scatter per segment plus one bold
        Overall trace drawn last (on top).

    Example:
        >>> df = pd.read_csv("lines_with_overall_highlight.csv")
        >>> fig = lines_with_overall_highlight(df, title="90+@9 by grade")
    """
    require_columns(df, [x, group, y], who="lines_with_overall_highlight")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    groups = list(df[group].drop_duplicates())
    # Draw the Overall last so it sits on top of the segment lines.
    non_overall = [g for g in groups if g != overall_label]
    ordered = non_overall + ([overall_label] if overall_label in groups else [])

    fig = go.Figure()
    for i, seg in enumerate(ordered):
        sub = df[df[group] == seg].sort_values(x).reset_index(drop=True)
        if sub.empty:
            continue
        ns = sub[n_col].tolist() if n_col else None
        opacities = (
            opacity_for_n(ns, mode=small_sample_handling)
            if ns
            else [1.0] * len(sub)
        )

        is_overall = seg == overall_label
        if is_overall:
            color = OVERLAY_BLACK
            width = 4
            marker_size = 7
        else:
            color = _segment_color(str(seg), i)
            width = 2
            marker_size = 5

        fig.add_trace(
            go.Scatter(
                x=sub[x],
                y=sub[y],
                mode="lines+markers",
                name=str(seg),
                line=dict(color=color, width=width),
                marker=dict(size=marker_size, opacity=opacities),
                customdata=ns if ns else None,
                hovertemplate=(
                    f"<b>{seg}</b><br>%{{x}}: %{{y:{y_tickformat[1:]}}}"
                    + (" (n=%{customdata})" if ns else "")
                    + "<extra></extra>"
                ),
            )
        )

        if annotate_n and n_col and ns and opacities[-1] > 0:
            fig.add_annotation(
                x=sub[x].iloc[-1],
                y=sub[y].iloc[-1],
                text=f"n={int(ns[-1])}",
                showarrow=False,
                yshift=12,
                xshift=4,
                font=dict(
                    size=10 if is_overall else 9,
                    color="black" if is_overall else "grey",
                ),
                xanchor="left",
            )

    fig.update_layout(
        title=title or "Rate by segment vs Overall",
        xaxis_title=x,
        yaxis=dict(title=ylabel, tickformat=y_tickformat),
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


def segment_compare_2x2_with_gap(
    df: pd.DataFrame,
    *,
    month: str = "month",
    a_col: str = "a",
    b_col: str = "b",
    adjusted_col: str = "b_adj",
    gap_col: str = "gap",
    a_good_share_col: str = "a_good_share",
    b_good_share_col: str = "b_good_share",
    n: str | None = "n",
    title: str | None = None,
    a_label: str = "Segment A",
    b_label: str = "Segment B",
    adjusted_label: str = "Segment B at A's mix",
    good_band_label: str = "A-E",
    risky_band_label: str = "F+",
    y_tickformat: str = ".1%",
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """2×2 generic two-segment compare: rate, raw gap, grade-mix, mix-adjusted gap.

    Use this when:
        - You have two subpopulation cuts of the book (BEV vs ROB, Carrera vs
          Torino, dealer vs non-dealer, co-applicant vs sole, etc.) and want to
          see both the underlying-rate gap AND whether it's driven by a
          different risk-grade mix.
        - You want one figure that answers: "is segment A's rate worse because
          its loans are worse, or because it has more risky-grade loans?"

    Data shape:
        Long/tidy DataFrame, one row per month with all metrics on the row:
            month         (str or date) — period label
            a             (float)        — segment A rate (decimal)
            b             (float)        — segment B rate (decimal)
            b_adj         (float)        — segment B rate reweighted to segment A's mix
            gap           (float, opt)   — raw gap (a − b) in pp; computed if absent
            a_good_share  (float)        — share of "good" grades in A (decimal 0-1)
            b_good_share  (float)        — share of "good" grades in B (decimal 0-1)
            n             (int, opt)     — sample size; required if annotate_n=True

        Note: any binary grade split works — "good" defaults to A-E and "risky"
        to F+ via the ``good_band_label`` / ``risky_band_label`` kwargs. Risky
        share is computed as ``1 − good_share`` per segment.

    Style:
        ``rows=2, cols=2`` grid:

        * (1,1) TOP-LEFT — 3-line rate panel: A (``ACTUAL`` blue), B (``SECONDARY``
          orange), B-at-A-mix (``ADJUSTED`` green, dashed). n= on last point.
        * (1,2) TOP-RIGHT — bar panel of raw gap (a − b) in pp, ``EXPECTED`` red.
        * (2,1) BOTTOM-LEFT — horizontal stacked bars showing grade mix per
          segment: good band (``ACTUAL`` blue) + risky band (``EXPECTED`` red).
          Shares are averaged across the period so this is a single snapshot.
        * (2,2) BOTTOM-RIGHT — line of mix-adjusted gap (a − b_adj) in pp,
          ``ADJUSTED`` green.

        Reading guide: if (1,2) shows a big gap and (2,2) shows a small one, the
        rate gap is largely a MIX effect — (2,1) will show why (segment A has
        more "good" grades or fewer "risky" ones).

    Parameters:
        df: input DataFrame.
        month, a_col, b_col, adjusted_col, gap_col, a_good_share_col,
            b_good_share_col, n: column names.
        title: figure title.
        a_label, b_label, adjusted_label: legend labels for the three lines.
        good_band_label, risky_band_label: legend/tooltip labels for the grade
            mix stacked bars (defaults "A-E" and "F+").
        y_tickformat: tick format for the rate panel (default ".1%"); gap
            panels are pp; the grade-mix panel is %.
        annotate_n: if True (default), annotate n= on the last point per series.
        small_sample_handling: "show" / "fade" / "suppress".

    Returns:
        plotly.graph_objects.Figure with 7 traces (3 rate lines + 1 gap bar +
        2 grade-mix bars + 1 mix-adjusted gap line).

    Example:
        >>> df = pd.read_csv("segment_compare_2x2_with_gap.csv")
        >>> # BEV vs ROB
        >>> fig = segment_compare_2x2_with_gap(
        ...     df, a_col="bev", b_col="rob", adjusted_col="rob_adj",
        ...     a_label="BEV", b_label="Rest of book", adjusted_label="ROB at BEV mix",
        ...     title="BEV vs ROB — 90+@9",
        ... )
        >>> # Carrera vs Torino on the same chart shape
        >>> fig = segment_compare_2x2_with_gap(
        ...     df, a_col="carrera", b_col="torino", adjusted_col="torino_at_carrera_mix",
        ...     a_label="Carrera", b_label="Torino", adjusted_label="Torino at Carrera mix",
        ... )
    """
    require_columns(
        df,
        [month, a_col, b_col, adjusted_col, a_good_share_col, b_good_share_col],
        who="segment_compare_2x2_with_gap",
    )
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    df = df.sort_values(month).reset_index(drop=True)

    # Raw gap in pp; computed if not supplied.
    gap_pp = df[gap_col] if gap_col in df.columns else (df[a_col] - df[b_col]) * 100.0
    adjusted_gap_pp = (df[a_col] - df[adjusted_col]) * 100.0

    ns = df[n_col].tolist() if n_col else None
    opacities = (
        opacity_for_n(ns, mode=small_sample_handling) if ns else [1.0] * len(df)
    )

    # Period-averaged grade-mix shares (single snapshot per segment).
    a_good = float(df[a_good_share_col].mean())
    b_good = float(df[b_good_share_col].mean())
    a_risky = 1.0 - a_good
    b_risky = 1.0 - b_good

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            f"{a_label} vs {b_label}",
            f"Raw gap ({a_label} − {b_label})",
            f"Grade mix ({good_band_label} vs {risky_band_label})",
            f"Mix-adjusted gap ({a_label} − {adjusted_label})",
        ),
        vertical_spacing=0.20,
        horizontal_spacing=0.10,
    )

    # ----- (1,1) Rate compare lines ----------------------------------------
    fig.add_trace(
        go.Scatter(
            x=df[month], y=df[a_col], mode="lines+markers", name=a_label,
            line=dict(color=ACTUAL, width=2),
            marker=dict(size=5, opacity=opacities),
            customdata=ns if ns else None,
            hovertemplate=(
                f"<b>{a_label}</b> %{{x}}: %{{y:{y_tickformat[1:]}}}"
                + (" (n=%{customdata})" if ns else "")
                + "<extra></extra>"
            ),
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df[month], y=df[b_col], mode="lines+markers", name=b_label,
            line=dict(color=SECONDARY, width=2),
            marker=dict(size=5, opacity=opacities),
            hovertemplate=f"<b>{b_label}</b> %{{x}}: %{{y:{y_tickformat[1:]}}}<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df[month], y=df[adjusted_col], mode="lines+markers", name=adjusted_label,
            line=dict(color=ADJUSTED, width=2, dash="dash"),
            marker=dict(size=5, opacity=opacities, symbol="diamond"),
            hovertemplate=f"<b>{adjusted_label}</b> %{{x}}: %{{y:{y_tickformat[1:]}}}<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.update_yaxes(tickformat=y_tickformat, row=1, col=1)
    fig.update_xaxes(tickangle=-30, row=1, col=1)
    if annotate_n and n_col and ns and opacities[-1] > 0:
        fig.add_annotation(
            x=df[month].iloc[-1], y=df[a_col].iloc[-1],
            text=f"n={int(ns[-1])}", showarrow=False,
            yshift=12, xshift=-2, font=dict(size=9, color="grey"),
            xanchor="right", row=1, col=1,
        )

    # ----- (1,2) Raw gap bars ---------------------------------------------
    fig.add_trace(
        go.Bar(
            x=df[month], y=gap_pp, name="Gap (pp)",
            marker_color=EXPECTED, showlegend=False,
            hovertemplate="%{x}: %{y:.2f}pp<extra></extra>",
        ),
        row=1, col=2,
    )
    fig.update_yaxes(ticksuffix="pp", row=1, col=2)
    fig.update_xaxes(tickangle=-30, row=1, col=2)
    if annotate_n and n_col and ns and opacities[-1] > 0:
        fig.add_annotation(
            x=df[month].iloc[-1], y=float(gap_pp.iloc[-1]),
            text=f"n={int(ns[-1])}", showarrow=False,
            yshift=12, xshift=-2, font=dict(size=9, color="grey"),
            xanchor="right", row=1, col=2,
        )

    # ----- (2,1) Grade-mix horizontal stacked bars ------------------------
    fig.add_trace(
        go.Bar(
            y=[a_label, b_label],
            x=[a_good * 100, b_good * 100],
            name=good_band_label,
            orientation="h",
            marker_color=ACTUAL,
            text=[f"{a_good * 100:.0f}%", f"{b_good * 100:.0f}%"],
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate=f"%{{y}} · {good_band_label}: %{{x:.1f}}%<extra></extra>",
        ),
        row=2, col=1,
    )
    fig.add_trace(
        go.Bar(
            y=[a_label, b_label],
            x=[a_risky * 100, b_risky * 100],
            name=risky_band_label,
            orientation="h",
            marker_color=EXPECTED,
            text=[f"{a_risky * 100:.0f}%", f"{b_risky * 100:.0f}%"],
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate=f"%{{y}} · {risky_band_label}: %{{x:.1f}}%<extra></extra>",
        ),
        row=2, col=1,
    )
    fig.update_xaxes(range=[0, 100], ticksuffix="%", row=2, col=1)
    fig.update_yaxes(autorange="reversed", row=2, col=1)

    # ----- (2,2) Mix-adjusted gap line ------------------------------------
    fig.add_trace(
        go.Scatter(
            x=df[month], y=adjusted_gap_pp, mode="lines+markers",
            name="Mix-adjusted gap (pp)",
            line=dict(color=ADJUSTED, width=2),
            marker=dict(size=5, opacity=opacities),
            showlegend=False,
            hovertemplate="%{x}: %{y:.2f}pp<extra></extra>",
        ),
        row=2, col=2,
    )
    fig.update_yaxes(ticksuffix="pp", row=2, col=2)
    fig.update_xaxes(tickangle=-30, row=2, col=2)
    if annotate_n and n_col and ns and opacities[-1] > 0:
        fig.add_annotation(
            x=df[month].iloc[-1], y=float(adjusted_gap_pp.iloc[-1]),
            text=f"n={int(ns[-1])}", showarrow=False,
            yshift=12, xshift=-2, font=dict(size=9, color="grey"),
            xanchor="right", row=2, col=2,
        )

    fig.update_layout(
        title=title or f"{a_label} vs {b_label} — rate, mix, gap",
        barmode="stack",
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


def lines_funnel_by_introducer_1x1(
    df: pd.DataFrame,
    *,
    month: str = "month",
    introducer: str = "introducer",
    y: str = "rate",
    n: str | None = "n",
    title: str | None = None,
    ylabel: str = "Rate",
    y_tickformat: str = ".1%",
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """Single-panel variant of ``lines_1x2_funnel_by_introducer``.

    Use this when:
        - You only have a single funnel stage (e.g. EV quote→sale rate) and want
          to track it over time, broken out by introducer category.
        - The 1×2 variant would waste real estate on a missing second metric.

    Data shape:
        Long/tidy DataFrame, one row per (month, introducer):
            month       (str or date) — origination month label
            introducer  (str)         — introducer category
            rate        (float)       — value to plot (decimal)
            n           (int, opt)    — sample size; required if annotate_n=True

    Style:
        Single panel. One 2-px coloured line per introducer using
        ``INTRODUCER_CATEGORY_COLORS`` (falls back to grey for unknown
        categories). n= annotation on the last point per introducer.

    Parameters:
        df: input DataFrame.
        month, introducer, y, n: column names.
        title: figure title (defaults to "Rate by introducer").
        ylabel: y-axis label.
        y_tickformat: tick format string (default ".1%").
        annotate_n: if True (default), annotate n= on the last point per series.
        small_sample_handling: see ``lines_1x2_funnel_by_introducer``.

    Returns:
        plotly.graph_objects.Figure with one Scatter trace per introducer.

    Example:
        >>> df = pd.read_csv("lines_funnel_by_introducer_1x1.csv")
        >>> fig = lines_funnel_by_introducer_1x1(df, title="EV quote-to-sale")
    """
    require_columns(
        df,
        [month, introducer, y],
        who="lines_funnel_by_introducer_1x1",
    )
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    introducers = list(df[introducer].drop_duplicates())
    fig = go.Figure()
    for intro in introducers:
        sub = df[df[introducer] == intro].sort_values(month).reset_index(drop=True)
        if sub.empty:
            continue
        ns = sub[n_col].tolist() if n_col else None
        opacities = (
            opacity_for_n(ns, mode=small_sample_handling)
            if ns
            else [1.0] * len(sub)
        )
        color = _introducer_color(str(intro))

        fig.add_trace(
            go.Scatter(
                x=sub[month],
                y=sub[y],
                mode="lines+markers",
                name=str(intro),
                line=dict(color=color, width=2),
                marker=dict(size=5, opacity=opacities),
                customdata=ns if ns else None,
                hovertemplate=(
                    f"<b>{intro}</b><br>%{{x}}: %{{y:{y_tickformat[1:]}}}"
                    + (" (n=%{customdata})" if ns else "")
                    + "<extra></extra>"
                ),
            )
        )

        if annotate_n and n_col and ns and opacities[-1] > 0:
            fig.add_annotation(
                x=sub[month].iloc[-1],
                y=sub[y].iloc[-1],
                text=f"n={int(ns[-1])}",
                showarrow=False,
                yshift=12,
                xshift=4,
                font=dict(size=9, color="grey"),
                xanchor="left",
            )

    fig.update_layout(
        title=title or "Rate by introducer",
        xaxis_title=month,
        yaxis=dict(title=ylabel, tickformat=y_tickformat),
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


def line_with_ci_band(
    df: pd.DataFrame,
    *,
    x: str = "month",
    group: str = "group",
    y: str = "rate",
    ci_lower: str = "ci_lower",
    ci_upper: str = "ci_upper",
    n: str | None = "n",
    title: str | None = None,
    ylabel: str = "Rate",
    y_tickformat: str = ".1%",
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """One line per group + filled confidence-interval band.

    Use this when:
        - You want to plot a rate over time per group and show its uncertainty
          (95% CI, Wilson interval, bootstrap band) as a shaded region.
        - The CI bounds are precomputed upstream (this function does not infer
          them from n).

    Data shape:
        Long/tidy DataFrame, one row per (x, group):
            x           (str or date) — typically origination month
            group       (str)         — series label
            rate        (float)       — central estimate (decimal)
            ci_lower    (float)       — lower CI bound (decimal)
            ci_upper    (float)       — upper CI bound (decimal)
            n           (int, opt)    — sample size; required if annotate_n=True

    Style:
        Single panel. Each group:
        - One 2-px line in a positional ``COHORT_COLORS`` colour (parent trace,
          legend visible).
        - One filled CI band traced as a closed polygon (upper bound forward +
          lower bound reversed) with ``fill='toself'`` and fill colour
          ``hex_to_rgba(line_color, CI_BAND_OPACITY)``; band is excluded from
          the legend.
        n= annotation on the last point of each line.

    Parameters:
        df: input DataFrame.
        x, group, y, ci_lower, ci_upper, n: column names.
        title: figure title (defaults to "Rate with 95% confidence interval").
        ylabel: y-axis label.
        y_tickformat: tick format string (default ".1%").
        annotate_n: if True (default), annotate n= on the last point per group.
        small_sample_handling: see ``lines_1x2_funnel_by_introducer``.

    Returns:
        plotly.graph_objects.Figure with two traces per group (band, line).

    Example:
        >>> df = pd.read_csv("line_with_ci_band.csv")
        >>> fig = line_with_ci_band(df, title="90+@9 with 95% CI")
    """
    require_columns(
        df,
        [x, group, y, ci_lower, ci_upper],
        who="line_with_ci_band",
    )
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    groups = list(df[group].drop_duplicates())
    fig = go.Figure()
    for i, grp in enumerate(groups):
        sub = df[df[group] == grp].sort_values(x).reset_index(drop=True)
        if sub.empty:
            continue
        ns = sub[n_col].tolist() if n_col else None
        opacities = (
            opacity_for_n(ns, mode=small_sample_handling)
            if ns
            else [1.0] * len(sub)
        )
        color = COHORT_COLORS[i % len(COHORT_COLORS)]
        band_fill = hex_to_rgba(color, CI_BAND_OPACITY)

        x_vals = sub[x].tolist()
        upper = sub[ci_upper].tolist()
        lower = sub[ci_lower].tolist()

        # Band: upper forward + lower reversed → closed polygon.
        fig.add_trace(
            go.Scatter(
                x=x_vals + x_vals[::-1],
                y=upper + lower[::-1],
                fill="toself",
                fillcolor=band_fill,
                line=dict(color="rgba(0,0,0,0)"),
                mode="lines",
                name=f"{grp} CI",
                legendgroup=str(grp),
                showlegend=False,
                hoverinfo="skip",
            )
        )

        # Central line.
        fig.add_trace(
            go.Scatter(
                x=sub[x],
                y=sub[y],
                mode="lines+markers",
                name=str(grp),
                legendgroup=str(grp),
                showlegend=True,
                line=dict(color=color, width=2),
                marker=dict(size=5, opacity=opacities),
                customdata=ns if ns else None,
                hovertemplate=(
                    f"<b>{grp}</b><br>%{{x}}: %{{y:{y_tickformat[1:]}}}"
                    + (" (n=%{customdata})" if ns else "")
                    + "<extra></extra>"
                ),
            )
        )

        if annotate_n and n_col and ns and opacities[-1] > 0:
            fig.add_annotation(
                x=sub[x].iloc[-1],
                y=sub[y].iloc[-1],
                text=f"n={int(ns[-1])}",
                showarrow=False,
                yshift=12,
                xshift=4,
                font=dict(size=9, color="grey"),
                xanchor="left",
            )

    fig.update_layout(
        title=title or "Rate with 95% confidence interval",
        xaxis_title=x,
        yaxis=dict(title=ylabel, tickformat=y_tickformat),
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig

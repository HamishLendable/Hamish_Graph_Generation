"""Additional bar-based chart styles (Batch 5b-c).

Adds four primitives to the catalogue:

* ``stacked_bar_volume_2x2_with_rate_line`` (#9)
* ``bar_horizontal_top_n`` (#14)
* ``bar_plus_line_share_top_n`` (#15)
* ``waterfall_components_by_grade`` (#16)
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from motor_graphs.style import apply_auto_legend
from motor_graphs.style.palette import (
    ACTUAL,
    COHORT_COLORS,
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


def _split_format_prefix(fmt: str) -> tuple[str, str]:
    """Split a user-supplied format string into (literal prefix, spec).

    Examples:
        ``"£,.0f"``  → (``"£"``, ``",.0f"``)
        ``".1%"``    → (``""``,  ``".1%"``)
        ``",.0f"``   → (``""``,  ``",.0f"``)
    """
    spec_chars = set("0123456789+-.,#%efgdboxnEFGDBOXN ")
    for i, ch in enumerate(fmt):
        if ch in spec_chars:
            return fmt[:i], fmt[i:]
    return fmt, ""


def _format_value(value: float, fmt: str) -> str:
    """Format ``value`` allowing an optional non-spec prefix character.

    Python's standard format spec doesn't allow leading literal characters
    (e.g. ``"£,.0f"``), so we split off any leading non-format chars and
    prepend them to the formatted number.
    """
    prefix, real_spec = _split_format_prefix(fmt)
    if real_spec:
        return f"{prefix}{format(value, real_spec)}"
    return f"{prefix}{value}"


def stacked_bar_volume_2x2_with_rate_line(
    df: pd.DataFrame,
    *,
    month: str = "month",
    introducer: str = "introducer",
    count_col: str = "count",
    amount_col: str = "amount",
    quoted_col: str = "quoted_count",
    quote_rate_col: str = "quote_rate",
    sale_rate_col: str = "sale_rate",
    title: str | None = None,
    annotate_n: bool = True,
) -> go.Figure:
    """2×2 panel: three stacked-bar volume panels by introducer + one rate-line panel.

    Use this when:
        - You want a single "KPI dashboard" snapshot of origination volume,
          loaned £, quoted volume, and the book-level quote/sale rates side
          by side in one figure.

    Data shape:
        Long/tidy DataFrame, one row per (month, introducer):
            month          (str or date) — origination month label
            introducer     (str)         — introducer category (mapped via
                                           INTRODUCER_CATEGORY_COLORS)
            count          (int)         — loans originated this row
            amount         (float)       — £ originated this row
            quoted_count   (int)         — quotes sent this row
            quote_rate     (float)       — book-level quote rate for the month
                                           (decimal, same on every row of a month)
            sale_rate      (float)       — book-level sale rate for the month
                                           (decimal, same on every row of a month)

    Style:
        2×2 subplot grid:
            (1,1) Stacked monthly bar of `count` by introducer.
            (1,2) Stacked monthly bar of `amount` (£) by introducer.
            (2,1) Stacked monthly bar of `quoted_count` by introducer.
            (2,2) Two-line panel of `quote_rate` and `sale_rate` over months
                  (book-level, NOT per introducer).
        Stack categories use INTRODUCER_CATEGORY_COLORS. n= total above each
        column in the three bar panels.

    Parameters:
        df: input DataFrame.
        month, introducer, count_col, amount_col, quoted_col, quote_rate_col,
        sale_rate_col: column names.
        title: figure title.
        annotate_n: if True (default), annotate total n above each bar column.

    Returns:
        plotly.graph_objects.Figure with 2×2 layout.

    Example:
        >>> df = pd.read_csv("stacked_bar_volume_2x2_with_rate_line.csv")
        >>> fig = stacked_bar_volume_2x2_with_rate_line(df, title="Origination KPIs")
    """
    require_columns(
        df,
        [
            month,
            introducer,
            count_col,
            amount_col,
            quoted_col,
            quote_rate_col,
            sale_rate_col,
        ],
        who="stacked_bar_volume_2x2_with_rate_line",
    )
    # n annotation here uses the count column total per month — no separate n.
    # We still honour the contract by validating shape if user asked for it.
    _ = annotate_n  # accepted for API symmetry

    months = list(df[month].drop_duplicates())
    introducers = list(df[introducer].drop_duplicates())

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=(
            "Originated loans (count)",
            "Originated £ (amount)",
            "Quotes sent (count)",
            "Quote & sale rates",
        ),
        vertical_spacing=0.18,
        horizontal_spacing=0.10,
    )

    bar_panels = [
        (count_col, 1, 1, "loans"),
        (amount_col, 1, 2, "£"),
        (quoted_col, 2, 1, "quotes"),
    ]

    for value_col, r, c, _label in bar_panels:
        show_legend = (r == 1 and c == 1)
        for intro in introducers:
            sub = (
                df[df[introducer] == intro]
                .set_index(month)
                .reindex(months)
                .reset_index()
            )
            color = INTRODUCER_CATEGORY_COLORS.get(str(intro), UNKNOWN_INTRODUCER_COLOR)
            fig.add_trace(
                go.Bar(
                    x=sub[month],
                    y=sub[value_col],
                    name=str(intro),
                    marker_color=color,
                    legendgroup=str(intro),
                    showlegend=show_legend,
                    hovertemplate=(
                        f"<b>{intro}</b> %{{x}}: %{{y:,.0f}}<extra></extra>"
                    ),
                ),
                row=r,
                col=c,
            )

        if annotate_n:
            totals = (
                df.groupby(month, sort=False)[value_col]
                .sum()
                .reindex(months)
            )
            ymax = float(totals.max()) if len(totals) else 0.0
            for x_val, total in totals.items():
                if pd.notna(total):
                    fig.add_annotation(
                        x=x_val,
                        y=total,
                        text=f"n={int(round(float(total)))}",
                        showarrow=False,
                        yshift=10,
                        font=dict(size=8, color="#666"),
                        row=r,
                        col=c,
                    )
            if ymax > 0:
                fig.update_yaxes(range=[0, ymax * 1.18], row=r, col=c)

    # Rate panel — book-level rates per month
    rates_df = (
        df.drop_duplicates(subset=[month])[[month, quote_rate_col, sale_rate_col]]
        .sort_values(month)
    )
    fig.add_trace(
        go.Scatter(
            x=rates_df[month],
            y=rates_df[quote_rate_col],
            mode="lines+markers",
            name="Quote rate",
            line=dict(color=ACTUAL, width=2),
            marker=dict(size=6),
            legendgroup="rates",
            showlegend=True,
            hovertemplate="Quote rate %{x}: %{y:.2%}<extra></extra>",
        ),
        row=2,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=rates_df[month],
            y=rates_df[sale_rate_col],
            mode="lines+markers",
            name="Sale rate",
            line=dict(color=SECONDARY, width=2),
            marker=dict(size=6),
            legendgroup="rates",
            showlegend=True,
            hovertemplate="Sale rate %{x}: %{y:.2%}<extra></extra>",
        ),
        row=2,
        col=2,
    )
    fig.update_yaxes(tickformat=".1%", row=2, col=2)

    fig.update_layout(
        title=title or "Origination volume & conversion rates",
        barmode="stack",
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


def bar_horizontal_top_n(
    df: pd.DataFrame,
    *,
    category: str = "category",
    value: str = "value",
    n: str | None = "n",
    top_n: int = 10,
    value_fmt: str = "£,.0f",
    title: str | None = None,
    xlabel: str = "Volume",
    ylabel: str | None = None,
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """Single horizontal bar chart, sorted descending, showing top-N categories.

    Use this when:
        - You want a league-table view of top introducers / dealers / brokers
          by £ originated (or any other count/volume metric).

    Data shape:
        Long/tidy DataFrame, one row per category:
            category  (str)   — bar label
            value     (float) — magnitude (£ or count)
            n         (int, opt) — sample size; required if annotate_n=True

    Style:
        Single horizontal bar trace, ACTUAL blue. Categories sorted descending
        by value; bars rendered top → bottom (largest at top). n= annotation
        inside each bar (right-aligned). Value label on each bar formatted via
        `value_fmt` (defaults to £-formatted whole numbers).

    Parameters:
        df: input DataFrame.
        category, value, n: column names.
        top_n: number of categories to retain (default 10).
        value_fmt: format string for value labels (default "£,.0f").
        title: figure title.
        xlabel: x-axis label (defaults "Volume").
        ylabel: y-axis label (defaults to None → the category column name).
        annotate_n: if True (default), annotate n= inside each bar.
        small_sample_handling: "show" (default), "fade" or "suppress".

    Returns:
        plotly.graph_objects.Figure with one Bar trace.

    Example:
        >>> df = pd.read_csv("bar_horizontal_top_n.csv")
        >>> fig = bar_horizontal_top_n(df, title="Top 10 introducers by £ originated")
    """
    require_columns(df, [category, value], who="bar_horizontal_top_n")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)
    _ = small_sample_handling  # accepted; opacity handling not used for solid bars here

    ranked = df.sort_values(value, ascending=False).head(top_n).reset_index(drop=True)
    # In a horizontal bar chart, the first category in y appears at the bottom
    # unless we reverse the axis. Reverse so largest is on top.
    ranked = ranked.iloc[::-1].reset_index(drop=True)

    value_labels = [_format_value(float(v), value_fmt) for v in ranked[value]]
    n_labels = (
        [f"n={int(nn)}" for nn in ranked[n_col]] if n_col else [""] * len(ranked)
    )
    v_prefix, v_spec = _split_format_prefix(value_fmt)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=ranked[value],
            y=ranked[category].astype(str),
            orientation="h",
            marker_color=ACTUAL,
            text=value_labels,
            textposition="outside",
            cliponaxis=False,
            customdata=ranked[n_col] if n_col else None,
            hovertemplate=(
                f"<b>%{{y}}</b>: {v_prefix}%{{x:{v_spec}}}"
                + (" (n=%{customdata})" if n_col else "")
                + "<extra></extra>"
            ),
        )
    )

    if n_col:
        for i, (val, label) in enumerate(zip(ranked[value], n_labels, strict=False)):
            fig.add_annotation(
                x=val,
                y=ranked[category].astype(str).iloc[i],
                text=label,
                showarrow=False,
                xanchor="right",
                xshift=-6,
                font=dict(size=9, color="white"),
            )

    xmax = float(ranked[value].max()) if len(ranked) else 0.0
    fig.update_layout(
        title=title or f"Top {top_n} by {value}",
        xaxis=dict(
            title=xlabel,
            range=[0, xmax * 1.18] if xmax > 0 else None,
            tickformat=v_spec,
            tickprefix=v_prefix or None,
        ),
        yaxis=dict(title=ylabel or category),
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


def bar_plus_line_share_top_n(
    df: pd.DataFrame,
    *,
    category: str = "category",
    bar_value: str = "amount_share",
    line_value: str = "count_share",
    n: str | None = "n",
    top_n: int = 10,
    title: str | None = None,
    xlabel: str | None = None,
    bar_ylabel: str = "Amount share",
    line_ylabel: str = "Count share",
    y_tickformat: str = ".1%",
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """Vertical bar (amount share) + overlaid line (count share) on top-N categories.

    Use this when:
        - You want to compare £-share against count-share across the same
          ranked set of categories — useful for spotting introducers that
          punch above their weight in £ vs volume.

    Data shape:
        Long/tidy DataFrame, one row per category:
            category      (str)   — bar/line x-axis label
            amount_share  (float) — bar value (decimal, e.g. 0.18 for 18%)
            count_share   (float) — overlaid-line value (decimal)
            n             (int, opt) — sample size; required if annotate_n=True

    Style:
        Single panel with secondary y-axis. Vertical bars (ACTUAL blue) for
        amount share on the left y-axis; overlaid line+markers (SECONDARY
        orange) for count share on the right y-axis. Categories sorted by
        `bar_value` descending; top_n retained. n= annotation above each bar.

    Parameters:
        df: input DataFrame.
        category, bar_value, line_value, n: column names.
        top_n: number of categories to retain (default 10).
        title: figure title.
        xlabel: x-axis label (defaults to the `category` column name).
        bar_ylabel: left-axis label.
        line_ylabel: right-axis label.
        y_tickformat: tick format string for both axes (default ".1%").
        annotate_n: if True (default), annotate n= above each bar.
        small_sample_handling: "show" (default), "fade" or "suppress".

    Returns:
        plotly.graph_objects.Figure with one Bar + one Scatter on a secondary y-axis.

    Example:
        >>> df = pd.read_csv("bar_plus_line_share_top_n.csv")
        >>> fig = bar_plus_line_share_top_n(df, title="Introducer share: £ vs count")
    """
    require_columns(df, [category, bar_value, line_value], who="bar_plus_line_share_top_n")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)
    _ = small_sample_handling

    ranked = df.sort_values(bar_value, ascending=False).head(top_n).reset_index(drop=True)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    bar_text = (
        [f"n={int(nn)}" for nn in ranked[n_col]] if n_col else None
    )

    fig.add_trace(
        go.Bar(
            x=ranked[category].astype(str),
            y=ranked[bar_value],
            name=bar_ylabel,
            marker_color=ACTUAL,
            text=bar_text,
            textposition="outside",
            cliponaxis=False,
            customdata=ranked[n_col] if n_col else None,
            hovertemplate=(
                f"<b>%{{x}}</b><br>{bar_ylabel}: %{{y:{y_tickformat[1:]}}}"
                + (" (n=%{customdata})" if n_col else "")
                + "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=ranked[category].astype(str),
            y=ranked[line_value],
            mode="lines+markers",
            name=line_ylabel,
            line=dict(color=SECONDARY, width=2),
            marker=dict(size=8, color=SECONDARY),
            hovertemplate=(
                f"<b>%{{x}}</b><br>{line_ylabel}: %{{y:{y_tickformat[1:]}}}<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    ymax_bar = float(ranked[bar_value].max()) if len(ranked) else 0.0
    ymax_line = float(ranked[line_value].max()) if len(ranked) else 0.0

    fig.update_xaxes(title_text=xlabel or category)
    fig.update_yaxes(
        title_text=bar_ylabel,
        tickformat=y_tickformat,
        range=[0, ymax_bar * 1.20] if ymax_bar > 0 else None,
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text=line_ylabel,
        tickformat=y_tickformat,
        range=[0, ymax_line * 1.20] if ymax_line > 0 else None,
        secondary_y=True,
    )
    fig.update_layout(title=title or f"{bar_ylabel} vs {line_ylabel} — top {top_n}")
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


def waterfall_components_by_grade(
    df: pd.DataFrame,
    *,
    grade_group: str = "grade_group",
    component: str = "component",
    value: str = "value",
    title: str | None = None,
    ylabel: str = "£ per loan",
    y_tickformat: str = "£,.0f",
    annotate_n: bool = False,
) -> go.Figure:
    """1×N panel grid of grouped bars over cashflow components, one panel per grade group.

    Use this when:
        - You want a snapshot of the per-loan cashflow buildup (gross yield →
          loss → VT → commission → servicing → net IRR) broken out by grade
          group (A-B / C-E / F+) in a single comparable figure.

    Data shape:
        Long/tidy DataFrame, one row per (grade_group, component):
            grade_group  (str)   — panel split (e.g. "A-B", "C-E", "F+")
            component    (str)   — bar label within each panel; preserves
                                    first-appearance order across panels
            value        (float) — height of the bar

    Style:
        1×N subplot grid (N = number of distinct grade groups). Each panel
        renders the components as a single grouped-bar series, colour cycled
        positionally through COHORT_COLORS. Value label above each bar
        (formatted via `y_tickformat`). Since components are aggregates and
        not per-loan samples, `annotate_n` defaults to False.

    Parameters:
        df: input DataFrame.
        grade_group, component, value: column names.
        title: figure title.
        ylabel: y-axis label (default "£ per loan").
        y_tickformat: tick + label format string (default "£,.0f").
        annotate_n: defaults to False — there is no n= concept for these aggregates.
            If True, the `n` column is required and annotated above each bar
            in place of the value label.

    Returns:
        plotly.graph_objects.Figure with N panels (one per grade group).

    Example:
        >>> df = pd.read_csv("waterfall_components_by_grade.csv")
        >>> fig = waterfall_components_by_grade(df, title="Cashflow components by grade")
    """
    require_columns(df, [grade_group, component, value], who="waterfall_components_by_grade")
    n_col = resolve_n_column(df, "n", annotate_n=annotate_n)

    # Preserve insertion order for both axes.
    groups = list(df[grade_group].drop_duplicates())
    components = list(df[component].drop_duplicates())
    component_color = {
        comp: COHORT_COLORS[i % len(COHORT_COLORS)]
        for i, comp in enumerate(components)
    }

    n_panels = len(groups)
    fig = make_subplots(
        rows=1,
        cols=n_panels,
        subplot_titles=[str(g) for g in groups],
        horizontal_spacing=0.08,
        shared_yaxes=True,
    )

    tick_prefix, tick_spec = _split_format_prefix(y_tickformat)

    for idx, grp in enumerate(groups):
        c = idx + 1
        sub = (
            df[df[grade_group] == grp]
            .set_index(component)
            .reindex(components)
            .reset_index()
        )
        colors = [component_color[comp] for comp in sub[component]]
        labels: list[str]
        if annotate_n and n_col:
            labels = [
                f"n={int(nn)}" if pd.notna(nn) else "" for nn in sub[n_col]
            ]
        else:
            labels = [
                _format_value(float(v), y_tickformat) if pd.notna(v) else ""
                for v in sub[value]
            ]

        fig.add_trace(
            go.Bar(
                x=sub[component].astype(str),
                y=sub[value],
                marker_color=colors,
                text=labels,
                textposition="outside",
                cliponaxis=False,
                showlegend=False,
                hovertemplate=(
                    f"<b>{grp} — %{{x}}</b>: {tick_prefix}%{{y:{tick_spec}}}<extra></extra>"
                ),
            ),
            row=1,
            col=c,
        )
        fig.update_yaxes(
            tickformat=tick_spec,
            tickprefix=tick_prefix or None,
            title_text=ylabel if c == 1 else None,
            row=1,
            col=c,
        )
        fig.update_xaxes(tickangle=-30, row=1, col=c)

    fig.update_layout(
        title=title or "Cashflow components by grade group",
        barmode="group",
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig

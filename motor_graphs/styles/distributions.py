"""Distribution chart styles (violin / box / histogram)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from motor_graphs.style import apply_auto_legend
from motor_graphs.style.palette import (
    COHORT_COLORS,
    GRADE_COLOURS,
    INTRODUCER_CATEGORY_COLORS,
)

from ._shared import (
    SmallSampleMode,
    add_pound_weighted_footnote,
    require_columns,
    resolve_n_column,
)


def _pick_category_palette(categories: list[str]) -> dict[str, str]:
    """Pick a sensible colour mapping for a category axis.

    - If categories look like risk grades (subset of GRADE_COLOURS keys),
      use GRADE_COLOURS.
    - Else if categories look like introducer-category labels (subset of
      INTRODUCER_CATEGORY_COLORS keys), use INTRODUCER_CATEGORY_COLORS.
    - Else fall back to COHORT_COLORS positionally.
    """
    cat_set = set(categories)
    if cat_set and cat_set.issubset(GRADE_COLOURS.keys()):
        return {c: GRADE_COLOURS[c] for c in categories}
    if cat_set and cat_set.issubset(INTRODUCER_CATEGORY_COLORS.keys()):
        return {c: INTRODUCER_CATEGORY_COLORS[c] for c in categories}
    return {c: COHORT_COLORS[i % len(COHORT_COLORS)] for i, c in enumerate(categories)}


def _per_category_n(df: pd.DataFrame, category: str, n_col: str) -> dict[str, int]:
    """Return {category: n} taking the first non-null n value per category."""
    out: dict[str, int] = {}
    for cat, sub in df.groupby(category, sort=False):
        vals = sub[n_col].dropna()
        if len(vals):
            out[str(cat)] = int(vals.iloc[0])
        else:
            out[str(cat)] = int(len(sub))
    return out


def violin_grouped(
    df: pd.DataFrame,
    *,
    category: str = "category",
    value: str = "value",
    n: str | None = "n",
    category_order: list[str] | None = None,
    category_colors: dict[str, str] | None = None,
    title: str | None = None,
    xlabel: str = "Category",
    ylabel: str = "Value",
    y_tickformat: str | None = None,
    show_box: bool = True,
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """One violin per category — distribution shape compare across grades/channels.

    Use this when:
        - You have a continuous metric (LTV, APR, term, score) measured on many
          observations per category, and want to see the full distribution
          shape rather than just summary stats.
        - You want to compare distribution shape across risk grades or
          introducer channels.

    Data shape:
        Long/tidy DataFrame, one row per observation:
            category (str)   — category label (grade, channel, etc.)
            value    (float) — the observed metric value
            n        (int, opt) — sample size per category (constant across rows
                                  of that category; required if annotate_n=True)

    Style:
        Single panel, one violin per category. Box overlaid inside violin if
        show_box=True. Colours are auto-picked: GRADE_COLOURS for grade labels,
        INTRODUCER_CATEGORY_COLORS for introducer labels, COHORT_COLORS otherwise.
        n= is appended to each x-axis tick label (e.g. "A (n=1500)").

    Parameters:
        df: input DataFrame.
        category, value, n: column names.
        category_order: explicit category ordering. Default = order of first
            appearance.
        category_colors: optional dict {category: hex} override.
        title, xlabel, ylabel: figure labels.
        y_tickformat: optional Plotly tick-format string (e.g. ".1%" or ",.0f").
        show_box: overlay a box inside each violin (default True).
        annotate_n: if True (default), append "(n=…)" to each x-tick label.
        small_sample_handling: "show" (default), "fade", or "suppress" — fades
            violin opacity below n=200 / drops entirely below n=50.

    Returns:
        plotly.graph_objects.Figure with one Violin trace per category.

    Example:
        >>> df = pd.read_csv("violin_grouped.csv")
        >>> fig = violin_grouped(df, category="grade", value="ltv",
        ...                      ylabel="LTV", y_tickformat=".0%")
    """
    require_columns(df, [category, value], who="violin_grouped")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    categories = category_order or list(df[category].drop_duplicates())
    colors = category_colors or _pick_category_palette(categories)
    n_map = _per_category_n(df, category, n_col) if n_col else {}

    fig = go.Figure()
    for cat in categories:
        sub = df[df[category] == cat]
        if sub.empty:
            continue
        cat_n = n_map.get(str(cat), int(len(sub))) if n_col else int(len(sub))

        # Small-sample handling: derive opacity from n_count
        opacity = 1.0
        if small_sample_handling == "suppress" and cat_n < 50:
            continue  # drop entirely
        if small_sample_handling in ("fade", "suppress") and cat_n < 200:
            opacity = 0.35

        color = colors.get(cat, COHORT_COLORS[0])
        fig.add_trace(
            go.Violin(
                x=[str(cat)] * len(sub),
                y=sub[value],
                name=str(cat),
                line_color=color,
                fillcolor=color,
                opacity=opacity,
                box=dict(visible=show_box),
                meanline=dict(visible=True),
                points=False,
                showlegend=False,
                hovertemplate=(
                    f"<b>{cat}</b><br>value=%{{y}}"
                    + (f"<br>n={cat_n}" if n_col else "")
                    + "<extra></extra>"
                ),
            )
        )

    # Append n= to each x-tick label
    if annotate_n and n_col:
        tick_text = [f"{c} (n={n_map.get(str(c), 0)})" for c in categories]
    else:
        tick_text = [str(c) for c in categories]

    yaxis_kwargs: dict = dict(title=ylabel)
    if y_tickformat:
        yaxis_kwargs["tickformat"] = y_tickformat

    fig.update_layout(
        title=title or "Distribution by category",
        xaxis=dict(
            title=xlabel,
            tickmode="array",
            tickvals=[str(c) for c in categories],
            ticktext=tick_text,
        ),
        yaxis=yaxis_kwargs,
        violinmode="group",
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


def box_quantile(
    df: pd.DataFrame,
    *,
    category: str = "category",
    value: str = "value",
    n: str | None = "n",
    q_low: float = 0.10,
    q_high: float = 0.90,
    category_order: list[str] | None = None,
    category_colors: dict[str, str] | None = None,
    title: str | None = None,
    xlabel: str = "Category",
    ylabel: str = "Value",
    y_tickformat: str | None = None,
    annotate_n: bool = True,
) -> go.Figure:
    """Box per category — quartiles + q_low/q_high whiskers, no points.

    Use this when:
        - You want a clean summary of distribution shape across categories
          without the visual density of a violin.
        - You prefer custom whiskers (e.g. 10/90) over Tukey's 1.5×IQR rule.

    Data shape:
        Long/tidy DataFrame, one row per observation:
            category (str)   — category label
            value    (float) — observed metric
            n        (int, opt) — sample size per category (required if
                                  annotate_n=True)

    Style:
        Single panel, one box per category. Box body = q1-q3; median line;
        whiskers stretch to the q_low / q_high quantiles (default 10/90).
        Colours auto-picked (grade / introducer / cohort cycle). n= is
        appended to each x-axis tick label.

    Parameters:
        df: input DataFrame.
        category, value, n: column names.
        q_low, q_high: whisker quantiles in [0, 1] (default 0.10, 0.90).
        category_order: explicit category ordering.
        category_colors: optional dict {category: hex} override.
        title, xlabel, ylabel: figure labels.
        y_tickformat: optional tick-format string.
        annotate_n: if True (default), append "(n=…)" to each x-tick label.

    Returns:
        plotly.graph_objects.Figure with one Box trace per category.

    Example:
        >>> df = pd.read_csv("box_quantile.csv")
        >>> fig = box_quantile(df, category="grade", value="apr",
        ...                    ylabel="APR", y_tickformat=".1%")
    """
    require_columns(df, [category, value], who="box_quantile")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)
    if not (0.0 <= q_low < q_high <= 1.0):
        raise ValueError(
            f"box_quantile requires 0 <= q_low < q_high <= 1, got q_low={q_low}, q_high={q_high}"
        )

    categories = category_order or list(df[category].drop_duplicates())
    colors = category_colors or _pick_category_palette(categories)
    n_map = _per_category_n(df, category, n_col) if n_col else {}

    fig = go.Figure()
    for cat in categories:
        sub = df[df[category] == cat]
        if sub.empty:
            continue
        vals = sub[value].astype(float).to_numpy()
        if len(vals) == 0:
            continue
        q1 = float(pd.Series(vals).quantile(0.25))
        q3 = float(pd.Series(vals).quantile(0.75))
        med = float(pd.Series(vals).quantile(0.50))
        lo = float(pd.Series(vals).quantile(q_low))
        hi = float(pd.Series(vals).quantile(q_high))
        mean = float(vals.mean())
        color = colors.get(cat, COHORT_COLORS[0])

        fig.add_trace(
            go.Box(
                x=[str(cat)],
                q1=[q1],
                median=[med],
                q3=[q3],
                lowerfence=[lo],
                upperfence=[hi],
                mean=[mean],
                name=str(cat),
                marker_color=color,
                line_color=color,
                boxpoints=False,
                showlegend=False,
                hovertemplate=(
                    f"<b>{cat}</b><br>"
                    f"q{int(q_low * 100)}={lo:.4g}<br>"
                    f"q1={q1:.4g}<br>"
                    f"median={med:.4g}<br>"
                    f"q3={q3:.4g}<br>"
                    f"q{int(q_high * 100)}={hi:.4g}"
                    "<extra></extra>"
                ),
            )
        )

    # x-axis tick labels with n=
    if annotate_n and n_col:
        tick_text = [f"{c} (n={n_map.get(str(c), 0)})" for c in categories]
    else:
        tick_text = [str(c) for c in categories]

    yaxis_kwargs: dict = dict(title=ylabel)
    if y_tickformat:
        yaxis_kwargs["tickformat"] = y_tickformat

    fig.update_layout(
        title=title
        or f"Box (q1-q3, whiskers at p{int(q_low * 100)}/p{int(q_high * 100)}) by category",
        xaxis=dict(
            title=xlabel,
            tickmode="array",
            tickvals=[str(c) for c in categories],
            ticktext=tick_text,
        ),
        yaxis=yaxis_kwargs,
        boxmode="group",
    )
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig


def histogram_by_grade(
    df: pd.DataFrame,
    *,
    value: str = "value",
    grade: str = "grade",
    nbins: int = 30,
    n: str | None = "n",
    title: str | None = None,
    xlabel: str = "Value",
    ylabel: str = "Count",
    normalised: bool = False,
    annotate_n: bool = True,
) -> go.Figure:
    """Stacked histogram coloured by risk grade — distribution by grade.

    Use this when:
        - You want to see how a continuous variable (origination score, APR,
          LTV) is distributed across the population, broken out by risk grade.
        - You want to verify that grade segmentation actually separates the
          underlying distribution.

    Data shape:
        Long/tidy DataFrame, one row per observation:
            value (float) — the observed value
            grade (str)   — grade label (one of GRADE_COLOURS keys)
            n     (int, opt) — sample size per grade (required if annotate_n=True;
                               constant across rows of the same grade)

    Style:
        Single panel stacked histogram with `barmode='stack'`. One trace per
        grade, coloured via GRADE_COLOURS. If normalised=True, uses
        histnorm='percent' so bars sum to 100% per bin. n= per grade is shown
        in the legend label (e.g. "A (n=1500)").

    Parameters:
        df: input DataFrame.
        value, grade, n: column names.
        nbins: number of histogram bins (default 30).
        title, xlabel, ylabel: figure labels.
        normalised: if True, use histnorm='percent' (default False = raw counts).
        annotate_n: if True (default), append "(n=…)" to each legend label.

    Returns:
        plotly.graph_objects.Figure with one Histogram trace per grade.

    Example:
        >>> df = pd.read_csv("histogram_by_grade.csv")
        >>> fig = histogram_by_grade(df, value="score", grade="grade",
        ...                          title="Score distribution by grade")
    """
    require_columns(df, [value, grade], who="histogram_by_grade")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    # Grades appear in GRADE_COLOURS order (canonical), filtered to those present.
    present = set(df[grade].unique())
    grades = [g for g in GRADE_COLOURS.keys() if g in present]
    # Append any leftover grades not in GRADE_COLOURS at the end.
    for g in df[grade].drop_duplicates():
        if g not in grades:
            grades.append(g)

    n_map = _per_category_n(df, grade, n_col) if n_col else {}

    fig = go.Figure()
    for g in grades:
        sub = df[df[grade] == g]
        if sub.empty:
            continue
        color = GRADE_COLOURS.get(g, COHORT_COLORS[len(fig.data) % len(COHORT_COLORS)])
        if annotate_n and n_col:
            label = f"{g} (n={n_map.get(str(g), 0)})"
        else:
            label = str(g)
        fig.add_trace(
            go.Histogram(
                x=sub[value],
                name=label,
                nbinsx=nbins,
                marker_color=color,
                opacity=0.85,
                histnorm="percent" if normalised else None,
                hovertemplate=(
                    f"<b>{label}</b><br>value=%{{x}}<br>"
                    + ("percent=%{y:.2f}%" if normalised else "count=%{y}")
                    + "<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=title or "Distribution by grade",
        xaxis_title=xlabel,
        yaxis_title="Percent" if normalised else ylabel,
        barmode="stack",
    )
    if normalised:
        fig.update_yaxes(ticksuffix="%")
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig

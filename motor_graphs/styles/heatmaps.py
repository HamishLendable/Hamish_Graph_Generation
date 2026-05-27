"""Heatmap chart styles."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from motor_graphs.style.palette import GRADE_COLOURS, SEQUENTIAL_HEATMAP

from ._shared import add_pound_weighted_footnote, require_columns


def heatmap_swap(
    df: pd.DataFrame,
    *,
    x_grade: str = "x_grade",
    y_grade: str = "y_grade",
    count: str = "count",
    amount_share: str | None = "pct_amount",
    title: str | None = None,
    x_label: str = "Y scorecard grade",
    y_label: str = "X scorecard grade",
    colorscale: str = SEQUENTIAL_HEATMAP,
    annotate: bool = True,
) -> go.Figure:
    """X-grade × Y-grade swap matrix heatmap with count + £-pct annotations.

    Use this when:
        - You have a pivot of two scorecards (X vs Y) and want to see how loans
          shift between grade buckets — the "swap matrix" that drives MoTa
          scorecard rollout decisions.

    Data shape:
        Long/tidy DataFrame, one row per cell:
            x_grade       (str)   — grade under scorecard X (rows)
            y_grade       (str)   — grade under scorecard Y (cols)
            count         (int)   — number of loans in this cell
            pct_amount    (float, opt) — £-share in 0-100; shown alongside count if present

    Style:
        Single panel heatmap. Sequential 'Blues' colorscale by default; pass
        DIVERGING_HEATMAP for deviation/lift-ratio variants. Each cell annotated
        with the count (and £-pct on a second line if `amount_share` column is
        present). Grade axes sorted by GRADE_COLOURS order (A → F**).

    Parameters:
        df: input DataFrame.
        x_grade, y_grade, count, amount_share: column names.
            Pass amount_share=None to suppress the £-pct line.
        title: figure title.
        x_label, y_label: axis labels.
        colorscale: Plotly colorscale name. Default SEQUENTIAL_HEATMAP ("Blues").
            Use DIVERGING_HEATMAP ("RdBu_r") for deviation matrices.
        annotate: if True (default), write count + £-pct text in each cell.

    Returns:
        plotly.graph_objects.Figure with one Heatmap trace.

    Example:
        >>> df = pd.read_csv("swap_matrix.csv")
        >>> fig = heatmap_swap(df, title="Carrera × Torino swap matrix")
    """
    require_columns(df, [x_grade, y_grade, count], who="heatmap_swap")

    grade_order = [g for g in GRADE_COLOURS.keys() if g in df[x_grade].values or g in df[y_grade].values]
    if not grade_order:
        grade_order = sorted(set(df[x_grade].unique()) | set(df[y_grade].unique()))

    count_pivot = df.pivot(index=x_grade, columns=y_grade, values=count).reindex(
        index=grade_order, columns=grade_order
    )

    text_matrix = None
    if annotate:
        if amount_share and amount_share in df.columns:
            amt_pivot = df.pivot(index=x_grade, columns=y_grade, values=amount_share).reindex(
                index=grade_order, columns=grade_order
            )
            text_matrix = [
                [
                    (
                        f"{int(c)}<br>£{amt_pivot.iloc[i, j]:.0f}%"
                        if pd.notna(c) and pd.notna(amt_pivot.iloc[i, j])
                        else ""
                    )
                    for j, c in enumerate(row)
                ]
                for i, row in enumerate(count_pivot.values)
            ]
        else:
            text_matrix = [
                [f"{int(c)}" if pd.notna(c) else "" for c in row]
                for row in count_pivot.values
            ]

    fig = go.Figure(
        data=go.Heatmap(
            z=count_pivot.values,
            x=list(count_pivot.columns),
            y=list(count_pivot.index),
            colorscale=colorscale,
            text=text_matrix,
            texttemplate="%{text}" if text_matrix else None,
            textfont=dict(size=11),
            hovertemplate="X=%{y} → Y=%{x}<br>count=%{z}<extra></extra>",
            colorbar=dict(title="Count"),
        )
    )
    fig.update_layout(
        title=title or "Swap matrix (X × Y grade)",
        xaxis=dict(title=x_label, side="bottom"),
        yaxis=dict(title=y_label, autorange="reversed"),
    )
    add_pound_weighted_footnote(fig)
    return fig

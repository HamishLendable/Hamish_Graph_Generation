"""Scatter chart styles."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from motor_graphs.style.palette import ACTUAL, OVERLAY_BLACK

from ._shared import add_pound_weighted_footnote, require_columns, resolve_n_column


def scatter_calibration(
    df: pd.DataFrame,
    *,
    expected_pd: str = "expected_pd",
    actual_default: str = "actual_default",
    n: str = "n",
    label: str | None = "bucket",
    title: str | None = None,
    xlabel: str = "Expected default rate (IRR input_90_in_9)",
    ylabel: str = "Actual default rate (90+@9)",
    tickformat: str = ".1%",
    annotate_n: bool = True,
) -> go.Figure:
    """Scatter of expected vs actual default rate per bucket, with y=x diagonal.

    Use this when:
        - You want to check whether your PD model (or equivalent — Lendable uses
          IRR `input_90_in_9` as the PD substitute, since there is no
          ORIGINATION_PD column) is calibrated against realised 90+@9 defaults.
        - Points above the y=x line mean realised defaults > expected; below
          means the model is conservative.

    Data shape:
        Long/tidy DataFrame, one row per bucket:
            expected_pd     (float) — expected default rate from the model (decimal)
            actual_default  (float) — realised 90+@9 rate for the bucket (decimal)
            n               (int)   — bucket size (drives bubble area)
            bucket          (str, opt) — label shown next to each point

    Style:
        Single panel scatter. Bubble area ∝ n (encodes sample size). Black y=x
        diagonal reference line. Point labels (bucket name) annotated next to
        each marker. Equal axes (both percentage). n= annotation on every point
        is implicit in the bubble size.

    Parameters:
        df: input DataFrame.
        expected_pd, actual_default, n, label: column names. label=None hides labels.
        title, xlabel, ylabel: figure labels.
        tickformat: tick format string (default ".1%" for percentage).
        annotate_n: if True (default), encode n via bubble size + show n= in hover.

    Returns:
        plotly.graph_objects.Figure with one Scatter (points) + one diagonal line.

    Example:
        >>> df = pd.read_csv("calibration_scatter.csv")
        >>> fig = scatter_calibration(df, title="PD calibration check")
    """
    require_columns(df, [expected_pd, actual_default, n], who="scatter_calibration")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    # Diagonal range
    lo = float(min(df[expected_pd].min(), df[actual_default].min()))
    hi = float(max(df[expected_pd].max(), df[actual_default].max()))
    pad = (hi - lo) * 0.10 if hi > lo else 0.01
    axis_lo, axis_hi = max(0.0, lo - pad), hi + pad

    # Bubble sizing — scale n into marker.size (px). Use sizeref for proper area scaling.
    ns = df[n_col].tolist() if n_col else [50] * len(df)
    max_n = max(ns) if ns else 50

    fig = go.Figure()
    # Diagonal y=x reference
    fig.add_trace(
        go.Scatter(
            x=[axis_lo, axis_hi],
            y=[axis_lo, axis_hi],
            mode="lines",
            line=dict(color=OVERLAY_BLACK, dash="dash", width=1.5),
            name="y = x",
            hoverinfo="skip",
        )
    )
    # Points
    fig.add_trace(
        go.Scatter(
            x=df[expected_pd],
            y=df[actual_default],
            mode="markers+text" if label and label in df.columns else "markers",
            marker=dict(
                color=ACTUAL,
                size=ns,
                sizemode="area",
                sizeref=2.0 * max_n / (40.0 ** 2),
                sizemin=4,
                line=dict(color="white", width=1),
            ),
            text=df[label].astype(str) if label and label in df.columns else None,
            textposition="top center",
            textfont=dict(size=9, color="grey"),
            name="Buckets",
            customdata=ns,
            hovertemplate=(
                "Bucket<br>"
                f"expected: %{{x:{tickformat[1:]}}}<br>"
                f"actual:   %{{y:{tickformat[1:]}}}<br>"
                "n=%{customdata}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title=title or "PD calibration: expected vs actual",
        xaxis=dict(title=xlabel, tickformat=tickformat, range=[axis_lo, axis_hi]),
        yaxis=dict(title=ylabel, tickformat=tickformat, range=[axis_lo, axis_hi]),
    )
    add_pound_weighted_footnote(fig)
    return fig

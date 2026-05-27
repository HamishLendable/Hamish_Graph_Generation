"""Shared helpers for chart-style primitives.

These implement universal house rules from docs/discovery/chart_inventory.md:
- £-weighted footnote on every chart
- n= visible by default (via per-style annotation patterns)
- EV small-sample handling (fade / suppress by n)
- Validation of required columns
"""

from __future__ import annotations

from typing import Iterable, Literal, Sequence

import pandas as pd
import plotly.graph_objects as go

from motor_graphs.style.palette import EV_FADE_N, EV_FADE_OPACITY, EV_SUPPRESS_N

POUND_WEIGHTED_FOOTNOTE = "Note: All rates are £ weighted."

SmallSampleMode = Literal["show", "fade", "suppress"]


def add_pound_weighted_footnote(
    fig: go.Figure,
    *,
    text: str = POUND_WEIGHTED_FOOTNOTE,
    y: float = -0.18,
) -> go.Figure:
    """Add the canonical '£ weighted' footnote in the bottom-left."""
    fig.add_annotation(
        text=text,
        xref="paper",
        yref="paper",
        x=0.0,
        y=y,
        xanchor="left",
        yanchor="top",
        showarrow=False,
        font=dict(size=10, color="grey"),
    )
    return fig


def require_columns(df: pd.DataFrame, columns: Sequence[str], *, who: str = "chart style") -> None:
    """Raise ValueError if any of `columns` is missing from `df`."""
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(
            f"{who} requires columns {missing}, but the DataFrame has {list(df.columns)}"
        )


def resolve_n_column(
    df: pd.DataFrame, n_col: str | None, *, annotate_n: bool
) -> str | None:
    """Resolve the n-column name. Raises if annotate_n=True and the column is missing.

    Returns the column name (or None if annotation is disabled).
    """
    if not annotate_n:
        return None
    n_col = n_col or "n"
    if n_col not in df.columns:
        raise ValueError(
            f"annotate_n=True requires column {n_col!r} in the DataFrame, "
            f"but the columns are: {list(df.columns)}. "
            "Pass annotate_n=False to skip n= annotation, or add the column."
        )
    return n_col


def opacity_for_n(n_values: Iterable[int], mode: SmallSampleMode = "show") -> list[float]:
    """Per-point opacity based on sample size + small-sample handling mode.

    Thresholds (from palette): EV_SUPPRESS_N=50, EV_FADE_N=200, EV_FADE_OPACITY=0.35.

    - "show":     all 1.0 (no opacity adjustment).
    - "fade":     n < EV_FADE_N → EV_FADE_OPACITY; else 1.0.
    - "suppress": n < EV_SUPPRESS_N → 0.0; EV_SUPPRESS_N ≤ n < EV_FADE_N → EV_FADE_OPACITY; else 1.0.
    """
    n_list = list(n_values)
    if mode == "show":
        return [1.0] * len(n_list)
    out: list[float] = []
    for n in n_list:
        if mode == "suppress" and n < EV_SUPPRESS_N:
            out.append(0.0)
        elif n < EV_FADE_N:
            out.append(EV_FADE_OPACITY)
        else:
            out.append(1.0)
    return out


def annotate_last_point(
    fig: go.Figure,
    *,
    x: Iterable,
    y: Iterable,
    text: str,
    row: int | None = None,
    col: int | None = None,
    yshift: int = 12,
    font_color: str = "grey",
) -> None:
    """Add a single text annotation at the last (x, y) of a series."""
    x_list = list(x)
    y_list = list(y)
    if not x_list:
        return
    kwargs = dict(
        x=x_list[-1],
        y=y_list[-1],
        text=text,
        showarrow=False,
        yshift=yshift,
        xshift=0,
        font=dict(size=9, color=font_color),
        xanchor="right",
    )
    if row is not None and col is not None:
        fig.add_annotation(**kwargs, row=row, col=col)
    else:
        fig.add_annotation(**kwargs)

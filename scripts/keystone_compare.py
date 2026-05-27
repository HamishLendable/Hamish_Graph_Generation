"""Keystone visual sanity check — render 4 synthetic charts to verify the motor template.

Outputs PNG + HTML to out/_keystone_compare/. Compare visually against the reference
repo PNGs at /Users/hamish.aitken/Documents/GitHub/credit.auto-monthly-monitoring/charts/.

Run:
    poetry run python scripts/keystone_compare.py

Reference PNGs to compare against (rough mappings):
    01_cohort_lines_vs_mob       <-> charts/voluntary_termination.png
    02_grouped_bars_by_grade     <-> charts/35_ev_early_performance_by_grade.png
    03_stacked_100pct            <-> charts/44_originated_vehicle_distributions_monthly_100pct.png
    04_dq_2x2_actual_vs_expected <-> charts/02_delinquency_subplot.png
"""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import motor_graphs
from motor_graphs.style import apply_auto_legend
from motor_graphs.style.palette import (
    ACTUAL,
    COHORT_COLORS,
    EXPECTED,
    GRADE_COLOURS,
    INTRODUCER_CATEGORY_COLORS,
    SECONDARY,
)

OUT = Path(__file__).parent.parent / "out" / "_keystone_compare"


def _synth_cohort_lines() -> go.Figure:
    """Style #4 cohort_lines_vs_mob: per-cohort cumulative line + dashed expected."""
    mobs = np.arange(0, 25)
    cohorts = pd.date_range("2024-01-01", periods=12, freq="MS").strftime("%Y-%m")
    rng = np.random.default_rng(42)
    fig = go.Figure()
    for i, c in enumerate(cohorts):
        peak = 0.04 + rng.uniform(-0.005, 0.005)
        # Logistic-shaped cumulative curve, tapered for immature cohorts
        max_mob = max(2, 24 - i * 2)
        curve = peak * (1 - np.exp(-mobs / 8))
        curve[max_mob:] = np.nan  # immature: don't plot
        fig.add_trace(
            go.Scatter(
                x=mobs,
                y=curve,
                mode="lines+markers",
                name=c,
                line=dict(color=COHORT_COLORS[i % len(COHORT_COLORS)], width=2),
                marker=dict(size=4),
                hovertemplate=f"<b>{c}</b><br>MOB %{{x}}: %{{y:.2%}}<extra></extra>",
            )
        )
    expected = 0.04 * (1 - np.exp(-mobs / 8))
    fig.add_trace(
        go.Scatter(
            x=mobs,
            y=expected,
            mode="lines",
            name="Expected",
            line=dict(color=EXPECTED, width=2, dash="dash"),
            hovertemplate="Expected MOB %{x}: %{y:.2%}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Synthetic: Cumulative VT by cohort (style #4)",
        xaxis_title="MOB",
        yaxis=dict(title="VT rate", tickformat=".1%"),
        annotations=[
            dict(
                text="Note: All rates are £ weighted.",
                xref="paper",
                yref="paper",
                x=0.01,
                y=-0.20,
                showarrow=False,
                font=dict(size=10, color="grey"),
            )
        ],
    )
    return fig


def _synth_grouped_bars_by_grade() -> go.Figure:
    """Style #13 grouped_bars_by_grade_two_series — with n= annotations."""
    grades = list(GRADE_COLOURS.keys())
    rng = np.random.default_rng(7)
    bev = 0.01 + 0.005 * np.arange(len(grades)) + rng.uniform(-0.005, 0.005, len(grades))
    rob = bev * 0.85 + rng.uniform(-0.003, 0.003, len(grades))
    n_bev = rng.integers(100, 500, len(grades))
    n_rob = rng.integers(800, 2000, len(grades))
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=grades,
            y=bev,
            name="BEV",
            marker_color=ACTUAL,
            text=[f"n={n}" for n in n_bev],
            textposition="outside",
            hovertemplate="<b>BEV %{x}</b>: %{y:.2%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=grades,
            y=rob,
            name="Rest of book",
            marker_color=SECONDARY,
            text=[f"n={n}" for n in n_rob],
            textposition="outside",
            hovertemplate="<b>ROB %{x}</b>: %{y:.2%}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Synthetic: 90+@9 DQ by grade — BEV vs Rest-of-book (style #13)",
        xaxis_title="Risk grade",
        yaxis=dict(title="90+@9 DQ rate", tickformat=".1%"),
        barmode="group",
        annotations=[
            dict(
                text="Note: All rates are £ weighted.",
                xref="paper",
                yref="paper",
                x=0.01,
                y=-0.20,
                showarrow=False,
                font=dict(size=10, color="grey"),
            )
        ],
    )
    return fig


def _synth_stacked_100pct() -> go.Figure:
    """Style #8 stacked_bar_100pct_monthly (single panel for keystone)."""
    months = pd.date_range("2024-01-01", periods=18, freq="MS").strftime("%Y-%m")
    categories = list(INTRODUCER_CATEGORY_COLORS.keys())
    rng = np.random.default_rng(13)
    raw = rng.uniform(0.1, 1.0, (len(categories), len(months)))
    shares = raw / raw.sum(axis=0, keepdims=True) * 100
    ns = rng.integers(500, 2500, len(months))
    fig = go.Figure()
    for i, cat in enumerate(categories):
        fig.add_trace(
            go.Bar(
                x=months,
                y=shares[i, :],
                name=cat,
                marker_color=INTRODUCER_CATEGORY_COLORS[cat],
                text=[f"{v:.0f}%" if v >= 5 else "" for v in shares[i, :]],
                textposition="inside",
                hovertemplate=f"<b>{cat}</b> %{{x}}: %{{y:.1f}}%<extra></extra>",
            )
        )
    for i, m in enumerate(months):
        fig.add_annotation(
            x=m, y=104, text=f"n={ns[i]}", showarrow=False, font=dict(size=9, color="#666")
        )
    fig.update_layout(
        title="Synthetic: Originated volume mix by introducer (style #8)",
        xaxis_title="Origination month",
        yaxis=dict(title="Share of volume", ticksuffix="%", range=[0, 112]),
        barmode="stack",
    )
    return fig


def _synth_dq_2x2() -> go.Figure:
    """Style #1 dq_2x2_actual_vs_expected."""
    cohorts = pd.date_range("2024-01-01", periods=15, freq="MS").strftime("%Y-%m")
    rng = np.random.default_rng(99)
    metrics = [
        ("30+ DPD at MOB 1", 0.018),
        ("30+ DPD at MOB 3", 0.035),
        ("60+ DPD at MOB 6", 0.022),
        ("90+ DPD at MOB 9", 0.028),
    ]
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=[m[0] for m in metrics],
        vertical_spacing=0.20,
        horizontal_spacing=0.08,
    )
    for idx, (name, base) in enumerate(metrics):
        r, c = idx // 2 + 1, idx % 2 + 1
        actual = base + rng.uniform(-0.005, 0.005, len(cohorts))
        # taper immature cohorts (last 3)
        actual[-3:] = actual[-3:] * np.linspace(0.7, 0.4, 3)
        expected = np.full_like(actual, base)
        n_per = rng.integers(150, 600, len(cohorts))
        fig.add_trace(
            go.Scatter(
                x=cohorts,
                y=actual,
                mode="lines+markers",
                name="Actual",
                line=dict(color=ACTUAL, width=2),
                marker=dict(size=5),
                showlegend=(idx == 0),
                customdata=n_per,
                hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y:.2%}} (n=%{{customdata}})<extra></extra>",
            ),
            row=r,
            col=c,
        )
        fig.add_trace(
            go.Scatter(
                x=cohorts,
                y=expected,
                mode="lines",
                name="Expected",
                line=dict(color=EXPECTED, width=2, dash="dash"),
                showlegend=(idx == 0),
                hovertemplate="Expected: %{y:.2%}<extra></extra>",
            ),
            row=r,
            col=c,
        )
        fig.update_yaxes(tickformat=".1%", row=r, col=c)
    fig.update_layout(title="Synthetic: DQ actual vs expected 2×2 (style #1)")
    return fig


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Rendering keystone comparison to {OUT}/")
    figs = [
        ("01_cohort_lines_vs_mob", _synth_cohort_lines()),
        ("02_grouped_bars_by_grade", _synth_grouped_bars_by_grade()),
        ("03_stacked_100pct", _synth_stacked_100pct()),
        ("04_dq_2x2_actual_vs_expected", _synth_dq_2x2()),
    ]
    for name, fig in figs:
        apply_auto_legend(fig)
        motor_graphs.save_figure(fig, OUT / name)
    print("Done.")
    print(f"  PNGs: {OUT}/*.png")
    print(f"  HTML: {OUT}/*.html")


if __name__ == "__main__":
    main()

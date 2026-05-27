"""Tests for motor_graphs.style — palette completeness + template registration + save_figure."""

import re
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
import pytest

import motor_graphs
from motor_graphs.style import apply_auto_legend, palette, set_background

HEX_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


def test_template_registered():
    assert "motor" in pio.templates
    assert pio.templates.default == "plotly_white+motor"


def test_palette_has_all_grades():
    expected = {"A", "B", "C", "D", "E", "F", "F*", "F**"}
    assert set(palette.GRADE_COLOURS.keys()) == expected
    for grade, hex_val in palette.GRADE_COLOURS.items():
        assert HEX_PATTERN.match(hex_val), f"{grade} has invalid hex {hex_val}"


def test_palette_has_grade_groups():
    assert set(palette.GRADE_GROUP_COLOURS.keys()) == {"A-B", "C-E", "F+"}
    assert set(palette.CASHFLOW_GRADE_GROUP_COLOURS.keys()) == {"A-C", "D-E", "F+"}


def test_palette_has_introducer_categories():
    expected = {
        "Aggregator",
        "Broker - Dealer led",
        "Broker - Online led",
        "Dealer",
        "Direct",
        "Unknown introducer",
    }
    assert set(palette.INTRODUCER_CATEGORY_COLORS.keys()) == expected
    for cat, hex_val in palette.INTRODUCER_CATEGORY_COLORS.items():
        assert HEX_PATTERN.match(hex_val), f"{cat} has invalid hex {hex_val}"


def test_cohort_colors_has_15():
    assert len(palette.COHORT_COLORS) == 15
    for c in palette.COHORT_COLORS:
        assert HEX_PATTERN.match(c)


def test_semantic_role_aliases():
    assert palette.ACTUAL == palette.PRIMARY_COLOR == palette.BEV_COLOR == palette.CARRERA_COLOR
    assert palette.SECONDARY == palette.ROB_COLOR == palette.TORINO_COLOR
    assert palette.EXPECTED == palette.PREDICTED_COLOR == palette.ASSUMED_COLOR == palette.GAP_COLOR


def test_hex_to_rgba():
    assert palette.hex_to_rgba("#1f77b4", 0.2) == "rgba(31,119,180,0.2)"
    assert palette.hex_to_rgba("#000000", 1.0) == "rgba(0,0,0,1.0)"
    assert palette.hex_to_rgba("#FFFFFF", 0.5) == "rgba(255,255,255,0.5)"


def test_heatmap_scales_set():
    assert palette.SEQUENTIAL_HEATMAP == "Blues"
    assert palette.DIVERGING_HEATMAP == "RdBu_r"


def test_ev_thresholds():
    assert palette.EV_SUPPRESS_N == 50
    assert palette.EV_FADE_N == 200
    assert palette.EV_FADE_OPACITY == 0.35


def test_save_figure_writes_png_and_html(tmp_path: Path):
    fig = go.Figure(data=[go.Scatter(x=[1, 2, 3], y=[1, 4, 9])])
    out = tmp_path / "test"
    motor_graphs.save_figure(fig, out)
    assert (tmp_path / "test.png").exists()
    assert (tmp_path / "test.html").exists()


def test_save_figure_png_only(tmp_path: Path):
    fig = go.Figure(data=[go.Scatter(x=[1, 2, 3], y=[1, 4, 9])])
    out = tmp_path / "test"
    motor_graphs.save_figure(fig, out, also_html=False)
    assert (tmp_path / "test.png").exists()
    assert not (tmp_path / "test.html").exists()


def test_save_figure_strips_existing_suffix(tmp_path: Path):
    """Passing path/test.png should still produce path/test.png + path/test.html."""
    fig = go.Figure(data=[go.Scatter(x=[1, 2, 3], y=[1, 4, 9])])
    motor_graphs.save_figure(fig, tmp_path / "test.png")
    assert (tmp_path / "test.png").exists()
    assert (tmp_path / "test.html").exists()


def test_set_background_valid():
    try:
        set_background("plotly")
        assert pio.templates.default == "plotly+motor"
        set_background("simple_white")
        assert pio.templates.default == "simple_white+motor"
    finally:
        set_background("plotly_white")
        assert pio.templates.default == "plotly_white+motor"


def test_set_background_invalid():
    with pytest.raises(ValueError):
        set_background("nonexistent")


def test_apply_auto_legend_few_series_leaves_default():
    fig = go.Figure()
    for i in range(3):
        fig.add_trace(go.Scatter(x=[1, 2], y=[1, 2], name=f"s{i}"))
    apply_auto_legend(fig)
    # 3 <= 6: should NOT override to vertical
    assert fig.layout.legend.orientation in (None, "h")


def test_apply_auto_legend_many_series_goes_vertical():
    fig = go.Figure()
    for i in range(10):
        fig.add_trace(go.Scatter(x=[1, 2], y=[1, 2], name=f"s{i}"))
    apply_auto_legend(fig)
    assert fig.layout.legend.orientation == "v"
    assert fig.layout.legend.x > 1.0


def test_apply_auto_legend_ignores_unnamed_and_hidden():
    fig = go.Figure()
    for _ in range(10):
        fig.add_trace(go.Scatter(x=[1, 2], y=[1, 2]))  # unnamed
    fig.add_trace(go.Scatter(x=[1, 2], y=[1, 2], name="hidden", showlegend=False))
    apply_auto_legend(fig)
    # 0 named visible series: should not flip to vertical
    assert fig.layout.legend.orientation in (None, "h")


def test_apply_auto_legend_custom_threshold():
    fig = go.Figure()
    for i in range(4):
        fig.add_trace(go.Scatter(x=[1, 2], y=[1, 2], name=f"s{i}"))
    apply_auto_legend(fig, threshold=3)
    # 4 > 3: should flip vertical
    assert fig.layout.legend.orientation == "v"

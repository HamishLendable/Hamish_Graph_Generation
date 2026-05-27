"""Tests for motor_graphs.cli — list / find / render commands."""

from pathlib import Path

import pandas as pd
import pytest
from click.testing import CliRunner

from motor_graphs.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_help_lists_all_commands(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for cmd in ("list", "find", "render"):
        assert cmd in result.output


def test_list_default_shows_styles_and_recipes(runner):
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    # spot-check one style and one recipe appear
    assert "heatmap_swap" in result.output
    assert "dq_aging_by_grade" in result.output


def test_list_kind_style(runner):
    result = runner.invoke(cli, ["list", "--kind", "style"])
    assert result.exit_code == 0
    assert "heatmap_swap" in result.output
    # Recipe should NOT appear
    assert "dq_aging_by_grade" not in result.output


def test_list_kind_recipe(runner):
    result = runner.invoke(cli, ["list", "--kind", "recipe"])
    assert result.exit_code == 0
    assert "dq_aging_by_grade" in result.output
    # Style should NOT appear
    assert "heatmap_swap" not in result.output


def test_find_hits_swap(runner):
    result = runner.invoke(cli, ["find", "swap"])
    assert result.exit_code == 0
    assert "heatmap_swap" in result.output


def test_find_no_match_exits_nonzero(runner):
    result = runner.invoke(cli, ["find", "zzz_does_not_exist"])
    assert result.exit_code == 1


def test_render_unknown_style(runner, tmp_path):
    csv = tmp_path / "fake.csv"
    csv.write_text("a,b\n1,2\n")
    result = runner.invoke(
        cli,
        ["render", "definitely_not_a_style", str(csv), "--out", str(tmp_path / "out")],
    )
    assert result.exit_code == 1
    assert "Unknown style" in result.output


def test_render_writes_png_and_html(runner, tmp_path):
    # Build a tiny fixture matching the heatmap_swap data shape
    df = pd.DataFrame({
        "x_grade": ["A", "A", "B", "B"],
        "y_grade": ["A", "B", "A", "B"],
        "count":   [100, 20, 30, 80],
    })
    csv_path = tmp_path / "swap.csv"
    df.to_csv(csv_path, index=False)

    out_stem = tmp_path / "rendered"
    result = runner.invoke(
        cli,
        ["render", "heatmap_swap", str(csv_path), "--out", str(out_stem),
         "-k", "amount_share=None"],
    )
    assert result.exit_code == 0, result.output
    assert Path(f"{out_stem}.png").exists()
    assert Path(f"{out_stem}.html").exists()


def test_render_bad_kwarg_format(runner, tmp_path):
    csv = tmp_path / "fake.csv"
    csv.write_text("a,b\n1,2\n")
    result = runner.invoke(
        cli,
        ["render", "heatmap_swap", str(csv), "--out", str(tmp_path / "out"), "-k", "no_equals_sign"],
    )
    assert result.exit_code == 2
    assert "name=value" in result.output

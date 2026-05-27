"""motor-graph CLI — `list`, `find`, `render` commands.

Wired as an entry point via ``[project.scripts]`` in pyproject.toml so users get
a ``motor-graph`` shell command after ``poetry install``.

Sub-commands:
    motor-graph list                          — show every style + recipe
    motor-graph find <keyword>                — substring search across docstrings
    motor-graph render <style> <csv> --out p  — render a style from a CSV file
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click
import pandas as pd

import motor_graphs
from motor_graphs.catalogue import build_catalogue, search


def _coerce(value: str) -> Any:
    """Convert a string from the CLI to int / float / bool / str."""
    lower = value.lower()
    if lower in ("true", "false"):
        return lower == "true"
    if lower == "none":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=motor_graphs.__version__, prog_name="motor-graph")
def cli() -> None:
    """motor-graph: discoverable chart-style library for MoTa credit risk."""


@cli.command("list")
@click.option(
    "--kind",
    type=click.Choice(["all", "style", "recipe"]),
    default="all",
    help="Filter by entry kind (default: all).",
)
def list_(kind: str) -> None:
    """List every chart style and / or recipe."""
    cat = build_catalogue()
    entries = []
    if kind in ("all", "style"):
        entries.extend(cat["styles"])
    if kind in ("all", "recipe"):
        entries.extend(cat["recipes"])
    width_name = max((len(e["name"]) for e in entries), default=30)
    click.echo(f"{'kind':7}  {'name':{width_name}}  summary")
    click.echo(f"{'-' * 7}  {'-' * width_name}  {'-' * 40}")
    for e in entries:
        summary = (e["summary"] or "").replace("\n", " ")
        click.echo(f"{e['kind']:7}  {e['name']:{width_name}}  {summary[:80]}")


@cli.command()
@click.argument("query")
def find(query: str) -> None:
    """Substring-search name, summary, use_when, data_shape and snowflake_tables_used."""
    hits = search(query)
    if not hits:
        click.echo(f"No matches for {query!r}.", err=True)
        sys.exit(1)
    for entry in hits:
        click.secho(f"\n[{entry['kind']}] {entry['name']}", bold=True)
        if entry["summary"]:
            click.echo(f"  {entry['summary']}")
        if entry["use_when"]:
            click.echo("  Use when:")
            for line in entry["use_when"].split("\n")[:5]:
                click.echo(f"    {line.strip()}")
        if entry["data_shape"]:
            shape_first_line = entry["data_shape"].split("\n", 1)[0]
            click.echo(f"  Data shape: {shape_first_line}")
        click.echo(f"  Module: {entry['module']}")


@cli.command()
@click.argument("style_name")
@click.argument("csv_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    required=True,
    help="Output path stem (PNG + HTML created with this stem).",
)
@click.option(
    "--kwarg",
    "-k",
    multiple=True,
    help="Style kwarg as name=value, e.g. -k x=cohort -k title='My chart'. "
    "Coerces 'true'/'false'/numbers automatically.",
)
def render(style_name: str, csv_path: Path, out: Path, kwarg: tuple[str, ...]) -> None:
    """Render a chart style from a CSV file (writes PNG + HTML)."""
    from motor_graphs import styles

    if style_name not in styles.__all__:
        click.echo(
            f"Unknown style {style_name!r}. Run `motor-graph list --kind style` for options.",
            err=True,
        )
        sys.exit(1)

    fn = getattr(styles, style_name)
    df = pd.read_csv(csv_path)

    kwargs: dict[str, Any] = {}
    for kw in kwarg:
        if "=" not in kw:
            click.echo(f"Bad --kwarg {kw!r}; expected name=value.", err=True)
            sys.exit(2)
        key, val = kw.split("=", 1)
        kwargs[key] = _coerce(val)

    fig = fn(df, **kwargs)
    motor_graphs.save_figure(fig, out)
    click.echo(f"rendered {out}.png and {out}.html")


def main() -> None:
    """Entry point referenced by [project.scripts] in pyproject.toml."""
    cli()


if __name__ == "__main__":
    main()

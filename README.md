# motor-graph-generation

A discoverable Python library of MoTa-styled Plotly chart primitives for Lendable UK motor finance.

The consumer pattern is **"I have a tidy DataFrame and a question — which chart fits?"**. The library exposes 25 named chart styles + 8 Snowflake-aware recipes, each as a function taking a `pandas.DataFrame` and returning a `plotly.graph_objects.Figure`. PNG and interactive HTML are saved side-by-side.

## Status

**v0.1.0** — production-ready for the v0.1 catalogue. 131 tests passing.

## Quickstart

```bash
poetry install
cp .env.example .env
# edit .env with your SNOWFLAKE_USERNAME
```

Authentication is Okta browser SSO — no password needed.

### Use a chart style directly (data you already have)

```python
import pandas as pd
from motor_graphs import save_figure, styles

df = pd.read_csv("my_dq_data.csv")
fig = styles.dq_2x2_actual_vs_expected(df, title="Motor DQ — Apr 2026")
save_figure(fig, "out/dq_apr2026")  # writes PNG + HTML
```

### Use a recipe (load real Snowflake data + render)

```python
from datetime import date
from motor_graphs import recipes, save_figure

fig = recipes.dq_aging_by_grade(date(2024, 1, 1), date(2025, 12, 31))
save_figure(fig, "out/dq_aging_2024_2025")
```

### Discover the right chart for your data

```bash
poetry run motor-graph list                       # 33-row table of every style + recipe
poetry run motor-graph find swap                  # search across docstrings
poetry run motor-graph find calibration
poetry run motor-graph render heatmap_swap data/swap.csv --out out/swap
```

Or from Python:

```python
from motor_graphs.catalogue import build_catalogue, search

cat = build_catalogue()
print(f"{cat['n_styles']} styles, {cat['n_recipes']} recipes")
for hit in search("dealer"):
    print(hit['name'], '—', hit['summary'])
```

## Architecture

```
motor_graphs/
├── styles/      ← 25 chart-style primitives — THE product. Tidy-DataFrame in, Figure out.
├── recipes/     ← 8 Snowflake-aware wrappers — load real data + call a style.
├── style/       ← palette + Plotly template (the visual lock-in).
├── data/        ← Okta-authenticated SnowflakeReader connection pool.
├── catalogue.py ← introspects styles + recipes from docstrings → docs/catalogue.json.
└── cli.py       ← motor-graph list / find / render.
```

## Documentation

For users picking the right chart:
- **[docs/chart_finder.md](docs/chart_finder.md)** — start here. Data-shape → style index. The agent-facing entry point.
- **[docs/gallery.md](docs/gallery.md)** — auto-generated. Rendered baseline PNG for every style.
- **[docs/catalogue.json](docs/catalogue.json)** — machine-readable. For programmatic search.

For contributors:
- **[docs/styling.md](docs/styling.md)** — palette, template, house rules.
- **[docs/extending.md](docs/extending.md)** — how to add a new style or recipe.
- **[docs/discovery/](docs/discovery/)** — original Batch 1 extraction from `credit.auto-monthly-monitoring` (chart inventory, palette spec, Snowflake conventions). Reference docs, frozen in time.
- **[CHANGELOG.md](CHANGELOG.md)** — version history.

## Prerequisites

- **Python 3.11** (only — not 3.12)
- **[Poetry](https://python-poetry.org/)** ≥ 2.x
- **Snowflake access** via Okta (READER_PROD role) — required for recipes, not for styles
- **Access to the Lendable internal PyPI** (`https://pypi.tools.int.zable.co.uk/`) — required for `lentils`

## Universal house rules

- Every primitive annotates `n=` by default (`annotate_n=False` to suppress).
- Actual = `#1f77b4` solid 2-px; Expected = `#d62728` dashed 2-px. Hardcoded.
- Risk-grade buckets when grouping: A-B / C-E / F+.
- £-weighted by default; the "Note: All rates are £ weighted." footnote is added automatically.
- 1440 × 740 px canvas unless overridden.
- `plotly_white+motor` template — switch the base via `motor_graphs.style.set_background("plotly")` for the reference-deck lavender look.

## Development

```bash
# Install dev deps
poetry install

# Run tests (excluding live-Snowflake tests)
poetry run pytest -m "not snowflake"

# Run the live-Snowflake smoke test (opens an Okta browser tab)
poetry run python scripts/snowflake_smoke_test.py

# Regenerate baseline PNGs after intentional style changes
poetry run python scripts/refresh_baselines.py

# Regenerate docs/catalogue.json + docs/gallery.md after docstring changes
poetry run python scripts/build_catalogue.py

# Pre-commit hooks (one-off setup)
poetry run pre-commit install
```

## Support

Maintainer: Hamish Aitken (hamish.aitken@lendable.co.uk).

# How to add a new chart style

Adding a new style is mechanical. Follow these 8 steps. Total work: 30–60 minutes for a basic style, more for complex multi-panel layouts.

## 1. Pick a name + module

- Name: `snake_case`, descriptive of visual + data shape. Examples: `bar_horizontal_top_n`, `cohort_lines_1x3_by_grade_group`, `heatmap_swap`. Bad: `chart_3`, `foo_plot`.
- Module: where it lives in `motor_graphs/styles/`. Use the existing modules where possible:

| Module | Holds |
|---|---|
| `bars.py` / `more_bars.py` | Bar charts |
| `lines.py` / `multi_lines.py` / `dq_subplots.py` | Line charts |
| `heatmaps.py` | Heatmaps |
| `scatters.py` | Scatter / calibration |
| `distributions.py` | Violin / box / histogram |
| `specialised.py` | Anything that doesn't fit elsewhere |

If your new style genuinely needs a new module, create one — but check the existing ones first.

## 2. Write the function

Standard signature template:

```python
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from motor_graphs.style import apply_auto_legend
from motor_graphs.style.palette import ACTUAL, EXPECTED, GRADE_COLOURS  # plus anything else
from ._shared import (
    SmallSampleMode,
    add_pound_weighted_footnote,
    opacity_for_n,
    require_columns,
    resolve_n_column,
)


def my_new_style(
    df: pd.DataFrame,
    *,
    # column-name params with sensible defaults that match common fixture columns
    x: str = "x",
    y: str = "y",
    n: str | None = "n",
    # display kwargs
    title: str | None = None,
    xlabel: str = "...",
    ylabel: str = "...",
    y_tickformat: str = ".1%",
    # universal kwargs (mandatory)
    annotate_n: bool = True,
    small_sample_handling: SmallSampleMode = "show",
) -> go.Figure:
    """One-line summary (this appears in `motor-graph list`).

    Use this when:
        - <natural-language scenario where this chart is the right answer>
        - <one more example so the agent has multiple anchors>

    Data shape:
        Long/tidy DataFrame with columns:
            x  (type)   — description
            y  (type)   — description
            n  (int, opt) — sample size; required if annotate_n=True

    Style:
        Visual pattern in 1–3 sentences. Mention colours and any special behaviour.

    Parameters:
        df: input DataFrame.
        x, y, n: column names.
        title, xlabel, ylabel: figure labels.
        annotate_n: if True (default), annotate n= where appropriate.
        small_sample_handling: "show" / "fade" / "suppress".

    Returns:
        plotly.graph_objects.Figure with N traces.

    Example:
        >>> df = pd.read_csv("my_fixture.csv")
        >>> fig = my_new_style(df, title="Demo")
    """
    require_columns(df, [x, y], who="my_new_style")
    n_col = resolve_n_column(df, n, annotate_n=annotate_n)

    fig = go.Figure()
    # ... build traces using palette constants only — no magic hex ...

    fig.update_layout(title=title or "My new style", xaxis_title=xlabel, yaxis_title=ylabel)
    add_pound_weighted_footnote(fig)
    apply_auto_legend(fig)
    return fig
```

Key rules:
- First positional arg is always `df: pd.DataFrame`. Everything else is keyword-only (use `*,`).
- Validate inputs up-front via `require_columns` and `resolve_n_column`.
- Never inline hex codes — import from `motor_graphs.style.palette`.
- End with `add_pound_weighted_footnote(fig)`, then `apply_auto_legend(fig)`, then `return fig`.
- The docstring sections (`Use this when:`, `Data shape:`, `Style:`, `Parameters:`, `Returns:`, `Example:`) are not optional — they drive `docs/catalogue.json` and `docs/gallery.md` and the `motor-graph find` CLI.

## 3. Add a fixture

Add a generator function to `tests/fixtures/_regen.py` (or to one of the `_regen_5b_*.py` sibling files — they're auto-discovered):

```python
def _my_new_style() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    # ... generate deterministic synthetic data matching the function's expected shape ...
    return df

SPECS = {
    ...,
    "my_new_style.csv": _my_new_style,
}
```

Run `poetry run python tests/fixtures/_regen.py` to materialize the CSV.

## 4. Export from the package

Update `motor_graphs/styles/__init__.py`:

```python
from .your_module import my_new_style

__all__ = [
    ...,
    "my_new_style",
]
```

## 5. Add to the baseline registry

Update `scripts/refresh_baselines.py`:

```python
REGISTRY = [
    ...,
    (
        "my_new_style",
        "my_new_style.csv",
        styles.my_new_style,
        dict(title="my_new_style — synthetic"),
    ),
]
```

Run `poetry run python scripts/refresh_baselines.py` to generate the baseline PNG + HTML. They land in `tests/baselines/` and are committed to the repo.

## 6. Write tests

Add to `tests/test_styles.py`:

```python
def test_my_new_style_returns_figure():
    fig = styles.my_new_style(_load("my_new_style.csv"))
    assert isinstance(fig, go.Figure)


def test_my_new_style_annotate_n_off():
    df = _load("my_new_style.csv")
    fig = styles.my_new_style(df, annotate_n=False)
    assert _n_annotations(fig) == []


def test_my_new_style_validates_required_cols():
    df = _load("my_new_style.csv").drop(columns=["y"])
    with pytest.raises(ValueError):
        styles.my_new_style(df)
```

At minimum: returns Figure, annotate_n=False suppresses, validators fire.

Also update the `test_styles_module_exports_all_25` test (rename to `_26` etc.) — keep the count assertion accurate.

## 7. Regenerate catalogue + gallery

```bash
poetry run python scripts/build_catalogue.py
```

This re-reads every docstring and rewrites `docs/catalogue.json` + `docs/gallery.md`. Spot-check the gallery entry for your new style.

## 8. Run pytest, commit

```bash
poetry run pytest -m "not snowflake"
git add motor_graphs/styles/your_module.py \
        motor_graphs/styles/__init__.py \
        tests/fixtures/_regen*.py \
        tests/fixtures/my_new_style.csv \
        tests/baselines/my_new_style.png \
        tests/baselines/my_new_style.html \
        tests/test_styles.py \
        scripts/refresh_baselines.py \
        docs/catalogue.json \
        docs/gallery.md
git commit -m "add my_new_style chart"
```

Don't forget to update `docs/chart_finder.md` if your style answers a question the existing taxonomy doesn't cover (the agent-facing data-shape index is hand-curated, not auto-generated).

---

# How to add a new recipe

Same idea but lighter:

1. Pick a name + module under `motor_graphs/recipes/`.
2. Write the function:

```python
from motor_graphs import styles
from motor_graphs.data import snowflake
from ._shared import validate_cohort_range, ORIGINATED_FLAG_PREDICATE


def my_new_recipe(
    cohort_start,
    cohort_end,
    *,
    title: str | None = None,
) -> go.Figure:
    """One-line summary.

    Use this when:
        - <natural-language scenario>

    Snowflake tables used:
        - PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR — purpose
        - ...

    Returns:
        plotly.graph_objects.Figure (via styles.<style_name>)

    Example:
        >>> fig = my_new_recipe(date(2024, 1, 1), date(2024, 12, 31))
    """
    start, end = validate_cohort_range(cohort_start, cohort_end)
    sql = f"""
        SELECT ...
        FROM PROD.X.Y a
        WHERE a.APPLICATION_CREATED_DATETIME >= '{start}'
          AND a.APPLICATION_CREATED_DATETIME <  '{end}'
          AND {ORIGINATED_FLAG_PREDICATE}
    """
    df = snowflake.run_query(sql)
    # pandas reshape if needed
    return styles.some_style(df, title=title or f"My recipe — {start} to {end}")
```

3. Export from `motor_graphs/recipes/__init__.py`.

4. Mocked test:

```python
def test_my_new_recipe(monkeypatch):
    fake = pd.DataFrame({...})
    monkeypatch.setattr(snowflake, "run_query", lambda sql: fake)
    fig = my_new_recipe("2024-01-01", "2024-04-01")
    assert isinstance(fig, go.Figure)
```

5. `poetry run python scripts/build_catalogue.py` to refresh the catalogue.

Recipes never go in the visual baseline gallery — they're not deterministic against synthetic data the way styles are.

---

# What to do when you change `palette.py` or `template.py`

These changes affect *every* baseline. The workflow:

```bash
# 1. Make your change in motor_graphs/style/palette.py (or template.py)
# 2. Regenerate every baseline
poetry run python scripts/refresh_baselines.py

# 3. Visually review the deltas
git diff tests/baselines/*.png  # binary diff — use `git show <file>` to view

# 4. If the deltas are intentional, commit
git add motor_graphs/style/ tests/baselines/
git commit -m "tweak palette: <what changed>"

# 5. Run pytest to confirm no tests broke
poetry run pytest -m "not snowflake"
```

Style changes are the keystone of the library. Take them seriously and review every baseline diff.

# CLAUDE.md — motor-graph-generation

Operational notes for Claude Code. `README.md` covers what the library is and
how to use it; this file is the **landmine map**: things that aren't in README
that, if you get them wrong, waste a session or break the visual lock-in.

For everything else, defer to:
- `README.md` — quickstart, public API
- `docs/styling.md` — palette / template / house rules
- `docs/extending.md` — step-by-step recipes for adding a style or recipe
- `docs/chart_finder.md` — data-shape → style index (the agent-facing entry)
- `docs/discovery/{chart_inventory,palette,snowflake_conventions}.md` — Batch 1
  extraction; **frozen reference, do not edit**

---

## Landmines (read first)

1. **Python 3.11 only.** `pyproject.toml:6` pins `>=3.11,<3.12`. Do not bump
   to 3.12 without checking `kaleido==0.2.1` and `lentils[snowflake]`
   compatibility.
2. **`lentils` lives on Lendable's internal PyPI**
   (`https://pypi.tools.int.zable.co.uk/`, `pyproject.toml:24-27`). Not
   reachable from GitHub Actions, so **CI runs ruff only — not pytest**
   (`.github/workflows/lint.yml`). Don't assume green CI means tests passed;
   run `poetry run pytest -m "not snowflake"` locally.
3. **Auto-generated files — never hand-edit:**
   - `docs/catalogue.json` and `docs/gallery.md` → regenerate with
     `poetry run python scripts/build_catalogue.py`
   - `tests/baselines/*.{png,html}` → regenerate with
     `poetry run python scripts/refresh_baselines.py`
   - `tests/fixtures/*.csv` → regenerate via the `_regen*.py` scripts in
     `tests/fixtures/`
   The next regen run will silently overwrite any hand edits.
4. **Colours are hardcoded by design.** Every hex lives in
   `motor_graphs/style/palette.py`. Do **not** parameterize, do **not** inline
   hex anywhere else in the codebase. The actual=blue / expected=red-dashed
   pairing is a load-bearing convention, not a default.
5. **The env var is `SNOWFLAKE_USERNAME`, not `SNOWFLAKE_USER`.** Lentils
   reads the former. See `.env.example`. Wrong name = silent auth failure.
6. **`run_query` lowercases column names**
   (`motor_graphs/data/snowflake.py:115`). All recipe code works in lowercase
   — write `df["origination_datetime"]`, not `df["ORIGINATION_DATETIME"]`.
7. **Every chart-style docstring drives docs.** Sections `Use this when:`,
   `Data shape:`, `Style:`, `Parameters:`, `Returns:`, `Example:` are parsed
   by `motor_graphs/catalogue.py` into `docs/catalogue.json` and
   `docs/gallery.md`. Recipes use `Snowflake tables used:` instead of
   `Data shape:`. Skipping these breaks `tests/test_catalogue.py`.
8. **`styles.__all__` and `recipes.__all__` are tested for exact counts**
   (`tests/test_catalogue.py:7-18` — 25 styles, 8 recipes). Adding or
   removing a function requires updating both the `__all__` list **and**
   the count assertions in `test_catalogue.py`.
9. **Recipes call Snowflake via the module reference.** They invoke
   `snowflake.run_query(...)` so tests can do
   `monkeypatch.setattr(snowflake, "run_query", ...)`. Don't write
   `from motor_graphs.data.snowflake import run_query` inside a recipe —
   that shortcut breaks the monkeypatch pattern used in every
   `tests/test_recipes_*.py`.
10. **Canvas is 1440 × 740 px**, applied at `save_figure` time
    (`motor_graphs/__init__.py:22-24`), not inside individual styles. Don't
    bake width/height into a style's `update_layout` call.
11. **`segment_compare_2x2_with_gap`** was renamed from
    `bev_vs_rob_2x2_with_gap` and now requires `a_good_share` /
    `b_good_share` columns (CHANGELOG §"Known limitations"). Don't
    reintroduce the old name.
12. **`docs/discovery/` is frozen.** It's the Batch 1 extraction from the
    reference repo (`credit.auto-monthly-monitoring`) and is treated as a
    historical spec, not living docs. Update `docs/styling.md` or
    `docs/extending.md` instead.

---

## Project shape in 30 seconds

```
motor_graphs/
├── styles/    25 chart primitives. df → Figure. THE product.
├── recipes/    8 Snowflake-aware wrappers. (cohort_start, cohort_end) → Figure.
├── style/     palette.py + template.py — the visual lock-in. Importing
│              motor_graphs.style registers the 'motor' Plotly template.
├── data/      SnowflakeReader pool + run_query + @cached decorator.
├── catalogue.py   walks styles + recipes, parses docstrings → JSON.
└── cli.py     motor-graph {list,find,render}
```

`motor_graphs/style/` (singular) is **not** the same as `motor_graphs/styles/`
(plural). `style/` = visual lock-in (palette + template); `styles/` = the
25 chart primitives. The naming is intentional but trips everyone once.

A **style** takes a tidy DataFrame and renders. A **recipe** loads Snowflake
data, reshapes it, then calls a style. Styles are deterministic and have
PNG baselines committed; recipes don't (they're tested with mocked
`run_query`).

---

## Where to look first

| Task | Start here |
|---|---|
| Add a new chart style | `docs/extending.md` (full procedure) |
| Add a new recipe | `docs/extending.md` §"How to add a new recipe" |
| Change a colour or template setting | `motor_graphs/style/palette.py`, then `scripts/refresh_baselines.py` (every baseline will need re-rendering) |
| Tweak universal house rules (n=, £-footnote, small-sample fade) | `motor_graphs/styles/_shared.py` |
| Debug why `motor-graph find <kw>` doesn't match | `motor_graphs/catalogue.py` (`search()` covers name, summary, use_when, data_shape, snowflake_tables_used) |
| Debug a recipe SQL | `motor_graphs/recipes/<area>.py` (`dq.py`, `volume.py`, `risk.py`, `funnel_distributions.py`); run `scripts/snowflake_smoke_test.py` to exercise auth |
| Change risk-grade buckets | `motor_graphs/recipes/_shared.py` (`RISK_GRADE_GROUPS`, `grade_to_group`) and `palette.py` (`GRADE_GROUP_COLOURS`) |
| Investigate a Snowflake auth failure | `.env` (check `SNOWFLAKE_USERNAME`, not `USER`), then `motor_graphs/data/snowflake.py:108-113` (error message points at the fix) |
| Regenerate docs after docstring edits | `poetry run python scripts/build_catalogue.py` |
| Regenerate baselines after a style/palette change | `poetry run python scripts/refresh_baselines.py` |
| Re-create test fixtures | `poetry run python tests/fixtures/_regen.py` (auto-discovers `_regen_5b_*.py` siblings) |
| Check the public API surface | `motor_graphs/__init__.py` + `styles/__init__.py` + `recipes/__init__.py` |

---

## Invariants (don't break these)

- Every chart style has the signature `fn(df: pd.DataFrame, *, ...) -> go.Figure`.
  First arg positional, everything else keyword-only.
- Every style starts with `require_columns(df, [...], who="<fn name>")` and,
  if it shows n=, `resolve_n_column(df, n, annotate_n=annotate_n)`
  (`motor_graphs/styles/_shared.py`).
- Every style invokes `add_pound_weighted_footnote(fig)` and
  `apply_auto_legend(fig)` before returning — universal across all 9 style
  modules.
- Every style accepts `annotate_n: bool = True` and (where small-sample
  fading applies) `small_sample_handling: SmallSampleMode = "show"`.
- Colours come from `motor_graphs.style.palette` imports — **no inline hex
  outside `palette.py`**. `docs/styling.md` flags this as a possible future
  CI grep check.
- Every recipe takes `(cohort_start, cohort_end)` as positional args (both
  `date | str`) and calls `validate_cohort_range(...)` first
  (`motor_graphs/recipes/_shared.py:31`).
- Every recipe filters with the canonical predicate
  `COALESCE(FLAG_ORIGINATED_AND_NOT_CANCELLED, FLAG_ORIGINATED) = TRUE`
  (exposed as `ORIGINATED_FLAG_PREDICATE` in `recipes/_shared.py:77`).
- Tables are `PROD.PRS_MOTOR.*`, `PROD.MRT_MOTOR.*`, `PROD.INT_MOTOR.*`.
  Database / warehouse / role are hardcoded `PROD / READER_PROD /
  READER_PROD` via Okta SSO — don't parameterize.

---

## Auto-generated artefacts (never hand-edit)

| File / dir | Generator | When to regenerate |
|---|---|---|
| `docs/catalogue.json` | `scripts/build_catalogue.py` | After any docstring change in `styles/` or `recipes/`, or after adding/removing a function |
| `docs/gallery.md` | `scripts/build_catalogue.py` | Same as above |
| `tests/baselines/*.png` and `*.html` | `scripts/refresh_baselines.py` | After any change in `motor_graphs/style/` (palette or template) or in a style function |
| `tests/fixtures/*.csv` | `tests/fixtures/_regen.py` (+ siblings `_regen_5b_a..d.py`) | After changing a fixture spec — rare |

`docs/discovery/*.md` is frozen-in-time reference, not auto-generated, but
also **not** to be hand-edited as part of ongoing work — treat it as a spec
snapshot from Batch 1.

---

## Commands you'll actually run

```bash
# Fast feedback loop (no Snowflake)
poetry run pytest -m "not snowflake"

# Single test file / single test
poetry run pytest tests/test_styles.py -k dq_2x2

# Live Snowflake smoke test (opens Okta browser tab on first run)
poetry run python scripts/snowflake_smoke_test.py

# After docstring or style/recipe addition
poetry run python scripts/build_catalogue.py

# After palette / template / style-behaviour change
poetry run python scripts/refresh_baselines.py
# Baselines are binary PNGs — use `git show` or open them; git diff is unhelpful

# CLI
poetry run motor-graph list
poetry run motor-graph find <keyword>
poetry run motor-graph render <style_name> <csv> --out out/<stem> -k title='...'
```

---

## Snowflake gotchas

- **Auth**: Okta browser SSO via
  `lentils.snowflake.SnowflakeReader.from_connection(authenticator="okta",
  database="PROD", warehouse="READER_PROD", role="READER_PROD")`. No
  password in `.env`.
- **Env var**: `SNOWFLAKE_USERNAME` (not `SNOWFLAKE_USER`).
- **Pool**: thread-safe singleton in `motor_graphs/data/snowflake.py`,
  30-minute idle TTL. Reset between tests with
  `snowflake.SnowflakeConnectionPool().reset()`.
- **Cache**: `@snowflake.cached(ttl_hours=24)` is **opt-in** per function;
  default cache dir is `~/.cache/motor-graphs/`. Apply only to
  deterministic helpers, not whole recipes.
- **Columns are lowercased** post-query. Always.
- **CI does not run pytest** because lentils is on the internal PyPI. Don't
  assume green CI = working code.
- **Test pattern for recipes** (every `tests/test_recipes_*.py` does this):
  ```python
  monkeypatch.setattr(snowflake, "run_query", lambda sql: fake_df)
  ```
  This requires recipes to call `snowflake.run_query(...)` via the module
  reference — not via a `from ... import run_query` shortcut.
- **Live tests are marked `@pytest.mark.snowflake`** and excluded by default
  (`pyproject.toml:65-68`). Run them with
  `poetry run pytest -m snowflake`.

---

## Adding a style or recipe — file checklist

`docs/extending.md` has the full procedure with code templates. The
checklist of files that must change together (forgetting any one breaks
something downstream):

**For a new style:**
- `motor_graphs/styles/<module>.py` — the function with full docstring
  sections (`Use this when:`, `Data shape:`, `Style:`, `Parameters:`,
  `Returns:`, `Example:`)
- `motor_graphs/styles/__init__.py` — import + add to `__all__`
- `tests/fixtures/_regen.py` (or a `_regen_5b_*.py` sibling) — add fixture
  spec, run regen
- `scripts/refresh_baselines.py` — add to the registry, run to produce baseline
- `tests/test_styles.py` — at minimum: returns-Figure / annotate_n-off /
  validators-fire
- `tests/test_catalogue.py` — bump the 25 → N count in
  `test_catalogue_lists_all_25_styles`
- `docs/chart_finder.md` — hand-curated; add the new style if it answers a
  new data-shape question
- Run `scripts/build_catalogue.py` to regenerate `docs/catalogue.json` +
  `docs/gallery.md`

**For a new recipe:** same idea but no baseline (recipes aren't
deterministic against synthetic data) and tests use mocked `run_query`
(see `tests/test_recipes_5e.py` for the canonical pattern). Bump the 8 → N
count in `test_catalogue_lists_all_8_recipes` and use docstring section
`Snowflake tables used:` instead of `Data shape:`.

---

## Project state

- v0.1.0 (2026-05-26), single tagged release. Git log shows a single
  Batch 1 commit; batches 2–7 (palette, template, styles, recipes,
  catalogue, tests, docs) were collapsed into the 0.1.0 release — see
  `CHANGELOG.md` for the full inventory.
- 131 tests passing locally (97 style + 16 recipe + 9 catalogue + 9 CLI);
  1 live-Snowflake test gated behind `@pytest.mark.snowflake`.
- Maintainer: Hamish Aitken (hamish.aitken@lendable.co.uk).

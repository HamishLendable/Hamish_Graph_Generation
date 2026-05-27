# Changelog

All notable changes to motor-graph-generation are recorded here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-05-26

### Initial release

A discoverable Python library of MoTa-styled Plotly chart primitives for Lendable UK motor finance. Mirrors the visual style of `credit.auto-monthly-monitoring` while exposing reusable chart-style functions instead of a monitoring-deck pipeline.

#### Added

**25 chart styles** in `motor_graphs.styles` — each a Plotly function taking a tidy `pandas.DataFrame` and returning a `Figure`. PNG + interactive HTML saved side-by-side via `motor_graphs.save_figure`.

Bars: `grouped_bars_by_grade_two_series`, `stacked_bar_100pct_monthly_2x2`, `bar_horizontal_top_n`, `bar_plus_line_share_top_n`, `stacked_bar_volume_2x2_with_rate_line`, `waterfall_components_by_grade`.

Lines: `cohort_lines_vs_mob`, `dq_2x2_actual_vs_expected`, `dq_2x2_with_n_annotated`, `regression_validation_1x3`, `cohort_lines_1x3_by_grade_group`, `cohort_lines_1x3_paired_expected`, `roll_rate_dual_axis_lines`, `lines_1x2_funnel_by_introducer`, `lines_with_overall_highlight`, `segment_compare_2x2_with_gap`, `lines_funnel_by_introducer_1x1`, `line_with_ci_band`.

Heatmaps / scatter: `heatmap_swap`, `scatter_calibration`.

Distributions: `violin_grouped`, `box_quantile`, `histogram_by_grade`.

Specialised: `cohort_grid_grade_x_period`, `funnel_horizontal`.

**8 recipes** in `motor_graphs.recipes` — thin Snowflake-aware wrappers that load real PROD data via `motor_graphs.data.snowflake` (Okta SSO via `lentils`):

- `dq_aging_by_grade`, `dq_2x2_recent_book`
- `introducer_volume_league_table`, `introducer_volume_mix_monthly`
- `funnel_app_to_originated`, `score_distribution_by_grade`
- `pd_calibration_irr`, `segment_compare_dealer_vs_nondealer`

**Data layer** (`motor_graphs.data.snowflake`): thread-safe `SnowflakeConnectionPool` singleton with 30-min idle TTL (mirrors `credit.auto-monthly-monitoring/data_loader.py`), `run_query(sql)` returning lowercased-column DataFrames, opt-in `@cached(ttl_hours=24)` decorator pickling to `~/.cache/motor-graphs/`.

**Style lock-in** (`motor_graphs.style`): palette constants (4-role spine + grade colours + cohort cycle + introducer dict + heatmap scales), custom `motor` Plotly template extending `plotly_white`, helpers `set_background()` and `apply_auto_legend(fig)`.

**Discoverability**:
- `motor_graphs.catalogue` — introspection + search built from docstrings
- `docs/catalogue.json` — machine-readable index (33 entries)
- `docs/gallery.md` — auto-generated visual gallery with embedded baseline PNGs
- `docs/chart_finder.md` — hand-curated data-shape → style index (the agent-facing entry point)
- `motor-graph` CLI: `list`, `find <kw>`, `render <style> <csv> --out <path>`

**Tests**: 131 passing (97 style + 16 recipe + 9 catalogue + 9 CLI), 1 live-Snowflake test gated behind `@pytest.mark.snowflake`.

**Docs**: README quickstart, `docs/discovery/` (the original style + palette + Snowflake extraction), `docs/styling.md`, `docs/extending.md`.

**CI**: `.github/workflows/lint.yml` — ruff on every push and PR. Full pytest is run locally (lentils private PyPI not reachable from GitHub Actions).

### Architecture decisions

- **Plotly-only** — no matplotlib. Mirrors the reference repo.
- **Poetry + internal PyPI** — `lentils[snowflake]` from `https://pypi.tools.int.zable.co.uk/`.
- **`plotly_white+motor` template** — uniform white background. Switch to lavender via `motor_graphs.style.set_background("plotly")` if you want the delinquency-section reference-deck look.
- **`annotate_n=True` is universal** — every style shows sample sizes by default. Stricter than the reference, which only annotates n= on EV charts.
- **Generic two-segment compare** — `segment_compare_2x2_with_gap` works for BEV/ROB, Carrera/Torino, dealer/non-dealer, co-applicant/sole, etc. The original BEV-specific `bev_vs_rob_2x2_with_gap` was generalised during iteration.

### Known limitations / v0.2 candidates

- `waterfall_components_by_grade` is a grouped-components view, not a true running-total bridge waterfall. Iterate if a bridge view becomes valuable.
- `bev_vs_rob_2x2_with_gap` was renamed to `segment_compare_2x2_with_gap` and now needs `a_good_share` / `b_good_share` columns on the input DataFrame for the grade-mix panel.
- Full pytest in CI requires configuring `lentils` source credentials as a GitHub secret (deferred for v0.1).
- No matplotlib backend. If a consumer specifically needs matplotlib output, add a sibling `_mpl.py` per chart family.

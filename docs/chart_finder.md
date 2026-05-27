# Chart finder — pick the right style for your data shape

This is the agent-facing index. Scan top-to-bottom; the first matching pattern is usually the right answer. If you only know the MoTa question (not the data shape), skip to the **MoTa shortcuts** section at the bottom.

Companion files:
- [`gallery.md`](gallery.md) — auto-generated, rendered baseline PNGs for every style
- [`catalogue.json`](catalogue.json) — machine-readable index (use this from code: `motor_graphs.catalogue.build_catalogue()`)
- `motor-graph list` / `motor-graph find <kw>` — same data from the CLI

---

## Time-series patterns (x = month or MOB)

### One rate over time, single line
**Data shape:** `month, rate, n` (one row per month).
→ Use `lines_with_overall_highlight` with just the one segment.

### One rate over time, with confidence band
**Data shape:** `month, group, rate, ci_lower, ci_upper, n` (one row per (month, group)).
→ Use `line_with_ci_band`.

### Multiple cohort lines vs MOB (cumulative behaviour curve)
**Data shape:** `cohort, mob, rate, n` (+ optional `expected`).
→ Use `cohort_lines_vs_mob` — single panel.
→ Use `cohort_lines_1x3_by_grade_group` — if you also have `grade_group` and want one panel per A-B / C-E / F+.
→ Use `cohort_lines_1x3_paired_expected` — if each cohort has its OWN expected curve (not a single benchmark).

### Multiple segments over time + portfolio average
**Data shape:** `month, segment, rate, n` where one segment value is `"Overall"`.
→ Use `lines_with_overall_highlight`.

### One rate per metric, 4 metrics in 2×2 subplots
**Data shape:** `cohort, metric, actual, expected, n` (exactly 4 distinct metrics).
→ Use `dq_2x2_actual_vs_expected` — clean variant; n= on last point only.
→ Use `dq_2x2_with_n_annotated` — if samples are small / EV-like (fades < 200, drops < 50).

### Actual vs predicted, 3 metrics in 1×3 subplots
**Data shape:** `cohort, metric, actual, predicted, n` (exactly 3 metrics).
→ Use `regression_validation_1x3`.

### Two rate-series with very different scales (e.g. 0–1% vs 1–4%)
**Data shape:** wide — `month, small_series, large_series_1, large_series_2, ...`.
→ Use `roll_rate_dual_axis_lines` — pass `small_axis_cols` and `large_axis_cols` explicitly. One series can be dashed via `dashed_cols` (the "counterfactual / improvement" convention).

### One rate per introducer over time (funnel-style)
**Data shape:** `month, introducer, rate, n`.
→ Use `lines_funnel_by_introducer_1x1` — single panel.
→ Use `lines_1x2_funnel_by_introducer` — if you have two rates (e.g. quote rate + quote-to-sale rate).

### Composition mix as % over time (stacked area-like, but bars)
**Data shape:** `month, category, share, n` where `share` ∈ [0, 100] per month sums to 100.
→ Use `stacked_bar_100pct_monthly_2x2` — single panel by default; pass `facet` to lay 4 panels in 2×2 (e.g. by fuel / age / value / LTV bands).

### Volume + composition + book-level rates in one figure (2×2)
**Data shape:** `month, introducer, count, amount, quoted_count, quote_rate, sale_rate`.
→ Use `stacked_bar_volume_2x2_with_rate_line`.

---

## Categorical / comparison patterns (x = grade or category)

### Top-N league table (one bar per category)
**Data shape:** `category, value, n`.
→ Use `bar_horizontal_top_n` — sorted descending by value, n= inside bars, value formatted via `value_fmt`.

### One categorical, two metrics on different scales
**Data shape:** `category, amount_share, count_share, n` (or any two metrics).
→ Use `bar_plus_line_share_top_n` — bars on left axis, line on right axis.

### Two series per grade (e.g. BEV vs ROB, two scorecards, two channels)
**Data shape:** `grade, series, rate, n` where `series` has exactly 2 distinct values.
→ Use `grouped_bars_by_grade_two_series`. (Grade order is locked: A → B → C → D → E → F → F* → F**.)

### Two subpopulations compared with grade-mix decomposition
**Data shape:** `month, a, b, b_adj, gap, a_good_share, b_good_share, n`.
→ Use `segment_compare_2x2_with_gap` — works for BEV vs ROB, Carrera vs Torino, dealer vs non-dealer, co-applicant vs sole, etc. The bottom-left panel shows the grade-mix gap (A-E vs F+), bottom-right shows the mix-adjusted underlying gap.

### X-grade × Y-grade contingency matrix (swap matrix)
**Data shape:** `x_grade, y_grade, count` (+ optional `pct_amount`).
→ Use `heatmap_swap`. Default colorscale is sequential blues; pass `colorscale="RdBu_r"` for deviation / lift-ratio matrices.

### Expected vs actual rate per bucket (calibration)
**Data shape:** `expected_pd, actual_default, n, bucket`.
→ Use `scatter_calibration` — y=x diagonal drawn automatically, bubble area ∝ n.

---

## Distribution patterns (one row per observation)

### Distribution shape per category
**Data shape:** long: `category, value, n` (one row per observation; n is per-category, broadcast).
→ Use `violin_grouped` — shape + overlaid box. n= baked into x-tick labels.
→ Use `box_quantile` — box only (q1/median/q3 + 10/90 whiskers). Less visual noise than violin for many categories.

### Continuous variable distribution coloured by grade
**Data shape:** `value, grade, n` (n=1 per observation, or pre-aggregated).
→ Use `histogram_by_grade` — stacked histogram, GRADE_COLOURS locked, n= in legend per grade.

---

## Specialised patterns

### Multi-stage drop-off (application → quoted → originated)
**Data shape:** `stage, count, n` (stages in funnel order; widest at top).
→ Use `funnel_horizontal` — counts inside, "% of top" labels, "↓ X% drop" between stages.

### Component breakdown per grade group (cashflow waterfall view)
**Data shape:** `grade_group, component, value` (components in insertion order).
→ Use `waterfall_components_by_grade` — 1×N panels (one per grade group), grouped bars per component, £-formatted value labels. (Note: this is a "grouped components" view, not a true running-total waterfall.)

### Granular per-cohort deviation grid (grade × period)
**Data shape:** `grade, period, mob, actual, model, deviation_text, n`.
→ Use `cohort_grid_grade_x_period` — M×N tiny line-charts in a grid, "Dev: ±X%" annotation per cell, dense but legible at 1440×740.

---

## MoTa shortcuts — pick by question, not by data shape

If you're starting from a MoTa question rather than a tidy DataFrame, these recipes load real Snowflake data and produce the chart for you. All take `(cohort_start, cohort_end)` as the first two arguments (date or 'YYYY-MM-DD' string).

| Question | Recipe |
|---|---|
| "What does DQ aging look like for cohorts in this window, by A-B / C-E / F+?" | `recipes.dq_aging_by_grade` |
| "Show me 30+@1, 30+@3, 60+@6, 90+@9 vs benchmark for monthly cohorts." | `recipes.dq_2x2_recent_book` |
| "Top-N introducers by £ volume." | `recipes.introducer_volume_league_table` |
| "Monthly introducer mix over the window." | `recipes.introducer_volume_mix_monthly` |
| "Application → quote → originated funnel." | `recipes.funnel_app_to_originated` |
| "Score distribution per risk grade." | `recipes.score_distribution_by_grade` (Delphi or Gauge) |
| "Is the IRR-implied PD calibrated against realised 90+@9?" | `recipes.pd_calibration_irr` |
| "Does dealer-channel underperform after adjusting for grade mix?" | `recipes.segment_compare_dealer_vs_nondealer` |

Example:
```python
from datetime import date
from motor_graphs import recipes, save_figure

fig = recipes.dq_aging_by_grade(date(2024, 1, 1), date(2025, 12, 31))
save_figure(fig, "out/dq_aging_2024_2025")  # writes PNG + HTML
```

---

## Universal house rules (apply to every style)

- Canvas: 1440 × 740 px unless overridden.
- `actual = #1f77b4` solid 2-px; `expected = #d62728` dashed 2-px. Hardcoded pairing.
- Risk-grade buckets when grouping: A-B / C-E / F+ (cashflow recipes may use A-C / D-E / F+).
- £-weighted by default; "Note: All rates are £ weighted." footnote added automatically.
- `annotate_n=True` is default — every style shows sample sizes somewhere appropriate (above bars, on last line points, in legend labels, in cell text, etc.). Pass `annotate_n=False` to suppress.
- `small_sample_handling="show" | "fade" | "suppress"` — fade points below n=200, drop below n=50.
- Hover: `"x unified"` on multi-cohort line charts.
- Template: `plotly_white+motor`. Switch the base via `motor_graphs.style.set_background("plotly")` if you want the reference-deck lavender look.

When a style's docstring says `Use this when:`, it's the canonical contract for that style. If your data fits, you've found the right chart.

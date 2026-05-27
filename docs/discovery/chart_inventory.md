# Chart-style catalogue — v0.1 (25 styles)

Locked by Hamish at Batch 1.4 sign-off. Each style is one named function in `motor_graphs/styles/*.py` (Batch 5). Source: **R** = mirrored from `credit.auto-monthly-monitoring`. **N** = new for the MoTa library.

## Universal house rules (apply to every style)

1. **Canvas**: 1440 × 740 px unless overridden by the caller.
2. **Sample-size annotation: ALWAYS** — every primitive shows `n=` for each data point/bar/category. Stricter than the reference. EV-style small-sample handling (fade-when-n<200, suppress-when-n<50) is **opt-in** via `small_sample_handling: 'show' | 'fade' | 'suppress'` (default `'show'`).
3. **Actual = `#1f77b4` solid 2-px**; **Expected = `#d62728` dashed 2-px**. Hardcoded pairing.
4. **Risk-grade buckets** for grouped views: `A-B / C-E / F+` (cashflow recipes may use `A-C / D-E / F+`).
5. **£-weighted by default**; chart footnote: `"Note: All rates are £ weighted."` added automatically.
6. **Cohort cadence**: quarterly until 2025-Q3, monthly from 2025-10 onward (`MONTHLY_CUTOFF_YEAR = 2025`).
7. **Incomplete-month handling**: `*` suffix on current-month label; share/mix series drop the current month entirely.
8. **Tick formats**: rates `.1%` or `.2%`; £ `tickprefix="£"`; percentage points `ticksuffix="pp"`.
9. **Hover**: `hovermode='x unified'` on every multi-cohort line chart.
10. **Template**: custom `motor` Plotly template (extends `plotly_white`) registered as default.
11. **Render pattern**: separate `_compute_*` (pandas) → `_render_*` (figure build + write_image + write_html) → public `style_*` function. Errors fall through to a same-size figure with a title-only error message (mirror reference).
12. **Output**: every chart saves both PNG (via Kaleido) and interactive HTML side-by-side.

## Catalogue

| # | Style ID | Origin | Visual pattern | Data shape | MoTa use |
|---|---|---|---|---|---|
| 1 | `dq_2x2_actual_vs_expected` | R | 2×2 line subplots; blue solid actual + red dashed expected; maturity tag on last point | long: cohort × metric × actual_rate × expected_rate; 4 metrics | DQ vs benchmark, all-book or PA/NPA/A-B/C-E/F+ slices |
| 2 | `dq_2x2_with_n_annotated` | R | Same as #1 + per-point opacity scaled by n + `n=` annotation on last visible point | + `cohort_size` col | Small-sample variants (EV, sub-segments) |
| 3 | `regression_validation_1x3` | R | 1×3 line subplots; actual solid + dashed reverse-engineered predicted | cohort × metric × rate × predicted | Pred-vs-actual rate validation by grade group |
| 4 | `cohort_lines_vs_mob` | R | Per-cohort coloured line vs MOB; optional dashed expected overlay | long: cohort × MOB × cum_rate; integer x | VT / prepay / cumulative-default by cohort |
| 5 | `cohort_lines_1x3_by_grade_group` | R | 1×3 subplots split by grade group; per-cohort lines + optional dashed expected per panel | cohort × MOB × grade_group | Behaviour curves segmented by A-B / C-E / F+ |
| 6 | `cohort_lines_1x3_paired_expected` | R | 1×3 subplots; per-cohort actual solid + per-cohort expected dashed in SAME colour | cohort × MOB × grade_group, both actual + expected per cohort | Per-cohort delta vs expectation |
| 7 | `roll_rate_dual_axis_lines` | R | Single chart, secondary-y; small-scale series on left axis, others on right; one series dashed | monthly × 4 rate series | Two-scale rate compare (e.g. 0–1 small series + 1–4 large series) |
| 8 | `stacked_bar_100pct_monthly_2x2` | R | 2×2 of 100%-stacked monthly bars (category mix); y = 0–100% | month × categorical_band × pct, 4 dims | Composition mix over time (vehicle / age / value / LTV) |
| 9 | `stacked_bar_volume_2x2_with_rate_line` | R | 2×2 — 3 stacked-bar volume panels by introducer + 1 multi-line rate panel | month × introducer (count or £) + month × rate cols | Volume KPIs with rates/fees sidekick |
| 10 | `lines_1x2_funnel_by_introducer` | R | 1×2 line subplots; one series per introducer; both panels are conversion rates | month × introducer × rate% | Funnel-stage conversion rates |
| 11 | `lines_with_overall_highlight` | R | Multi-line single chart; one line per segment + bold thick "Overall" series | month × segment × rate% | Rate by category + portfolio average overlay |
| 12 | `segment_compare_2x2_with_gap` | R+N | 2×2 — top-left 3-line rate panel, top-right raw-gap bars, bottom-left horizontal stacked grade-mix bars (good band vs risky band per segment), bottom-right mix-adjusted gap line | month × {a, b, b_adj, gap, a_good_share, b_good_share, n} | Generic two-segment compare (BEV/ROB, Carrera/Torino, dealer/non-dealer, etc.) — answers whether a rate gap is mix-driven or performance-driven |
| 13 | `grouped_bars_by_grade_two_series` | R | Vertical grouped bars by risk grade; two series per group | grade × {series_a, series_b} | Side-by-side rate compare across grades |
| 14 | `bar_horizontal_top_n` | R | Single horizontal bar sorted desc, top-N | category × value (£) | League table (top introducers / dealers / brokers) |
| 15 | `bar_plus_line_share_top_n` | R | Vertical bar (£ share) + overlaid line (count share) on same x | category × {share_£, share_n} | Two-metric share view on shared categories |
| 16 | `waterfall_components_by_grade` | R | 1×N subplots, one per grade group; grouped bars over cashflow components at single MOB | grade × component × value | Cashflow component breakdown snapshot |
| 17 | `cohort_grid_grade_x_period` | R | M×N grid (grade rows × period cols); each cell mini actual+model line + "Dev: ±%" annotation | grade × period × MOB × {actual, model} | Granular per-cohort deviation panel |
| 18 | `lines_funnel_by_introducer_1x1` | R | Single-panel variant of #10 used in EV context | month × introducer × rate% | EV quote→sale rate |
| 19 | `heatmap_swap` | N | X-grade × Y-grade contingency matrix; cell-level count + £-pct dual annotation; diverging colorscale (`RdBu_r`) | pivot: X grade × Y grade × {count, £_share} | Scorecard-vs-scorecard swap matrix |
| 20 | `scatter_calibration` | N | Scatter X = expected vs Y = actual; y = x diagonal reference; one point per bucket; bubble size = n | bucket × expected × actual × n | Calibration scatter — PD substitute via IRR `input_90_in_9` since `ORIGINATION_PD` doesn't exist |
| 21 | `line_with_ci_band` | N | Single chart, one line + filled CI band (0.2 opacity of line colour) per group | month × group × {rate, ci_lower, ci_upper} | Rate with confidence interval |
| 22 | `violin_grouped` | N | Violins per category; optional overlaid box | category × value (long) | Distribution shape compare across grades / channels |
| 23 | `box_quantile` | N | Box plot per category; quartile + 10/90 whisker | category × value (long) | Distribution summary without violin density |
| 24 | `histogram_by_grade` | N | Stacked histogram of a continuous variable, coloured by grade (via `GRADE_COLOURS`) | value × grade | Score distribution by risk grade |
| 25 | `funnel_horizontal` | N | Horizontal funnel; stages stacked descending; drop-off labels between stages | stage × count × pct_of_top | App → quote → originated funnel |

## Layout / spacing conventions (mirrored from reference)

- 2×2 DQ subplots: `vertical_spacing=0.20, horizontal_spacing=0.08`
- 2×2 mix charts: `vertical_spacing=0.15-0.2, horizontal_spacing=0.08-0.15`
- 1×3 by-grade subplots: `horizontal_spacing=0.06-0.08`

## Legend conventions

- Cohort/category charts: grouped legend (`traceorder='grouped'`, `groupclick='toggleitem'`, explicit `legendgrouptitle_text`).
- DQ 2×2: vertical right-side legend at `x=1.02, y=0.5`.
- 1×3 by-grade subplots: horizontal-below legend at `y=-0.12, x=0.5`.
- EV early-performance: horizontal-above legend at `y=1.02, x=1`.

## Filename conventions (mirror reference)

- snake_case, optional section prefix (`ev_`, `cf_`).
- Risk-grade slugs: `a_b`, `c_e`, `fplus`.

## Out of scope for v0.1

- Pie / donut / 3D charts (forbidden).
- Dual-axis where avoidable (allowed only for `roll_rate_dual_axis_lines`).
- Maps, network graphs.
- 3D scatter / surface.
- Sankey / chord diagrams.

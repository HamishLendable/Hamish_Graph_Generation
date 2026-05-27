# Styling reference

The visual style is **locked**. Every chart in the library uses the palette and template defined here. No magic hex strings outside `motor_graphs/style/palette.py`.

## The four-colour spine

The reference repo's palette collapses to four semantic roles, used universally across styles:

| Constant | Hex | Stroke | Role |
|---|---|---|---|
| `ACTUAL` | `#1f77b4` | solid 2-px | Actual / primary / BEV / Carrera |
| `SECONDARY` | `#ff7f0e` | solid 2-px | Secondary / ROB / Torino |
| `ADJUSTED` | `#2ca02c` | solid 2-px | Mix-adjusted benchmark |
| `EXPECTED` | `#d62728` | **dashed 2-px** | Expected / predicted / assumed / gap |
| `OVERLAY_BLACK` | `#000000` | dashed 3-px | "Overall / All" highlight overlays |

Aliases (resolve to the same hex — keep the reference variable names usable):
`PRIMARY_COLOR = ACTUAL`, `BEV_COLOR = ACTUAL`, `CARRERA_COLOR = ACTUAL`, `ROB_COLOR = SECONDARY`, `TORINO_COLOR = SECONDARY`, `PREDICTED_COLOR = EXPECTED`, `ASSUMED_COLOR = EXPECTED`, `GAP_COLOR = EXPECTED`.

## Risk-grade colours (locked positional mapping)

```python
GRADE_COLOURS = {
    "A":   "#1f77b4",
    "B":   "#ff7f0e",
    "C":   "#2ca02c",
    "D":   "#d62728",
    "E":   "#9467bd",
    "F":   "#8c564b",
    "F*":  "#e377c2",
    "F**": "#7f7f7f",
}

GRADE_GROUP_COLOURS = {
    "A-B": "#1f77b4",
    "C-E": "#ff7f0e",
    "F+":  "#d62728",
}

CASHFLOW_GRADE_GROUP_COLOURS = {  # alternative bucketing
    "A-C": "#1f77b4",
    "D-E": "#ff7f0e",
    "F+":  "#d62728",
}
```

## Introducer category colours

```python
INTRODUCER_CATEGORY_COLORS = {
    "Aggregator":          "#1f77b4",
    "Broker - Dealer led": "#ff7f0e",
    "Broker - Online led": "#2ca02c",
    "Dealer":              "#d62728",
    "Direct":              "#9467bd",
    "Unknown introducer":  "#7f7f7f",
}
```

Unmapped categories fall back to `UNKNOWN_INTRODUCER_COLOR` (`#7f7f7f`).

## Cohort colour cycle

```python
COHORT_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
]
```

Cycled positionally — cohort-N gets the same colour across every chart.

## Heatmap colorscales

| Constant | Plotly scale | Use case |
|---|---|---|
| `SEQUENTIAL_HEATMAP` | `"Blues"` | Volume / count heatmaps |
| `DIVERGING_HEATMAP` | `"RdBu_r"` | Deviation / lift-ratio (centre at 1.0) |

## CI band fill

```python
CI_BAND_OPACITY = 0.2
# fill_color = hex_to_rgba(line_color, CI_BAND_OPACITY)
```

## EV small-sample handling

```python
EV_SUPPRESS_N   = 50    # n < this → drop the point
EV_FADE_N       = 200   # n < this → marker opacity = EV_FADE_OPACITY
EV_FADE_OPACITY = 0.35
```

Exposed on every style as `small_sample_handling: "show" | "fade" | "suppress"` (default `"show"`).

## Plotly template

Custom `motor` template extending `plotly_white`, registered as default on package import:

```python
import plotly.io as pio
pio.templates.default = "plotly_white+motor"
```

Switch the base via `motor_graphs.style.set_background("plotly")` if you want the reference-deck lavender plot background.

The `motor` template overrides:
- `colorway = COHORT_COLORS`
- `font = "Open Sans, Verdana, Arial, sans-serif"`, size 12
- `title.x = 0.5, xanchor = "center"` (centred titles)
- `hovermode = "x unified"`
- `legend = horizontal-below` by default; `motor_graphs.style.apply_auto_legend(fig)` flips to vertical-right when there are more than 6 named legend entries
- `xaxis/yaxis = ticks="outside", gridcolor="rgba(0,0,0,0.06)"`

## Universal house rules (every style enforces)

1. **Canvas 1440 × 740 px** unless explicitly overridden.
2. **`actual` = `#1f77b4` solid 2-px** | **`expected` = `#d62728` dashed 2-px**. Hardcoded pairing.
3. **`annotate_n=True` is the default**. Every style shows sample sizes somewhere appropriate (above bars, on last line points, in legend labels, in cell text, in x-tick labels for distributions). Pass `annotate_n=False` to suppress. Pass `small_sample_handling="fade"` for EV-style fading below n=200, or `"suppress"` to drop entirely below n=50.
4. **£-weighted by default**; the footnote `"Note: All rates are £ weighted."` is added automatically via `_shared.add_pound_weighted_footnote`.
5. **Tick formats**: rates `.1%` / `.2%`; £ `tickprefix="£"`; pp `ticksuffix="pp"`.
6. **Hover** `"x unified"` for multi-cohort line charts.
7. **Risk-grade buckets**: `A-B / C-E / F+` for grouped views; `A-C / D-E / F+` for cashflow.
8. **Cohort cadence** in MoTa data: quarterly until 2025-Q3, monthly from 2025-10 onwards.
9. **Incomplete-month handling**: trailing `*` on current-month label; share/mix series drop the current month.

## What is FORBIDDEN

- ❌ Pie / donut charts
- ❌ 3D charts (scatter / surface)
- ❌ Dual-axis where it can be avoided (`roll_rate_dual_axis_lines` is the sanctioned exception)
- ❌ Default Plotly styling (anything that bypasses the `motor` template)
- ❌ Magic hex strings outside `motor_graphs/style/palette.py` — CI lint may add a grep check for this

## What is MANDATORY

- ✅ `annotate_n=True` default on every primitive
- ✅ Count + £-weighted side-by-side for risk metrics where applicable (e.g. `bar_count_pound_twin` if added later)
- ✅ `Use this when:` / `Data shape:` / `Style:` sections in every docstring (or `Snowflake tables used:` for recipes)
- ✅ Locked colour pairing: actual is blue, expected is red dashed
- ✅ Visual baselines committed to `tests/baselines/` for every style

If you change something in `palette.py` or `template.py`, run `poetry run python scripts/refresh_baselines.py` to regenerate the 25 baselines, then `git diff` to review the visual deltas before committing.

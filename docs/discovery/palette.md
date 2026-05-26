# Palette specification — v0.1

Locked by Hamish at Batch 1.4 sign-off. Implemented in `motor_graphs/style/palette.py` (Batch 3). The reference repo's palette is sparse (4 semantic roles + introducer dict + cohort cycle); this library extends it for new chart types (heatmaps, CI bands, locked grade-to-hex map).

## Plotly template

Custom `motor` template extending `plotly_white`, registered as default on package import.

```python
# motor_graphs/style/template.py
import plotly.graph_objects as go
import plotly.io as pio

motor_template = go.layout.Template(
    layout=go.Layout(
        # extends plotly_white; override font, colorway, legend, etc.
    )
)
pio.templates["motor"] = pio.templates["plotly_white"].update(motor_template.layout)
pio.templates.default = "motor"
```

## Canonical semantic roles (the four-colour spine — mirrored from reference)

| Constant | Hex | Style notes |
|---|---|---|
| `ACTUAL` | `#1f77b4` (muted blue) | Solid 2-px line, primary marker fill |
| `SECONDARY` | `#ff7f0e` (safety orange) | Solid 2-px line, secondary series |
| `ADJUSTED` | `#2ca02c` (green) | Solid 2-px line, mix-adjusted benchmark |
| `EXPECTED` | `#d62728` (brick red) | **Dashed 2-px** line — always |
| `OVERLAY_BLACK` | `#000000` | Dashed 3-px, used for "All / Overall" overlays |

Semantic aliases (resolve to the same hex — match reference variable names): `PRIMARY = ACTUAL`, `BEV_COLOR = ACTUAL`, `CARRERA_COLOR = ACTUAL`, `ROB_COLOR = SECONDARY`, `TORINO_COLOR = SECONDARY`, `PREDICTED = EXPECTED`, `ASSUMED = EXPECTED`, `GAP_COLOR = EXPECTED`.

## Introducer category colours (verbatim from `electric_vehicles.py:39-51`)

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

Fallback for unmapped categories: `"#7f7f7f"` (grey).

## Cohort colour cycle (verbatim from `cashflow_monitoring.py:29-33`)

```python
COHORT_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
]
```

Cycled positionally — cohort-N gets the same colour across every chart.

## Grade colours (NEW — locked positional mapping)

Reference uses positional Plotly defaults; we LOCK them so grade-A always renders blue regardless of insertion order.

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

# Cashflow variant
CASHFLOW_GRADE_GROUP_COLOURS = {
    "A-C": "#1f77b4",
    "D-E": "#ff7f0e",
    "F+":  "#d62728",
}
```

## Heatmap colorscales (NEW)

```python
SEQUENTIAL_HEATMAP = "Blues"          # Plotly built-in
DIVERGING_HEATMAP  = "RdBu_r"         # for deviation-from-zero (e.g. swap-matrix lift ratio)
```

Used by `heatmap_swap` (style #19). Diverging scale centred at 1.0 for lift-ratio charts; sequential scale for count/volume heatmaps.

## CI band fill (NEW)

```python
CI_BAND_OPACITY = 0.2

# usage:
fill_color = hex_to_rgba(line_color, CI_BAND_OPACITY)
```

Used by `line_with_ci_band` (style #21).

## Translucency helper (verbatim from `electric_vehicles.py:_ev_rgba`)

```python
def hex_to_rgba(hex_color: str, opacity: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{opacity})"
```

## EV small-sample discipline (parameterisable; default off except where styles explicitly opt in)

```python
EV_SUPPRESS_N   = 50    # drop point if n < this
EV_FADE_N       = 200   # fade point opacity to EV_FADE_OPACITY if n < this
EV_FADE_OPACITY = 0.35
```

Exposed via `small_sample_handling: 'show' | 'fade' | 'suppress'` on every style.

## What is NOT in the palette

- ❌ `paper_bgcolor` / `plot_bgcolor` / `gridcolor` overrides. Defer to `plotly_white` defaults.
- ❌ `add_hrect` / `add_vrect` / `add_shape` threshold-band colours. If a recipe needs them, define inline.
- ❌ Font hex overrides. Use Plotly's default sans-serif.
- ❌ Per-channel introducer colours beyond the 5 categories above. Unknown → grey.

## Hard rule

No magic hex string anywhere in the codebase outside `palette.py`. Every colour reference imports from this module. CI lint check planned in Batch 8: grep for `'#[0-9a-fA-F]{6}'` in `motor_graphs/` and fail if any hit is outside `style/palette.py`.

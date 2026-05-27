"""Palette constants for motor-graph-generation.

Source of truth — every chart imports colours from here, never inlines hex.
See docs/discovery/palette.md for the full spec.
"""

# --- Canonical semantic roles (the four-colour spine) --------------------
ACTUAL = "#1f77b4"           # muted blue   — primary / actual / BEV / Carrera
SECONDARY = "#ff7f0e"        # safety orange — secondary series / ROB / Torino
ADJUSTED = "#2ca02c"         # green        — mix-adjusted benchmark
EXPECTED = "#d62728"         # brick red    — expected / predicted / assumed / gap (ALWAYS dashed 2-px)
OVERLAY_BLACK = "#000000"    # dashed 3-px overlay (e.g. "All / Overall" highlights)


# --- Aliases — mirror reference-repo variable names ----------------------
PRIMARY_COLOR = ACTUAL
ACTUAL_COLOR = ACTUAL
BEV_COLOR = ACTUAL
CARRERA_COLOR = ACTUAL

SECONDARY_COLOR = SECONDARY
ROB_COLOR = SECONDARY
TORINO_COLOR = SECONDARY

ADJUSTED_COLOR = ADJUSTED

EXPECTED_COLOR = EXPECTED
PREDICTED_COLOR = EXPECTED
ASSUMED_COLOR = EXPECTED
GAP_COLOR = EXPECTED


# --- Introducer category colours (verbatim from reference electric_vehicles.py) ---
INTRODUCER_CATEGORY_COLORS = {
    "Aggregator":          "#1f77b4",
    "Broker - Dealer led": "#ff7f0e",
    "Broker - Online led": "#2ca02c",
    "Dealer":              "#d62728",
    "Direct":              "#9467bd",
    "Unknown introducer":  "#7f7f7f",
}
UNKNOWN_INTRODUCER_COLOR = "#7f7f7f"


# --- Cohort colour cycle (verbatim from reference cashflow_monitoring.py) ---
COHORT_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#aec7e8", "#ffbb78", "#98df8a", "#ff9896", "#c5b0d5",
]


# --- Grade colours (NEW — locked positional mapping for motor-graph-generation) ---
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

# Cashflow charts in the reference use a different grouping
CASHFLOW_GRADE_GROUP_COLOURS = {
    "A-C": "#1f77b4",
    "D-E": "#ff7f0e",
    "F+":  "#d62728",
}


# --- Heatmap colorscales (NEW) ------------------------------------------
SEQUENTIAL_HEATMAP = "Blues"   # Plotly built-in — volume / count heatmaps
DIVERGING_HEATMAP = "RdBu_r"   # Plotly built-in — deviation / lift-ratio heatmaps (centre at 1.0)


# --- Confidence band fill opacity (NEW) ---------------------------------
CI_BAND_OPACITY = 0.2


# --- EV small-sample discipline thresholds (verbatim from reference) ----
EV_SUPPRESS_N = 50      # drop point if n < this
EV_FADE_N = 200         # fade point opacity to EV_FADE_OPACITY if n < this
EV_FADE_OPACITY = 0.35


def hex_to_rgba(hex_color: str, opacity: float) -> str:
    """Convert ``#RRGGBB`` + opacity ∈ [0,1] → ``rgba(r,g,b,a)``.

    Mirrors the reference repo's ``electric_vehicles._ev_rgba``.
    """
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{opacity})"

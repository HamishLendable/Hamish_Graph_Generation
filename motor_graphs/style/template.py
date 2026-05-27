"""Custom 'motor' Plotly template — extends plotly_white with MoTa house defaults.

Registered as the package default on import. Composes via ``plotly_white+motor``,
so plotly_white provides the white background and gridlines, and the motor
template layers on top with: colorway = COHORT_COLORS, hovermode = 'x unified',
font defaults, legend defaults, axis tick conventions.
"""

import plotly.graph_objects as go
import plotly.io as pio

from .palette import COHORT_COLORS

_motor_overrides = go.layout.Template(
    layout=go.Layout(
        colorway=COHORT_COLORS,
        font=dict(
            family="Open Sans, Verdana, Arial, sans-serif",
            size=12,
            color="#222",
        ),
        title=dict(
            font=dict(size=18),
            x=0.5,
            xanchor="center",
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.18,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="rgba(0,0,0,0)",
            font=dict(size=11),
        ),
        margin=dict(l=70, r=40, t=80, b=80),
        xaxis=dict(
            ticks="outside",
            ticklen=4,
            zeroline=False,
            gridcolor="rgba(0,0,0,0.06)",
        ),
        yaxis=dict(
            ticks="outside",
            ticklen=4,
            zeroline=False,
            gridcolor="rgba(0,0,0,0.06)",
        ),
    )
)

pio.templates["motor"] = _motor_overrides
pio.templates.default = "plotly_white+motor"

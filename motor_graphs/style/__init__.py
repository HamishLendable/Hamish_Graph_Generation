"""Style lock-in: palette + Plotly template.

Importing this package registers the 'motor' Plotly template as the default.
"""

import plotly.graph_objects as go
import plotly.io as pio

from . import (
    palette,  # noqa: F401
    template,  # noqa: F401  (side effect: registers 'motor' template)
)

VALID_BASE_TEMPLATES = {"plotly_white", "plotly", "simple_white", "ggplot2", "seaborn"}


def set_background(name: str = "plotly_white") -> None:
    """Switch the base Plotly template that the motor template extends.

    Default is ``"plotly_white"`` (unified white). Other options:

    * ``"plotly"`` — Plotly default; subtle lavender plot background. Matches the
      delinquency / VT charts in credit.auto-monthly-monitoring.
    * ``"simple_white"`` — minimal, no gridlines.
    * ``"ggplot2"`` / ``"seaborn"`` — Plotly's ports of those R/Python defaults.
    """
    if name not in VALID_BASE_TEMPLATES:
        raise ValueError(
            f"Unknown base template {name!r}. Valid options: {sorted(VALID_BASE_TEMPLATES)}"
        )
    pio.templates.default = f"{name}+motor"


def apply_auto_legend(fig: go.Figure, threshold: int = 6) -> go.Figure:
    """Pick legend orientation based on the number of unique legend entries.

    * ``<= threshold`` unique series → leave as template default (horizontal below).
    * ``>  threshold`` unique series → vertical right (``x=1.02, y=0.5``).

    Mutates and returns ``fig`` for chaining.
    """
    visible_names: set[str] = set()
    for trace in fig.data:
        if getattr(trace, "showlegend", True) is False:
            continue
        name = getattr(trace, "name", None)
        if name:
            visible_names.add(name)
    if len(visible_names) > threshold:
        fig.update_layout(
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.02,
            )
        )
    return fig

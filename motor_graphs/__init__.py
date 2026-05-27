"""motor-graph-generation: MoTa-styled chart-style catalogue.

See docs/discovery/chart_inventory.md for the v0.1 catalogue of 25 chart styles.
"""

from pathlib import Path
from typing import Union

import plotly.graph_objects as go

# Triggers Plotly template registration on package import
from . import style  # noqa: F401

__version__ = "0.1.0"


def save_figure(
    fig: go.Figure,
    path: Union[str, Path],
    *,
    also_html: bool = True,
    width: int = 1440,
    height: int = 740,
    scale: int = 1,
) -> None:
    """Save ``fig`` as PNG (via Kaleido) and — by default — interactive HTML alongside.

    The ``path`` may include an extension; it is stripped and both ``.png`` and
    ``.html`` are written to it. Parent directories are created if needed.
    """
    p = Path(path).with_suffix("")
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(f"{p}.png", width=width, height=height, scale=scale)
    if also_html:
        fig.write_html(f"{p}.html", include_plotlyjs="cdn")

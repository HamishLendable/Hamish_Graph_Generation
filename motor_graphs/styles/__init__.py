"""Chart-style primitives for motor-graph-generation — v0.1 catalogue (25 styles).

See docs/discovery/chart_inventory.md for the full catalogue with "Use this when"
notes per style. Each function takes a tidy pandas DataFrame and returns a
plotly.graph_objects.Figure. All annotate sample size by default.
"""

from .bars import grouped_bars_by_grade_two_series, stacked_bar_100pct_monthly_2x2
from .distributions import box_quantile, histogram_by_grade, violin_grouped
from .dq_subplots import (
    cohort_lines_1x3_by_grade_group,
    cohort_lines_1x3_paired_expected,
    dq_2x2_with_n_annotated,
    regression_validation_1x3,
    roll_rate_dual_axis_lines,
)
from .heatmaps import heatmap_swap
from .lines import cohort_lines_vs_mob, dq_2x2_actual_vs_expected
from .more_bars import (
    bar_horizontal_top_n,
    bar_plus_line_share_top_n,
    stacked_bar_volume_2x2_with_rate_line,
    waterfall_components_by_grade,
)
from .multi_lines import (
    line_with_ci_band,
    lines_1x2_funnel_by_introducer,
    lines_funnel_by_introducer_1x1,
    lines_with_overall_highlight,
    segment_compare_2x2_with_gap,
)
from .scatters import scatter_calibration
from .specialised import cohort_grid_grade_x_period, funnel_horizontal

__all__ = [
    # --- bars ---
    "grouped_bars_by_grade_two_series",
    "stacked_bar_100pct_monthly_2x2",
    "bar_horizontal_top_n",
    "bar_plus_line_share_top_n",
    "stacked_bar_volume_2x2_with_rate_line",
    "waterfall_components_by_grade",
    # --- heatmaps ---
    "heatmap_swap",
    # --- lines ---
    "cohort_lines_vs_mob",
    "dq_2x2_actual_vs_expected",
    "dq_2x2_with_n_annotated",
    "regression_validation_1x3",
    "cohort_lines_1x3_by_grade_group",
    "cohort_lines_1x3_paired_expected",
    "roll_rate_dual_axis_lines",
    "lines_1x2_funnel_by_introducer",
    "lines_with_overall_highlight",
    "segment_compare_2x2_with_gap",
    "lines_funnel_by_introducer_1x1",
    "line_with_ci_band",
    # --- scatters ---
    "scatter_calibration",
    # --- distributions ---
    "violin_grouped",
    "box_quantile",
    "histogram_by_grade",
    # --- specialised ---
    "cohort_grid_grade_x_period",
    "funnel_horizontal",
]

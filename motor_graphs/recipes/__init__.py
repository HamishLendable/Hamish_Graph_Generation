"""MoTa Snowflake-aware chart recipes.

A recipe is a thin wrapper that loads real Snowflake data via
``motor_graphs.data.snowflake`` and feeds it into one of the chart styles.
Each takes ``(cohort_start, cohort_end)`` (date | str) plus optional kwargs
and returns a ``plotly.graph_objects.Figure``.

Recipes never call live Snowflake at import time; they only execute SQL when
called. ``run_query`` is invoked via the module-level reference so tests can
``monkeypatch.setattr(snowflake, "run_query", ...)``.
"""

from .dq import dq_2x2_recent_book, dq_aging_by_grade
from .funnel_distributions import funnel_app_to_originated, score_distribution_by_grade
from .risk import pd_calibration_irr, segment_compare_dealer_vs_nondealer
from .volume import introducer_volume_league_table, introducer_volume_mix_monthly

__all__ = [
    # --- DQ ---
    "dq_aging_by_grade",
    "dq_2x2_recent_book",
    # --- volume ---
    "introducer_volume_league_table",
    "introducer_volume_mix_monthly",
    # --- funnel + distributions ---
    "funnel_app_to_originated",
    "score_distribution_by_grade",
    # --- risk ---
    "pd_calibration_irr",
    "segment_compare_dealer_vs_nondealer",
]

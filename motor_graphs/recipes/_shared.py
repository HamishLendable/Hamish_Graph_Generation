"""Shared helpers for MoTa recipes.

Recipes are thin Snowflake-aware wrappers that load real data via
``motor_graphs.data.snowflake`` and pass it to a chart style.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import pandas as pd


def normalize_date(d: date | str) -> str:
    """Convert ``date`` / ``datetime`` / 'YYYY-MM-DD' string to canonical 'YYYY-MM-DD'.

    Raises:
        ValueError: if the input string doesn't match the YYYY-MM-DD format.
    """
    if isinstance(d, str):
        datetime.strptime(d, "%Y-%m-%d")  # validates format; raises ValueError on miss
        return d
    if isinstance(d, datetime):
        return d.date().strftime("%Y-%m-%d")
    if isinstance(d, date):
        return d.strftime("%Y-%m-%d")
    raise TypeError(f"date must be str / date / datetime, got {type(d).__name__}")


def validate_cohort_range(cohort_start: date | str, cohort_end: date | str) -> tuple[str, str]:
    """Normalize ``cohort_start`` and ``cohort_end`` and validate ``start < end``.

    Returns the pair of YYYY-MM-DD strings ready to interpolate into SQL.
    """
    start = normalize_date(cohort_start)
    end = normalize_date(cohort_end)
    if start >= end:
        raise ValueError(f"cohort_start ({start}) must be strictly before cohort_end ({end})")
    return start, end


def simplify_risk_grade(grade) -> Optional[str]:
    """Mirror credit.auto-monthly-monitoring/charts/vt_assumptions._simplify_risk_grade.

    Strips ``^`` suffix while preserving F / F* / F** distinction. Unknown → None.
    """
    if pd.isna(grade):
        return None
    g = str(grade).strip().replace("^", "")
    if g in {"A", "B", "C", "D", "E", "F", "F*", "F**"}:
        return g
    if g and g[0] in {"A", "B", "C", "D", "E"}:
        return g[0]
    return None


RISK_GRADE_GROUPS = {
    "A-B": ["A", "B"],
    "C-E": ["C", "D", "E"],
    "F+":  ["F", "F*", "F**"],
}


def grade_to_group(grade) -> Optional[str]:
    """Map a (possibly suffixed) risk grade to one of A-B / C-E / F+."""
    simplified = simplify_risk_grade(grade)
    if simplified is None:
        return None
    for group, members in RISK_GRADE_GROUPS.items():
        if simplified in members:
            return group
    return None


# Canonical filters used across recipes
ORIGINATED_FLAG_PREDICATE = (
    "COALESCE(FLAG_ORIGINATED_AND_NOT_CANCELLED, FLAG_ORIGINATED) = TRUE"
)

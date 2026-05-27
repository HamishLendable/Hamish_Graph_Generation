"""Introspect motor_graphs.styles + motor_graphs.recipes to build a machine-readable catalogue.

The catalogue is the agent-facing index — given a data shape or a natural-language
question, a future Claude (or any consumer) scans ``docs/catalogue.json`` to find
the right chart style / recipe.

Public API:
    build_catalogue() -> dict      # builds the in-memory index
    write_catalogue(path: Path)    # writes docs/catalogue.json

Conventions parsed from every docstring:
    Use this when:
        ...
    Data shape:            (styles only)
        ...
    Style:                 (styles only)
        ...
    Snowflake tables used: (recipes only)
        ...
    Example:
        ...
"""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from typing import Any, Optional

from motor_graphs import __version__

# Section headers we look for in docstrings. Order matters when splitting.
SECTION_HEADERS = [
    "Use this when",
    "Data shape",
    "Style",
    "Snowflake tables used",
    "Parameters",
    "Returns",
    "Example",
]


def _split_docstring(doc: str) -> dict[str, str]:
    """Parse a docstring with our standard ``Header:\\n    body`` section format."""
    if not doc:
        return {}
    cleaned = inspect.cleandoc(doc)
    lines = cleaned.split("\n")
    section_pattern = re.compile(r"^(" + "|".join(re.escape(h) for h in SECTION_HEADERS) + r"):\s*$")

    summary_lines: list[str] = []
    sections: dict[str, list[str]] = {}
    current: Optional[str] = None
    for raw in lines:
        match = section_pattern.match(raw.strip())
        if match:
            current = match.group(1)
            sections[current] = []
        elif current is None:
            summary_lines.append(raw)
        else:
            sections[current].append(raw)

    out: dict[str, str] = {"summary": "\n".join(summary_lines).strip()}
    for header, body_lines in sections.items():
        # Dedent the body lines (drop the common leading whitespace).
        body = "\n".join(body_lines).strip("\n")
        out[header.lower().replace(" ", "_")] = inspect.cleandoc(body).strip()
    return out


def _parse_signature(fn) -> list[dict[str, Any]]:
    """Return a list of parameter dicts for the function signature."""
    sig = inspect.signature(fn)
    params = []
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        default = param.default
        if default is inspect.Parameter.empty:
            default_repr = None
            has_default = False
        else:
            try:
                json.dumps(default)
                default_repr = default
            except TypeError:
                default_repr = repr(default)
            has_default = True
        annotation = (
            param.annotation
            if param.annotation is not inspect.Parameter.empty
            else None
        )
        params.append(
            {
                "name": name,
                "kind": str(param.kind).rsplit(".", 1)[-1],
                "annotation": _annotation_str(annotation),
                "has_default": has_default,
                "default": default_repr,
            }
        )
    return params


def _annotation_str(annotation) -> Optional[str]:
    if annotation is None:
        return None
    if isinstance(annotation, str):
        return annotation
    # Best-effort string form
    try:
        return inspect.formatannotation(annotation)
    except Exception:
        return repr(annotation)


def _entry(fn, kind: str) -> dict[str, Any]:
    """Build one catalogue entry from a function."""
    doc = inspect.getdoc(fn) or ""
    parsed = _split_docstring(doc)
    module = fn.__module__
    return {
        "name": fn.__name__,
        "kind": kind,
        "module": module,
        "summary": parsed.get("summary", "").split("\n")[0],  # first line only
        "use_when": parsed.get("use_this_when", ""),
        "data_shape": parsed.get("data_shape", ""),
        "style_description": parsed.get("style", ""),
        "snowflake_tables_used": parsed.get("snowflake_tables_used", ""),
        "example": parsed.get("example", ""),
        "parameters": _parse_signature(fn),
    }


def build_catalogue() -> dict[str, Any]:
    """Walk motor_graphs.styles and motor_graphs.recipes; return the structured index."""
    from motor_graphs import recipes, styles

    style_entries = []
    for name in styles.__all__:
        fn = getattr(styles, name)
        style_entries.append(_entry(fn, kind="style"))

    recipe_entries = []
    for name in recipes.__all__:
        fn = getattr(recipes, name)
        recipe_entries.append(_entry(fn, kind="recipe"))

    return {
        "version": __version__,
        "n_styles": len(style_entries),
        "n_recipes": len(recipe_entries),
        "styles": style_entries,
        "recipes": recipe_entries,
    }


def write_catalogue(path: Path | str) -> Path:
    """Write the catalogue as pretty JSON. Returns the resolved path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = build_catalogue()
    with path.open("w") as f:
        json.dump(data, f, indent=2, sort_keys=False)
    return path


def search(query: str, catalogue: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Substring search across name / summary / use_when / data_shape (case-insensitive).

    Used by ``motor-graph find``.
    """
    catalogue = catalogue or build_catalogue()
    q = query.lower().strip()
    if not q:
        return []
    hits = []
    search_fields = ("name", "summary", "use_when", "data_shape", "snowflake_tables_used")
    for entry in catalogue["styles"] + catalogue["recipes"]:
        haystack = " ".join(str(entry.get(k, "")) for k in search_fields).lower()
        if q in haystack:
            hits.append(entry)
    return hits

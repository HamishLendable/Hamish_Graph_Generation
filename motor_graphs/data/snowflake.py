"""Snowflake data layer — lentils-backed SnowflakeReader with connection pool + opt-in cache.

Mirrors ``credit.auto-monthly-monitoring/data_loader.py`` exactly for the pool.
See ``docs/discovery/snowflake_conventions.md`` for the full spec.

Public API:
    SnowflakeConnectionPool — singleton pool with 30-min idle TTL
    run_query(sql)          — execute SQL, return lowercase-column DataFrame
    cached(ttl_hours=24)    — pickle-cache decorator (opt-in, per-function)
"""

from __future__ import annotations

import hashlib
import logging
import pickle
import threading
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd

logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".cache" / "motor-graphs"


class SnowflakeConnectionPool:
    """Thread-safe singleton SnowflakeReader pool with 30-min idle TTL.

    Mirrors ``credit.auto-monthly-monitoring/data_loader.py``. Double-checked
    locking around both instance creation and reader instantiation. Defaults
    are hardcoded to ``PROD / READER_PROD / Okta SSO`` — see discovery doc.
    """

    _instance: Optional["SnowflakeConnectionPool"] = None
    _lock = threading.Lock()
    _reader: Any = None
    _last_used: Optional[float] = None
    _connection_timeout = 1800  # 30 min

    def __new__(cls) -> "SnowflakeConnectionPool":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_reader(self) -> Any:
        """Return the shared SnowflakeReader, reconnecting if the TTL has expired."""
        from lentils.snowflake import SnowflakeReader

        current_time = time.time()
        needs_new = (
            self._reader is None
            or self._last_used is None
            or current_time - self._last_used > self._connection_timeout
        )
        if needs_new:
            with self._lock:
                needs_new = (
                    self._reader is None
                    or self._last_used is None
                    or current_time - self._last_used > self._connection_timeout
                )
                if needs_new:
                    logger.info("Opening new SnowflakeReader (Okta SSO)…")
                    self._reader = SnowflakeReader.from_connection(
                        authenticator="okta",
                        database="PROD",
                        warehouse="READER_PROD",
                        role="READER_PROD",
                    )
                    self._last_used = current_time
        self._last_used = current_time
        return self._reader

    def reset(self) -> None:
        """Drop the cached reader. Useful between tests."""
        with self._lock:
            self._reader = None
            self._last_used = None


_pool = SnowflakeConnectionPool()


def run_query(sql: str) -> pd.DataFrame:
    """Execute SQL against Snowflake; return a DataFrame with lowercased column names.

    Raises:
        ValueError: if ``sql`` is empty or whitespace-only.
        RuntimeError: if lentils is missing or the Snowflake connection fails.
            The error message points at the most likely fixes (.env, Okta access).
    """
    if not sql or not sql.strip():
        raise ValueError("Empty SQL query")
    try:
        reader = _pool.get_reader()
    except ImportError as e:
        raise RuntimeError(
            f"Could not import lentils[snowflake]: {e}. "
            "If a transitive dependency is missing (e.g. sniffio), add it to "
            "pyproject.toml [project.dependencies] and re-run `poetry lock && poetry install`."
        ) from e
    except Exception as e:
        raise RuntimeError(
            "Could not connect to Snowflake. Check .env "
            "(SNOWFLAKE_ACCOUNT + SNOWFLAKE_USERNAME) and Okta access. "
            f"Underlying error: {e}"
        ) from e
    df = reader.read_to_dataframe(query_string=sql)
    df.columns = df.columns.str.lower()
    return df


def cached(ttl_hours: int = 24, cache_dir: Path = CACHE_DIR) -> Callable:
    """Decorator: pickle-cache a function's return on disk.

    Keyed by SHA256 of ``(qualname, args, sorted kwargs)``. Default TTL 24h,
    stored at ``~/.cache/motor-graphs/``. Opt-in per function — apply with
    ``@cached()`` above query helpers in recipes/.

    Example::

        @cached(ttl_hours=24)
        def applications_pulled(start, end):
            return run_query(f"SELECT ... WHERE date >= '{start}' AND date < '{end}'")
    """

    def deco(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            cache_dir.mkdir(parents=True, exist_ok=True)
            key_src = repr((fn.__qualname__, args, sorted(kwargs.items())))
            key = hashlib.sha256(key_src.encode()).hexdigest()[:16]
            path = cache_dir / f"{key}.pkl"
            if path.exists():
                age_seconds = time.time() - path.stat().st_mtime
                if age_seconds < ttl_hours * 3600:
                    logger.debug("Cache hit (age %.1fh): %s", age_seconds / 3600, path)
                    with path.open("rb") as f:
                        return pickle.load(f)
                logger.debug("Cache stale (age %.1fh): %s", age_seconds / 3600, path)
            logger.debug("Cache miss: running %s", fn.__qualname__)
            result = fn(*args, **kwargs)
            with path.open("wb") as f:
                pickle.dump(result, f)
            return result

        return wrapper

    return deco

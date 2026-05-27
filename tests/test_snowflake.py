"""Tests for motor_graphs.data.snowflake — pool, cache, and one live smoke test."""

import os
import time
from unittest.mock import MagicMock

import pandas as pd
import pytest

from motor_graphs.data import snowflake

# ---------------------------------------------------------------- pool ----


def test_pool_is_singleton():
    p1 = snowflake.SnowflakeConnectionPool()
    p2 = snowflake.SnowflakeConnectionPool()
    assert p1 is p2


def test_pool_reset_drops_reader():
    pool = snowflake.SnowflakeConnectionPool()
    pool._reader = MagicMock()
    pool._last_used = time.time()
    pool.reset()
    assert pool._reader is None
    assert pool._last_used is None


# ---------------------------------------------------------------- run_query ----


def test_run_query_rejects_empty_sql():
    with pytest.raises(ValueError):
        snowflake.run_query("")
    with pytest.raises(ValueError):
        snowflake.run_query("   ")


def test_run_query_lowercases_columns(monkeypatch):
    """run_query should always lowercase the column names from Snowflake."""
    fake_df = pd.DataFrame({"FOO": [1], "BAR_BAZ": [2]})
    fake_reader = MagicMock()
    fake_reader.read_to_dataframe.return_value = fake_df

    pool = snowflake.SnowflakeConnectionPool()
    monkeypatch.setattr(pool, "get_reader", lambda: fake_reader)

    df = snowflake.run_query("SELECT 1")
    assert list(df.columns) == ["foo", "bar_baz"]


# ---------------------------------------------------------------- cache ----


def test_cached_first_call_runs_fn(tmp_path):
    calls = {"n": 0}

    @snowflake.cached(ttl_hours=1, cache_dir=tmp_path)
    def my_fn(x):
        calls["n"] += 1
        return pd.DataFrame({"x": [x]})

    df = my_fn(1)
    assert calls["n"] == 1
    assert df.iloc[0]["x"] == 1
    assert any(tmp_path.iterdir())


def test_cached_second_call_uses_cache(tmp_path):
    calls = {"n": 0}

    @snowflake.cached(ttl_hours=1, cache_dir=tmp_path)
    def my_fn(x):
        calls["n"] += 1
        return pd.DataFrame({"x": [x]})

    my_fn(1)
    my_fn(1)
    assert calls["n"] == 1


def test_cached_different_args_different_keys(tmp_path):
    calls = {"n": 0}

    @snowflake.cached(ttl_hours=1, cache_dir=tmp_path)
    def my_fn(x):
        calls["n"] += 1
        return pd.DataFrame({"x": [x]})

    my_fn(1)
    my_fn(2)
    assert calls["n"] == 2


def test_cached_different_kwargs_different_keys(tmp_path):
    calls = {"n": 0}

    @snowflake.cached(ttl_hours=1, cache_dir=tmp_path)
    def my_fn(x, *, suffix="a"):
        calls["n"] += 1
        return pd.DataFrame({"x": [x], "s": [suffix]})

    my_fn(1, suffix="a")
    my_fn(1, suffix="b")
    assert calls["n"] == 2


def test_cached_expired_reruns(tmp_path):
    calls = {"n": 0}

    @snowflake.cached(ttl_hours=1, cache_dir=tmp_path)
    def my_fn(x):
        calls["n"] += 1
        return pd.DataFrame({"x": [x]})

    my_fn(1)
    # Force the cache file's mtime to be 2 hours ago
    cache_file = next(tmp_path.iterdir())
    past = time.time() - 7200
    os.utime(cache_file, (past, past))
    my_fn(1)
    assert calls["n"] == 2


# ---------------------------------------------------------------- live ----


@pytest.mark.snowflake
def test_live_select_one():
    """Smoke test: SELECT 1 against live Snowflake. Requires Okta auth + .env.

    Excluded from CI via the `snowflake` marker
    (run with ``poetry run pytest -m snowflake`` to include).
    """
    df = snowflake.run_query("SELECT 1 AS x")
    assert df.iloc[0]["x"] == 1

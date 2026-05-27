"""Smoke test the live Snowflake connection + one MoTa recipe end-to-end.

Run::

    poetry run python scripts/snowflake_smoke_test.py

Expects ``.env`` in repo root with ``SNOWFLAKE_ACCOUNT`` + ``SNOWFLAKE_USERNAME``.
On first run, Okta will open a browser tab for SSO. Subsequent runs reuse the token.

Three checks:
    1. ``SELECT 1`` — proves auth, lentils, and the pool work.
    2. ``COUNT(*)`` of applications in the last 30 days — proves we can hit a real
       PROD table with a realistic WHERE clause.
    3. ``introducer_volume_league_table`` recipe end-to-end — proves the full
       data → reshape → chart pipeline works against live Snowflake. Saves the
       PNG + HTML to out/_smoke/.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load .env BEFORE importing motor_graphs so lentils sees the env vars.
load_dotenv()

import motor_graphs  # noqa: E402
from motor_graphs import recipes  # noqa: E402
from motor_graphs.data import snowflake  # noqa: E402

OUT = Path(__file__).parent.parent / "out" / "_smoke"


def main() -> int:
    print("=" * 60)
    print("Snowflake smoke test")
    print("=" * 60)

    print("\n[1/3] SELECT 1 ...", flush=True)
    try:
        df = snowflake.run_query("SELECT 1 AS x")
        print(f"      returned: {df.iloc[0]['x']}")
    except Exception as e:
        print(f"      FAILED: {e}")
        return 1

    print("\n[2/3] COUNT(*) of applications in the last 30 days ...", flush=True)
    end = date.today().replace(day=1)
    start = end - timedelta(days=30)
    sql = (
        "SELECT COUNT(*) AS n "
        "FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR "
        f"WHERE APPLICATION_CREATED_DATETIME >= '{start}' "
        f"  AND APPLICATION_CREATED_DATETIME <  '{end}' "
        "  AND COALESCE(FLAG_ORIGINATED_AND_NOT_CANCELLED, FLAG_ORIGINATED) = TRUE"
    )
    try:
        df = snowflake.run_query(sql)
        n = int(df.iloc[0]["n"])
        print(f"      originations from {start} to {end}: n={n:,}")
    except Exception as e:
        print(f"      FAILED: {e}")
        return 1

    print("\n[3/3] introducer_volume_league_table recipe (last 90 days) ...", flush=True)
    end90 = date.today().replace(day=1)
    start90 = end90 - timedelta(days=90)
    try:
        OUT.mkdir(parents=True, exist_ok=True)
        fig = recipes.introducer_volume_league_table(
            start90, end90, top_n=10,
            title=f"Top-10 introducers by £ — {start90} to {end90}",
        )
        out_path = OUT / "introducer_volume_league_table"
        motor_graphs.save_figure(fig, out_path)
        print(f"      rendered {out_path}.png and .html")
    except Exception as e:
        print(f"      FAILED: {e}")
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

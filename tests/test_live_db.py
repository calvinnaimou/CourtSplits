"""Tests for the live-DB data layer (engine/live_db.py, and the
DATABASE_URL branch of engine/data.py). Skipped entirely unless
TEST_DATABASE_URL is set -- these need a real, schema-loaded Postgres to
run against, so they're not part of the normal `pytest` run:

    createdb courtsplitz_test
    psql -d courtsplitz_test -f db/schema.sql
    TEST_DATABASE_URL=postgresql://localhost/courtsplitz_test \\
        .venv/bin/python3 -m pytest tests/test_live_db.py -q
"""

import os
import time

import pandas as pd
import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="set TEST_DATABASE_URL to run")


def _insert_team_row(**overrides):
    import psycopg

    row = {
        "dataset": "test", "game_id": 90000001, "date": "2026-11-01", "team": "Boston",
        "venue": "H", "q1": 30, "q2": 25, "q3": 28, "q4": 22,
        "team_points": 105, "team_min": 240,
        "fgm": 40, "fga": 85, "fg3m": 12, "fg3a": 30, "ftm": 13, "fta": 15,
        "oreb": 10, "dreb": 35, "reb": 45, "ast": 25, "pf": 18, "stl": 8,
        "tov": 12, "tov_total": 13, "blk": 5,
        "opponent": "Miami", "opponent_points": 100, "win": True, "margin": 5,
        "combined_total": 205, "season_type": "regular",
        "is_home": True, "is_back_to_back": False, "in_back_to_back": False,
    }
    row.update(overrides)
    columns = list(row.keys())
    placeholders = ", ".join(["%s"] * len(columns))
    with psycopg.connect(TEST_DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(f"INSERT INTO team_boxscore ({', '.join(columns)}) VALUES ({placeholders})", list(row.values()))
        conn.commit()


@pytest.fixture(autouse=True)
def _clean_tables():
    """Every test starts from empty tables so they can run in any order
    without interfering with each other."""
    import psycopg

    with psycopg.connect(TEST_DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE player_boxscore, player_dnp, team_boxscore")
        conn.commit()
    yield


def test_fetch_live_rows_round_trips_a_real_row():
    from engine.live_db import fetch_live_rows

    _insert_team_row(team="Boston", team_points=105)
    df = fetch_live_rows("team_boxscore", TEST_DATABASE_URL)
    assert len(df) == 1
    assert df.iloc[0]["team"] == "Boston"
    assert df.iloc[0]["team_points"] == 105
    assert df["date"].dtype.kind == "M"  # datetime, not still a string


def test_fetch_live_rows_empty_table_returns_empty_df_not_none():
    from engine.live_db import fetch_live_rows

    df = fetch_live_rows("team_boxscore", TEST_DATABASE_URL)
    assert df is not None
    assert df.empty


def test_fetch_live_rows_returns_none_on_bad_connection():
    from engine.live_db import fetch_live_rows

    df = fetch_live_rows("team_boxscore", "postgresql://bogus:bogus@localhost:1/nope")
    assert df is None


def test_ttl_cache_refetches_only_after_expiry():
    from engine.live_db import TTLCache

    calls = []
    cache = TTLCache(ttl_seconds=0.2)

    def fetch():
        calls.append(1)
        return len(calls)

    assert cache.get(fetch) == 1
    assert cache.get(fetch) == 1  # still within TTL -- no refetch
    assert len(calls) == 1

    time.sleep(0.3)
    assert cache.get(fetch) == 2  # expired -- refetches
    assert len(calls) == 2


def test_engine_data_merges_historical_and_live_team_boxscore(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("LIVE_DATA_TTL_SECONDS", "0")  # don't let earlier tests' cache linger
    import importlib

    import engine.data as data_module
    importlib.reload(data_module)  # fresh TTLCache instances for this test

    _insert_team_row(team="Boston", game_id=90000002, date="2026-11-02")
    combined = data_module.team_boxscore()
    historical = data_module._historical_team_boxscore()

    assert len(combined) == len(historical) + 1
    assert 90000002 in combined["game_id"].values
    # Sorted by [team, date], same as preprocess.py's own sort -- not just
    # "however concat happened to leave it".
    assert combined.sort_values(["team", "date"]).reset_index(drop=True).equals(combined)

    importlib.reload(data_module)  # leave a clean module for whatever runs next


def test_merged_dataframe_passes_existing_integrity_checks():
    """Re-run a couple of tests/test_data_integrity.py's own assertions
    against a synthetic pd.concat -- catches dtype-concat drift (e.g.
    pandas "string" + "object" silently upcasting) that row counts alone
    wouldn't surface."""
    historical = pd.read_parquet("data/processed/team_boxscore.parquet")
    live = historical.iloc[:5].copy()
    live["game_id"] = range(90000100, 90000105)  # distinct from historical game_ids

    combined = pd.concat([historical, live], ignore_index=True)
    assert combined.duplicated(subset=["game_id", "team"]).sum() == 0
    assert (combined["margin"] == combined["team_points"] - combined["opponent_points"]).all()
    assert (combined["combined_total"] == combined["team_points"] + combined["opponent_points"]).all()

"""Loads the processed parquet files once and caches them in memory.

Historical seasons live in the committed parquet files under
data/processed/ and never change, so they stay behind a plain lru_cache.
The current live season, once DATABASE_URL is set, is fetched from
Postgres (engine/live_db.py) and merged in on top -- behind a short-TTL
cache instead, since that data can change daily and lru_cache would never
notice. Without DATABASE_URL set (local dev, CI, the test suite), every
function here behaves exactly as it always has -- historical parquet only,
no database involved at all.
"""

import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

from engine.live_db import TTLCache, fetch_live_rows

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
_LIVE_TTL_SECONDS = float(os.environ.get("LIVE_DATA_TTL_SECONDS", 3600))


@lru_cache
def _historical_player_boxscore() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "player_boxscore.parquet")


@lru_cache
def _historical_player_dnp() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "player_dnp.parquet")


@lru_cache
def _historical_team_boxscore() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "team_boxscore.parquet")


_player_boxscore_cache = TTLCache(_LIVE_TTL_SECONDS)
_player_dnp_cache = TTLCache(_LIVE_TTL_SECONDS)
_team_boxscore_cache = TTLCache(_LIVE_TTL_SECONDS)


def _with_live_data(historical: pd.DataFrame, table: str, dedup_subset: list[str], sort_cols: list[str]) -> pd.DataFrame:
    database_url = os.environ["DATABASE_URL"]
    live = fetch_live_rows(table, database_url)
    if live is None or live.empty:
        return historical
    # keep="last" -- if a game somehow exists in both (it shouldn't, historical
    # and live cover different seasons), the live row wins as the fresher one.
    combined = pd.concat([historical, live], ignore_index=True)
    combined = combined.drop_duplicates(subset=dedup_subset, keep="last")
    return combined.sort_values(sort_cols).reset_index(drop=True)


def player_boxscore() -> pd.DataFrame:
    if "DATABASE_URL" not in os.environ:
        return _historical_player_boxscore()
    return _player_boxscore_cache.get(
        lambda: _with_live_data(_historical_player_boxscore(), "player_boxscore", ["game_id", "player_id"], ["player_id", "date"])
    )


def player_dnp() -> pd.DataFrame:
    if "DATABASE_URL" not in os.environ:
        return _historical_player_dnp()
    return _player_dnp_cache.get(
        lambda: _with_live_data(_historical_player_dnp(), "player_dnp", ["game_id", "player_id"], ["player_id", "date"])
    )


def team_boxscore() -> pd.DataFrame:
    if "DATABASE_URL" not in os.environ:
        return _historical_team_boxscore()
    return _team_boxscore_cache.get(
        lambda: _with_live_data(_historical_team_boxscore(), "team_boxscore", ["game_id", "team"], ["team", "date"])
    )


@lru_cache
def teams() -> pd.DataFrame:
    # No live counterpart -- 30 static rows, roster/conference/division
    # don't change mid-season.
    return pd.read_parquet(PROCESSED / "teams.parquet")

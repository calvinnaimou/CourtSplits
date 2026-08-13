"""Loads the processed parquet files once and caches them in memory."""

from functools import lru_cache
from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"


@lru_cache
def player_boxscore() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "player_boxscore.parquet")


@lru_cache
def player_dnp() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "player_dnp.parquet")


@lru_cache
def team_boxscore() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "team_boxscore.parquet")


@lru_cache
def teams() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "teams.parquet")

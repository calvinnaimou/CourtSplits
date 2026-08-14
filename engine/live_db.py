"""Live/current-season data, read from Postgres (see db/schema.sql).
Historical seasons come from the committed parquet files instead --
engine/data.py combines both. This module is only ever touched when
DATABASE_URL is set; importing it is always safe (psycopg is imported
lazily inside fetch_live_rows(), never at module load), so local dev, CI,
and the existing test suite are unaffected when there's no database."""

import logging
import threading
import time

import pandas as pd

logger = logging.getLogger(__name__)

_SELECT = {
    "player_boxscore": "SELECT * FROM player_boxscore",
    "player_dnp": "SELECT * FROM player_dnp",
    "team_boxscore": "SELECT * FROM team_boxscore",
}

_DATE_COLUMNS = {
    "player_boxscore": ["date"],
    "player_dnp": ["date"],
    "team_boxscore": ["date"],
}

# Matches the real parquet dtypes (see data/processed/*.parquet) so
# pd.concat-ing historical + live rows in engine/data.py doesn't silently
# upcast a column (e.g. pandas "string" + plain "object" -> "object").
# Date columns are handled separately via _DATE_COLUMNS/pd.to_datetime.
_DTYPES = {
    "player_boxscore": {
        "dataset": "string", "game_id": "int64", "player_id": "int64",
        "player_name": "string", "position": "string", "team": "string",
        "opponent": "string", "venue": "string", "starter": "bool", "min": "float64",
        "fgm": "int64", "fga": "int64", "fg3m": "int64", "fg3a": "int64",
        "ftm": "int64", "fta": "int64", "oreb": "int64", "dreb": "int64",
        "reb": "int64", "ast": "int64", "pf": "int64", "stl": "int64",
        "tov": "int64", "blk": "int64", "pts": "int64", "usage_rate": "float64",
        "days_rest_raw": "string", "is_home": "bool", "days_rest_bucket": "string",
        "pra": "int64", "pts_ast": "int64", "pts_reb": "int64", "reb_ast": "int64",
        "fg2m": "int64", "fg2a": "int64", "fg2_pct": "float64", "season_type": "string",
    },
    "player_dnp": {
        "game_id": "int64", "team": "string", "opponent": "string",
        "player_id": "int64", "player_name": "string", "status": "string", "reason": "string",
    },
    "team_boxscore": {
        "dataset": "string", "game_id": "int64", "team": "string", "venue": "string",
        "q1": "int64", "q2": "int64", "q3": "int64", "q4": "int64",
        "ot1": "float64", "ot2": "float64", "ot3": "float64", "ot4": "float64", "ot5": "float64",
        "team_points": "int64", "team_min": "int64",
        "fgm": "int64", "fga": "int64", "fg3m": "int64", "fg3a": "int64",
        "ftm": "int64", "fta": "int64", "oreb": "int64", "dreb": "int64",
        "reb": "int64", "ast": "int64", "pf": "int64", "stl": "int64",
        "tov": "int64", "tov_total": "int64", "blk": "int64",
        "poss": "float64", "pace": "float64", "oeff": "float64", "deff": "float64",
        "team_rest_days_raw": "string",
        "starter_1": "string", "starter_2": "string", "starter_3": "string",
        "starter_4": "string", "starter_5": "string",
        "crew_chief": "string", "referee_umpire": "string",
        "opening_odds": "string", "opening_spread": "float64", "opening_total": "float64",
        "line_movement_1": "string", "line_movement_2": "string", "line_movement_3": "string",
        "closing_odds": "string", "closing_spread": "float64", "closing_total": "float64",
        "moneyline": "string", "halftime": "string",
        "box_score_url": "string", "full_game_odds_url": "string",
        "is_home": "bool", "is_back_to_back": "bool", "in_back_to_back": "bool",
        "opponent": "string", "opponent_points": "int64",
        "win": "bool", "margin": "int64", "combined_total": "int64", "season_type": "string",
        "covered_spread_closing": "bool", "covered_spread_opening": "bool",
    },
}


def fetch_live_rows(table: str, database_url: str) -> pd.DataFrame | None:
    """None on any failure (bad credentials, network, DB down) -- a live-DB
    hiccup should degrade to historical-only, never 500 the API."""
    import psycopg

    try:
        with psycopg.connect(database_url, connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute(_SELECT[table])
            columns = [d.name for d in cur.description]
            rows = cur.fetchall()
    except Exception:
        logger.exception("live fetch failed for %s; serving historical-only", table)
        return None

    df = pd.DataFrame.from_records(rows, columns=columns)
    if df.empty:
        return df
    for col in _DATE_COLUMNS[table]:
        df[col] = pd.to_datetime(df[col])
    return df.astype(_DTYPES[table])


class TTLCache:
    """Re-computes at most once every ttl_seconds; a plain lru_cache would
    serve stale-forever data since nothing ever invalidates it. Locked --
    FastAPI runs sync route handlers in a threadpool, so .get() can race
    across threads."""

    def __init__(self, ttl_seconds: float):
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._value = None
        self._fetched_at: float | None = None

    def get(self, fetch_fn):
        with self._lock:
            now = time.monotonic()
            if self._fetched_at is None or (now - self._fetched_at) > self._ttl_seconds:
                self._value = fetch_fn()
                self._fetched_at = now
            return self._value

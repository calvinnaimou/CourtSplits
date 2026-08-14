"""Loads a BigDataBall workbook into Postgres for the live/current season
(see db/schema.sql). Run whenever a fresh export is available:

    DATABASE_URL=postgresql://... .venv/bin/python3 scripts/ingest_live_data.py \\
        path/to/player_workbook.xlsx path/to/team_workbook.xlsx \\
        --player-sheet "NBA-2026-27-PLAYER" --team-sheet "NBA-2026-27-TEAM"

NOT incremental. This re-runs the full preprocess.py transforms over the
whole file every time and replaces each table's entire contents (TRUNCATE +
reload, one transaction) rather than upserting new rows. Two reasons:
team_rest_gaps() needs full-season context to compute rest correctly at
every row (it diffs each team's whole game log), and team rows are derived
by self-merging each game's two teams together -- neither works right on
just a slice of "new" rows. A full reload also means BigDataBall's
after-the-fact stat corrections just show up next run, and a crash midway
leaves the previous day's snapshot untouched (the transaction never
commits) instead of leaving the table half-updated.

This assumes the workbook is cumulative (the whole season to date), matching
how the existing full-season raw files are shaped -- not confirmed for the
live daily file yet since it doesn't exist until the season starts. Verify
this against the very first real file before trusting the unattended cron.
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preprocess import preprocess_player_boxscore, preprocess_player_dnp, preprocess_team_boxscore


def _rows_for_insert(df: pd.DataFrame) -> list[tuple]:
    """Plain Python values (int/float/str/bool/date/None), the way psycopg
    wants them -- NaN/NaT/pd.NA (however a given column represents "no
    value") all become SQL NULL via the same df.notna() check regardless of
    which one it is."""
    df = df.copy()
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    for col in date_cols:
        df[col] = df[col].dt.date
    df = df.astype(object).where(df.notna(), None)
    return [tuple(row) for row in df.itertuples(index=False, name=None)]


def _reload_table(conn, table: str, df: pd.DataFrame) -> None:
    columns = list(df.columns)
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
    rows = _rows_for_insert(df)
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {table}")
        if rows:
            cur.executemany(sql, rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("player_file", type=Path, help="Path to the player/DNP workbook")
    parser.add_argument("team_file", type=Path, help="Path to the team workbook")
    parser.add_argument("--player-sheet", default="NBA-2025-26-PLAYER")
    parser.add_argument("--dnp-sheet", default="DNP-DND-NWT")
    parser.add_argument("--team-sheet", default="NBA-2025-26-TEAM")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL is not set -- nothing to load into.")

    import psycopg

    player_bs = preprocess_player_boxscore(args.player_file, args.player_sheet)
    dnp = preprocess_player_dnp(args.player_file, args.dnp_sheet)
    team_bs = preprocess_team_boxscore(args.team_file, args.team_sheet)

    with psycopg.connect(database_url) as conn:
        with conn.transaction():
            _reload_table(conn, "player_boxscore", player_bs)
            _reload_table(conn, "player_dnp", dnp)
            _reload_table(conn, "team_boxscore", team_bs)

    print(f"player_boxscore: {len(player_bs)} rows")
    print(f"player_dnp:      {len(dnp)} rows")
    print(f"team_boxscore:   {len(team_bs)} rows")


if __name__ == "__main__":
    main()

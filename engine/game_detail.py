"""Full box score for a single game: both teams' team-level stats, every
player who played (from both teams), and anyone who didn't play (DNP/DND).

This is the "click a game from the results list to see everything" lookup —
each game a query returns includes a game_id that feeds straight into this.
"""

import pandas as pd

from engine.data import player_boxscore, player_dnp, team_boxscore
from engine.errors import NotFoundError


def _clean(value):
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if pd.isna(value):
        return None
    if isinstance(value, float):
        return round(value, 2)
    return value


def _clean_records(df: pd.DataFrame) -> list[dict]:
    return [
        {col: _clean(val) for col, val in record.items()}
        for record in df.to_dict("records")
    ]


def game_detail(game_id: int) -> dict:
    team_rows = team_boxscore()[team_boxscore()["game_id"] == game_id]
    player_rows = player_boxscore()[player_boxscore()["game_id"] == game_id]
    dnp_rows = player_dnp()[player_dnp()["game_id"] == game_id]

    if team_rows.empty:
        raise NotFoundError(f"no game found with game_id={game_id}")

    teams = {}
    for _, trow in team_rows.iterrows():
        team_name = trow["team"]
        team_players = player_rows[player_rows["team"] == team_name].sort_values(
            ["starter", "min"], ascending=[False, False]
        )
        team_dnps = dnp_rows[dnp_rows["team"] == team_name]
        teams[team_name] = {
            "team_stats": {k: _clean(v) for k, v in trow.to_dict().items()},
            "players": _clean_records(team_players),
            "dnp": _clean_records(team_dnps[["player_name", "status", "reason"]]),
        }

    return {
        "game_id": int(game_id),
        "date": team_rows["date"].iloc[0].strftime("%Y-%m-%d"),
        "teams": teams,
    }

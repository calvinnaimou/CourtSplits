"""Integrity checks on the processed parquet files.

Run after preprocess.py. Prints PASS/FAIL for each check; does not raise,
so you can see every issue in one run rather than stopping at the first.
"""

from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"

failures = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(label)


def validate_player_boxscore() -> None:
    print("\n=== player_boxscore ===")
    df = pd.read_parquet(PROCESSED / "player_boxscore.parquet")
    teams = pd.read_parquet(PROCESSED / "teams.parquet")

    dupes = df.duplicated(subset=["game_id", "player_id"]).sum()
    check("no duplicate (game_id, player_id) rows", dupes == 0, f"{dupes} duplicates")

    required_not_null = ["pts", "reb", "ast", "min", "team", "opponent", "date", "player_id"]
    for col in required_not_null:
        n_null = df[col].isna().sum()
        check(f"no nulls in '{col}'", n_null == 0, f"{n_null} nulls")

    arithmetic_ok = (df["pts"] == 2 * df["fg2m"] + 3 * df["fg3m"] + df["ftm"]).all()
    check("pts == 2*fg2m + 3*fg3m + ftm for every row", arithmetic_ok)

    check("fga >= fgm everywhere", (df["fga"] >= df["fgm"]).all())
    check("fg3a >= fg3m everywhere", (df["fg3a"] >= df["fg3m"]).all())
    check("fta >= ftm everywhere", (df["fta"] >= df["ftm"]).all())
    check("reb == oreb + dreb everywhere", (df["reb"] == df["oreb"] + df["dreb"]).all())

    known_teams = set(teams["short_name"])
    bad_team = set(df["team"].unique()) - known_teams
    bad_opp = set(df["opponent"].unique()) - known_teams
    check("all 'team' values match teams.parquet short_name", not bad_team, f"unmatched: {bad_team}")
    check("all 'opponent' values match teams.parquet short_name", not bad_opp, f"unmatched: {bad_opp}")

    # a player_id should map to exactly one player_name, and vice versa
    id_to_name = df.groupby("player_id")["player_name"].nunique()
    name_to_id = df.groupby("player_name")["player_id"].nunique()
    check("each player_id maps to exactly one player_name", (id_to_name == 1).all(),
          f"offenders: {id_to_name[id_to_name > 1].index.tolist()}")
    check("each player_name maps to exactly one player_id", (name_to_id == 1).all(),
          f"offenders: {name_to_id[name_to_id > 1].index.tolist()}")

    check("min is within [0, 68] (68 = longest NBA game on record, 4OT)",
          df["min"].between(0, 68).all(), f"range seen: {df['min'].min()}-{df['min'].max()}")

    check("no nulls in 'season_type'", df["season_type"].isna().sum() == 0)


def validate_team_boxscore() -> None:
    print("\n=== team_boxscore ===")
    df = pd.read_parquet(PROCESSED / "team_boxscore.parquet")
    teams = pd.read_parquet(PROCESSED / "teams.parquet")

    dupes = df.duplicated(subset=["game_id", "team"]).sum()
    check("no duplicate (game_id, team) rows", dupes == 0, f"{dupes} duplicates")

    known_teams = set(teams["short_name"])
    bad_team = set(df["team"].unique()) - known_teams
    check("all 'team' values match teams.parquet short_name", not bad_team, f"unmatched: {bad_team}")

    each_game_has_two_teams = df.groupby("game_id")["team"].nunique()
    check("every game_id has exactly 2 team rows", (each_game_has_two_teams == 2).all(),
          f"offenders: {each_game_has_two_teams[each_game_has_two_teams != 2].index.tolist()[:10]}")

    check("opponent never equals team", (df["team"] != df["opponent"]).all())
    check("margin == team_points - opponent_points", (df["margin"] == df["team_points"] - df["opponent_points"]).all())
    check("combined_total == team_points + opponent_points",
          (df["combined_total"] == df["team_points"] + df["opponent_points"]).all())
    check("no tied games (margin != 0)", (df["margin"] != 0).all())

    wins_per_game = df.groupby("game_id")["win"].sum()
    check("exactly one winner per game", (wins_per_game == 1).all(),
          f"offenders: {wins_per_game[wins_per_game != 1].index.tolist()[:10]}")

    check("no nulls in 'season_type'", df["season_type"].isna().sum() == 0)

    check("covered_spread_closing == (margin + closing_spread) > 0",
          (df["covered_spread_closing"] == ((df["margin"] + df["closing_spread"]) > 0)).all())
    check("covered_spread_opening == (margin + opening_spread) > 0",
          (df["covered_spread_opening"] == ((df["margin"] + df["opening_spread"]) > 0)).all())

    periods = ["q1", "q2", "q3", "q4", "ot1", "ot2", "ot3", "ot4", "ot5"]
    period_sum = df[periods].fillna(0).sum(axis=1)
    check("q1+q2+q3+q4+OT periods == team_points", (period_sum == df["team_points"]).all())


def main() -> None:
    validate_player_boxscore()
    validate_team_boxscore()
    print(f"\n{len(failures)} check(s) failed" if failures else "\nAll checks passed")


if __name__ == "__main__":
    main()

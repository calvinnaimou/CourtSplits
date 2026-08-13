"""Regression tests for invariants the preprocessing pipeline guarantees.
Complements scripts/validate.py (a human-readable PASS/FAIL report) with
pytest assertions that fail CI/local runs if a future change breaks them.
"""


def test_no_duplicate_player_game_rows(player_df):
    assert player_df.duplicated(subset=["game_id", "player_id"]).sum() == 0


def test_no_duplicate_team_game_rows(team_df):
    assert team_df.duplicated(subset=["game_id", "team"]).sum() == 0


def test_player_points_arithmetic(player_df):
    assert (player_df["pts"] == 2 * player_df["fg2m"] + 3 * player_df["fg3m"] + player_df["ftm"]).all()


def test_player_rebounds_arithmetic(player_df):
    assert (player_df["reb"] == player_df["oreb"] + player_df["dreb"]).all()


def test_every_player_has_a_position(player_df):
    assert player_df["position"].notna().all()


def test_positions_are_detailed_not_a_simplified_fallback(player_df):
    # NBA_Player_Positions.xlsx + missing_players_positions_filled.xlsx
    # together cover every player as of 2026-08-13 (checked by hand: 424 +
    # 158 = 582, the exact unique-player count, zero overlap). If this ever
    # fails, a new player showed up who isn't in either sheet and fell back
    # to ESPN's simplified G/F/C (or BigDataBall's raw combo tags) instead
    # -- add them to one of the two sheets and re-run preprocess.py.
    assert set(player_df["position"].unique()) <= {"PG", "SG", "SF", "PF", "C"}


def test_each_player_has_exactly_one_position(player_df):
    positions_per_player = player_df.groupby("player_name")["position"].nunique()
    assert (positions_per_player == 1).all()


def test_team_names_match_reference_table(player_df, team_df, teams_df):
    known = set(teams_df["short_name"])
    assert set(player_df["team"].unique()) <= known
    assert set(player_df["opponent"].unique()) <= known
    assert set(team_df["team"].unique()) <= known


def test_every_game_has_exactly_two_team_rows(team_df):
    counts = team_df.groupby("game_id")["team"].nunique()
    assert (counts == 2).all()


def test_no_tied_games_and_exactly_one_winner(team_df):
    assert (team_df["margin"] != 0).all()
    wins_per_game = team_df.groupby("game_id")["win"].sum()
    assert (wins_per_game == 1).all()


def test_margin_and_combined_total_arithmetic(team_df):
    assert (team_df["margin"] == team_df["team_points"] - team_df["opponent_points"]).all()
    assert (team_df["combined_total"] == team_df["team_points"] + team_df["opponent_points"]).all()


def test_covered_spread_arithmetic(team_df):
    assert (team_df["covered_spread_closing"] == ((team_df["margin"] + team_df["closing_spread"]) > 0)).all()
    assert (team_df["covered_spread_opening"] == ((team_df["margin"] + team_df["opening_spread"]) > 0)).all()


def test_quarters_and_ot_sum_to_team_points(team_df):
    periods = ["q1", "q2", "q3", "q4", "ot1", "ot2", "ot3", "ot4", "ot5"]
    assert (team_df[periods].fillna(0).sum(axis=1) == team_df["team_points"]).all()


def test_season_game_counts_match_real_nba_schedule(team_df):
    # 2025-26 regular season: 30 teams x 82 games / 2 = 1230.
    prefix = team_df["game_id"].astype(str).str[0]
    regular_games = (prefix == "2").sum() / 2
    assert regular_games == 1230


def test_team_rest_days_bucket_only_takes_known_values(team_df):
    assert set(team_df["team_rest_days_raw"].unique()) <= {"1", "2", "3+", "B2B"}


def test_is_back_to_back_matches_rest_days_bucket(team_df):
    assert (team_df["is_back_to_back"] == (team_df["team_rest_days_raw"] == "B2B")).all()


def test_rest_days_computed_from_dates_not_bigdataball_tag(team_df):
    # BigDataBall's own "TEAM REST DAYS" tag was wrong for both of these
    # rows (confirmed against the real schedule on basketball-reference.com,
    # 2026-08-13) -- Chicago's tag implied 1 day of rest, Miami's implied 1
    # day too, but both teams actually had a game-less gap of 2 and 3 days
    # respectively. team_rest_gaps() computes this from the date gap between
    # a team's actual games instead of trusting that tag, so pin these two
    # down to make sure a future change doesn't quietly go back to trusting it.
    chicago = team_df[(team_df["team"] == "Chicago") & (team_df["date"] == "2026-01-10")]
    miami = team_df[(team_df["team"] == "Miami") & (team_df["date"] == "2026-01-10")]
    assert chicago["team_rest_days_raw"].iloc[0] == "2"
    assert miami["team_rest_days_raw"].iloc[0] == "3+"


def test_in_back_to_back_covers_both_legs(team_df):
    # is_back_to_back only flags the second (no-rest) game; in_back_to_back
    # should flag that plus the game right before it, so "show me both
    # back-to-back games" can filter on one boolean.
    assert (team_df.loc[team_df["is_back_to_back"], "in_back_to_back"]).all()
    assert team_df["in_back_to_back"].sum() == 2 * team_df["is_back_to_back"].sum()

    # Concrete pair: Atlanta played 2025-10-24 then 2025-10-25 (a
    # back-to-back). The front leg had normal rest before it and isn't
    # is_back_to_back, but should still be in_back_to_back.
    front_leg = team_df[(team_df["team"] == "Atlanta") & (team_df["date"] == "2025-10-24")].iloc[0]
    back_leg = team_df[(team_df["team"] == "Atlanta") & (team_df["date"] == "2025-10-25")].iloc[0]
    assert not front_leg["is_back_to_back"] and front_leg["in_back_to_back"]
    assert back_leg["is_back_to_back"] and back_leg["in_back_to_back"]


def test_game_id_is_consistent_between_date_and_team(player_df, team_df):
    """Independent check: derive game_id from (date, team) via team_boxscore
    and confirm it matches the game_id already on every player row."""
    truth = team_df.set_index(["date", "team"])["game_id"]
    merged = player_df.merge(
        team_df[["date", "team", "game_id"]], on=["date", "team"],
        how="left", suffixes=("_player", "_truth"),
    )
    assert (merged["game_id_player"] == merged["game_id_truth"]).all()
    assert merged["game_id_truth"].notna().all()

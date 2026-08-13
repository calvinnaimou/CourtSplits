import pandas as pd
import pytest

from engine.query import NotFoundError, player_season, query_player

COLUMNS = [
    "game_id", "date", "player_name", "team", "opponent", "venue", "is_home",
    "starter", "min", "pts", "ast", "reb", "season_type", "days_rest_bucket",
    "position",
]


def make_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    return df


@pytest.fixture()
def synthetic_df() -> pd.DataFrame:
    # Player X: 5 games with Team A (current team), 1 earlier game with Team B
    # (traded mid-season) — exercises current_team_only.
    return make_df([
        dict(game_id=1, date="2025-10-01", player_name="Player X", team="Team B",
             opponent="Team C", venue="H", is_home=True, starter=True, min=20.0,
             pts=10, ast=2, reb=3, season_type="regular", days_rest_bucket="1", position="F"),
        dict(game_id=2, date="2025-11-01", player_name="Player X", team="Team A",
             opponent="Team C", venue="H", is_home=True, starter=True, min=30.0,
             pts=25, ast=5, reb=6, season_type="regular", days_rest_bucket="1", position="F"),
        dict(game_id=3, date="2025-11-05", player_name="Player X", team="Team A",
             opponent="Team D", venue="R", is_home=False, starter=True, min=32.0,
             pts=30, ast=4, reb=8, season_type="regular", days_rest_bucket="0", position="F"),
        dict(game_id=4, date="2025-11-10", player_name="Player X", team="Team A",
             opponent="Team C", venue="H", is_home=True, starter=False, min=15.0,
             pts=8, ast=1, reb=2, season_type="regular", days_rest_bucket="2", position="F"),
        dict(game_id=5, date="2025-11-15", player_name="Player X", team="Team A",
             opponent="Team D", venue="N", is_home=False, starter=True, min=34.0,
             pts=30, ast=6, reb=5, season_type="playoffs", days_rest_bucket="3+", position="F"),
        dict(game_id=6, date="2025-11-20", player_name="Player X", team="Team A",
             opponent="Team C", venue="H", is_home=True, starter=True, min=33.0,
             pts=22, ast=5, reb=7, season_type="regular", days_rest_bucket="1", position="F"),
        dict(game_id=7, date="2025-11-01", player_name="Player Y", team="Team C",
             opponent="Team A", venue="R", is_home=False, starter=True, min=28.0,
             pts=18, ast=3, reb=4, season_type="regular", days_rest_bucket="1", position="G"),
    ])


def test_unknown_player_raises_not_found(synthetic_df):
    with pytest.raises(NotFoundError):
        query_player(synthetic_df, player_name="Nobody", conditions=[
            {"metric": "pts", "threshold": 10, "direction": "over"},
        ])


def test_unknown_metric_raises_value_error(synthetic_df):
    with pytest.raises(ValueError):
        query_player(synthetic_df, player_name="Player X", conditions=[
            {"metric": "not_a_stat", "threshold": 10, "direction": "over"},
        ])


def test_current_team_only_excludes_prior_team(synthetic_df):
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ])
    # 5 games with Team A; the 1 game with Team B is excluded by default.
    assert result["sample_size"] == 5
    assert all(g["opponent"] != "Team B" for g in result["games"])


def test_current_team_only_false_includes_all_teams(synthetic_df):
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], current_team_only=False)
    assert result["sample_size"] == 6


def test_threshold_is_inclusive_at_exact_value(synthetic_df):
    # Two Team-A games have exactly 30 pts (game_id 3 and 5); "over 30" should
    # include both, matching how people phrase whole-number thresholds.
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 30, "direction": "over"},
    ], current_team_only=False)
    assert result["hits"] == 2
    assert {g["game_id"] for g in result["games"]} == {3, 5}


def test_games_list_is_hits_only(synthetic_df):
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 30, "direction": "over"},
    ])
    assert result["sample_size"] == 5  # full filtered pool
    assert result["hits"] == 2
    assert len(result["games"]) == 2  # only hits appear
    assert all(g["values"]["pts"] >= 30 for g in result["games"])


def test_multiple_conditions_require_all_to_match(synthetic_df):
    # pts >= 22 AND ast >= 5 -> game_id 2 (25/5), 5 (30/6), 6 (22/5);
    # not game_id 3 (30 pts but only 4 ast).
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 22, "direction": "over"},
        {"metric": "ast", "threshold": 5, "direction": "over"},
    ])
    assert result["hits"] == 3
    assert {g["game_id"] for g in result["games"]} == {2, 5, 6}


def test_condition_summary_describes_hits_only_not_full_sample(synthetic_df):
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 30, "direction": "over"},
    ])
    # Both hit games score exactly 30 -> average/median/min/max should all be 30,
    # not diluted by the non-hit games in the sample.
    assert result["conditions"]["pts"]["average"] == 30.0
    assert result["conditions"]["pts"]["minimum"] == 30.0
    assert result["conditions"]["pts"]["maximum"] == 30.0


def test_occurrence_rate_is_a_percentage_rounded_to_2dp(synthetic_df):
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 30, "direction": "over"},
    ])
    assert result["sample_size"] == 5
    assert result["hits"] == 2
    assert result["occurrence_rate_pct"] == 40.0


def test_season_type_filter(synthetic_df):
    both = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ])
    regular_only = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], season_type="regular")
    playoffs_only = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], season_type="playoffs")
    assert both["sample_size"] == 5
    assert regular_only["sample_size"] == 4
    assert playoffs_only["sample_size"] == 1


def test_last_n_games_omitted_uses_full_history(synthetic_df):
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ])
    assert result["sample_size"] == 5


def test_last_n_games_trims_to_most_recent(synthetic_df):
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], last_n_games=2)
    assert result["sample_size"] == 2
    assert {g["game_id"] for g in result["games"]} <= {5, 6}


def test_min_minutes_filter(synthetic_df):
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], min_minutes=30)
    assert result["sample_size"] == 4  # excludes the 15-min game (game_id 4)


def test_starter_filter(synthetic_df):
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], starter=False)
    assert result["sample_size"] == 1
    assert result["games"][0]["game_id"] == 4


def test_home_away_filter(synthetic_df):
    home = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], home_away="home")
    away = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], home_away="away")
    assert home["sample_size"] == 3
    assert away["sample_size"] == 2


def test_invalid_home_away_raises(synthetic_df):
    with pytest.raises(ValueError):
        query_player(synthetic_df, player_name="Player X", conditions=[
            {"metric": "pts", "threshold": 0, "direction": "over"},
        ], home_away="Home")


def test_unknown_opponent_raises(synthetic_df):
    with pytest.raises(ValueError):
        query_player(synthetic_df, player_name="Player X", conditions=[
            {"metric": "pts", "threshold": 0, "direction": "over"},
        ], opponent="Fake Team")


def test_empty_conditions_raises(synthetic_df):
    with pytest.raises(ValueError):
        query_player(synthetic_df, player_name="Player X", conditions=[])


def test_player_name_optional_browses_all_players(synthetic_df):
    result = query_player(synthetic_df, conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ])
    assert result["sample_size"] == 7  # every row, no player/team narrowing


def test_team_filter_without_player_name(synthetic_df):
    result = query_player(synthetic_df, team="Team A", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ])
    assert result["sample_size"] == 5
    assert all(g["team"] == "Team A" for g in result["games"])


def test_position_filter(synthetic_df):
    result = query_player(synthetic_df, position="G", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ])
    assert result["sample_size"] == 1
    assert result["games"][0]["game_id"] == 7


def test_venue_filter(synthetic_df):
    result = query_player(synthetic_df, player_name="Player X", venue="N", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], current_team_only=False)
    assert result["sample_size"] == 1
    assert result["games"][0]["game_id"] == 5


def test_invalid_venue_raises(synthetic_df):
    with pytest.raises(ValueError):
        query_player(synthetic_df, player_name="Player X", conditions=[
            {"metric": "pts", "threshold": 0, "direction": "over"},
        ], venue="X")


def test_date_range_filter(synthetic_df):
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], start_date="2025-11-05", end_date="2025-11-15")
    assert result["sample_size"] == 3  # game_ids 3, 4, 5
    assert {g["game_id"] for g in result["games"]} == {3, 4, 5}


def test_strict_vs_inclusive_direction(synthetic_df):
    inclusive = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 30, "direction": "over", "inclusive": True},
    ], current_team_only=False)
    strict = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 30, "direction": "over", "inclusive": False},
    ], current_team_only=False)
    assert inclusive["hits"] == 2  # game_ids 3, 5 score exactly 30
    assert strict["hits"] == 0  # nobody scored strictly more than 30


def test_pagination_slices_games_but_not_hits(synthetic_df):
    # 6 games total for Player X with current_team_only=False.
    full = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], current_team_only=False)
    page1 = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], current_team_only=False, page=1, page_size=2)
    page3 = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], current_team_only=False, page=3, page_size=2)

    assert full["hits"] == 6
    assert page1["hits"] == 6  # hits/sample_size describe the full pool
    assert page1["sample_size"] == full["sample_size"]
    assert len(page1["games"]) == 2
    assert page1["page"] == 1
    assert page1["page_size"] == 2
    assert page1["total_pages"] == 3
    assert len(page3["games"]) == 2
    assert page1["games"] != page3["games"]


def test_pagination_page_past_the_end_returns_empty_games(synthetic_df):
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], current_team_only=False, page=99, page_size=2)
    assert result["hits"] == 6
    assert result["games"] == []


def test_invalid_page_raises(synthetic_df):
    with pytest.raises(ValueError):
        query_player(synthetic_df, player_name="Player X", conditions=[
            {"metric": "pts", "threshold": 0, "direction": "over"},
        ], page=0)


def test_invalid_page_size_raises(synthetic_df):
    with pytest.raises(ValueError):
        query_player(synthetic_df, player_name="Player X", conditions=[
            {"metric": "pts", "threshold": 0, "direction": "over"},
        ], page_size=0)
    with pytest.raises(ValueError):
        query_player(synthetic_df, player_name="Player X", conditions=[
            {"metric": "pts", "threshold": 0, "direction": "over"},
        ], page_size=10000)


def test_full_row_includes_display_columns(synthetic_df):
    result = query_player(synthetic_df, player_name="Player X", conditions=[
        {"metric": "pts", "threshold": 0, "direction": "over"},
    ], current_team_only=False)
    game = next(g for g in result["games"] if g["game_id"] == 3)
    assert game["position"] == "F"
    assert game["team"] == "Team A"
    assert game["starter"] is True
    assert game["days_rest_bucket"] == "0"
    assert game["player_name"] == "Player X"
    assert game["stats"]["pts"] == 30
    assert game["stats"]["ast"] == 4
    assert game["stats"]["reb"] == 8
    assert game["stats"]["min"] == 32.0


# --- player_season ---

def test_player_season_defaults_to_regular(synthetic_df):
    result = player_season(synthetic_df, "Player X")
    assert result["season_type"] == "regular"
    assert result["games_played"] == 5  # excludes the 1 playoff game
    assert result["averages"]["pts"] == 19.0


def test_player_season_playoffs_toggle(synthetic_df):
    result = player_season(synthetic_df, "Player X", season_type="playoffs")
    assert result["games_played"] == 1
    assert result["averages"]["pts"] == 30.0


def test_player_season_games_in_chronological_order(synthetic_df):
    result = player_season(synthetic_df, "Player X", season_type="both")
    dates = [g["date"] for g in result["games"]]
    assert dates == sorted(dates)
    assert result["games"][0]["game_id"] == 1  # earliest date first


def test_player_season_unknown_player_raises(synthetic_df):
    with pytest.raises(NotFoundError):
        player_season(synthetic_df, "Nobody")


# --- Regression checks against the real season data ---

def test_lebron_full_season_30plus_points(player_df):
    # "over 30" is inclusive: 3 games at exactly 30 pts + 3 games above it.
    result = query_player(player_df, player_name="LeBron James", conditions=[
        {"metric": "pts", "threshold": 30, "direction": "over"},
    ])
    assert result["sample_size"] == 70
    assert result["hits"] == 6


def test_curry_last20_home_min30_threes(player_df):
    result = query_player(player_df, player_name="Stephen Curry", conditions=[
        {"metric": "fg3m", "threshold": 4.5, "direction": "over"},
    ], last_n_games=20, home_away="home", min_minutes=30)
    assert result["sample_size"] == 13
    assert result["hits"] == 6

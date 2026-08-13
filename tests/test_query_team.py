import pandas as pd
import pytest

from engine.query import NotFoundError, query_team

COLUMNS = [
    "game_id", "date", "team", "opponent", "venue", "is_home", "is_back_to_back",
    "team_rest_days_raw", "season_type", "q1", "q2", "q3", "q4", "ot1", "team_points",
    "opponent_points", "margin", "win", "closing_spread", "closing_total",
]


def make_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"])
    return df


@pytest.fixture()
def synthetic_df() -> pd.DataFrame:
    # Team A: 4 games. Spread signed as usual (favorite negative, dog positive).
    return make_df([
        # margin=+10, spread=-6.5 -> covers (10 > 6.5)
        dict(game_id=1, date="2025-10-01", team="Team A", opponent="Team B",
             venue="H", is_home=True, is_back_to_back=False, team_rest_days_raw="2",
             season_type="regular",
             q1=28, q2=27, q3=25, q4=30, ot1=None, team_points=110, opponent_points=100,
             margin=10, win=True, closing_spread=-6.5, closing_total=210.0),
        # margin=-3, spread=+6.5 -> covers (-3 > -6.5)
        dict(game_id=2, date="2025-10-05", team="Team A", opponent="Team C",
             venue="R", is_home=False, is_back_to_back=True, team_rest_days_raw="B2B",
             season_type="regular",
             q1=20, q2=22, q3=24, q4=26, ot1=None, team_points=92, opponent_points=95,
             margin=-3, win=False, closing_spread=6.5, closing_total=190.0),
        # margin=-10, spread=+6.5 -> does NOT cover (-10 < -6.5)
        dict(game_id=3, date="2025-10-10", team="Team A", opponent="Team B",
             venue="H", is_home=True, is_back_to_back=False, team_rest_days_raw="1",
             season_type="regular",
             q1=15, q2=20, q3=18, q4=22, ot1=None, team_points=75, opponent_points=85,
             margin=-10, win=False, closing_spread=6.5, closing_total=180.0),
        # playoff game, margin=+20, spread=-3.5 -> covers
        dict(game_id=4, date="2025-11-01", team="Team A", opponent="Team C",
             venue="H", is_home=True, is_back_to_back=False, team_rest_days_raw="1",
             season_type="playoffs",
             q1=30, q2=28, q3=32, q4=30, ot1=10, team_points=130, opponent_points=110,
             margin=20, win=True, closing_spread=-3.5, closing_total=220.0),
    ])


def test_unknown_team_raises_not_found(synthetic_df):
    with pytest.raises(NotFoundError):
        query_team(synthetic_df, team_name="Fake Team", conditions=[
            {"metric": "team_points", "threshold": 100, "direction": "over"},
        ])


def test_win_boolean_metric(synthetic_df):
    result = query_team(synthetic_df, team_name="Team A", conditions=[
        {"metric": "win", "threshold": True, "direction": "equals"},
    ])
    assert result["sample_size"] == 4
    assert result["hits"] == 2
    assert {g["game_id"] for g in result["games"]} == {1, 4}


def test_period_combo_sums_selected_columns(synthetic_df):
    # Q1+Q4 for game 1 = 28+30 = 58; game 4 = 30+30 = 60.
    result = query_team(synthetic_df, team_name="Team A", conditions=[
        {"periods": ["q1", "q4"], "threshold": 58, "direction": "over"},
    ])
    assert result["hits"] == 2
    values = {g["game_id"]: g["values"]["Q1+Q4"] for g in result["games"]}
    assert values == {1: 58.0, 4: 60.0}


def test_period_combo_treats_missing_ot_as_zero(synthetic_df):
    # game 1 has ot1=None; Q4+OT1 should still just be 30 (not NaN/error).
    result = query_team(synthetic_df, team_name="Team A", conditions=[
        {"periods": ["q4", "ot1"], "threshold": 0, "direction": "over"},
    ])
    game1 = next(g for g in result["games"] if g["game_id"] == 1)
    assert game1["values"]["Q4+OT1"] == 30.0


def test_invalid_period_rejected(synthetic_df):
    with pytest.raises(ValueError):
        query_team(synthetic_df, team_name="Team A", conditions=[
            {"periods": ["ot3"], "threshold": 5, "direction": "over"},
        ])


def test_metric_and_periods_both_use_available_columns_only(synthetic_df):
    # ot2 was never in this synthetic df's columns at all -> must be rejected
    # the same way a never-occurring period is, not a KeyError.
    with pytest.raises(ValueError):
        query_team(synthetic_df, team_name="Team A", conditions=[
            {"metric": "ot2", "threshold": 5, "direction": "over"},
        ])


def test_season_type_filter(synthetic_df):
    regular = query_team(synthetic_df, team_name="Team A", conditions=[
        {"metric": "team_points", "threshold": 0, "direction": "over"},
    ], season_type="regular")
    playoffs = query_team(synthetic_df, team_name="Team A", conditions=[
        {"metric": "team_points", "threshold": 0, "direction": "over"},
    ], season_type="playoffs")
    assert regular["sample_size"] == 3
    assert playoffs["sample_size"] == 1


def test_back_to_back_filter(synthetic_df):
    result = query_team(synthetic_df, team_name="Team A", conditions=[
        {"metric": "team_points", "threshold": 0, "direction": "over"},
    ], back_to_back=True)
    assert result["sample_size"] == 1
    assert result["games"][0]["game_id"] == 2


def test_team_rest_days_filter(synthetic_df):
    result = query_team(synthetic_df, team_name="Team A", team_rest_days="B2B")
    assert result["sample_size"] == 1
    assert result["games"][0]["game_id"] == 2
    assert result["games"][0]["team_rest_days"] == "B2B"


def test_team_rest_days_alone_satisfies_filter_requirement(synthetic_df):
    # No team_name given, but team_rest_days counts as a real filter.
    result = query_team(synthetic_df, team_rest_days="1")
    assert result["sample_size"] == 2  # game_ids 3, 4


def test_line_filter_narrows_pool_independent_of_condition(synthetic_df):
    # "Getting closing_spread >= 6.5 or more" -> games 2 and 3 (both spread
    # exactly +6.5). Within that pool, how often did they cover? Game 2 covers
    # (margin -3 > -6.5), game 3 doesn't (margin -10 < -6.5) -> 1 of 2 = 50%.
    result = query_team(synthetic_df, team_name="Team A", conditions=[
        {"metric": "margin", "threshold": -6.5, "direction": "over"},  # proxy for "covered"
    ], line_filters=[
        {"metric": "closing_spread", "threshold": 6.5, "direction": "over"},
    ])
    assert result["sample_size"] == 2  # games 2 and 3 only
    assert result["hits"] == 1  # only game 2 covers
    assert result["occurrence_rate_pct"] == 50.0


def test_line_filter_unknown_metric_rejected(synthetic_df):
    with pytest.raises(ValueError):
        query_team(synthetic_df, team_name="Team A", conditions=[
            {"metric": "team_points", "threshold": 0, "direction": "over"},
        ], line_filters=[
            {"metric": "not_a_real_column", "threshold": 5, "direction": "over"},
        ])


def test_no_team_and_no_filter_raises(synthetic_df):
    with pytest.raises(ValueError):
        query_team(synthetic_df)


def test_team_alone_with_no_other_filter_is_valid(synthetic_df):
    result = query_team(synthetic_df, team_name="Team A")
    assert result["sample_size"] == 4


def test_browse_without_team_name_using_another_filter(synthetic_df):
    # No team_name, but season_type narrows the pool -> valid, and browses
    # across whichever teams matched (here only Team A, but team_name was
    # never specified).
    result = query_team(synthetic_df, season_type="playoffs")
    assert result["sample_size"] == 1  # game_id 4
    assert result["games"][0]["team"] == "Team A"


def test_zero_conditions_returns_every_game(synthetic_df):
    # Unlike query_player, a purely categorical team search (no stat
    # threshold at all) is valid — every game in the pool counts as a hit.
    result = query_team(synthetic_df, team_name="Team A", conditions=[])
    assert result["sample_size"] == 4
    assert result["hits"] == 4
    assert result["occurrence_rate_pct"] == 100.0


def test_pagination_slices_games_but_not_hits(synthetic_df):
    full = query_team(synthetic_df, team_name="Team A", conditions=[])
    page1 = query_team(synthetic_df, team_name="Team A", conditions=[], page=1, page_size=2)
    page2 = query_team(synthetic_df, team_name="Team A", conditions=[], page=2, page_size=2)

    assert full["hits"] == 4
    assert page1["hits"] == 4
    assert len(page1["games"]) == 2
    assert page1["total_pages"] == 2
    assert len(page2["games"]) == 2
    assert page1["games"] != page2["games"]


def test_full_row_includes_stats_and_identity(synthetic_df):
    result = query_team(synthetic_df, team_name="Team A", conditions=[
        {"metric": "team_points", "threshold": 0, "direction": "over"},
    ])
    game = next(g for g in result["games"] if g["game_id"] == 1)
    assert game["stats"]["team_points"] == 110
    assert game["stats"]["opponent_points"] == 100
    assert game["stats"]["margin"] == 10
    assert game["win"] is True
    assert game["is_back_to_back"] is False


def test_games_are_hits_only_and_rounded(synthetic_df):
    result = query_team(synthetic_df, team_name="Team A", conditions=[
        {"metric": "team_points", "threshold": 100, "direction": "over"},
    ])
    assert result["sample_size"] == 4
    assert result["hits"] == 2
    assert len(result["games"]) == 2
    assert all(g["values"]["team_points"] >= 100 for g in result["games"])


# --- Regression checks against the real season data ---

def test_lakers_full_season_110plus_points(team_df):
    result = query_team(team_df, team_name="LA Lakers", conditions=[
        {"metric": "team_points", "threshold": 110, "direction": "over"},
    ])
    assert result["sample_size"] == 92
    assert result["hits"] == 59


def test_celtics_last20_home_105_5(team_df):
    result = query_team(team_df, team_name="Boston", conditions=[
        {"metric": "team_points", "threshold": 105.5, "direction": "over"},
    ], last_n_games=20, home_away="home")
    assert result["sample_size"] == 20
    assert result["hits"] == 14


def test_available_periods_excludes_never_occurring_ot(team_df):
    from engine.query import available_periods
    periods = available_periods(team_df)
    assert periods == ["q1", "q2", "q3", "q4", "ot1", "ot2"]
    assert "ot3" not in periods

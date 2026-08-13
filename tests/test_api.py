def test_list_players(api_client):
    r = api_client.get("/players")
    assert r.status_code == 200
    names = r.json()
    assert "LeBron James" in names
    assert names == sorted(names)


def test_list_teams(api_client):
    r = api_client.get("/teams")
    assert r.status_code == 200
    teams = r.json()
    assert len(teams) == 30
    assert {"initials", "long_name", "short_name", "conference", "division"} <= set(teams[0])


def test_player_search_case_insensitive(api_client):
    lower = api_client.get("/players/search", params={"q": "curry"}).json()
    upper = api_client.get("/players/search", params={"q": "CURRY"}).json()
    assert lower == upper
    assert "Stephen Curry" in lower
    assert lower == sorted(lower, key=str.lower)


def test_player_search_no_match_returns_empty_list(api_client):
    r = api_client.get("/players/search", params={"q": "zzznotarealplayer"})
    assert r.status_code == 200
    assert r.json() == []


def test_team_search_matches_long_name(api_client):
    r = api_client.get("/teams/search", params={"q": "lakers"})
    matches = r.json()
    assert len(matches) == 1
    assert matches[0]["short_name"] == "LA Lakers"


def test_teams_periods_excludes_never_occurring_ot(api_client):
    r = api_client.get("/teams/periods")
    assert r.status_code == 200
    assert r.json() == ["q1", "q2", "q3", "q4", "ot1", "ot2"]


def test_players_metrics_and_teams_metrics(api_client):
    player_metrics = api_client.get("/players/metrics").json()
    team_metrics = api_client.get("/teams/metrics").json()
    assert "pts" in player_metrics
    assert "player_name" not in player_metrics  # identity column, not a metric
    assert "team_points" in team_metrics
    assert "game_id" not in team_metrics


def test_player_query_success(api_client):
    r = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "pts", "threshold": 30, "direction": "over"}],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["sample_size"] == 70
    assert body["hits"] == 6
    assert "occurrence_rate_pct" in body
    assert "met_threshold" not in body["games"][0]  # games list is hits-only now


def test_player_query_unknown_player_is_404(api_client):
    r = api_client.post("/players/query", json={
        "player_name": "Not A Real Player",
        "conditions": [{"metric": "pts", "threshold": 10, "direction": "over"}],
    })
    assert r.status_code == 404


def test_player_query_unknown_metric_is_400(api_client):
    r = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "not_a_stat", "threshold": 10, "direction": "over"}],
    })
    assert r.status_code == 400


def test_player_query_bad_direction_is_400(api_client):
    r = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "pts", "threshold": 10, "direction": "sideways"}],
    })
    assert r.status_code == 400


def test_threshold_decimal_rounds_to_nearest_half(api_client):
    messy = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "pts", "threshold": 30.4345, "direction": "over"}],
    }).json()
    clean_half = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "pts", "threshold": 30.5, "direction": "over"}],
    }).json()
    whole_number = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "pts", "threshold": 30, "direction": "over"}],
    }).json()
    # 30.4345 should round to 30.5, matching the already-clean 30.5 query
    # exactly (3 strictly-above-30 games) rather than the whole-number 30
    # query (6 games, since inclusive >=30 also counts the exact-30 games).
    assert messy["hits"] == clean_half["hits"] == 3
    assert whole_number["hits"] == 6


def test_boolean_threshold_unaffected_by_rounding(api_client):
    r = api_client.post("/teams/query", json={
        "team_name": "Boston",
        "conditions": [{"metric": "win", "threshold": True, "direction": "equals"}],
        "last_n_games": 5,
    })
    assert r.status_code == 200
    assert r.json()["sample_size"] == 5


def test_player_query_bad_home_away_is_400(api_client):
    r = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "pts", "threshold": 10, "direction": "over"}],
        "home_away": "Home",
    })
    assert r.status_code == 400


def test_team_query_success(api_client):
    r = api_client.post("/teams/query", json={
        "team_name": "Boston",
        "conditions": [{"metric": "team_points", "threshold": 105.5, "direction": "over"}],
        "last_n_games": 20,
        "home_away": "home",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["sample_size"] == 20
    assert body["hits"] == 14


def test_team_query_with_periods(api_client):
    r = api_client.post("/teams/query", json={
        "team_name": "Boston",
        "conditions": [{"periods": ["q1", "q4"], "threshold": 55.5, "direction": "over"}],
        "last_n_games": 10,
    })
    assert r.status_code == 200
    body = r.json()
    assert "Q1+Q4" in body["conditions"]


def test_team_query_with_line_filters(api_client):
    r = api_client.post("/teams/query", json={
        "team_name": "Boston",
        "conditions": [{"metric": "covered_spread_closing", "threshold": True, "direction": "equals"}],
        "line_filters": [{"metric": "closing_spread", "threshold": 6.5, "direction": "over"}],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["sample_size"] == 4
    assert body["hits"] == 4


def test_team_query_unknown_team_is_404(api_client):
    r = api_client.post("/teams/query", json={
        "team_name": "Fake Team",
        "conditions": [{"metric": "team_points", "threshold": 100, "direction": "over"}],
    })
    assert r.status_code == 404


def test_game_detail_success(api_client):
    r = api_client.get("/games/22500002")
    assert r.status_code == 200
    body = r.json()
    assert body["game_id"] == 22500002
    assert set(body["teams"]) == {"Golden State", "LA Lakers"}


def test_game_detail_unknown_is_404(api_client):
    r = api_client.get("/games/999999999")
    assert r.status_code == 404


def test_player_query_player_name_optional(api_client):
    r = api_client.post("/players/query", json={
        "team": "Houston",
        "position": "PF",
        "conditions": [{"metric": "pts", "threshold": 20, "direction": "over"}],
    })
    assert r.status_code == 200
    assert r.json()["sample_size"] > 0


def test_player_query_no_conditions_is_400(api_client):
    r = api_client.post("/players/query", json={"conditions": []})
    assert r.status_code == 400


def test_team_query_no_team_and_no_filter_is_400(api_client):
    r = api_client.post("/teams/query", json={})
    assert r.status_code == 400


def test_team_query_no_team_name_with_a_filter_succeeds(api_client):
    r = api_client.post("/teams/query", json={"opponent": "Boston", "last_n_games": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["sample_size"] == 5
    assert "team" in body["games"][0]


def test_team_query_no_conditions_succeeds(api_client):
    r = api_client.post("/teams/query", json={"team_name": "Memphis"})
    assert r.status_code == 200
    body = r.json()
    assert body["sample_size"] == body["hits"]


def test_player_query_strict_vs_inclusive(api_client):
    inclusive = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "pts", "threshold": 30, "direction": "over", "inclusive": True}],
    }).json()
    strict = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "pts", "threshold": 30, "direction": "over", "inclusive": False}],
    }).json()
    assert inclusive["hits"] == 6
    assert strict["hits"] == 3


def test_player_query_bad_venue_is_400(api_client):
    r = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "pts", "threshold": 10, "direction": "over"}],
        "venue": "X",
    })
    assert r.status_code == 400


def test_player_query_row_includes_full_stat_line(api_client):
    r = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "pts", "threshold": 30, "direction": "over"}],
    })
    game = r.json()["games"][0]
    assert set(game["stats"]) >= {"min", "fgm", "fga", "pts", "usage_rate"}
    assert game["position"]
    assert game["team"] == "LA Lakers"


def test_player_query_pagination(api_client):
    full = api_client.post("/players/query", json={
        "conditions": [{"metric": "pts", "threshold": 5, "direction": "over"}],
        "page_size": 10,
    }).json()
    assert full["hits"] > 10  # a loose filter with no player pinned
    assert len(full["games"]) == 10
    assert full["page"] == 1
    assert full["page_size"] == 10
    assert full["total_pages"] == -(-full["hits"] // 10)

    page2 = api_client.post("/players/query", json={
        "conditions": [{"metric": "pts", "threshold": 5, "direction": "over"}],
        "page": 2,
        "page_size": 10,
    }).json()
    assert page2["hits"] == full["hits"]  # same pool, different slice
    assert page2["games"] != full["games"]


def test_player_query_bad_page_is_422(api_client):
    r = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "pts", "threshold": 10, "direction": "over"}],
        "page": 0,
    })
    assert r.status_code == 422  # rejected by the Pydantic Field bound (ge=1)


def test_player_query_page_size_too_large_is_422(api_client):
    r = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "pts", "threshold": 10, "direction": "over"}],
        "page_size": 10000,
    })
    assert r.status_code == 422  # rejected by the Pydantic Field bound, not the engine


def test_players_positions(api_client):
    r = api_client.get("/players/positions")
    assert r.status_code == 200
    # Detailed PG/SG/SF/PF/C only -- the BRef + missing-players sheets now
    # cover every player, so the simplified ESPN G/F/C fallback should never
    # actually surface.
    assert set(r.json()) == {"PG", "SG", "SF", "PF", "C"}


def test_player_season_success(api_client):
    r = api_client.post("/players/season", json={"player_name": "LeBron James"})
    assert r.status_code == 200
    body = r.json()
    assert body["season_type"] == "regular"
    assert body["games_played"] > 0
    assert body["games"] == sorted(body["games"], key=lambda g: g["date"])


def test_player_season_unknown_player_is_404(api_client):
    r = api_client.post("/players/season", json={"player_name": "Not A Real Player"})
    assert r.status_code == 404


def test_player_query_games_omit_full_game_stats(api_client):
    # full_game_stats used to be eagerly embedded per row via a call to
    # game_detail() for every hit -- for loose filters matching thousands of
    # rows (e.g. "pts over 5" with no player pinned) that made the query
    # itself crash. The modal fetches GET /games/{id} lazily on click
    # instead, so this field should no longer appear in query results.
    r = api_client.post("/players/query", json={
        "player_name": "LeBron James",
        "conditions": [{"metric": "pts", "threshold": 30, "direction": "over"}],
    })
    game = r.json()["games"][0]
    assert "full_game_stats" not in game
    assert game["game_id"] > 0

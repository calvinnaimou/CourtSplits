import pytest

from engine.errors import NotFoundError
from engine.game_detail import game_detail


def test_unknown_game_id_raises_not_found():
    with pytest.raises(NotFoundError):
        game_detail(999_999_999)


def test_structure_has_both_teams_with_full_stats_and_players():
    detail = game_detail(22500002)  # Warriors @ Lakers, 2025-10-21 (used in earlier manual checks)
    assert detail["date"] == "2025-10-21"
    assert set(detail["teams"]) == {"Golden State", "LA Lakers"}

    for team_data in detail["teams"].values():
        assert "team_stats" in team_data
        assert "players" in team_data
        assert "dnp" in team_data
        assert len(team_data["players"]) > 0
        for player in team_data["players"]:
            assert "player_name" in player
            assert "pts" in player


def test_players_sorted_starters_first_then_by_minutes():
    detail = game_detail(22500002)
    players = detail["teams"]["Golden State"]["players"]
    starters = [p for p in players if p["starter"]]
    bench = [p for p in players if not p["starter"]]
    # all starters should come before all bench players
    assert players[: len(starters)] == starters
    assert players[len(starters):] == bench
    # each group individually sorted by minutes descending
    assert [p["min"] for p in starters] == sorted((p["min"] for p in starters), reverse=True)
    assert [p["min"] for p in bench] == sorted((p["min"] for p in bench), reverse=True)


def test_dnp_players_included_with_reason():
    detail = game_detail(22500002)
    lakers_dnp = detail["teams"]["LA Lakers"]["dnp"]
    assert len(lakers_dnp) > 0
    for entry in lakers_dnp:
        assert set(entry) == {"player_name", "status", "reason"}


def test_win_and_covered_spread_flags_present_on_team_stats():
    detail = game_detail(22501174)  # used earlier: Boston blowout win, covered
    boston = detail["teams"]["Boston"]["team_stats"]
    assert boston["win"] is True
    assert boston["covered_spread_closing"] is True
    opponent_name = next(t for t in detail["teams"] if t != "Boston")
    opponent = detail["teams"][opponent_name]["team_stats"]
    assert opponent["win"] is False


def test_no_nan_leaks_through_as_float_nan():
    # OT columns are NaN for a game with no overtime; _clean should convert
    # them to None (JSON null), not a raw float('nan') which isn't valid JSON.
    import math

    detail = game_detail(22500002)
    for team_data in detail["teams"].values():
        ot1 = team_data["team_stats"].get("ot1")
        assert ot1 is None or not (isinstance(ot1, float) and math.isnan(ot1))

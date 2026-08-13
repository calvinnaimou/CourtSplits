from engine.data import player_boxscore, team_boxscore
from engine.game_detail import game_detail
from engine.query import query_player, query_team


def main() -> None:
    curry = query_player(
        player_boxscore(),
        player_name="Stephen Curry",
        conditions=[
            {"metric": "pts", "threshold": 29.5, "direction": "over"},
            {"metric": "ast", "threshold": 4.5, "direction": "over"},
        ],
        last_n_games=None,  # full season
    )
    print("Curry: pts > 29.5 AND ast > 4.5, full season:")
    print({k: v for k, v in curry.items() if k != "games"})
    for g in curry["games"]:
        print(" ", g)

    if curry["games"]:
        example_game_id = curry["games"][0]["game_id"]
        print(f"\nDrilling into game_id={example_game_id}:")
        detail = game_detail(example_game_id)
        print("date:", detail["date"])
        for team_name, team_data in detail["teams"].items():
            ts = team_data["team_stats"]
            print(f"  {team_name}: {ts['team_points']} pts ({'home' if ts['is_home'] else 'away'})")
            for p in team_data["players"]:
                print(f"    {p['player_name']:<25} MIN {p['min']:.1f}  PTS {p['pts']}  REB {p['reb']}  AST {p['ast']}")
            for d in team_data["dnp"]:
                print(f"    DNP: {d['player_name']} ({d['reason']})")

    print()

    celtics = query_team(
        team_boxscore(),
        team_name="Boston",
        conditions=[{"metric": "team_points", "threshold": 105.5, "direction": "over"}],
        last_n_games=20,
        home_away="home",
    )
    print("Celtics team_points > 105.5, last 20, home:")
    print({k: v for k, v in celtics.items() if k != "games"})


if __name__ == "__main__":
    main()

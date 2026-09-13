import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from engine.analytics import log_query
from engine.data import player_boxscore, team_boxscore, teams
from engine.game_detail import game_detail
from engine.query import (
    NotFoundError,
    available_periods,
    player_metrics,
    player_season,
    query_player,
    query_team,
    team_metrics,
)

from api.schemas import PlayerQueryRequest, PlayerSeasonRequest, TeamQueryRequest

app = FastAPI(title="NBA Trend Analysis API")

# Wide open ("*") by default so local dev just works. In production, set
# ALLOWED_ORIGINS to a comma-separated list (e.g. the deployed frontend's
# URL) so the API doesn't answer requests from anywhere on the internet.
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allowed_origins == "*" else _allowed_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Plain liveness check for deploy platforms/uptime monitors -- doesn't
    touch the data layer, so it stays fast and up even if the parquet files
    are somehow missing (that'll surface as a 500 on the real endpoints)."""
    return {"status": "ok"}


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/players")
def list_players() -> list[str]:
    return sorted(player_boxscore()["player_name"].unique().tolist())


@app.get("/teams")
def list_teams() -> list[dict]:
    return teams().to_dict("records")


@app.get("/players/search")
def search_players(q: str = "") -> list[str]:
    """Case-insensitive substring match, sorted alphabetically — so a
    frontend can highlight/select matches[0] on Enter, and treat an empty
    list as 'invalid player'."""
    names = player_boxscore()["player_name"].unique().tolist()
    matches = [n for n in names if q.lower() in n.lower()]
    return sorted(matches, key=str.lower)


@app.get("/teams/search")
def search_teams(q: str = "") -> list[dict]:
    """Same as /players/search but matches against short_name or long_name
    (e.g. 'lakers' finds 'LA Lakers'), sorted alphabetically by short_name."""
    records = teams().to_dict("records")
    q_lower = q.lower()
    matches = [
        r for r in records
        if q_lower in r["short_name"].lower() or q_lower in r["long_name"].lower()
    ]
    return sorted(matches, key=lambda r: r["short_name"].lower())


@app.get("/players/metrics")
def list_player_metrics() -> list[str]:
    """Valid `metric` values for a player condition."""
    return player_metrics(player_boxscore())


@app.get("/players/positions")
def list_positions() -> list[str]:
    return sorted(player_boxscore()["position"].dropna().unique().tolist())


@app.post("/players/query")
def player_query(req: PlayerQueryRequest, request: Request) -> dict:
    log_query(request, "players/query")
    return query_player(
        player_boxscore(),
        player_name=req.player_name,
        conditions=[c.model_dump() for c in req.conditions],
        last_n_games=req.last_n_games,
        home_away=req.home_away,
        venue=req.venue,
        opponent=req.opponent,
        team=req.team,
        position=req.position,
        start_date=req.start_date,
        end_date=req.end_date,
        min_minutes=req.min_minutes,
        starter=req.starter,
        days_rest_bucket=req.days_rest_bucket,
        current_team_only=req.current_team_only,
        season_type=req.season_type,
        page=req.page,
        page_size=req.page_size,
    )


@app.post("/players/season")
def player_season_route(req: PlayerSeasonRequest) -> dict:
    return player_season(
        player_boxscore(),
        player_name=req.player_name,
        season_type=req.season_type,
    )


@app.get("/teams/metrics")
def list_team_metrics() -> list[str]:
    """Valid `metric` values for a team condition or line_filter."""
    return team_metrics(team_boxscore())


@app.get("/teams/periods")
def list_periods() -> list[str]:
    """Which quarter/OT periods actually occurred this season — use this to
    build a period picker instead of hardcoding all 5 possible OT slots."""
    return available_periods(team_boxscore())


@app.get("/teams/rest-days")
def list_team_rest_days() -> list[str]:
    """Valid `team_rest_days` values: "1", "2", "3+", "B2B"."""
    return sorted(team_boxscore()["team_rest_days_raw"].dropna().unique().tolist())


@app.post("/teams/query")
def team_query(req: TeamQueryRequest, request: Request) -> dict:
    log_query(request, "teams/query")
    return query_team(
        team_boxscore(),
        team_name=req.team_name,
        conditions=[c.model_dump() for c in req.conditions],
        last_n_games=req.last_n_games,
        home_away=req.home_away,
        opponent=req.opponent,
        back_to_back=req.back_to_back,
        team_rest_days=req.team_rest_days,
        season_type=req.season_type,
        line_filters=[lf.model_dump() for lf in req.line_filters] if req.line_filters else None,
        page=req.page,
        page_size=req.page_size,
    )


@app.get("/games/{game_id}")
def game(game_id: int) -> dict:
    return game_detail(game_id)

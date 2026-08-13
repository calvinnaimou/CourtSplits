import math

from pydantic import BaseModel, Field, field_validator


def round_to_half(value: float) -> float:
    """Round-half-up to the nearest 0.5 — e.g. 30.4345 -> 30.5, 30.5 -> 30.5
    unchanged, 30 -> 30 unchanged. Sports thresholds are conventionally whole
    numbers or X.5; this keeps a free-typed decimal from producing a
    meaningless value like 30.4345."""
    return math.floor(value * 2 + 0.5) / 2


class Condition(BaseModel):
    # Either metric (a single column, e.g. "team_points") or periods (a
    # combination of quarters/OT to sum, e.g. ["q1", "q4"]) — periods is
    # team-only, since player data has no quarter-by-quarter breakdown.
    metric: str | None = None
    periods: list[str] | None = None
    threshold: float | bool
    direction: str = "over"  # "over" | "under" | "equals"
    # over -> >= threshold, under -> <= threshold when True (default);
    # False makes them strict (> / <). No effect on "equals".
    inclusive: bool = True

    @field_validator("threshold")
    @classmethod
    def _round_threshold(cls, v: float | bool) -> float | bool:
        if isinstance(v, bool):
            return v
        return round_to_half(v)


class PlayerQueryRequest(BaseModel):
    # Omit player_name to search across every player (e.g. filter by
    # team/position/date range/stat thresholds only). At least one condition
    # is still required regardless.
    player_name: str | None = None
    conditions: list[Condition]
    last_n_games: int | None = None
    home_away: str | None = None  # "home" | "away" | None
    venue: str | None = None  # "H" | "R" | "N" | None
    opponent: str | None = None
    team: str | None = None
    position: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    min_minutes: float | None = None
    starter: bool | None = None
    days_rest_bucket: str | None = None
    current_team_only: bool = True
    season_type: str = "both"  # "regular" | "playoffs" | "both"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


class PlayerSeasonRequest(BaseModel):
    player_name: str
    season_type: str = "regular"  # "regular" | "playoffs" | "both"


class TeamQueryRequest(BaseModel):
    # Omit to browse across every team (e.g. "every game against the
    # Grizzlies" without naming a specific team) — but if team_name is
    # omitted, at least one other filter must be given.
    team_name: str | None = None
    # A purely categorical search (e.g. "every game against the Grizzlies")
    # is valid on its own — unlike player queries, conditions may be empty.
    conditions: list[Condition] = []
    last_n_games: int | None = None
    home_away: str | None = None
    opponent: str | None = None
    back_to_back: bool | None = None
    team_rest_days: str | None = None  # "1" | "2" | "3+" | "B2B"
    season_type: str = "both"  # "regular" | "playoffs" | "both"
    # Narrows the sample to games where a real historical value (e.g.
    # closing_spread) was at/beyond a line, BEFORE measuring how often
    # `conditions` hit within that group — e.g. "when this team was getting
    # at least +6.5, how often did they cover?"
    line_filters: list[Condition] | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)

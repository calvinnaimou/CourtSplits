"""Core stats engine. Filter historical games and report how often the given
conditions were all true at once (e.g. "30+ points AND 5+ assists"). Team
conditions can also target a combo of scoring periods, like "1st + 4th
quarter points", instead of a single metric column.

Team queries also take "line filters", which narrow the sample down to games
where a real historical value (closing_spread, say) was at or beyond some
number first. That's what lets you ask prop-style questions like "when this
team was getting at least +6.5, how often did they actually cover?"

No web/UI stuff lives here — just DataFrame + filter params in, plain dict
out. Something else (the API layer) wraps this for HTTP.
"""

import math

import pandas as pd

from engine.errors import NotFoundError

DIRECTION_NAMES = {"over", "under", "equals"}
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500


def _comparator(direction: str, inclusive: bool):
    """'over'/'under' default inclusive (>=/<=) — matches how people phrase
    whole-number thresholds ("30 or more"). Pass inclusive=False for a
    strict >/< comparison instead. 'equals' ignores inclusive."""
    if direction == "over":
        return (lambda values, t: values >= t) if inclusive else (lambda values, t: values > t)
    if direction == "under":
        return (lambda values, t: values <= t) if inclusive else (lambda values, t: values < t)
    return lambda values, t: values == t


SEASON_TYPES = {"regular", "playoffs", "both"}
HOME_AWAY_VALUES = {None, "home", "away"}
VENUE_VALUES = {None, "H", "R", "N"}
ALL_PERIODS = ["q1", "q2", "q3", "q4", "ot1", "ot2", "ot3", "ot4", "ot5"]

# Full box-score line shown for every row in a player search, regardless of
# which columns were actually used as filter conditions.
PLAYER_ROW_STAT_COLUMNS = [
    "min", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
    "oreb", "dreb", "reb", "ast", "pf", "stl", "tov", "blk", "pts",
    "pra", "pts_reb", "reb_ast", "usage_rate",
]

# Same idea, team side: every column from the raw BigDataBall sheet
# (quarters/OT, shooting splits, team_min, tov_total) plus the derived
# columns that aren't in the raw sheet (opponent_points, margin,
# combined_total). OT3-5 skipped, same reason — see available_periods().
TEAM_ROW_STAT_COLUMNS = [
    "q1", "q2", "q3", "q4", "ot1", "ot2",
    "team_min", "fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
    "oreb", "dreb", "reb", "ast", "pf", "stl", "tov", "tov_total", "blk",
    "team_points", "opponent_points", "margin", "combined_total",
    "poss", "pace", "oeff", "deff",
]

# Columns that identify/describe a row rather than something you'd set a
# threshold on — everything else in the dataframe is a valid metric name.
PLAYER_NON_METRIC_COLUMNS = {
    "dataset", "game_id", "date", "player_id", "player_name", "position",
    "team", "opponent", "venue", "starter", "is_home",
    "days_rest_bucket", "season_type",
}
TEAM_NON_METRIC_COLUMNS = {
    "dataset", "game_id", "date", "team", "opponent", "venue", "season_type",
    "team_rest_days_raw", "crew_chief", "referee_umpire", "opening_odds",
    "line_movement_1", "line_movement_2", "line_movement_3", "closing_odds",
    "moneyline", "halftime", "box_score_url", "full_game_odds_url",
    "starter_1", "starter_2", "starter_3", "starter_4", "starter_5",
}


def available_periods(df: pd.DataFrame) -> list[str]:
    """Only the scoring periods that actually occurred at least once (e.g.
    OT3-5 never happened this season, so they're not offered as options)."""
    return [p for p in ALL_PERIODS if p in df.columns and df[p].notna().any()]


def player_metrics(df: pd.DataFrame) -> list[str]:
    """Every column that's valid as a query_player condition metric."""
    return [c for c in df.columns if c not in PLAYER_NON_METRIC_COLUMNS]


def team_metrics(df: pd.DataFrame) -> list[str]:
    """Every column that's valid as a query_team condition metric — period
    columns that never occurred (e.g. ot3-5) are excluded, same as periods."""
    never_occurred = set(ALL_PERIODS) - set(available_periods(df))
    return [c for c in df.columns if c not in TEAM_NON_METRIC_COLUMNS and c not in never_occurred]


def _r2(value):
    """Round to 2 decimal places; passes None through untouched."""
    return None if value is None else round(float(value), 2)


def _display_value(value):
    """Clean a single row value for a full-row display column: rounds
    floats, passes bools/strings through as-is, turns NaN into None."""
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return None
    if isinstance(value, float):
        return round(value, 2)
    return value


def _condition_label(cond: dict) -> str:
    """'q1'+'q4' -> 'Q1+Q4'; a plain metric just uses its own name."""
    if cond.get("periods"):
        return "+".join(p.upper() for p in cond["periods"])
    return cond["metric"]


def _condition_series(df: pd.DataFrame, cond: dict) -> pd.Series:
    """The per-game value a condition is checked against. A period combo is
    summed across those columns (missing OT periods count as 0 — the team
    just didn't play one, not missing data)."""
    if cond.get("periods"):
        return df[cond["periods"]].fillna(0).sum(axis=1)
    return df[cond["metric"]]


def _valid_metrics_for(df: pd.DataFrame) -> list[str]:
    if "player_name" in df.columns:
        return player_metrics(df)
    return team_metrics(df)


def _validate_conditions(df: pd.DataFrame, conditions: list[dict], require_nonempty: bool = True) -> None:
    if not conditions:
        if require_nonempty:
            raise ValueError("at least one condition is required")
        return
    valid_periods = available_periods(df)
    valid_metrics = _valid_metrics_for(df)
    for cond in conditions:
        periods = cond.get("periods")
        if periods:
            if not isinstance(periods, list) or not periods:
                raise ValueError("periods must be a non-empty list")
            for p in periods:
                if p not in valid_periods:
                    raise ValueError(f"invalid or never-occurring period: {p!r}, must be one of {valid_periods}")
        elif cond.get("metric") not in valid_metrics:
            raise ValueError(f"unknown metric: {cond.get('metric')!r}, must be one of {valid_metrics}")

        if cond.get("direction", "over") not in DIRECTION_NAMES:
            raise ValueError(f"direction must be one of {sorted(DIRECTION_NAMES)}")


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1:
        raise ValueError("page must be >= 1")
    if not (1 <= page_size <= MAX_PAGE_SIZE):
        raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}")


def _paginate(hit_subset: pd.DataFrame, page: int, page_size: int) -> tuple[pd.DataFrame, int]:
    """Slice to just the requested page — the (often expensive) per-row
    stat/identity work in _game_rows only runs on this slice, not every hit."""
    n_hits = len(hit_subset)
    total_pages = math.ceil(n_hits / page_size) if n_hits else 0
    start = (page - 1) * page_size
    return hit_subset.iloc[start : start + page_size], total_pages


def _validate_home_away(home_away: str | None) -> None:
    if home_away not in HOME_AWAY_VALUES:
        raise ValueError(f"home_away must be one of {sorted(v for v in HOME_AWAY_VALUES if v)} or null")


def _validate_venue(venue: str | None) -> None:
    if venue not in VENUE_VALUES:
        raise ValueError(f"venue must be one of {sorted(v for v in VENUE_VALUES if v)} or null")


def _validate_opponent(df: pd.DataFrame, opponent: str | None) -> None:
    if opponent is not None and opponent not in df["team"].unique():
        raise ValueError(f"unknown opponent: {opponent!r}")


def _filter_season_type(subset: pd.DataFrame, season_type: str) -> pd.DataFrame:
    if season_type not in SEASON_TYPES:
        raise ValueError(f"season_type must be one of {sorted(SEASON_TYPES)}")
    if season_type == "both":
        # "both" = no filter — also keeps play-in / NBA Cup final games, which
        # exist in the data but aren't "regular" or "playoffs" specifically.
        return subset
    return subset[subset["season_type"] == season_type]


def _apply_line_filters(subset: pd.DataFrame, line_filters: list[dict] | None) -> pd.DataFrame:
    """Narrows the sample to games where a real historical value (closing_
    spread, closing_total, whatever) met a threshold. This is a pool filter,
    not a hit/miss condition — it doesn't count toward 'hits' below, it just
    shrinks the pool before hits get counted."""
    if not line_filters:
        return subset
    valid_metrics = team_metrics(subset)
    for lf in line_filters:
        metric = lf.get("metric")
        if metric not in valid_metrics:
            raise ValueError(f"unknown line_filter metric: {metric!r}, must be one of {valid_metrics}")
        direction = lf.get("direction", "over")
        if direction not in DIRECTION_NAMES:
            raise ValueError(f"direction must be one of {sorted(DIRECTION_NAMES)}")
        inclusive = lf.get("inclusive", True)
        subset = subset[_comparator(direction, inclusive)(subset[metric], lf["threshold"])]
    return subset


def _combined_hits(subset: pd.DataFrame, conditions: list[dict]) -> pd.Series:
    hits = pd.Series(True, index=subset.index)
    for cond in conditions:
        direction = cond.get("direction", "over")
        inclusive = cond.get("inclusive", True)
        values = _condition_series(subset, cond)
        hits &= _comparator(direction, inclusive)(values, cond["threshold"])
    return hits


def _condition_summaries(hit_subset: pd.DataFrame, conditions: list[dict]) -> dict:
    """Stats describing only the games where every condition was met."""
    summaries = {}
    for cond in conditions:
        values = _condition_series(hit_subset, cond).astype(float)
        summaries[_condition_label(cond)] = dict(
            average=_r2(values.mean()) if len(values) else None,
            median=_r2(values.median()) if len(values) else None,
            std_dev=_r2(values.std()) if len(values) > 1 else None,
            minimum=_r2(values.min()) if len(values) else None,
            maximum=_r2(values.max()) if len(values) else None,
        )
    return summaries


def _game_rows(
    hit_subset: pd.DataFrame,
    conditions: list[dict],
    extra_cols: dict,
    stat_columns: list[str] | None = None,
    identity_cols: dict[str, str] | None = None,
) -> list[dict]:
    """One row per game that met every condition (games list is hits-only,
    so there's no need for a met_threshold flag on each row).

    stat_columns/identity_cols additionally attach the complete box-score
    line (every stat column, not just the ones used as filter conditions)
    plus identifying fields — for search screens that always show the full
    row regardless of what was filtered on."""
    condition_series = {
        _condition_label(cond): _condition_series(hit_subset, cond) for cond in conditions
    }
    games = []
    for idx, row in zip(hit_subset.index, hit_subset.itertuples()):
        game = {
            "game_id": row.game_id,
            "date": row.date.strftime("%Y-%m-%d"),
            "opponent": row.opponent,
            "venue": row.venue,
            "season_type": row.season_type,
            "values": {label: _r2(series.loc[idx]) for label, series in condition_series.items()},
        }
        for key, col in extra_cols.items():
            game[key] = _r2(getattr(row, col))
        if identity_cols:
            for key, col in identity_cols.items():
                game[key] = _display_value(getattr(row, col, None))
        if stat_columns:
            game["stats"] = {
                col: _display_value(getattr(row, col))
                for col in stat_columns
                if col in hit_subset.columns
            }
        games.append(game)
    return games


def query_player(
    df: pd.DataFrame,
    player_name: str | None = None,
    conditions: list[dict] | None = None,
    last_n_games: int | None = None,
    home_away: str | None = None,  # "home" | "away" | None
    venue: str | None = None,  # "H" | "R" | "N" | None
    opponent: str | None = None,
    team: str | None = None,
    position: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    min_minutes: float | None = None,
    starter: bool | None = None,
    days_rest_bucket: str | None = None,
    current_team_only: bool = True,
    season_type: str = "both",  # "regular" | "playoffs" | "both"
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> dict:
    """player_name is optional — omit it to search across every player (e.g.
    filter by team/position/date range/stat thresholds only). At least one
    numeric condition is still required either way; a player search with no
    stat filter at all isn't supported (unlike query_team).

    current_team_only (on by default) locks the search to whichever team the
    player's most recent game in the full dataset was for, before any other
    filter runs. Combine that with an explicit team= for a team they were
    traded away from and you'll get zero rows, not their old-team games —
    current_team_only wins. Nobody's hit this in practice since the frontend
    never sends an explicit team for a pinned player, but it'd be a
    confusing silent-empty-result if it ever came up.

    games is paginated (page/page_size) since a loose filter with no player
    pinned can match tens of thousands of rows — sample_size/hits/conditions
    still describe the full matching pool, only the games list is sliced."""
    conditions = conditions or []
    _validate_conditions(df, conditions, require_nonempty=True)
    _validate_home_away(home_away)
    _validate_venue(venue)
    _validate_opponent(df, opponent)
    _validate_pagination(page, page_size)

    subset = df

    if player_name is not None:
        if player_name not in df["player_name"].unique():
            raise NotFoundError(f"unknown player_name: {player_name!r}")
        subset = subset[subset["player_name"] == player_name]

        if current_team_only and not subset.empty:
            current_team = subset.sort_values("date")["team"].iloc[-1]
            subset = subset[subset["team"] == current_team]

    if team is not None:
        subset = subset[subset["team"] == team]

    if position is not None:
        subset = subset[subset["position"] == position]

    subset = _filter_season_type(subset, season_type)

    if home_away == "home":
        subset = subset[subset["is_home"]]
    elif home_away == "away":
        subset = subset[~subset["is_home"]]

    if venue is not None:
        subset = subset[subset["venue"] == venue]

    if opponent is not None:
        subset = subset[subset["opponent"] == opponent]

    if start_date is not None:
        subset = subset[subset["date"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        subset = subset[subset["date"] <= pd.to_datetime(end_date)]

    if min_minutes is not None:
        subset = subset[subset["min"] >= min_minutes]

    if starter is not None:
        subset = subset[subset["starter"] == starter]

    if days_rest_bucket is not None:
        subset = subset[subset["days_rest_bucket"] == days_rest_bucket]

    subset = subset.sort_values("date", ascending=False)
    if last_n_games is not None:
        subset = subset.head(last_n_games)
    subset = subset.sort_values("date")

    hits = _combined_hits(subset, conditions)
    hit_subset = subset[hits]
    sample_size = len(subset)
    n_hits = len(hit_subset)
    page_subset, total_pages = _paginate(hit_subset, page, page_size)

    return dict(
        sample_size=sample_size,
        hits=n_hits,
        occurrence_rate_pct=_r2(n_hits / sample_size * 100) if sample_size else None,
        average_minutes=_r2(hit_subset["min"].mean()) if n_hits else None,
        conditions=_condition_summaries(hit_subset, conditions),
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        games=_game_rows(
            page_subset, conditions, {"minutes": "min"},
            stat_columns=PLAYER_ROW_STAT_COLUMNS,
            identity_cols={
                "player_name": "player_name", "position": "position", "team": "team",
                "starter": "starter", "days_rest_bucket": "days_rest_bucket",
            },
        ),
    )


def player_season(df: pd.DataFrame, player_name: str, season_type: str = "regular") -> dict:
    """A player's full game log for one season scope, chronological, plus
    their averages across it — the "click a player's name" drill-down from
    the search screen. season_type defaults to regular season only."""
    if player_name not in df["player_name"].unique():
        raise NotFoundError(f"unknown player_name: {player_name!r}")

    subset = df[df["player_name"] == player_name]
    subset = _filter_season_type(subset, season_type)
    subset = subset.sort_values("date")

    games_played = len(subset)
    averages = {
        col: _r2(subset[col].astype(float).mean()) if games_played else None
        for col in PLAYER_ROW_STAT_COLUMNS
        if col in subset.columns
    }

    return dict(
        player_name=player_name,
        season_type=season_type,
        games_played=games_played,
        averages=averages,
        games=_game_rows(
            subset, [], {"minutes": "min"},
            stat_columns=PLAYER_ROW_STAT_COLUMNS,
            identity_cols={
                "player_name": "player_name", "position": "position", "team": "team",
                "starter": "starter", "days_rest_bucket": "days_rest_bucket",
            },
        ),
    )


def query_team(
    df: pd.DataFrame,
    team_name: str | None = None,
    conditions: list[dict] | None = None,
    last_n_games: int | None = None,
    home_away: str | None = None,
    opponent: str | None = None,
    back_to_back: bool | None = None,
    team_rest_days: str | None = None,
    season_type: str = "both",  # "regular" | "playoffs" | "both"
    line_filters: list[dict] | None = None,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> dict:
    """team_name is optional — omit it to browse across every team. Unlike
    query_player, no numeric condition is required either; instead, at
    least one filter of any kind (team, opponent, home/away, back-to-back,
    team_rest_days, a non-default season_type, last_n_games, a condition, or
    a line_filter) must be given, so an entirely unfiltered "every game
    ever" search isn't possible.

    games is paginated the same way as query_player — sample_size/hits/
    conditions describe the full matching pool, only the games list is
    sliced to the requested page."""
    conditions = conditions or []
    if not any([
        team_name, opponent, home_away, back_to_back is not None, team_rest_days,
        season_type != "both", last_n_games, conditions, line_filters,
    ]):
        raise ValueError("at least one filter is required")
    if team_name is not None and team_name not in df["team"].unique():
        raise NotFoundError(f"unknown team_name: {team_name!r}")
    _validate_conditions(df, conditions, require_nonempty=False)
    _validate_home_away(home_away)
    _validate_opponent(df, opponent)
    _validate_pagination(page, page_size)

    subset = df if team_name is None else df[df["team"] == team_name]

    subset = _filter_season_type(subset, season_type)

    if home_away == "home":
        subset = subset[subset["is_home"]]
    elif home_away == "away":
        subset = subset[~subset["is_home"]]

    if opponent is not None:
        subset = subset[subset["opponent"] == opponent]

    if back_to_back is not None:
        subset = subset[subset["is_back_to_back"] == back_to_back]

    if team_rest_days is not None:
        subset = subset[subset["team_rest_days_raw"] == team_rest_days]

    subset = _apply_line_filters(subset, line_filters)

    subset = subset.sort_values("date", ascending=False)
    if last_n_games is not None:
        subset = subset.head(last_n_games)
    subset = subset.sort_values("date")

    hits = _combined_hits(subset, conditions)
    hit_subset = subset[hits]
    sample_size = len(subset)
    n_hits = len(hit_subset)
    page_subset, total_pages = _paginate(hit_subset, page, page_size)

    return dict(
        sample_size=sample_size,
        hits=n_hits,
        occurrence_rate_pct=_r2(n_hits / sample_size * 100) if sample_size else None,
        conditions=_condition_summaries(hit_subset, conditions),
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        games=_game_rows(
            page_subset, conditions, {},
            stat_columns=TEAM_ROW_STAT_COLUMNS,
            identity_cols={
                "team": "team", "win": "win", "is_back_to_back": "is_back_to_back",
                "team_rest_days": "team_rest_days_raw",
            },
        ),
    )

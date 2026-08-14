"""Clean raw NBA box score Excel exports into typed parquet files.

Reads data/raw/*.xlsx and writes data/processed/*.parquet:
  - player_boxscore.parquet
  - player_dnp.parquet
  - team_boxscore.parquet
  - teams.parquet
"""

import re
import unicodedata
from pathlib import Path

import pandas as pd

from espn_positions import ESPN_POSITIONS

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
BREF_POSITIONS_FILE = PROCESSED / "NBA_Player_Positions.xlsx"
MISSING_POSITIONS_FILE = PROCESSED / "missing_players_positions_filled.xlsx"

_SUFFIX_RE = re.compile(r"\s+(jr|sr|ii|iii|iv|v)\.?$")


def _normalize_name(name: str) -> str:
    """'O.G. Anunoby' / 'Craig Porter Jr.' / 'Luka Dončić' -> 'og anunoby' /
    'craig porter' / 'luka doncic', so different sources' naming conventions
    line up with BigDataBall's plain-ASCII, no-suffix names."""
    n = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    n = n.strip().lower().replace(".", "")
    n = _SUFFIX_RE.sub("", n)
    return re.sub(r"\s+", " ", n).strip()


def _normalized_map(mapping: dict) -> dict:
    out: dict = {}
    for name, value in mapping.items():
        out.setdefault(_normalize_name(name), value)
    return out


def _load_bref_positions() -> dict:
    """Detailed PG/SG/SF/PF/C positions. Basketball-Reference blocks
    automated fetching, so this is a manually-provided sheet (not re-fetched
    on every preprocessing run) -- see data/processed/NBA_Player_Positions.xlsx."""
    if not BREF_POSITIONS_FILE.exists():
        return {}
    df = pd.read_excel(BREF_POSITIONS_FILE)
    return dict(zip(df["Player"], df["Position"]))


def _load_missing_players_positions() -> dict:
    """Same idea as the BRef sheet, but specifically for the players it
    doesn't cover -- manually filled in by the user rather than fetched,
    same reasoning as the BRef sheet (also see espn_positions.py). Together
    these two sheets cover every player in the box score data as of
    2026-08-13, so ESPN/raw BigDataBall below shouldn't actually get used
    anymore -- kept as a fallback in case a new player shows up who isn't
    in either sheet yet."""
    if not MISSING_POSITIONS_FILE.exists():
        return {}
    df = pd.read_excel(MISSING_POSITIONS_FILE)
    return dict(zip(df["Name"], df["Position"]))


_BREF_POSITIONS = _load_bref_positions()
_NORMALIZED_BREF_POSITIONS = _normalized_map(_BREF_POSITIONS)
_MISSING_PLAYERS_POSITIONS = _load_missing_players_positions()
_NORMALIZED_MISSING_PLAYERS_POSITIONS = _normalized_map(_MISSING_PLAYERS_POSITIONS)
_NORMALIZED_ESPN_POSITIONS = _normalized_map(ESPN_POSITIONS)


def apply_position_overrides(position: pd.Series, player_name: pd.Series) -> pd.Series:
    """Layered position override, most trustworthy first:
    1. Basketball-Reference sheet -- detailed PG/SG/SF/PF/C, 424 players.
    2. The "missing players" sheet -- same PG/SG/SF/PF/C detail, manually
       filled in for the players the BRef sheet doesn't cover. Between the
       two, every player in the box score data is covered (424 + 158 = 582
       unique players, zero overlap, zero gaps -- checked 2026-08-13).
    3. ESPN's current roster position -- simpler G/F/C. Shouldn't matter
       anymore given #1+#2 cover everyone, but stays as a fallback.
    4. BigDataBall's own raw POSITION -- last resort for anyone none of the
       above cover (e.g. a new player added to the data later)."""
    normalized_name = player_name.map(_normalize_name)
    bref = player_name.map(_BREF_POSITIONS).fillna(normalized_name.map(_NORMALIZED_BREF_POSITIONS))
    missing = player_name.map(_MISSING_PLAYERS_POSITIONS).fillna(
        normalized_name.map(_NORMALIZED_MISSING_PLAYERS_POSITIONS)
    )
    espn = player_name.map(ESPN_POSITIONS).fillna(normalized_name.map(_NORMALIZED_ESPN_POSITIONS))
    return bref.fillna(missing).fillna(espn).fillna(position)

PLAYER_FILE = RAW / "2025-2026-NBA_Player_BoxScore-Dataset.xlsx"
TEAM_FILE = RAW / "2025-2026_NBA_Team_BoxScore-Stats.xlsx"


def clean_column_names(columns: pd.Index) -> pd.Index:
    return (
        columns
        .str.replace("\n", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


SEASON_TYPE_BY_PREFIX = {
    "1": "preseason",
    "2": "regular",  # includes NBA Cup group-stage games, which count in standings
    "3": "all_star",
    "4": "playoffs",
    "5": "play_in",
    "6": "nba_cup_final",
}


def season_type(game_id: pd.Series) -> pd.Series:
    prefix = game_id.astype(str).str[0]
    return prefix.map(SEASON_TYPE_BY_PREFIX)


def days_rest_bucket(raw: pd.Series) -> pd.Series:
    """Collapse to the standard 0 / 1 / 2 / 3+ rest buckets used for filtering."""
    numeric = pd.to_numeric(raw, errors="coerce")
    bucket = numeric.clip(upper=3).astype("Int64").astype(str)
    bucket = bucket.where(numeric.notna(), "3+")
    bucket = bucket.mask(bucket == "<NA>", "3+")
    return bucket.replace({"0": "0", "1": "1", "2": "2", "3": "3+"})


def team_rest_gaps(team: pd.Series, date: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Days of rest before and after each game (rest_before, rest_after),
    from the calendar gap to that team's previous/next game in this
    dataset. NaN at either end of a team's tracked games — no prior/next
    game to compare against.

    We used to trust BigDataBall's raw "TEAM REST DAYS" tag for rest_before
    ("3IN4", "3IN4-B2B", etc), but that tag describes schedule context
    ("3rd game in a 4-day stretch"), not the actual rest count, and it's not
    reliable for guessing the latter: a "3IN4" game could be the stretch's
    last leg coming off a back-to-back (1 day of rest, the common case) or
    its first leg with 2+ days of rest. Checked a couple of these against
    the real schedule on basketball-reference.com and the tag was wrong
    both times, so now we just do the date math directly instead of
    guessing from the label.

    rest_after exists so we can tell the front leg of a back-to-back from
    the back leg: is_back_to_back only catches the second game (0 days
    *before* it) — the first game had normal rest before it and only looks
    like part of a back-to-back if you check what came *after* it too."""
    frame = pd.DataFrame({"team": team, "date": date}).sort_values(["team", "date"])
    rest_before = frame.groupby("team")["date"].diff().dt.days - 1
    rest_after = rest_before.groupby(frame["team"]).shift(-1)
    return rest_before.reindex(date.index), rest_after.reindex(date.index)


def team_rest_days_bucket(gap: pd.Series) -> pd.Series:
    """Bucket a computed rest-day gap into 1 / 2 / 3+ / B2B (0 days) —
    mirrors days_rest_bucket()'s player-side buckets, with "B2B" standing
    in for "0" since that's the term used throughout the team screens.
    NaN (a team's first tracked game) buckets to "3+"."""
    bucket = gap.clip(upper=3).astype("Int64").astype(str)
    bucket = bucket.where(gap.notna(), "3+")
    return bucket.replace({"0": "B2B", "3": "3+"})


def preprocess_player_boxscore(player_file: Path = PLAYER_FILE, sheet_name: str = "NBA-2025-26-PLAYER") -> pd.DataFrame:
    df = pd.read_excel(player_file, sheet_name=sheet_name)
    df.columns = clean_column_names(df.columns)

    df = df.rename(columns={
        "BIGDATABALL DATASET": "dataset",
        "GAME-ID": "game_id",
        "DATE": "date",
        "PLAYER-ID": "player_id",
        "PLAYER FULL NAME": "player_name",
        "POSITION": "position",
        "OWN TEAM": "team",
        "OPPONENT TEAM": "opponent",
        "VENUE (R/H/N)": "venue",
        "STARTER (Y/N)": "starter",
        "MIN": "min",
        "FG": "fgm",
        "FGA": "fga",
        "3P": "fg3m",
        "3PA": "fg3a",
        "FT": "ftm",
        "FTA": "fta",
        "OR": "oreb",
        "DR": "dreb",
        "TOT": "reb",
        "A": "ast",
        "PF": "pf",
        "ST": "stl",
        "TO": "tov",
        "BL": "blk",
        "PTS": "pts",
        "USAGE RATE (%)": "usage_rate",
        "DAYS REST": "days_rest_raw",
    })

    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y")
    df["starter"] = df["starter"].map({"Y": True, "N": False})
    df["is_home"] = df["venue"] == "H"
    df["position"] = apply_position_overrides(df["position"], df["player_name"])
    df["days_rest_bucket"] = days_rest_bucket(df["days_rest_raw"])
    df["days_rest_raw"] = df["days_rest_raw"].astype(str)

    df["pra"] = df["pts"] + df["reb"] + df["ast"]
    df["pts_ast"] = df["pts"] + df["ast"]
    df["pts_reb"] = df["pts"] + df["reb"]
    df["reb_ast"] = df["reb"] + df["ast"]

    df["fg2m"] = df["fgm"] - df["fg3m"]
    df["fg2a"] = df["fga"] - df["fg3a"]
    df["fg2_pct"] = (df["fg2m"] / df["fg2a"]).where(df["fg2a"] > 0)
    df["season_type"] = season_type(df["game_id"])

    df = df.sort_values(["player_id", "date"]).reset_index(drop=True)
    return df


def preprocess_player_dnp(player_file: Path = PLAYER_FILE, sheet_name: str = "DNP-DND-NWT") -> pd.DataFrame:
    df = pd.read_excel(player_file, sheet_name=sheet_name)
    df.columns = clean_column_names(df.columns)
    df = df.rename(columns={
        "GAME DATE": "date",
        "GAME-ID": "game_id",
        "TEAM": "team",
        "OPPONENT": "opponent",
        "PLAYER-ID": "player_id",
        "PLAYER NAME": "player_name",
        "STATUS": "status",
        "REASON": "reason",
    })
    return df.sort_values(["player_id", "date"]).reset_index(drop=True)


def preprocess_team_boxscore(team_file: Path = TEAM_FILE, sheet_name: str = "NBA-2025-26-TEAM") -> pd.DataFrame:
    df = pd.read_excel(team_file, sheet_name=sheet_name)
    df.columns = clean_column_names(df.columns)

    # The 5 starting-lineup names live in "STARTING LINEUPS" + 4 unnamed
    # columns immediately after it (Excel merged header, one label for 5 cols).
    lineup_idx = df.columns.get_loc("STARTING LINEUPS")
    starter_cols = list(df.columns[lineup_idx: lineup_idx + 5])
    rename_starters = {col: f"starter_{i+1}" for i, col in enumerate(starter_cols)}

    df = df.rename(columns={
        "BIGDATABALL DATASET": "dataset",
        "GAME-ID": "game_id",
        "DATE": "date",
        "TEAM": "team",
        "VENUE (R/H/N)": "venue",
        "1Q": "q1", "2Q": "q2", "3Q": "q3", "4Q": "q4",
        "OT1": "ot1", "OT2": "ot2", "OT3": "ot3", "OT4": "ot4", "OT5": "ot5",
        "F": "team_points",
        "MIN": "team_min",
        "FG": "fgm", "FGA": "fga",
        "3P": "fg3m", "3PA": "fg3a",
        "FT": "ftm", "FTA": "fta",
        "OR": "oreb", "DR": "dreb", "TOT": "reb",
        "A": "ast", "PF": "pf", "ST": "stl",
        "TO": "tov", "TO TO": "tov_total", "BL": "blk", "PTS": "pts",
        "POSS": "poss", "PACE": "pace", "OEFF": "oeff", "DEFF": "deff",
        "TEAM REST DAYS": "team_rest_days_raw",
        "CREW CHIEF": "crew_chief",
        "REFEREE & UMPIRE": "referee_umpire",
        "OPENING ODDS": "opening_odds",
        "OPENING SPREAD": "opening_spread",
        "OPENING TOTAL": "opening_total",
        "LINE MOVEMENT #1": "line_movement_1",
        "LINE MOVEMENT #2": "line_movement_2",
        "LINE MOVEMENT #3": "line_movement_3",
        "CLOSING ODDS": "closing_odds",
        "CLOSING SPREAD": "closing_spread",
        "CLOSING TOTAL": "closing_total",
        "MONEYLINE": "moneyline",
        "HALFTIME": "halftime",
        "BOX SCORE URL": "box_score_url",
        "FULL GAME ODDS URL": "full_game_odds_url",
        **rename_starters,
    })

    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y")
    df["is_home"] = df["venue"] == "H"
    rest_before, rest_after = team_rest_gaps(df["team"], df["date"])
    df["is_back_to_back"] = rest_before == 0
    df["team_rest_days_raw"] = team_rest_days_bucket(rest_before)
    # Either leg of a back-to-back, not just the no-rest second one — lets a
    # "show me both back-to-back games" filter include the game right
    # before it too, not just the game that had zero rest.
    df["in_back_to_back"] = (rest_before == 0) | (rest_after == 0)

    # 'pts' (traditional-stats section) disagrees with 'team_points' (F, the
    # quarter-by-quarter final) on 1 of 2644 rows in the raw file. team_points
    # reconciles with q1+q2+q3+q4(+OT), so it's the authoritative score —
    # drop the redundant, less trustworthy 'pts' column.
    df = df.drop(columns=["pts"])

    # Each row is one team's box score; pair it with the other team's row for
    # the same game to get opponent identity/score and derive win/margin/total.
    opponent = df[["game_id", "team", "team_points"]].rename(
        columns={"team": "opponent", "team_points": "opponent_points"}
    )
    df = df.merge(opponent, on="game_id")
    df = df[df["team"] != df["opponent"]].reset_index(drop=True)

    df["win"] = df["team_points"] > df["opponent_points"]
    df["margin"] = df["team_points"] - df["opponent_points"]
    df["combined_total"] = df["team_points"] + df["opponent_points"]
    df["season_type"] = season_type(df["game_id"])

    # Did this team cover its own (signed) spread? e.g. spread -6.5 (favorite)
    # covers if margin > 6.5; spread +6.5 (underdog) covers if margin > -6.5.
    df["covered_spread_closing"] = (df["margin"] + df["closing_spread"]) > 0
    df["covered_spread_opening"] = (df["margin"] + df["opening_spread"]) > 0

    df = df.sort_values(["team", "date"]).reset_index(drop=True)
    return df


def coerce_object_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Some Excel columns mix numeric-looking and text cells (e.g. odds, halftime
    lines, rest-day codes). Force any leftover 'object' columns to a uniform
    string dtype so parquet writing doesn't choke on mixed int/str values."""
    for col in df.select_dtypes(include=["object", "str"]).columns:
        df[col] = df[col].astype("string")
    return df


def preprocess_teams() -> pd.DataFrame:
    df = pd.read_excel(PLAYER_FILE, sheet_name="TEAMS")
    df.columns = clean_column_names(df.columns)
    df = df.rename(columns={
        "INITIALS": "initials",
        "LONG NAME": "long_name",
        "SHORT NAME": "short_name",
        "CONFERENCE": "conference",
        "DIVISION": "division",
    })
    return df


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)

    player_bs = coerce_object_columns(preprocess_player_boxscore())
    player_dnp = coerce_object_columns(preprocess_player_dnp())
    team_bs = coerce_object_columns(preprocess_team_boxscore())
    teams = coerce_object_columns(preprocess_teams())

    player_bs.to_parquet(PROCESSED / "player_boxscore.parquet", index=False)
    player_dnp.to_parquet(PROCESSED / "player_dnp.parquet", index=False)
    team_bs.to_parquet(PROCESSED / "team_boxscore.parquet", index=False)
    teams.to_parquet(PROCESSED / "teams.parquet", index=False)

    print(f"player_boxscore: {player_bs.shape}")
    print(f"player_dnp:      {player_dnp.shape}")
    print(f"team_boxscore:   {team_bs.shape}")
    print(f"teams:           {teams.shape}")


if __name__ == "__main__":
    main()

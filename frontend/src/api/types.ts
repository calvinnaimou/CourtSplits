// Mirrors api/schemas.py and the shapes returned by engine/query.py +
// engine/game_detail.py. Keep these in sync by hand for now — if the
// backend response shape changes, update here too.

export type Direction = "over" | "under" | "equals";
export type HomeAway = "home" | "away" | null;
export type Venue = "H" | "R" | "N" | null;
export type SeasonType = "regular" | "playoffs" | "both";

export interface Condition {
  metric?: string | null;
  periods?: string[] | null;
  threshold: number | boolean;
  direction?: Direction;
  inclusive?: boolean; // over -> >= (default) vs >, under -> <= (default) vs <
}

export interface PlayerQueryRequest {
  // Omit to search across every player (e.g. filter by team/position/date
  // range/stat thresholds only). At least one condition is still required.
  player_name?: string | null;
  conditions: Condition[];
  last_n_games?: number | null;
  home_away?: HomeAway;
  venue?: Venue;
  opponent?: string | null;
  team?: string | null;
  position?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  min_minutes?: number | null;
  starter?: boolean | null;
  days_rest_bucket?: string | null;
  current_team_only?: boolean;
  season_type?: SeasonType;
  page?: number;
  page_size?: number;
}

export interface PlayerSeasonRequest {
  player_name: string;
  season_type?: SeasonType;
}

export interface TeamQueryRequest {
  // Omit to browse across every team — but if team_name is omitted, at
  // least one other filter must be given.
  team_name?: string | null;
  // A purely categorical search (no stat threshold) is valid on its own.
  conditions?: Condition[];
  last_n_games?: number | null;
  home_away?: HomeAway;
  opponent?: string | null;
  back_to_back?: boolean | null;
  team_rest_days?: string | null; // "1" | "2" | "3+" | "B2B"
  season_type?: SeasonType;
  line_filters?: Condition[] | null;
  page?: number;
  page_size?: number;
}

export interface ConditionSummary {
  average: number | null;
  median: number | null;
  std_dev: number | null;
  minimum: number | null;
  maximum: number | null;
}

// A team's/player's full box-score row — many fields, deliberately loose
// (see api/main.py list_team_metrics / list_player_metrics for real names).
export type StatRow = Record<string, string | number | boolean | null>;

export interface DnpEntry {
  player_name: string;
  status: string;
  reason: string;
}

export interface GameDetail {
  game_id: number;
  date: string;
  teams: Record<
    string,
    {
      team_stats: StatRow;
      players: StatRow[];
      dnp: DnpEntry[];
    }
  >;
}

// The full box-score line attached to every row of a player or team search,
// regardless of which columns were used as filter conditions — keys vary by
// engine (see statFilters.ts / teamStatFilters.ts for the real metric names).
export type RowStats = Record<string, number | null>;

export interface GameResult {
  game_id: number;
  date: string;
  opponent: string;
  venue: string;
  season_type: string;
  values: Record<string, number>;
  minutes?: number; // player queries only
  // present when stat_columns/identity_cols were attached (player queries,
  // player season, team queries) — the display columns shown alongside the
  // stat line.
  player_name?: string;
  position?: string | null;
  team?: string;
  starter?: boolean | null;
  days_rest_bucket?: string | null;
  win?: boolean | null; // team queries only
  is_back_to_back?: boolean | null; // team queries only
  team_rest_days?: string | null; // team queries only
  stats?: RowStats;
}

export interface QueryResult {
  sample_size: number;
  hits: number;
  occurrence_rate_pct: number | null;
  average_minutes?: number | null; // player queries only
  conditions: Record<string, ConditionSummary>;
  // games is paginated -- hits/sample_size/conditions describe the full
  // matching pool regardless of page.
  page: number;
  page_size: number;
  total_pages: number;
  games: GameResult[];
}

export interface PlayerSeasonResult {
  player_name: string;
  season_type: SeasonType;
  games_played: number;
  averages: RowStats;
  games: GameResult[];
}

export interface TeamInfo {
  initials: string;
  long_name: string;
  short_name: string;
  conference: string;
  division: string;
}

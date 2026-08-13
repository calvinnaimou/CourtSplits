// Display order + labels for every stat metric shown throughout the app —
// search filters, results table, game-detail modal, season averages.
// `hint` is shown as a hover tooltip so abbreviations are self-explanatory.
export const STAT_FILTERS: { label: string; metric: string; hint: string }[] = [
  { label: "PTS", metric: "pts", hint: "Points" },
  { label: "ORBS", metric: "oreb", hint: "Offensive Rebounds" },
  { label: "DRBS", metric: "dreb", hint: "Defensive Rebounds" },
  { label: "TRBS", metric: "reb", hint: "Total Rebounds (Offensive + Defensive)" },
  { label: "AST", metric: "ast", hint: "Assists" },
  { label: "PRA", metric: "pra", hint: "Points + Rebounds + Assists" },
  { label: "PR", metric: "pts_reb", hint: "Points + Rebounds" },
  { label: "AR", metric: "reb_ast", hint: "Assists + Rebounds" },
  { label: "FGM", metric: "fgm", hint: "Field Goals Made" },
  { label: "FGA", metric: "fga", hint: "Field Goals Attempted" },
  { label: "3PM", metric: "fg3m", hint: "3-Point Field Goals Made" },
  { label: "3PA", metric: "fg3a", hint: "3-Point Field Goals Attempted" },
  { label: "FTM", metric: "ftm", hint: "Free Throws Made" },
  { label: "FTA", metric: "fta", hint: "Free Throws Attempted" },
  { label: "STL", metric: "stl", hint: "Steals" },
  { label: "BLK", metric: "blk", hint: "Blocks" },
  { label: "TO", metric: "tov", hint: "Turnovers" },
  { label: "PERFOUL", metric: "pf", hint: "Personal Fouls" },
  { label: "MIN", metric: "min", hint: "Minutes Played" },
];

// USAGE RATE (%) and DAYS REST, styled separately in the design but
// filtered the same way as any other stat.
export const RATE_FILTERS: { label: string; metric: string; hint: string }[] = [
  { label: "USAGE RATE (%)", metric: "usage_rate", hint: "Share of the team's plays used by this player while on the court" },
  { label: "REST DAYS", metric: "days_rest_raw", hint: "Days of rest since the player's previous game" },
];

// metric -> label, for anywhere that needs a one-off lookup (e.g. the game
// detail modal) instead of iterating the ordered lists above.
export const STAT_LABELS: Record<string, string> = Object.fromEntries(
  [...STAT_FILTERS, ...RATE_FILTERS].map((f) => [f.metric, f.label]),
);

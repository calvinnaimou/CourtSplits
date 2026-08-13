// Display order + labels for team stat metrics. Points-related values
// (final + quarter/OT breakdown) are grouped together up front, then
// shooting/rebounding/counting stats, then POSS/PACE/OEFF/DEFF. team_min
// is the one metric left out entirely -- the results table shows overtime
// via a dedicated Overtime filter instead (see TeamSearchPage.tsx), so a
// raw minutes-played threshold isn't useful. TOT PTS/OPP PTS/TOTAL stay
// filterable here even though the results table also shows a combined
// Score/Total column for them (TeamResultsTable.tsx excludes those three
// from the generic column loop to avoid showing the same number twice).
// OT3-5 are left out entirely since they never occurred this season (see
// engine/query.py's TEAM_ROW_STAT_COLUMNS).
// `hint` is shown as a hover tooltip so abbreviations are self-explanatory;
// it's optional, so a metric can skip it and just show no tooltip at all.
export const TEAM_STAT_FILTERS: { label: string; metric: string; hint?: string }[] = [
  { label: "TOT PTS", metric: "team_points", hint: "Total Points (this team's final score)" },
  { label: "1Q PTS", metric: "q1", hint: "This team's points scored in the 1st Quarter" },
  { label: "2Q PTS", metric: "q2", hint: "This team's points scored in the 2nd Quarter" },
  { label: "3Q PTS", metric: "q3", hint: "This team's points scored in the 3rd Quarter" },
  { label: "4Q PTS", metric: "q4", hint: "This team's points scored in the 4th Quarter" },
  { label: "OT1 PTS", metric: "ot1", hint: "This team's points scored in Overtime 1" },
  { label: "OT2 PTS", metric: "ot2", hint: "This team's points scored in Overtime 2" },
  { label: "OPP PTS", metric: "opponent_points", hint: "Opponent's Total Points" },
  { label: "MARGIN", metric: "margin", hint: "Difference in points between the two teams" },
  { label: "TOTAL", metric: "combined_total", hint: "Game Total (Team Points + Opponent Points)" },
  { label: "FGM", metric: "fgm", hint: "Field Goals Made" },
  { label: "FGA", metric: "fga", hint: "Field Goals Attempted" },
  { label: "3PM", metric: "fg3m", hint: "3-Point Field Goals Made" },
  { label: "3PA", metric: "fg3a", hint: "3-Point Field Goals Attempted" },
  { label: "FTM", metric: "ftm", hint: "Free Throws Made" },
  { label: "FTA", metric: "fta", hint: "Free Throws Attempted" },
  { label: "ORBS", metric: "oreb", hint: "Offensive Rebounds" },
  { label: "DRBS", metric: "dreb", hint: "Defensive Rebounds" },
  { label: "TRBS", metric: "reb", hint: "Total Rebounds (Offensive + Defensive)" },
  { label: "AST", metric: "ast", hint: "Assists" },
  { label: "PERFOUL", metric: "pf", hint: "Personal Fouls" },
  { label: "STL", metric: "stl", hint: "Steals" },
  { label: "TO", metric: "tov", hint: "Turnovers tied to a specific play" },
  { label: "TO TOTAL", metric: "tov_total", hint: "All team turnovers, including ones not tied to a specific play (e.g. shot-clock/backcourt violations)" },
  { label: "BLK", metric: "blk", hint: "Blocks" },
  { label: "POSS", metric: "poss", hint: "Possessions" },
  { label: "PACE", metric: "pace", hint: "Pace (possessions per 48 minutes)" },
  { label: "OEFF", metric: "oeff", hint: "Offensive Efficiency (points scored per 100 possessions)" },
  { label: "DEFF", metric: "deff", hint: "Defensive Efficiency (points allowed per 100 possessions)" },
];

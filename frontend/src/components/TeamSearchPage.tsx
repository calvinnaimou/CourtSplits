import { useEffect, useMemo, useState } from "react";
import { listTeamMetrics, listTeamPeriods, listTeamRestDays, listTeams, queryTeam } from "../api/client";
import type { Condition, QueryResult, SeasonType, TeamInfo } from "../api/types";
import { TEAM_STAT_FILTERS } from "../teamStatFilters";
import Pagination from "./Pagination";
import TeamResultsTable from "./TeamResultsTable";

interface Props {
  onSelectGame: (gameId: number) => void;
}

type FilterState = Record<string, { direction: "over" | "under"; value: string }>;

export default function TeamSearchPage({ onSelectGame }: Props) {
  const [teams, setTeams] = useState<TeamInfo[]>([]);
  const [periods, setPeriods] = useState<string[]>([]);
  const [restDayOptions, setRestDayOptions] = useState<string[]>([]);
  // Guards against offering a filter input for any metric the backend
  // wouldn't actually accept (e.g. a stat column that never occurred this
  // season) — only relevant if TEAM_STAT_FILTERS ever includes one again.
  const [validMetrics, setValidMetrics] = useState<Set<string>>(new Set());

  const [teamName, setTeamNameRaw] = useState("");
  const [opponent, setOpponent] = useState("");
  const [homeAway, setHomeAway] = useState("");
  const [teamRestDays, setTeamRestDays] = useState("");
  // Only meaningful (and only shown) when Rest Days = B2B. is_back_to_back
  // only tags the no-rest second game of a back-to-back, so a plain "Rest
  // Days = B2B" search never shows the game right before it -- check this
  // to pull in both games instead of just the one with zero rest.
  const [includeB2BFrontLeg, setIncludeB2BFrontLeg] = useState(false);

  // Switching away from B2B makes the checkbox disappear -- reset it so a
  // stale "include both" choice doesn't silently reapply if the user picks
  // B2B again later.
  useEffect(() => {
    if (teamRestDays !== "B2B") setIncludeB2BFrontLeg(false);
  }, [teamRestDays]);
  // Derived from team_min, not a raw column — regulation is 240 team-minutes
  // (5 players x 48 min); each 5-min overtime period adds 25 (5 players x 5
  // min). No game went past 2 OT this season, so 265/290 cover every case.
  const [overtimeFilter, setOvertimeFilter] = useState<"" | "none" | "ot1" | "ot2" | "any">("");
  const [win, setWin] = useState("");
  const [seasonType, setSeasonType] = useState<SeasonType>("both");
  const [lastNGames, setLastNGames] = useState("");
  const [inclusive, setInclusive] = useState(true);
  const [statFilters, setStatFilters] = useState<FilterState>({});
  // Only meaningful (and only shown) when a team is picked — "favored" means
  // this team's own opening_spread is negative, "underdog" means positive.
  const [favoriteFilter, setFavoriteFilter] = useState<"" | "favored" | "underdog">("");
  const [selectedPeriods, setSelectedPeriods] = useState<Record<string, boolean>>({});
  const [periodDirection, setPeriodDirection] = useState<"over" | "under">("over");
  const [periodValue, setPeriodValue] = useState("");
  const anyPeriodSelected = Object.values(selectedPeriods).some(Boolean);

  // No periods picked -> the combined-total value is meaningless; clear it
  // so it can't silently reactivate with a stale threshold if a period is
  // checked again later.
  useEffect(() => {
    if (!anyPeriodSelected) setPeriodValue("");
  }, [anyPeriodSelected]);

  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listTeams().then(setTeams).catch(() => {});
    listTeamPeriods().then(setPeriods).catch(() => {});
    listTeamRestDays().then(setRestDayOptions).catch(() => {});
    listTeamMetrics().then((m) => setValidMetrics(new Set(m))).catch(() => {});
  }, []);

  function setStatValue(metric: string, value: string) {
    setStatFilters((prev) => ({ ...prev, [metric]: { direction: prev[metric]?.direction ?? "over", value } }));
  }

  function setStatDirection(metric: string, direction: "over" | "under") {
    setStatFilters((prev) => ({ ...prev, [metric]: { direction, value: prev[metric]?.value ?? "" } }));
  }

  // Team unpicked -> the favorite/underdog filter no longer applies or shows.
  function setTeamName(value: string) {
    setTeamNameRaw(value);
    if (!value) setFavoriteFilter("");
  }

  const activeConditions: Condition[] = useMemo(() => {
    const conds: Condition[] = TEAM_STAT_FILTERS.filter((f) => statFilters[f.metric]?.value.trim()).map((f) => ({
      metric: f.metric,
      threshold: Number(statFilters[f.metric].value),
      direction: statFilters[f.metric].direction,
      inclusive,
    }));
    if (win !== "") {
      conds.push({ metric: "win", direction: "equals", threshold: win === "true" });
    }
    const picked = Object.keys(selectedPeriods).filter((p) => selectedPeriods[p]);
    if (picked.length > 0 && periodValue.trim() !== "") {
      conds.push({ periods: picked, direction: periodDirection, threshold: Number(periodValue), inclusive });
    }
    return conds;
  }, [statFilters, inclusive, win, selectedPeriods, periodDirection, periodValue]);

  const activeLineFilters: Condition[] = useMemo(() => {
    const filters: Condition[] = [];
    // Only applies with a team pinned — opening_spread is signed from that
    // team's own perspective (negative = favored to win, positive = favored
    // to lose), and a pick'em (spread of exactly 0) matches neither option.
    if (teamName && favoriteFilter !== "") {
      filters.push({
        metric: "opening_spread",
        direction: favoriteFilter === "favored" ? "under" : "over",
        threshold: 0,
        inclusive: false,
      });
    }
    if (overtimeFilter === "none") {
      filters.push({ metric: "team_min", direction: "equals", threshold: 240 });
    } else if (overtimeFilter === "ot1") {
      filters.push({ metric: "team_min", direction: "equals", threshold: 265 });
    } else if (overtimeFilter === "ot2") {
      filters.push({ metric: "team_min", direction: "equals", threshold: 290 });
    } else if (overtimeFilter === "any") {
      filters.push({ metric: "team_min", direction: "over", threshold: 240, inclusive: false });
    }
    // "B2B" alone (via team_rest_days below) only matches the no-rest second
    // game. This swaps that out for in_back_to_back, which covers both legs.
    if (teamRestDays === "B2B" && includeB2BFrontLeg) {
      filters.push({ metric: "in_back_to_back", direction: "equals", threshold: true });
    }
    return filters;
  }, [teamName, favoriteFilter, overtimeFilter, teamRestDays, includeB2BFrontLeg]);

  // A team alone is a valid search on its own; if no team is picked, at
  // least one other filter is required (enforced again server-side).
  const hasAnyFilter =
    !!teamName ||
    !!opponent ||
    !!homeAway ||
    !!teamRestDays ||
    seasonType !== "both" ||
    !!lastNGames ||
    activeConditions.length > 0 ||
    activeLineFilters.length > 0;

  async function handleSearch(page = 1) {
    setLoading(true);
    setError(null);
    try {
      const res = await queryTeam({
        team_name: teamName || undefined,
        conditions: activeConditions,
        last_n_games: lastNGames ? Number(lastNGames) : undefined,
        home_away: (homeAway || undefined) as "home" | "away" | undefined,
        opponent: opponent || undefined,
        // The in_back_to_back line_filter above already covers this case
        // (and more precisely), so don't also apply the plain B2B-only match.
        team_rest_days: teamRestDays === "B2B" && includeB2BFrontLeg ? undefined : teamRestDays || undefined,
        season_type: seasonType,
        line_filters: activeLineFilters.length > 0 ? activeLineFilters : undefined,
        page,
      });
      setResult(res);
    } catch (err) {
      setError(String(err));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <h1>Team</h1>
      <p className="hint">Everything optional, but at least one filter is required if no team is picked.</p>

      <div className="filters">
        <div className="field">
          <label htmlFor="team-name">Team</label>
          <select id="team-name" value={teamName} onChange={(e) => setTeamName(e.target.value)}>
            <option value="">Any team</option>
            {teams.map((t) => (
              <option key={t.short_name} value={t.short_name}>
                {t.short_name}
              </option>
            ))}
          </select>
        </div>

        {teamName && (
          <div className="field">
            <label htmlFor="team-favorite">Vegas Line</label>
            <select
              id="team-favorite"
              value={favoriteFilter}
              onChange={(e) => setFavoriteFilter(e.target.value as "" | "favored" | "underdog")}
            >
              <option value="">Any</option>
              <option value="favored">Favored to win</option>
              <option value="underdog">Favored to lose</option>
            </select>
          </div>
        )}

        <div className="field">
          <label htmlFor="team-opponent">Opponent</label>
          <select id="team-opponent" value={opponent} onChange={(e) => setOpponent(e.target.value)}>
            <option value="">Any</option>
            {teams.map((t) => (
              <option key={t.short_name} value={t.short_name}>
                {t.short_name}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="team-home-away">Home/Away</label>
          <select id="team-home-away" value={homeAway} onChange={(e) => setHomeAway(e.target.value)}>
            <option value="">Any</option>
            <option value="home">Home</option>
            <option value="away">Away</option>
          </select>
        </div>

        <div className="field">
          <label
            htmlFor="team-rest-days"
            className="tooltip"
            data-tooltip="1 / 2 / 3+ = days since the team's last game. B2B = back-to-back (0 days rest)."
          >
            Rest Days
          </label>
          <select id="team-rest-days" value={teamRestDays} onChange={(e) => setTeamRestDays(e.target.value)}>
            <option value="">Any</option>
            {restDayOptions.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          {teamRestDays === "B2B" && (
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, textTransform: "none" }}>
              <input
                type="checkbox"
                checked={includeB2BFrontLeg}
                onChange={(e) => setIncludeB2BFrontLeg(e.target.checked)}
              />
              Also show the game right before it
            </label>
          )}
        </div>

        <div className="field">
          <label htmlFor="team-overtime">Overtime</label>
          <select
            id="team-overtime"
            value={overtimeFilter}
            onChange={(e) => setOvertimeFilter(e.target.value as "" | "none" | "ot1" | "ot2" | "any")}
          >
            <option value="">Any</option>
            <option value="none">No OT</option>
            <option value="any">Any OT</option>
            <option value="ot1">OT1 (1 overtime)</option>
            <option value="ot2">OT2 (2 overtimes)</option>
          </select>
        </div>

        <div className="field">
          <label htmlFor="team-win">Result</label>
          <select id="team-win" value={win} onChange={(e) => setWin(e.target.value)}>
            <option value="">Any</option>
            <option value="true">Win</option>
            <option value="false">Loss</option>
          </select>
        </div>

        <div className="field">
          <label htmlFor="team-season-type">Season type</label>
          <select id="team-season-type" value={seasonType} onChange={(e) => setSeasonType(e.target.value as SeasonType)}>
            <option value="both">Both</option>
            <option value="regular">Regular</option>
            <option value="playoffs">Playoffs</option>
          </select>
        </div>

        <div className="field">
          <label htmlFor="team-last-n">Last N games</label>
          <input id="team-last-n" type="number" min="1" value={lastNGames} onChange={(e) => setLastNGames(e.target.value)} />
        </div>
      </div>

      <div className="stat-bar">
        <div className="stat-grid">
          {TEAM_STAT_FILTERS.map((f) => {
            const state = statFilters[f.metric] ?? { direction: "over" as const, value: "" };
            // Before the /teams/metrics fetch resolves, assume every filter
            // is usable rather than flashing them all as disabled.
            const isFilterable = validMetrics.size === 0 || validMetrics.has(f.metric);
            return (
              <div className="stat-cell" key={f.metric}>
                <div className={f.hint ? "stat-label tooltip" : "stat-label"} data-tooltip={f.hint}>{f.label}</div>
                {isFilterable ? (
                  <div className="stat-controls">
                    <select value={state.direction} onChange={(e) => setStatDirection(f.metric, e.target.value as "over" | "under")}>
                      <option value="over">Over</option>
                      <option value="under">Under</option>
                    </select>
                    <input type="number" step="0.5" placeholder="-" value={state.value} onChange={(e) => setStatValue(f.metric, e.target.value)} />
                  </div>
                ) : (
                  <div className="stat-controls tooltip" data-tooltip="Didn't occur this season, so it can't be filtered — still shown in results.">
                    <input type="text" value="N/A" disabled />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <p className="hint" style={{ marginTop: 16, marginBottom: 4 }}>
          Combine two or more periods into a single summed threshold (e.g. Q1+Q4 over 58) —
          for a single period on its own, use its own cell above instead (e.g. "1Q PTS").
        </p>
        <div className="stat-grid">
          {periods.map((p) => (
            <label key={p} className="inclusive-toggle" style={{ marginTop: 0 }}>
              <input
                type="checkbox"
                checked={!!selectedPeriods[p]}
                onChange={(e) => setSelectedPeriods((prev) => ({ ...prev, [p]: e.target.checked }))}
              />
              {p.toUpperCase()}
            </label>
          ))}
        </div>
        {periods.length > 0 && (
          <div className="stat-cell" style={{ maxWidth: 200, marginTop: 8 }}>
            <div className="stat-label">COMBINED PERIODS TOTAL</div>
            <div
              className={anyPeriodSelected ? "stat-controls" : "stat-controls tooltip"}
              data-tooltip={anyPeriodSelected ? undefined : "Check at least one period above first"}
            >
              <select
                value={periodDirection}
                onChange={(e) => setPeriodDirection(e.target.value as "over" | "under")}
                disabled={!anyPeriodSelected}
              >
                <option value="over">Over</option>
                <option value="under">Under</option>
              </select>
              <input
                type="number"
                step="0.5"
                placeholder="-"
                value={periodValue}
                onChange={(e) => setPeriodValue(e.target.value)}
                disabled={!anyPeriodSelected}
              />
            </div>
          </div>
        )}

        <label className="inclusive-toggle">
          <input type="checkbox" checked={inclusive} onChange={(e) => setInclusive(e.target.checked)} />
          Inclusive thresholds (over = &ge;, under = &le;)
        </label>
      </div>

      <div className="actions">
        <button className="search-btn" onClick={() => handleSearch(1)} disabled={loading || !hasAnyFilter}>
          {loading ? "Searching..." : "Search"}
        </button>
        {!hasAnyFilter && <span className="hint">Pick a team or set at least one other filter</span>}
      </div>

      {error && <p className="error-banner">{error}</p>}

      {result && (
        <>
          <p className="summary">
            {teamName ? (
              <>
                {result.hits} of {result.sample_size} games matched
                {result.occurrence_rate_pct !== null && ` (${result.occurrence_rate_pct}%)`}
              </>
            ) : (
              // No team pinned -> the pool has both teams' rows per game, so
              // a shared stat (e.g. closing total) can hit on both sides of
              // the same game. "X of Y (Z%)" would misleadingly imply a rate
              // against a games count; report the raw occurrence count instead.
              <>{result.hits} occurrences matched</>
            )}
          </p>
          <TeamResultsTable games={result.games} onSelectGame={onSelectGame} />
          <Pagination page={result.page} totalPages={result.total_pages} onChange={handleSearch} />
        </>
      )}
    </div>
  );
}

import { useEffect, useMemo, useState } from "react";
import { listPlayers, listPositions, listTeams, queryPlayer } from "../api/client";
import type { Condition, QueryResult, SeasonType, TeamInfo } from "../api/types";
import { RATE_FILTERS, STAT_FILTERS } from "../statFilters";
import Pagination from "./Pagination";
import ResultsTable from "./ResultsTable";

interface Props {
  onSelectPlayer: (playerName: string) => void;
  onSelectGame: (gameId: number) => void;
}

type StatFilterState = Record<string, { direction: "over" | "under"; value: string }>;

const ALL_STAT_FIELDS = [...STAT_FILTERS, ...RATE_FILTERS];

// Guard-to-center, not the alphabetical order the backend returns them in.
const POSITION_ORDER = ["PG", "SG", "SF", "PF", "C"];
function sortPositions(positions: string[]): string[] {
  return [...positions].sort((a, b) => POSITION_ORDER.indexOf(a) - POSITION_ORDER.indexOf(b));
}

export default function PlayerSearchPage({ onSelectPlayer, onSelectGame }: Props) {
  const [players, setPlayers] = useState<string[]>([]);
  const [teams, setTeams] = useState<TeamInfo[]>([]);
  const [positions, setPositions] = useState<string[]>([]);

  const [playerName, setPlayerName] = useState("");
  const [position, setPosition] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [team, setTeam] = useState("");
  const [opponent, setOpponent] = useState("");
  const [venue, setVenue] = useState("");
  const [starter, setStarter] = useState("");
  const [seasonType, setSeasonType] = useState<SeasonType>("both");
  const [inclusive, setInclusive] = useState(true);
  const [statFilters, setStatFilters] = useState<StatFilterState>({});

  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listPlayers().then(setPlayers).catch(() => {});
    listTeams().then(setTeams).catch(() => {});
    listPositions().then((p) => setPositions(sortPositions(p))).catch(() => {});
  }, []);

  const activeConditions: Condition[] = useMemo(() => {
    return ALL_STAT_FIELDS.filter((f) => statFilters[f.metric]?.value.trim() !== "" && statFilters[f.metric]?.value !== undefined)
      .map((f) => ({
        metric: f.metric,
        threshold: Number(statFilters[f.metric].value),
        direction: statFilters[f.metric].direction,
        inclusive,
      }));
  }, [statFilters, inclusive]);

  function setStatValue(metric: string, value: string) {
    setStatFilters((prev) => ({
      ...prev,
      [metric]: { direction: prev[metric]?.direction ?? "over", value },
    }));
  }

  function setStatDirection(metric: string, direction: "over" | "under") {
    setStatFilters((prev) => ({
      ...prev,
      [metric]: { direction, value: prev[metric]?.value ?? "" },
    }));
  }

  async function handleSearch(page = 1) {
    setLoading(true);
    setError(null);
    try {
      const res = await queryPlayer({
        player_name: playerName || undefined,
        position: position || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        team: team || undefined,
        opponent: opponent || undefined,
        venue: (venue || undefined) as "H" | "R" | "N" | undefined,
        starter: starter === "" ? undefined : starter === "true",
        season_type: seasonType,
        conditions: activeConditions,
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
      <h1>Player</h1>
      <p className="hint">Everything optional. Fill in a filter to require it; leave blank to match anything.</p>

      <div className="filters">
        <div className="field">
          <label htmlFor="player">Player name</label>
          <select id="player" value={playerName} onChange={(e) => setPlayerName(e.target.value)}>
            <option value="">Any player</option>
            {players.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="position">Position</label>
          <select id="position" value={position} onChange={(e) => setPosition(e.target.value)}>
            <option value="">Any</option>
            {positions.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="start-date" className="tooltip" data-tooltip="Defaults to the beginning of the 2025-26 season if left blank">
            Start date
          </label>
          <input id="start-date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </div>

        <div className="field">
          <label htmlFor="end-date" className="tooltip" data-tooltip="Defaults to the most recent game in the data if left blank">
            End date
          </label>
          <input id="end-date" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>

        <div className="field">
          <label htmlFor="team">Team playing for</label>
          <select id="team" value={team} onChange={(e) => setTeam(e.target.value)}>
            <option value="">Any</option>
            {teams.map((t) => (
              <option key={t.short_name} value={t.short_name}>
                {t.short_name}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="opponent">Team playing against</label>
          <select id="opponent" value={opponent} onChange={(e) => setOpponent(e.target.value)}>
            <option value="">Any</option>
            {teams.map((t) => (
              <option key={t.short_name} value={t.short_name}>
                {t.short_name}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="venue">Venue</label>
          <select id="venue" value={venue} onChange={(e) => setVenue(e.target.value)}>
            <option value="">Any</option>
            <option value="H">Home</option>
            <option value="R">Road</option>
            <option value="N">Neutral</option>
          </select>
        </div>

        <div className="field">
          <label htmlFor="starter">Starter</label>
          <select id="starter" value={starter} onChange={(e) => setStarter(e.target.value)}>
            <option value="">Any</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </div>

        <div className="field">
          <label htmlFor="season-type">Season type</label>
          <select id="season-type" value={seasonType} onChange={(e) => setSeasonType(e.target.value as SeasonType)}>
            <option value="both">Both</option>
            <option value="regular">Regular</option>
            <option value="playoffs">Playoffs</option>
          </select>
        </div>
      </div>

      <div className="stat-bar">
        <div className="stat-grid">
          {ALL_STAT_FIELDS.map((f) => {
            const state = statFilters[f.metric] ?? { direction: "over" as const, value: "" };
            return (
              <div className="stat-cell" key={f.metric}>
                <div className="stat-label tooltip" data-tooltip={f.hint}>{f.label}</div>
                <div className="stat-controls">
                  <select value={state.direction} onChange={(e) => setStatDirection(f.metric, e.target.value as "over" | "under")}>
                    <option value="over">Over</option>
                    <option value="under">Under</option>
                  </select>
                  <input
                    type="number"
                    step="0.5"
                    placeholder="-"
                    value={state.value}
                    onChange={(e) => setStatValue(f.metric, e.target.value)}
                  />
                </div>
              </div>
            );
          })}
        </div>
        <label className="inclusive-toggle">
          <input type="checkbox" checked={inclusive} onChange={(e) => setInclusive(e.target.checked)} />
          Inclusive thresholds (over = &ge;, under = &le;)
        </label>
      </div>

      <div className="actions">
        <button className="search-btn" onClick={() => handleSearch(1)} disabled={loading || activeConditions.length === 0}>
          {loading ? "Searching..." : "Search"}
        </button>
        {activeConditions.length === 0 && <span className="hint">Set at least one stat filter to search</span>}
      </div>

      {error && <p className="error-banner">{error}</p>}

      {result && (
        <>
          <p className="summary">
            {playerName ? (
              <>
                {result.hits} of {result.sample_size} games matched
                {result.occurrence_rate_pct !== null && ` (${result.occurrence_rate_pct}%)`}
              </>
            ) : (
              // No player pinned -> each row is still a distinct player-game
              // (no duplication risk like team rows), but the rate no longer
              // means "how often does one player do this" -- just report
              // the raw occurrence count for clarity.
              <>{result.hits} occurrences matched</>
            )}
          </p>
          <ResultsTable games={result.games} onSelectPlayer={onSelectPlayer} onSelectGame={onSelectGame} />
          <Pagination page={result.page} totalPages={result.total_pages} onChange={handleSearch} />
        </>
      )}
    </div>
  );
}

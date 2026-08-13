import { useEffect, useState } from "react";
import { getGameDetail } from "../api/client";
import type { GameDetail, StatRow } from "../api/types";
import { STAT_FILTERS } from "../statFilters";
import { TEAM_STAT_FILTERS } from "../teamStatFilters";

interface Props {
  gameId: number;
  onClose: () => void;
}

const VENUE_LABELS: Record<string, string> = { H: "Home", R: "Road", N: "Neutral" };

const PLAYER_COLUMNS: { label: string; key: string }[] = [
  { label: "Player", key: "player_name" },
  { label: "Pos", key: "position" },
  { label: "Starter", key: "starter" },
  ...STAT_FILTERS.map((f) => ({ label: f.label, key: f.metric })),
  { label: "Usg%", key: "usage_rate" },
];

function fmt(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "boolean") return value ? "Y" : "N";
  return String(value);
}

// "Over"/"Under"/"Push" against a betting total line. Uses the clean
// combined_total + opening_total/closing_total fields, not the raw
// mixed-format odds strings — those mix spread and total across the two
// team rows and aren't safe to parse here.
function totalResult(combinedTotal: unknown, line: unknown): string | null {
  const total = Number(combinedTotal);
  const n = Number(line);
  if (!Number.isFinite(total) || !Number.isFinite(n)) return null;
  if (total > n) return "Over";
  if (total < n) return "Under";
  return "Push";
}

// Spreads are stored as signed numbers already (favorite negative, dog
// positive), but a bare positive number reads as ambiguous next to the
// other team's "-1.5" -- make the + explicit.
function fmtSpread(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "-";
  return n > 0 ? `+${n}` : String(n);
}

// The raw `halftime` field is either a spread or a total depending on the
// row, and not in a predictable home/away pattern. But a half-total is
// always way bigger than any realistic spread (spreads top out around 20,
// half-totals bottom out around 80), so we just go by magnitude.
function parseLeadingNumber(raw: unknown): number | null {
  if (raw === null || raw === undefined) return null;
  const m = String(raw).trim().match(/-?\d+(\.\d+)?/);
  return m ? Number(m[0]) : null;
}

function halfPoints(stats: StatRow): number | null {
  const q1 = Number(stats.q1);
  const q2 = Number(stats.q2);
  return Number.isFinite(q1) && Number.isFinite(q2) ? q1 + q2 : null;
}

function OddsTable({ teams }: { teams: GameDetail["teams"] }) {
  const entries = Object.entries(teams);
  const shared = entries[0]?.[1]?.team_stats;
  const openingResult = shared ? totalResult(shared.combined_total, shared.opening_total) : null;

  // Figure out which team's halftime field is the total line vs. the
  // spread line, then compute the real half score (q1+q2) for each team
  // and compare it the same way the full-game numbers are compared above.
  const halfLines = entries.map(([name, data]) => ({
    name,
    value: parseLeadingNumber(data.team_stats.halftime),
  }));
  const halfTotalEntry = halfLines.find((h) => h.value !== null && Math.abs(h.value) > 50);
  const halfSpreadEntry = halfLines.find((h) => h.value !== null && Math.abs(h.value) <= 50);
  const halfScores = Object.fromEntries(entries.map(([name, data]) => [name, halfPoints(data.team_stats)]));
  const halfTotalActual = Object.values(halfScores).every((v) => v !== null)
    ? (Object.values(halfScores) as number[]).reduce((a, b) => a + b, 0)
    : null;
  const halfTotalResult =
    halfTotalActual !== null && halfTotalEntry?.value != null ? totalResult(halfTotalActual, halfTotalEntry.value) : null;

  return (
    <>
      {shared && (
        <p className="hint" style={{ marginBottom: 4 }}>
          Total: {fmt(shared.opening_total)} ({fmt(shared.combined_total)} actual
          {openingResult && <span className="stat-good"> — {openingResult}</span>})
        </p>
      )}
      {halfTotalEntry?.value != null && (
        <p className="hint" style={{ marginBottom: 8 }}>
          Half Total: {halfTotalEntry.value} ({fmt(halfTotalActual)} actual
          {halfTotalResult && <span className="stat-good"> — {halfTotalResult}</span>})
        </p>
      )}
      <div className="table-scroll" style={{ marginBottom: 20 }}>
        <table className="results">
          <thead>
            <tr>
              <th>Team</th>
              <th>Opening Spread</th>
              <th>Moneyline</th>
              <th>Half Spread</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([teamName, teamData]) => {
              const s = teamData.team_stats;
              // This team's own half spread: their own line if theirs is
              // the spread entry, otherwise the negation of the other
              // team's spread (spreads are always opposite signs).
              const ownHalfSpread =
                halfSpreadEntry?.name === teamName
                  ? halfSpreadEntry.value
                  : halfSpreadEntry?.value != null
                    ? -halfSpreadEntry.value
                    : null;
              const opponentName = entries.find(([n]) => n !== teamName)?.[0];
              const ownHalf = halfScores[teamName];
              const oppHalf = opponentName ? halfScores[opponentName] : null;
              const coveredHalf =
                ownHalf !== null && oppHalf !== null && ownHalfSpread !== null
                  ? ownHalf - oppHalf + ownHalfSpread > 0
                  : null;
              return (
                <tr key={teamName}>
                  <td>{teamName}</td>
                  <td className={s.covered_spread_opening ? "stat-good" : ""}>{fmtSpread(s.opening_spread)}</td>
                  <td className={s.win ? "stat-good" : ""}>{fmt(s.moneyline)}</td>
                  <td className={coveredHalf ? "stat-good" : ""}>{fmtSpread(ownHalfSpread)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}

// Same row shape the Team search results table's filter grid uses (TOT
// PTS/OPP PTS included), so a player-search user sees exactly what a
// team-search user would've seen for this game.
const TEAM_COLUMNS: { label: string; key: string }[] = [
  { label: "Team", key: "team" },
  { label: "Venue", key: "venue" },
  { label: "Season", key: "season_type" },
  { label: "Win", key: "win" },
  { label: "B2B", key: "is_back_to_back" },
  { label: "Rest Days", key: "team_rest_days_raw" },
  ...TEAM_STAT_FILTERS.map((f) => ({ label: f.label, key: f.metric })),
];

function TeamStatsTable({ teams }: { teams: GameDetail["teams"] }) {
  return (
    <div className="table-scroll" style={{ marginBottom: 20 }}>
      <table className="results">
        <thead>
          <tr>
            {TEAM_COLUMNS.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Object.entries(teams).map(([teamName, teamData]) => (
            <tr key={teamName}>
              {TEAM_COLUMNS.map((c) => (
                <td key={c.key}>{fmt(teamData.team_stats[c.key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PlayerTable({ players }: { players: StatRow[] }) {
  if (players.length === 0) return null;
  return (
    <div className="table-scroll">
      <table className="results">
        <thead>
          <tr>
            {PLAYER_COLUMNS.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {players.map((row, i) => (
            <tr key={i}>
              {PLAYER_COLUMNS.map((c) => (
                <td key={c.key}>{fmt(row[c.key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function GameDetailModal({ gameId, onClose }: Props) {
  const [detail, setDetail] = useState<GameDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDetail(null);
    setError(null);
    getGameDetail(gameId)
      .then(setDetail)
      .catch((err) => setError(String(err)));
  }, [gameId]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close">
          &times;
        </button>
        {error && <p className="error-banner">{error}</p>}
        {!detail && !error && <p>Loading...</p>}
        {detail && (
          <>
            <h2>{detail.date}</h2>
            {Object.values(detail.teams)[0] && (
              <p className="hint">{String(Object.values(detail.teams)[0].team_stats.dataset ?? "")}</p>
            )}
            <h3>Odds Data</h3>
            <OddsTable teams={detail.teams} />
            <h3>Team Stats</h3>
            <TeamStatsTable teams={detail.teams} />
            {Object.entries(detail.teams).map(([teamName, teamData]) => {
              const venue = teamData.team_stats.venue as string | null;
              return (
                <div className="team-block" key={teamName}>
                  <h3>
                    {teamName}
                    {venue && ` (${VENUE_LABELS[venue] ?? venue})`}
                  </h3>
                  <PlayerTable players={teamData.players} />
                  {teamData.dnp.length > 0 && (
                    <div className="dnp-list">
                      Did not play: {teamData.dnp.map((d) => `${d.player_name} (${d.reason})`).join(", ")}
                    </div>
                  )}
                </div>
              );
            })}
          </>
        )}
      </div>
    </div>
  );
}

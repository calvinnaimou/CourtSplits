import type { GameResult } from "../api/types";
import { TEAM_STAT_FILTERS } from "../teamStatFilters";

interface Props {
  games: GameResult[];
  onSelectGame: (gameId: number) => void;
}

function fmt(value: number | string | boolean | null | undefined): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "boolean") return value ? "Y" : "N";
  return String(value);
}

// team_points/opponent_points/combined_total stay filterable in the search
// grid (TEAM_STAT_FILTERS), but here they'd just repeat what the dedicated
// Score ("116-117") and Total columns already show, so skip them in the
// generic stat-column loop.
const HIDDEN_IN_RESULTS = new Set(["team_points", "opponent_points", "combined_total"]);
const REMAINING_STAT_FILTERS = TEAM_STAT_FILTERS.filter((f) => !HIDDEN_IN_RESULTS.has(f.metric));

export default function TeamResultsTable({ games, onSelectGame }: Props) {
  if (games.length === 0) {
    return <p className="hint">No games match these filters.</p>;
  }

  return (
    <div className="table-scroll">
      <table className="results">
        <thead>
          <tr>
            <th>Date</th>
            <th>Team</th>
            <th>Opp</th>
            <th>Score</th>
            <th>Total</th>
            <th>Game</th>
            <th>Venue</th>
            <th>Season</th>
            <th>Win</th>
            <th>B2B</th>
            <th>Rest Days</th>
            {REMAINING_STAT_FILTERS.map((f) => (
              <th key={f.metric}>{f.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {games.map((game) => {
            const teamPts = game.stats?.team_points;
            const oppPts = game.stats?.opponent_points;
            const hasScore = typeof teamPts === "number" && typeof oppPts === "number";
            const teamClass = hasScore ? (teamPts! > oppPts! ? "stat-good" : teamPts! < oppPts! ? "stat-bad" : "") : "";
            const oppClass = hasScore ? (oppPts! > teamPts! ? "stat-good" : oppPts! < teamPts! ? "stat-bad" : "") : "";
            return (
              <tr key={`${game.game_id}-${game.team ?? ""}`}>
                <td>{game.date}</td>
                <td className={teamClass}>{fmt(game.team)}</td>
                <td className={oppClass}>{fmt(game.opponent)}</td>
                <td>{hasScore ? `${teamPts}-${oppPts}` : "-"}</td>
                <td>{fmt(game.stats?.combined_total)}</td>
                <td>
                  <button className="game-link" onClick={() => onSelectGame(game.game_id)}>
                    Game
                  </button>
                </td>
                <td>{fmt(game.venue)}</td>
                <td>{fmt(game.season_type)}</td>
                <td>{fmt(game.win)}</td>
                <td>{fmt(game.is_back_to_back)}</td>
                <td>{fmt(game.team_rest_days)}</td>
                {REMAINING_STAT_FILTERS.map((f) => (
                  <td key={f.metric}>{fmt(game.stats?.[f.metric])}</td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

import type { GameResult } from "../api/types";
import { STAT_FILTERS } from "../statFilters";

interface Props {
  games: GameResult[];
  onSelectPlayer?: (playerName: string) => void;
  onSelectGame: (gameId: number) => void;
  // Hide the Player column when every row is already known to be the same
  // player (e.g. a single player's season page) — their name is shown once
  // as the page title instead of repeating on every row.
  showPlayerColumn?: boolean;
}

function fmt(value: number | string | boolean | null | undefined): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "boolean") return value ? "Y" : "N";
  return String(value);
}

export default function ResultsTable({ games, onSelectPlayer, onSelectGame, showPlayerColumn = true }: Props) {
  if (games.length === 0) {
    return <p className="hint">No games match these filters.</p>;
  }

  return (
    <div className="table-scroll">
      <table className="results">
        <thead>
          <tr>
            <th>Date</th>
            {showPlayerColumn && <th>Player</th>}
            <th>Pos</th>
            <th>Team</th>
            <th>Opp</th>
            <th>Game</th>
            <th>Venue</th>
            <th>Starter</th>
            {STAT_FILTERS.map((f) => (
              <th key={f.metric}>{f.label}</th>
            ))}
            <th>Usg%</th>
            <th>Rest</th>
          </tr>
        </thead>
        <tbody>
          {games.map((game) => (
            <tr key={`${game.game_id}-${game.player_name ?? ""}`}>
              <td>{game.date}</td>
              {showPlayerColumn && (
                <td>
                  {onSelectPlayer && game.player_name ? (
                    <button className="player-link" onClick={() => onSelectPlayer(game.player_name!)}>
                      {game.player_name}
                    </button>
                  ) : (
                    fmt(game.player_name)
                  )}
                </td>
              )}
              <td>{fmt(game.position)}</td>
              <td>{fmt(game.team)}</td>
              <td>{fmt(game.opponent)}</td>
              <td>
                <button className="game-link" onClick={() => onSelectGame(game.game_id)}>
                  Game
                </button>
              </td>
              <td>{fmt(game.venue)}</td>
              <td>{fmt(game.starter)}</td>
              {STAT_FILTERS.map((f) => (
                <td key={f.metric}>{fmt(game.stats?.[f.metric as keyof typeof game.stats])}</td>
              ))}
              <td>{fmt(game.stats?.usage_rate)}</td>
              <td>{fmt(game.days_rest_bucket)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

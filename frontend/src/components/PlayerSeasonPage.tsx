import { useEffect, useState } from "react";
import { getPlayerSeason } from "../api/client";
import type { PlayerSeasonResult, SeasonType } from "../api/types";
import { STAT_FILTERS } from "../statFilters";
import ResultsTable from "./ResultsTable";

interface Props {
  playerName: string;
  onBack: () => void;
  onSelectGame: (gameId: number) => void;
}

const SEASON_OPTIONS: { label: string; value: SeasonType }[] = [
  { label: "Season", value: "regular" },
  { label: "Playoffs", value: "playoffs" },
  { label: "Both", value: "both" },
];

export default function PlayerSeasonPage({ playerName, onBack, onSelectGame }: Props) {
  const [seasonType, setSeasonType] = useState<SeasonType>("regular");
  const [result, setResult] = useState<PlayerSeasonResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setResult(null);
    setError(null);
    getPlayerSeason({ player_name: playerName, season_type: seasonType })
      .then(setResult)
      .catch((err) => setError(String(err)));
  }, [playerName, seasonType]);

  return (
    <div className="page">
      <button className="back-btn" onClick={onBack}>
        &larr; Back to search
      </button>
      <h1>{playerName}</h1>

      <div className="season-toggle">
        {SEASON_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            className={seasonType === opt.value ? "active" : ""}
            onClick={() => setSeasonType(opt.value)}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {error && <p className="error-banner">{error}</p>}
      {!result && !error && <p>Loading...</p>}

      {result && (
        <>
          <p className="summary">{result.games_played} games played</p>
          <div className="averages-bar">
            {STAT_FILTERS.map((f) => (
              <div className="avg-cell" key={f.metric}>
                <div className="avg-label">{f.label}</div>
                <div className="avg-value">
                  {result.averages[f.metric as keyof typeof result.averages] ?? "-"}
                </div>
              </div>
            ))}
          </div>
          <ResultsTable games={result.games} onSelectGame={onSelectGame} showPlayerColumn={false} />
        </>
      )}
    </div>
  );
}

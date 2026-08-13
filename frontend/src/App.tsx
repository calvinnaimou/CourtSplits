import { useState } from "react";
import "./App.css";
import GameDetailModal from "./components/GameDetailModal";
import PlayerSearchPage from "./components/PlayerSearchPage";
import PlayerSeasonPage from "./components/PlayerSeasonPage";
import TeamSearchPage from "./components/TeamSearchPage";

type View =
  | { type: "playerSearch" }
  | { type: "teamSearch" }
  | { type: "playerSeason"; playerName: string };

function App() {
  const [view, setView] = useState<View>({ type: "playerSearch" });
  const [selectedGameId, setSelectedGameId] = useState<number | null>(null);

  const showTabs = view.type === "playerSearch" || view.type === "teamSearch";

  return (
    <>
      <img src="/CourtSplitzLogo.png" alt="courtSplitz" className="app-logo" />
      {showTabs && (
        <div className="season-toggle" style={{ padding: "16px 24px 0" }}>
          <button
            className={view.type === "playerSearch" ? "active" : ""}
            onClick={() => setView({ type: "playerSearch" })}
          >
            Player
          </button>
          <button
            className={view.type === "teamSearch" ? "active" : ""}
            onClick={() => setView({ type: "teamSearch" })}
          >
            Team
          </button>
        </div>
      )}
      {view.type === "playerSearch" && (
        <PlayerSearchPage
          onSelectPlayer={(playerName) => setView({ type: "playerSeason", playerName })}
          onSelectGame={setSelectedGameId}
        />
      )}
      {view.type === "teamSearch" && <TeamSearchPage onSelectGame={setSelectedGameId} />}
      {view.type === "playerSeason" && (
        <PlayerSeasonPage
          playerName={view.playerName}
          onBack={() => setView({ type: "playerSearch" })}
          onSelectGame={setSelectedGameId}
        />
      )}
      {selectedGameId !== null && (
        <GameDetailModal gameId={selectedGameId} onClose={() => setSelectedGameId(null)} />
      )}
    </>
  );
}

export default App;

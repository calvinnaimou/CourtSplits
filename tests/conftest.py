import pandas as pd
import pytest

from engine.data import player_boxscore, player_dnp, team_boxscore, teams


@pytest.fixture(scope="session", autouse=True)
def _no_live_db():
    """Several tests assert exact historical totals (e.g. exactly 1230
    regular-season games) -- if a dev happens to have DATABASE_URL set in
    their shell for unrelated reasons, those would fail confusingly against
    a live-merged dataset instead of the plain historical one they expect."""
    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("DATABASE_URL", raising=False)
        yield


@pytest.fixture(scope="session")
def player_df() -> pd.DataFrame:
    return player_boxscore()


@pytest.fixture(scope="session")
def team_df() -> pd.DataFrame:
    return team_boxscore()


@pytest.fixture(scope="session")
def dnp_df() -> pd.DataFrame:
    return player_dnp()


@pytest.fixture(scope="session")
def teams_df() -> pd.DataFrame:
    return teams()


@pytest.fixture()
def api_client():
    from fastapi.testclient import TestClient

    from api.main import app

    return TestClient(app)

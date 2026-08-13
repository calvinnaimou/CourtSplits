import pandas as pd
import pytest

from engine.data import player_boxscore, player_dnp, team_boxscore, teams


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

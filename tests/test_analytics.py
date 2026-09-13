from engine.analytics import _visitor_hash, log_query


def test_visitor_hash_is_deterministic():
    assert _visitor_hash("1.2.3.4") == _visitor_hash("1.2.3.4")


def test_visitor_hash_differs_by_ip():
    assert _visitor_hash("1.2.3.4") != _visitor_hash("5.6.7.8")


def test_visitor_hash_differs_by_salt(monkeypatch):
    monkeypatch.delenv("VISITOR_HASH_SALT", raising=False)
    unsalted = _visitor_hash("1.2.3.4")
    monkeypatch.setenv("VISITOR_HASH_SALT", "some-secret")
    salted = _visitor_hash("1.2.3.4")
    assert unsalted != salted


def test_log_query_is_a_noop_without_database_url(monkeypatch, api_client):
    # The session-wide _no_live_db fixture already unsets DATABASE_URL, so
    # this just confirms hitting a logged endpoint doesn't error without it.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    res = api_client.post(
        "/players/query",
        json={"conditions": [{"metric": "pts", "threshold": 10, "direction": "over"}]},
    )
    assert res.status_code == 200


def test_log_query_swallows_connection_failures(monkeypatch, api_client):
    # Points at a real-looking but unreachable database -- log_query should
    # catch the failure itself, never bubble up into the API response.
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost:1/does_not_exist")
    res = api_client.post(
        "/players/query",
        json={"conditions": [{"metric": "pts", "threshold": 10, "direction": "over"}]},
    )
    assert res.status_code == 200

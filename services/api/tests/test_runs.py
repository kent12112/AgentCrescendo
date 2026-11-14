import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from crescendo_api.config import get_settings
from crescendo_api.database import get_session
from crescendo_api.main import app
from crescendo_api.models import Base

TOKEN = "test-only-token-with-more-than-32-characters"


@pytest.fixture
def client(monkeypatch):
    # pytest creates this fixture for each test case. monkeypatch restores the
    # environment afterward; clear our settings cache so tests do not reuse it.
    monkeypatch.setenv("DEV_API_TOKEN", TOKEN)
    get_settings.cache_clear()
    # One temporary in-memory SQLite connection is shared with TestClient's
    # request thread. These tests are fast but do not prove PostgreSQL behavior.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def session_override():
        with Session(engine) as session:
            yield session

    # Replace only persistence, leaving real routing, validation, and auth active.
    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as client:
        yield client
    # Normal fixture teardown: avoid leaking overrides/connections into later cases.
    app.dependency_overrides.clear()
    get_settings.cache_clear()
    engine.dispose()


def auth():
    return {"Authorization": f"Bearer {TOKEN}"}


def test_drafts_require_authentication(client):
    assert client.get("/runs").status_code == 401
    assert client.post("/runs", json={"goal": "Research a weekend trip"}).status_code == 401
    assert client.get("/runs", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_draft_is_persisted_and_retrievable(client):
    response = client.post("/runs", headers=auth(), json={"goal": "  Compare beginner cameras under $500  "})
    assert response.status_code == 201
    run = response.json()
    assert run["goal"] == "Compare beginner cameras under $500"
    assert run["status"] == "draft"
    assert client.get(f"/runs/{run['id']}", headers=auth()).json() == run
    assert client.get("/runs", headers=auth()).json() == [run]


@pytest.mark.parametrize("sent, stored", [
    ({}, None),
    ({"constraints": None}, None),
    ({"constraints": "   "}, None),
    ({"constraints": "  no flights  "}, "no flights"),
])
def test_blank_constraints_are_stored_as_absent(client, sent, stored):
    # One meaning, one value: missing, null, and blank all mean "no constraints",
    # so downstream prompt building only ever checks for None.
    response = client.post("/runs", headers=auth(), json={"goal": "Plan a weekend trip", **sent})
    assert response.status_code == 201
    assert response.json()["constraints"] == stored
    assert client.get("/runs", headers=auth()).json()[0]["constraints"] == stored

@pytest.mark.parametrize("patch", [
    {"max_workers": 4}, {"max_workers": True}, {"timeout_seconds": 601},
    {"model_budget_cents": 0}, {"model_budget_cents": 501},
    {"goal": "          "}, {"goal": "x" * 4001}, {"constraints": "x" * 1001}, {"permissions": ["purchase"]},
])
def test_invalid_or_escalated_request_is_rejected(client, patch):
    # Parametrize runs this same behavioral check once per invalid payload.
    # Check both the error and its consequence: no draft should have been saved.
    response = client.post("/runs", headers=auth(), json={"goal": "Plan a weekend trip", **patch})
    assert response.status_code == 422
    assert client.get("/runs", headers=auth()).json() == []


def test_capabilities_do_not_claim_execution(client):
    assert client.get("/capabilities", headers=auth()).json()["execution"] is False
    assert client.get("/runs/00000000-0000-0000-0000-000000000000", headers=auth()).status_code == 404


def test_delete_draft_persists_and_preserves_other_drafts(client):
    first = client.post("/runs", headers=auth(), json={"goal": "Research a weekend trip"}).json()
    second = client.post("/runs", headers=auth(), json={"goal": "Compare beginner cameras"}).json()

    response = client.delete(f"/runs/{first['id']}", headers=auth())

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/runs/{first['id']}", headers=auth()).status_code == 404
    assert client.get("/runs", headers=auth()).json() == [second]
    assert client.delete(f"/runs/{first['id']}", headers=auth()).status_code == 404


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}])
def test_unauthorized_delete_preserves_draft(client, headers):
    run = client.post("/runs", headers=auth(), json={"goal": "Research a weekend trip"}).json()

    assert client.delete(f"/runs/{run['id']}", headers=headers).status_code == 401
    assert client.get(f"/runs/{run['id']}", headers=auth()).json() == run


def test_delete_rejects_missing_and_malformed_ids(client):
    assert client.delete("/runs/00000000-0000-0000-0000-000000000000", headers=auth()).status_code == 404
    assert client.delete("/runs/not-a-uuid", headers=auth()).status_code == 422


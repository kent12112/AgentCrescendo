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


@pytest.mark.parametrize("patch", [
    {"max_workers": 4}, {"max_workers": True}, {"timeout_seconds": 601},
    {"model_budget_cents": 0}, {"model_budget_cents": 501},
    {"goal": "          "}, {"goal": "x" * 4001}, {"permissions": ["purchase"]},
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


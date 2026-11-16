# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest
# Import from fastapi.testclient: TestClient (drives the real ASGI app locally without a live HTTP
# server).
from fastapi.testclient import TestClient
# Import from sqlalchemy: create_engine (constructs a database connection-pool manager).
from sqlalchemy import create_engine
# Import from sqlalchemy.orm: Session (groups SQLAlchemy database work and transaction state).
from sqlalchemy.orm import Session
# Import from sqlalchemy.pool: StaticPool (reuses one SQLite connection across request/test
# threads).
from sqlalchemy.pool import StaticPool

# Import from crescendo_api.config: get_settings (loads and caches validated local configuration).
from crescendo_api.config import get_settings
# Import from crescendo_api.database: get_session (yields a request-scoped database unit of work).
from crescendo_api.database import get_session
# Import from crescendo_api.main: app (a dependency used below).
from crescendo_api.main import app
# Import from crescendo_api.models: Base (the SQLAlchemy registry whose metadata holds the table
# definitions).
from crescendo_api.models import Base

# Set TOKEN to 'test-only-token-with-more-than-32-characters'.
TOKEN = "test-only-token-with-more-than-32-characters"


# Register a pytest fixture; tests request it by parameter name and pytest manages teardown.
@pytest.fixture
# Define client with parameters monkeypatch.
def client(monkeypatch):
    # pytest creates this fixture for each test case. monkeypatch restores the
    # environment afterward; clear our settings cache so tests do not reuse it.
    # Call monkeypatch.setenv with 'DEV_API_TOKEN', TOKEN.
    monkeypatch.setenv("DEV_API_TOKEN", TOKEN)
    # Call get_settings.cache_clear with no arguments.
    get_settings.cache_clear()
    # One temporary in-memory SQLite connection is shared with TestClient's
    # request thread. These tests are fast but do not prove PostgreSQL behavior.
    # Set engine to create_engine('sqlite://', connect_args={'check_same_thread': False},
    # poolclass=StaticPool).
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # Call Base.metadata.create_all with engine.
    Base.metadata.create_all(engine)

    # Define session_override with no parameters.
    def session_override():
        # Use Session(engine) as session; leave the context and run its cleanup when this block
        # ends.
        with Session(engine) as session:
            # Give session to the caller and pause here until execution resumes.
            yield session

    # Replace only persistence, leaving real routing, validation, and auth active.
    # Set app.dependency_overrides[get_session] to session_override.
    app.dependency_overrides[get_session] = session_override
    # Use TestClient(app) as client; leave the context and run its cleanup when this block ends.
    with TestClient(app) as client:
        # Give client to the caller and pause here until execution resumes.
        yield client
    # Normal fixture teardown: avoid leaking overrides/connections into later cases.
    # Call app.dependency_overrides.clear with no arguments.
    app.dependency_overrides.clear()
    # Call get_settings.cache_clear with no arguments.
    get_settings.cache_clear()
    # Call engine.dispose with no arguments.
    engine.dispose()


# Define auth with no parameters.
def auth():
    # Return {'Authorization': f'Bearer {TOKEN}'}.
    return {"Authorization": f"Bearer {TOKEN}"}


# Define test_drafts_require_authentication with parameters client.
def test_drafts_require_authentication(client):
    # Assert that client.get('/runs').status_code equals 401. If false, this check fails with
    # AssertionError.
    assert client.get("/runs").status_code == 401
    # Assert that client.post('/runs', json={'goal': 'Research a weekend trip'}).status_code equals
    # 401. If false, this check fails with AssertionError.
    assert client.post("/runs", json={"goal": "Research a weekend trip"}).status_code == 401
    # Assert that client.get('/runs', headers={'Authorization': 'Bearer wrong'}).status_code equals
    # 401. If false, this check fails with AssertionError.
    assert client.get("/runs", headers={"Authorization": "Bearer wrong"}).status_code == 401


# Define test_draft_is_persisted_and_retrievable with parameters client.
def test_draft_is_persisted_and_retrievable(client):
    # Set response to client.post('/runs', headers=auth(), json={'goal': '  Compare beginner cameras
    # under $500  '}).
    response = client.post("/runs", headers=auth(), json={"goal": "  Compare beginner cameras under $500  "})
    # Assert that response.status_code equals 201. If false, this check fails with AssertionError.
    assert response.status_code == 201
    # Set run to response.json().
    run = response.json()
    # Assert that run['goal'] equals 'Compare beginner cameras under $500'. If false, this check
    # fails with AssertionError.
    assert run["goal"] == "Compare beginner cameras under $500"
    # Assert that run['status'] equals 'draft'. If false, this check fails with AssertionError.
    assert run["status"] == "draft"
    # Assert that client.get(f"/runs/{run['id']}", headers=auth()).json() equals run. If false, this
    # check fails with AssertionError.
    assert client.get(f"/runs/{run['id']}", headers=auth()).json() == run
    # Assert that client.get('/runs', headers=auth()).json() equals a new list containing run. If
    # false, this check fails with AssertionError.
    assert client.get("/runs", headers=auth()).json() == [run]


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("sent, stored", [
    # Add this item to the surrounding list: ({}, None),.
    ({}, None),
    # Add this item to the surrounding list: ({"constraints": None}, None),.
    ({"constraints": None}, None),
    # Add this item to the surrounding list: ({"constraints": " "}, None),.
    ({"constraints": "   "}, None),
    # Add this item to the surrounding list: ({"constraints": " no flights "}, "no flights"),.
    ({"constraints": "  no flights  "}, "no flights"),
])
# Define test_blank_constraints_are_stored_as_absent with parameters client, sent, stored.
def test_blank_constraints_are_stored_as_absent(client, sent, stored):
    # One meaning, one value: missing, null, and blank all mean "no constraints",
    # so downstream prompt building only ever checks for None.
    # Set response to client.post('/runs', headers=auth(), json={'goal': 'Plan a weekend trip',
    # **sent}).
    response = client.post("/runs", headers=auth(), json={"goal": "Plan a weekend trip", **sent})
    # Assert that response.status_code equals 201. If false, this check fails with AssertionError.
    assert response.status_code == 201
    # Assert that response.json()['constraints'] equals stored. If false, this check fails with
    # AssertionError.
    assert response.json()["constraints"] == stored
    # Assert that client.get('/runs', headers=auth()).json()[0]['constraints'] equals stored. If
    # false, this check fails with AssertionError.
    assert client.get("/runs", headers=auth()).json()[0]["constraints"] == stored

# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("patch", [
    # Add this item to the surrounding list: {"max_workers": 4}, {"max_workers": True},
    # {"timeout_seconds": 601},.
    {"max_workers": 4}, {"max_workers": True}, {"timeout_seconds": 601},
    # Add this item to the surrounding list: {"model_budget_cents": 0}, {"model_budget_cents":
    # 501},.
    {"model_budget_cents": 0}, {"model_budget_cents": 501},
    # Add this item to the surrounding list: {"goal": " "}, {"goal": "x" * 4001}, {"constraints":
    # "x" * 1001}, {"permissions": ["purchase"]},.
    {"goal": "          "}, {"goal": "x" * 4001}, {"constraints": "x" * 1001}, {"permissions": ["purchase"]},
])
# Define test_invalid_or_escalated_request_is_rejected with parameters client, patch.
def test_invalid_or_escalated_request_is_rejected(client, patch):
    # Parametrize runs this same behavioral check once per invalid payload.
    # Check both the error and its consequence: no draft should have been saved.
    # Set response to client.post('/runs', headers=auth(), json={'goal': 'Plan a weekend trip',
    # **patch}).
    response = client.post("/runs", headers=auth(), json={"goal": "Plan a weekend trip", **patch})
    # Assert that response.status_code equals 422. If false, this check fails with AssertionError.
    assert response.status_code == 422
    # Assert that client.get('/runs', headers=auth()).json() equals a new list (empty). If false,
    # this check fails with AssertionError.
    assert client.get("/runs", headers=auth()).json() == []


# Define test_capabilities_do_not_claim_execution with parameters client.
def test_capabilities_do_not_claim_execution(client):
    # Assert that client.get('/capabilities', headers=auth()).json()['execution'] is False. If
    # false, this check fails with AssertionError.
    assert client.get("/capabilities", headers=auth()).json()["execution"] is False
    # Assert that client.get('/runs/00000000-0000-0000-0000-000000000000',
    # headers=auth()).status_code equals 404. If false, this check fails with AssertionError.
    assert client.get("/runs/00000000-0000-0000-0000-000000000000", headers=auth()).status_code == 404


# Define test_delete_draft_persists_and_preserves_other_drafts with parameters client.
def test_delete_draft_persists_and_preserves_other_drafts(client):
    # Set first to client.post('/runs', headers=auth(), json={'goal': 'Research a weekend
    # trip'}).json().
    first = client.post("/runs", headers=auth(), json={"goal": "Research a weekend trip"}).json()
    # Set second to client.post('/runs', headers=auth(), json={'goal': 'Compare beginner
    # cameras'}).json().
    second = client.post("/runs", headers=auth(), json={"goal": "Compare beginner cameras"}).json()

    # Set response to client.delete(f"/runs/{first['id']}", headers=auth()).
    response = client.delete(f"/runs/{first['id']}", headers=auth())

    # Assert that response.status_code equals 204. If false, this check fails with AssertionError.
    assert response.status_code == 204
    # Assert that response.content equals b''. If false, this check fails with AssertionError.
    assert response.content == b""
    # Assert that client.get(f"/runs/{first['id']}", headers=auth()).status_code equals 404. If
    # false, this check fails with AssertionError.
    assert client.get(f"/runs/{first['id']}", headers=auth()).status_code == 404
    # Assert that client.get('/runs', headers=auth()).json() equals a new list containing second. If
    # false, this check fails with AssertionError.
    assert client.get("/runs", headers=auth()).json() == [second]
    # Assert that client.delete(f"/runs/{first['id']}", headers=auth()).status_code equals 404. If
    # false, this check fails with AssertionError.
    assert client.delete(f"/runs/{first['id']}", headers=auth()).status_code == 404


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}])
# Define test_unauthorized_delete_preserves_draft with parameters client, headers.
def test_unauthorized_delete_preserves_draft(client, headers):
    # Set run to client.post('/runs', headers=auth(), json={'goal': 'Research a weekend
    # trip'}).json().
    run = client.post("/runs", headers=auth(), json={"goal": "Research a weekend trip"}).json()

    # Assert that client.delete(f"/runs/{run['id']}", headers=headers).status_code equals 401. If
    # false, this check fails with AssertionError.
    assert client.delete(f"/runs/{run['id']}", headers=headers).status_code == 401
    # Assert that client.get(f"/runs/{run['id']}", headers=auth()).json() equals run. If false, this
    # check fails with AssertionError.
    assert client.get(f"/runs/{run['id']}", headers=auth()).json() == run


# Define test_delete_rejects_missing_and_malformed_ids with parameters client.
def test_delete_rejects_missing_and_malformed_ids(client):
    # Assert that client.delete('/runs/00000000-0000-0000-0000-000000000000',
    # headers=auth()).status_code equals 404. If false, this check fails with AssertionError.
    assert client.delete("/runs/00000000-0000-0000-0000-000000000000", headers=auth()).status_code == 404
    # Assert that client.delete('/runs/not-a-uuid', headers=auth()).status_code equals 422. If
    # false, this check fails with AssertionError.
    assert client.delete("/runs/not-a-uuid", headers=auth()).status_code == 422


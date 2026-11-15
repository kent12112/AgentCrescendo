# Learn: Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest
# Learn: From fastapi.testclient, import TestClient (drives the real ASGI app locally without a live HTTP
# server).
from fastapi.testclient import TestClient
# Learn: From sqlalchemy, import create_engine (constructs a database connection-pool manager).
from sqlalchemy import create_engine
# Learn: From sqlalchemy.orm, import Session (groups SQLAlchemy database work and transaction state).
from sqlalchemy.orm import Session
# Learn: From sqlalchemy.pool, import StaticPool (reuses one SQLite connection across request/test threads).
from sqlalchemy.pool import StaticPool

# Learn: From crescendo_api.config, import get_settings (loads and caches validated local configuration).
from crescendo_api.config import get_settings
# Learn: From crescendo_api.database, import get_session (yields a request-scoped database unit of work).
from crescendo_api.database import get_session
# Learn: From crescendo_api.main, import app (a dependency used below).
from crescendo_api.main import app
# Learn: From crescendo_api.models, import Base (the SQLAlchemy registry whose metadata holds the table
# definitions).
from crescendo_api.models import Base

# Learn: Set TOKEN to 'test-only-token-with-more-than-32-characters'.
TOKEN = "test-only-token-with-more-than-32-characters"


# Learn: Register a pytest fixture; tests request it by parameter name and pytest manages teardown.
@pytest.fixture
# Learn: Define client(monkeypatch). The body runs when called, not when defined.
def client(monkeypatch):
    # pytest creates this fixture for each test case. monkeypatch restores the
    # environment afterward; clear our settings cache so tests do not reuse it.
    # Learn: Temporarily set an environment variable for this test on monkeypatch; inputs: 'DEV_API_TOKEN',
    # TOKEN.
    monkeypatch.setenv("DEV_API_TOKEN", TOKEN)
    # Learn: Clear cached configuration so this test reads its own environment on get_settings.
    get_settings.cache_clear()
    # One temporary in-memory SQLite connection is shared with TestClient's
    # request thread. These tests are fast but do not prove PostgreSQL behavior.
    # Learn: Set engine to create_engine('sqlite://', connect_args={'check_same_thread': False},
    # poolclass=StaticPool); the SQLAlchemy connection-pool manager, not a permanently open transaction.
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # Learn: Call Base.metadata.create_all with the arguments shown.
    Base.metadata.create_all(engine)

    # Learn: Define session_override(). The body runs when called, not when defined.
    def session_override():
        # Learn: Enter Session(engine) as session. The context manager controls setup/exit; inspect it for
        # the actual cleanup behavior.
        with Session(engine) as session:
            # Learn: Yield session to the with-block/request; resume here for cleanup afterward.
            yield session

    # Replace only persistence, leaving real routing, validation, and auth active.
    # Learn: Set app.dependency_overrides[get_session] to session_override.
    app.dependency_overrides[get_session] = session_override
    # Learn: Enter TestClient(app) as client. The context manager controls setup/exit; inspect it for the
    # actual cleanup behavior.
    with TestClient(app) as client:
        # Learn: Yield client to the with-block/request; resume here for cleanup afterward.
        yield client
    # Normal fixture teardown: avoid leaking overrides/connections into later cases.
    # Learn: Call app.dependency_overrides.clear with no arguments.
    app.dependency_overrides.clear()
    # Learn: Clear cached configuration so this test reads its own environment on get_settings.
    get_settings.cache_clear()
    # Learn: Call engine.dispose with no arguments.
    engine.dispose()


# Learn: Define auth(). The body runs when called, not when defined.
def auth():
    # Learn: Return a new dictionary with keys 'Authorization' to the caller and stop this function.
    return {"Authorization": f"Bearer {TOKEN}"}


# Learn: Test drafts require authentication. pytest supplies named fixtures and checks assertions below.
def test_drafts_require_authentication(client):
    # Learn: Assert that client.get('/runs').status_code equals 401. If false, this check fails with
    # AssertionError.
    assert client.get("/runs").status_code == 401
    # Learn: Assert that client.post('/runs', json={'goal': 'Research a weekend trip'}).status_code equals
    # 401. If false, this check fails with AssertionError.
    assert client.post("/runs", json={"goal": "Research a weekend trip"}).status_code == 401
    # Learn: Assert that client.get('/runs', headers={'Authorization': 'Bearer wrong'}).status_code equals
    # 401. If false, this check fails with AssertionError.
    assert client.get("/runs", headers={"Authorization": "Bearer wrong"}).status_code == 401


# Learn: Test draft is persisted and retrievable. pytest supplies named fixtures and checks assertions
# below.
def test_draft_is_persisted_and_retrievable(client):
    # Learn: Set response to client.post('/runs', headers=auth(), json={'goal': ' Compare beginner cameras
    # under $500 '}); the returned HTTP or model-provider response.
    response = client.post("/runs", headers=auth(), json={"goal": "  Compare beginner cameras under $500  "})
    # Learn: Assert that response.status_code equals 201. If false, this check fails with AssertionError.
    assert response.status_code == 201
    # Learn: Set run to response.json(); the persisted task draft or returned draft representation.
    run = response.json()
    # Learn: Assert that run['goal'] equals 'Compare beginner cameras under $500'. If false, this check
    # fails with AssertionError.
    assert run["goal"] == "Compare beginner cameras under $500"
    # Learn: Assert that run['status'] equals 'draft'. If false, this check fails with AssertionError.
    assert run["status"] == "draft"
    # Learn: Assert that client.get(f"/runs/{run['id']}", headers=auth()).json() equals run. If false, this
    # check fails with AssertionError.
    assert client.get(f"/runs/{run['id']}", headers=auth()).json() == run
    # Learn: Assert that client.get('/runs', headers=auth()).json() equals a new list containing run. If
    # false, this check fails with AssertionError.
    assert client.get("/runs", headers=auth()).json() == [run]


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("sent, stored", [
    # Learn: Add this item to the surrounding list: ({}, None),.
    ({}, None),
    # Learn: Add this item to the surrounding list: ({"constraints": None}, None),.
    ({"constraints": None}, None),
    # Learn: Add this item to the surrounding list: ({"constraints": " "}, None),.
    ({"constraints": "   "}, None),
    # Learn: Add this item to the surrounding list: ({"constraints": " no flights "}, "no flights"),.
    ({"constraints": "  no flights  "}, "no flights"),
# Learn: Close this list literal; delimiters group the values into one object.
])
# Learn: Test blank constraints are stored as absent. pytest supplies named fixtures and checks assertions
# below.
def test_blank_constraints_are_stored_as_absent(client, sent, stored):
    # One meaning, one value: missing, null, and blank all mean "no constraints",
    # so downstream prompt building only ever checks for None.
    # Learn: Set response to client.post('/runs', headers=auth(), json={'goal': 'Plan a weekend trip',
    # **sent}); the returned HTTP or model-provider response.
    response = client.post("/runs", headers=auth(), json={"goal": "Plan a weekend trip", **sent})
    # Learn: Assert that response.status_code equals 201. If false, this check fails with AssertionError.
    assert response.status_code == 201
    # Learn: Assert that response.json()['constraints'] equals stored. If false, this check fails with
    # AssertionError.
    assert response.json()["constraints"] == stored
    # Learn: Assert that client.get('/runs', headers=auth()).json()[0]['constraints'] equals stored. If
    # false, this check fails with AssertionError.
    assert client.get("/runs", headers=auth()).json()[0]["constraints"] == stored

# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("patch", [
    # Learn: Add this item to the surrounding list: {"max_workers": 4}, {"max_workers": True},
    # {"timeout_seconds": 601},.
    {"max_workers": 4}, {"max_workers": True}, {"timeout_seconds": 601},
    # Learn: Add this item to the surrounding list: {"model_budget_cents": 0}, {"model_budget_cents": 501},.
    {"model_budget_cents": 0}, {"model_budget_cents": 501},
    # Learn: Add this item to the surrounding list: {"goal": " "}, {"goal": "x" * 4001}, {"constraints": "x"
    # * 1001}, {"permissions": ["purchase"]},.
    {"goal": "          "}, {"goal": "x" * 4001}, {"constraints": "x" * 1001}, {"permissions": ["purchase"]},
# Learn: Close this list literal; delimiters group the values into one object.
])
# Learn: Test invalid or escalated request is rejected. pytest supplies named fixtures and checks assertions
# below.
def test_invalid_or_escalated_request_is_rejected(client, patch):
    # Parametrize runs this same behavioral check once per invalid payload.
    # Check both the error and its consequence: no draft should have been saved.
    # Learn: Set response to client.post('/runs', headers=auth(), json={'goal': 'Plan a weekend trip',
    # **patch}); the returned HTTP or model-provider response.
    response = client.post("/runs", headers=auth(), json={"goal": "Plan a weekend trip", **patch})
    # Learn: Assert that response.status_code equals 422. If false, this check fails with AssertionError.
    assert response.status_code == 422
    # Learn: Assert that client.get('/runs', headers=auth()).json() equals a new list (empty). If false,
    # this check fails with AssertionError.
    assert client.get("/runs", headers=auth()).json() == []


# Learn: Test capabilities do not claim execution. pytest supplies named fixtures and checks assertions
# below.
def test_capabilities_do_not_claim_execution(client):
    # Learn: Assert that client.get('/capabilities', headers=auth()).json()['execution'] is False. If false,
    # this check fails with AssertionError.
    assert client.get("/capabilities", headers=auth()).json()["execution"] is False
    # Learn: Assert that client.get('/runs/00000000-0000-0000-0000-000000000000',
    # headers=auth()).status_code equals 404. If false, this check fails with AssertionError.
    assert client.get("/runs/00000000-0000-0000-0000-000000000000", headers=auth()).status_code == 404


# Learn: Test delete draft persists and preserves other drafts. pytest supplies named fixtures and checks
# assertions below.
def test_delete_draft_persists_and_preserves_other_drafts(client):
    # Learn: Set first to client.post('/runs', headers=auth(), json={'goal': 'Research a weekend
    # trip'}).json().
    first = client.post("/runs", headers=auth(), json={"goal": "Research a weekend trip"}).json()
    # Learn: Set second to client.post('/runs', headers=auth(), json={'goal': 'Compare beginner
    # cameras'}).json().
    second = client.post("/runs", headers=auth(), json={"goal": "Compare beginner cameras"}).json()

    # Learn: Set response to client.delete(f"/runs/{first['id']}", headers=auth()); the returned HTTP or
    # model-provider response.
    response = client.delete(f"/runs/{first['id']}", headers=auth())

    # Learn: Assert that response.status_code equals 204. If false, this check fails with AssertionError.
    assert response.status_code == 204
    # Learn: Assert that response.content equals b''. If false, this check fails with AssertionError.
    assert response.content == b""
    # Learn: Assert that client.get(f"/runs/{first['id']}", headers=auth()).status_code equals 404. If
    # false, this check fails with AssertionError.
    assert client.get(f"/runs/{first['id']}", headers=auth()).status_code == 404
    # Learn: Assert that client.get('/runs', headers=auth()).json() equals a new list containing second. If
    # false, this check fails with AssertionError.
    assert client.get("/runs", headers=auth()).json() == [second]
    # Learn: Assert that client.delete(f"/runs/{first['id']}", headers=auth()).status_code equals 404. If
    # false, this check fails with AssertionError.
    assert client.delete(f"/runs/{first['id']}", headers=auth()).status_code == 404


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer wrong"}])
# Learn: Test unauthorized delete preserves draft. pytest supplies named fixtures and checks assertions
# below.
def test_unauthorized_delete_preserves_draft(client, headers):
    # Learn: Set run to client.post('/runs', headers=auth(), json={'goal': 'Research a weekend
    # trip'}).json(); the persisted task draft or returned draft representation.
    run = client.post("/runs", headers=auth(), json={"goal": "Research a weekend trip"}).json()

    # Learn: Assert that client.delete(f"/runs/{run['id']}", headers=headers).status_code equals 401. If
    # false, this check fails with AssertionError.
    assert client.delete(f"/runs/{run['id']}", headers=headers).status_code == 401
    # Learn: Assert that client.get(f"/runs/{run['id']}", headers=auth()).json() equals run. If false, this
    # check fails with AssertionError.
    assert client.get(f"/runs/{run['id']}", headers=auth()).json() == run


# Learn: Test delete rejects missing and malformed ids. pytest supplies named fixtures and checks assertions
# below.
def test_delete_rejects_missing_and_malformed_ids(client):
    # Learn: Assert that client.delete('/runs/00000000-0000-0000-0000-000000000000',
    # headers=auth()).status_code equals 404. If false, this check fails with AssertionError.
    assert client.delete("/runs/00000000-0000-0000-0000-000000000000", headers=auth()).status_code == 404
    # Learn: Assert that client.delete('/runs/not-a-uuid', headers=auth()).status_code equals 422. If false,
    # this check fails with AssertionError.
    assert client.delete("/runs/not-a-uuid", headers=auth()).status_code == 422


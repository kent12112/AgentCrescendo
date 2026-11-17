"""POST /runs/{id}/start: idempotency and failure recovery with a fake Temporal.

The fake mimics the one property under test (one execution per workflow ID) so
these tests run offline. services/workers/tests proves that property against a
real Temporal server.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from crescendo_api.config import get_settings
from crescendo_api.database import get_session
from crescendo_api.main import app
from crescendo_api.models import Base, Run
from crescendo_api.run_start_service import reconcile_pending_starts
from crescendo_api.run_starter import RunStartUnavailable, get_run_starter
from crescendo_workers.run_start import StartResult, workflow_id_for_run

TOKEN = "test-only-token-with-more-than-32-characters"
DRAFT = {"goal": "Find a cited fact about Boston"}


class FakeStarter:
    """Records calls; keeps one 'execution' per workflow ID, like Temporal."""

    def __init__(self):
        self.calls: list[str] = []
        self.executions: dict[str, str] = {}
        self.fail_next = 0

    async def start(self, run_id: str) -> StartResult:
        self.calls.append(run_id)
        if self.fail_next:
            self.fail_next -= 1
            raise RunStartUnavailable
        workflow_id = workflow_id_for_run(run_id)
        execution = self.executions.setdefault(workflow_id, f"exec-{len(self.executions) + 1}")
        return StartResult(workflow_id=workflow_id, run_id=execution)


@pytest.fixture
def engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def starter():
    return FakeStarter()


@pytest.fixture
def client(monkeypatch, engine, starter):
    monkeypatch.setenv("DEV_API_TOKEN", TOKEN)
    get_settings.cache_clear()

    def session_override():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_run_starter] = lambda: starter
    with TestClient(app, headers={"Authorization": f"Bearer {TOKEN}"}) as client:
        yield client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def make_draft(client) -> str:
    response = client.post("/runs", json=DRAFT)
    assert response.status_code == 201
    return response.json()["id"]


def test_start_requires_authentication(client):
    run_id = make_draft(client)
    response = client.post(f"/runs/{run_id}/start", headers={"Authorization": ""})
    assert response.status_code == 401


def test_start_moves_draft_to_started_with_stable_workflow_id(client, starter):
    run_id = make_draft(client)
    response = client.post(f"/runs/{run_id}/start")
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "started"
    assert body["workflow_id"] == f"run-{run_id}"
    assert body["start_requested_at"] is not None
    assert starter.calls == [run_id]


def test_repeated_start_returns_same_run_without_new_execution(client, starter):
    run_id = make_draft(client)
    first = client.post(f"/runs/{run_id}/start").json()
    second = client.post(f"/runs/{run_id}/start").json()
    assert second == first
    # Already confirmed, so the second request does not even ask Temporal.
    assert starter.calls == [run_id]
    assert len(starter.executions) == 1


def test_unconfirmed_start_returns_503_and_retry_reuses_the_same_id(client, starter):
    run_id = make_draft(client)
    starter.fail_next = 1
    failed = client.post(f"/runs/{run_id}/start")
    assert failed.status_code == 503
    # The start command survived the failure.
    pending = client.get(f"/runs/{run_id}").json()
    assert pending["status"] == "starting"
    assert pending["workflow_id"] == f"run-{run_id}"

    retried = client.post(f"/runs/{run_id}/start")
    assert retried.status_code == 202
    assert retried.json()["status"] == "started"
    assert retried.json()["start_requested_at"] == pending["start_requested_at"]
    assert starter.calls == [run_id, run_id]
    assert len(starter.executions) == 1


def test_different_runs_get_different_workflows(client, starter):
    first, second = make_draft(client), make_draft(client)
    client.post(f"/runs/{first}/start")
    client.post(f"/runs/{second}/start")
    assert set(starter.executions) == {f"run-{first}", f"run-{second}"}


def test_start_unknown_run_is_404(client, starter):
    response = client.post("/runs/00000000-0000-4000-8000-000000000000/start")
    assert response.status_code == 404
    assert starter.calls == []


def test_started_run_can_no_longer_be_deleted(client):
    run_id = make_draft(client)
    client.post(f"/runs/{run_id}/start")
    assert client.delete(f"/runs/{run_id}").status_code == 404
    assert client.get(f"/runs/{run_id}").status_code == 200


def test_reconciler_finishes_stuck_starts_only(engine, starter):
    """Simulate the API crashing after step 1: rows stuck in 'starting'."""
    old = datetime.now(timezone.utc) - timedelta(minutes=5)
    with Session(engine) as session:
        stuck = Run(goal=DRAFT["goal"], max_workers=1, timeout_seconds=60, model_budget_cents=1)
        fresh = Run(goal=DRAFT["goal"], max_workers=1, timeout_seconds=60, model_budget_cents=1)
        draft = Run(goal=DRAFT["goal"], max_workers=1, timeout_seconds=60, model_budget_cents=1)
        session.add_all([stuck, fresh, draft])
        session.commit()
        for run, requested in ((stuck, old), (fresh, datetime.now(timezone.utc))):
            session.execute(
                update(Run)
                .where(Run.id == run.id)
                .values(status="starting", workflow_id=workflow_id_for_run(run.id), start_requested_at=requested)
            )
        session.commit()
        stuck_id, fresh_id, draft_id = stuck.id, fresh.id, draft.id

        confirmed = asyncio.run(reconcile_pending_starts(session, starter))

        assert confirmed == [stuck_id]
        assert session.get(Run, stuck_id).status == "started"
        assert session.get(Run, fresh_id).status == "starting"  # possibly still in flight
        assert session.get(Run, draft_id).status == "draft"  # never requested


def test_reconciler_leaves_row_starting_when_temporal_is_down(engine, starter):
    with Session(engine) as session:
        run = Run(goal=DRAFT["goal"], max_workers=1, timeout_seconds=60, model_budget_cents=1)
        session.add(run)
        session.commit()
        session.execute(
            update(Run)
            .where(Run.id == run.id)
            .values(
                status="starting",
                workflow_id=workflow_id_for_run(run.id),
                start_requested_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            )
        )
        session.commit()
        starter.fail_next = 1

        assert asyncio.run(reconcile_pending_starts(session, starter)) == []
        assert session.get(Run, run.id).status == "starting"


def test_database_rejects_unknown_status(engine):
    with Session(engine) as session:
        session.add(Run(goal=DRAFT["goal"], status="running", max_workers=1, timeout_seconds=60, model_budget_cents=1))
        with pytest.raises(Exception, match="CHECK constraint failed"):
            session.commit()

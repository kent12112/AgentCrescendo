"""W2-F01 evidence: duplicate run starts produce one Temporal execution.

ID tests always run. The server tests need a real Temporal server and run only
with TEMPORAL_INTEGRATION=1: the SDK downloads and starts the official
development server (first run downloads it; later runs reuse it).

    TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest -q services/workers/tests
"""

import asyncio
import os
import uuid
from datetime import timedelta

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.worker import Worker

from crescendo_workers.activities import RunStartRecord
from crescendo_workers.run_start import (
    COORDINATOR_TASK_QUEUE,
    RUN_WORKFLOW_NAME,
    RunWorkflowInput,
    start_run_workflow,
    workflow_id_for_run,
)
from crescendo_workers.workflows import RunWorkflow

RUN_ID = "3f2b8c1e-9a4d-4e7b-8c2a-1d5e6f7a8b9c"


# ---- Stable ID rule (no server needed) --------------------------------------


def test_workflow_id_is_derived_from_run_id():
    assert workflow_id_for_run(RUN_ID) == f"run-{RUN_ID}"
    assert workflow_id_for_run(uuid.UUID(RUN_ID)) == workflow_id_for_run(RUN_ID)


def test_workflow_id_normalizes_case_so_one_run_has_one_id():
    assert workflow_id_for_run(RUN_ID.upper()) == workflow_id_for_run(RUN_ID)


@pytest.mark.parametrize("bad", ["", "not-a-uuid", "run-" + RUN_ID])
def test_workflow_id_rejects_non_uuid_run_ids(bad):
    with pytest.raises(ValueError):
        workflow_id_for_run(bad)


# ---- Against a real Temporal server -----------------------------------------

integration = pytest.mark.skipif(
    os.environ.get("TEMPORAL_INTEGRATION") != "1", reason="set TEMPORAL_INTEGRATION=1 to start a local Temporal server"
)


class CountingActivity:
    """Stands in for record_run_start (same registered name) and counts runs.

    `gate` lets a test hold the workflow open so later starts hit a *running*
    execution, which is the double-click case.
    """

    def __init__(self):
        self.calls: list[str] = []
        self.gate = asyncio.Event()

    def defn(self):
        @activity.defn(name="record_run_start")
        async def record_run_start(params: RunWorkflowInput) -> RunStartRecord:
            self.calls.append(params.run_id)
            await self.gate.wait()
            info = activity.info()
            return RunStartRecord(run_id=params.run_id, workflow_id=info.workflow_id, attempt=info.attempt)

        return record_run_start


@pytest.fixture(scope="module")
def temporal():
    """One dev server and event loop shared by this module's server tests."""
    if os.environ.get("TEMPORAL_INTEGRATION") != "1":
        pytest.skip("set TEMPORAL_INTEGRATION=1")
    from temporalio.testing import WorkflowEnvironment

    loop = asyncio.new_event_loop()
    env = loop.run_until_complete(WorkflowEnvironment.start_local())
    yield loop, env
    loop.run_until_complete(env.shutdown())
    loop.close()


def run_with_worker(temporal, scenario):
    """Run `scenario(client, counter)` while a worker serves the coordinator queue."""
    loop, env = temporal
    counter = CountingActivity()

    async def main():
        task_queue = COORDINATOR_TASK_QUEUE
        async with Worker(env.client, task_queue=task_queue, workflows=[RunWorkflow], activities=[counter.defn()]):
            return await scenario(env.client, counter)

    return loop.run_until_complete(asyncio.wait_for(main(), timeout=60))


async def wait_for_calls(counter, expected, timeout=10.0):
    async def poll():
        while len(counter.calls) < expected:
            await asyncio.sleep(0.05)

    await asyncio.wait_for(poll(), timeout)


@integration
def test_concurrent_duplicate_starts_create_one_execution(temporal):
    run_id = str(uuid.uuid4())

    async def scenario(client: Client, counter: CountingActivity):
        # Five simultaneous starts for the same run (a burst of double clicks).
        results = await asyncio.gather(*(start_run_workflow(client, run_id) for _ in range(5)))
        await wait_for_calls(counter, 1)
        # While the first execution is still running, start again.
        late = await start_run_workflow(client, run_id)
        counter.gate.set()
        # Typed handle, so the result is decoded as RunStartRecord, not a dict.
        handle = client.get_workflow_handle_for(RunWorkflow.run, workflow_id_for_run(run_id))
        record = await handle.result()
        return results, late, record, list(counter.calls)

    results, late, record, calls = run_with_worker(temporal, scenario)
    execution_ids = {result.run_id for result in results} | {late.run_id}
    assert len(execution_ids) == 1, "every start must land on the same execution"
    assert calls == [run_id], "the run's first activity must execute exactly once"
    assert record.workflow_id == f"run-{run_id}"


@integration
def test_start_after_completion_does_not_run_again(temporal):
    run_id = str(uuid.uuid4())

    async def scenario(client: Client, counter: CountingActivity):
        counter.gate.set()
        first = await start_run_workflow(client, run_id)
        handle = client.get_workflow_handle(workflow_id_for_run(run_id))
        await handle.result()
        # The workflow is closed. REJECT_DUPLICATE forbids a fresh execution.
        again = await start_run_workflow(client, run_id)
        await asyncio.sleep(1)  # give a wrongly started execution time to call the activity
        description = await handle.describe()
        return first, again, description, list(counter.calls)

    first, again, description, calls = run_with_worker(temporal, scenario)
    assert again.run_id == first.run_id
    assert description.run_id == first.run_id
    assert description.status == WorkflowExecutionStatus.COMPLETED
    assert calls == [run_id]


@integration
def test_control_random_ids_would_duplicate(temporal):
    """Deliberate break: what happens without a stable ID (the failure we prevent)."""
    run_id = str(uuid.uuid4())

    async def scenario(client: Client, counter: CountingActivity):
        counter.gate.set()
        for _ in range(2):
            await client.start_workflow(
                RUN_WORKFLOW_NAME,
                RunWorkflowInput(run_id=run_id),
                id=f"run-{uuid.uuid4()}",  # a new random ID per request
                task_queue=COORDINATOR_TASK_QUEUE,
            )
        await wait_for_calls(counter, 2)
        return list(counter.calls)

    assert run_with_worker(temporal, scenario) == [run_id, run_id]


@integration
def test_api_double_post_starts_one_workflow(temporal, tmp_path, monkeypatch):
    """End to end: real FastAPI route + real Temporal; SQLite instead of PostgreSQL."""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool

    from crescendo_api.config import get_settings
    from crescendo_api.database import get_session
    from crescendo_api.main import app
    from crescendo_api.models import Base
    from crescendo_api.run_starter import TemporalRunStarter, get_run_starter

    loop, env = temporal
    token = "temporal-test-token-with-more-than-32-characters"
    monkeypatch.setenv("DEV_API_TOKEN", token)
    get_settings.cache_clear()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def session_override():
        with Session(engine) as session:
            yield session

    target = env.client.service_client.config.target_host
    starter = TemporalRunStarter(target, env.client.namespace)
    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_run_starter] = lambda: starter
    try:
        with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as http:
            run_id = http.post("/runs", json={"goal": "Find a cited fact about Boston"}).json()["id"]
            first = http.post(f"/runs/{run_id}/start")
            second = http.post(f"/runs/{run_id}/start")
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()
        engine.dispose()

    assert first.status_code == second.status_code == 202
    assert first.json()["workflow_id"] == second.json()["workflow_id"] == f"run-{run_id}"

    async def scenario(client: Client, counter: CountingActivity):
        counter.gate.set()
        handle = client.get_workflow_handle(f"run-{run_id}")
        await handle.result()
        return list(counter.calls)

    assert run_with_worker(temporal, scenario) == [run_id]

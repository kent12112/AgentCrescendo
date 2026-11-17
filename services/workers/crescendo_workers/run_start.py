"""The run-start contract shared by the API (which starts runs) and the worker.

Duplicate prevention rests on one idea: a run's workflow ID is computed from the
run ID, never generated randomly. Temporal allows only one workflow execution per
ID at a time, so every retry, double click, or concurrent request for the same run
lands on the same execution instead of creating a second one.
"""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

# Lightweight orchestration queue named in the architecture. Desktop-heavy
# activities will move to a separate "desktop-work" queue in later features.
COORDINATOR_TASK_QUEUE = "coordinator"
# Registered workflow type name. The API starts workflows by this name so it never
# imports workflow code (which must stay deterministic and sandboxed).
RUN_WORKFLOW_NAME = "RunWorkflow"
# Bound how long one start RPC may wait, so an unreachable server fails the HTTP
# request quickly instead of hanging it. The caller can safely retry.
START_RPC_TIMEOUT = timedelta(seconds=5)


@dataclass(frozen=True)
class RunWorkflowInput:
    """Workflow argument. Only the ID: the run's details stay in PostgreSQL."""

    run_id: str


@dataclass(frozen=True)
class StartResult:
    """Which execution a start call landed on (new or already existing)."""

    workflow_id: str
    run_id: str | None


def workflow_id_for_run(run_id: str | UUID) -> str:
    """Return the one stable workflow ID for a run.

    Parsing through UUID normalizes case and rejects malformed input, so
    "ABC..." and "abc..." cannot become two different workflow IDs.
    """
    return f"run-{UUID(str(run_id))}"


async def start_run_workflow(client: Client, run_id: str | UUID) -> StartResult:
    """Start the run's workflow, or find the execution that already exists.

    Two Temporal policies cover the two duplicate cases:
    - Conflict policy USE_EXISTING: if an execution with this ID is *running*,
      return a handle to it rather than failing or starting another.
    - Reuse policy REJECT_DUPLICATE: if an execution with this ID has *closed*
      (completed, failed, cancelled), never start a fresh one under the same ID.
      Temporal raises WorkflowAlreadyStartedError, which we treat as "already
      started" because, for this caller, it is the same successful outcome.
    """
    workflow_id = workflow_id_for_run(run_id)
    try:
        handle = await client.start_workflow(
            RUN_WORKFLOW_NAME,
            RunWorkflowInput(run_id=str(UUID(str(run_id)))),
            id=workflow_id,
            task_queue=COORDINATOR_TASK_QUEUE,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
            id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
            rpc_timeout=START_RPC_TIMEOUT,
        )
    except WorkflowAlreadyStartedError as error:
        # Only reachable for a closed execution (USE_EXISTING covers running ones).
        return StartResult(workflow_id=workflow_id, run_id=error.run_id)
    return StartResult(workflow_id=workflow_id, run_id=handle.result_run_id)

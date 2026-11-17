"""Activities: the place for side effects (model calls, desktops, network, DB).

Workflow code must be deterministic so Temporal can replay it; anything that
touches the outside world runs here instead.
"""

from dataclasses import dataclass

from temporalio import activity

from .run_start import RunWorkflowInput


@dataclass(frozen=True)
class RunStartRecord:
    """What the placeholder activity observed. Returned as the workflow result."""

    run_id: str
    workflow_id: str
    attempt: int


@activity.defn(name="record_run_start")
async def record_run_start(params: RunWorkflowInput) -> RunStartRecord:
    """Placeholder first step of a run.

    W2-F01 only proves start de-duplication, so this performs no agent work. Later
    features replace it with desktop task activities, heartbeats (W2-F02), and
    persisted run state (W2-F03). Tests count its executions to show that duplicate
    start requests produce exactly one run.
    """
    info = activity.info()
    activity.logger.info("Run %s started in workflow %s", params.run_id, info.workflow_id)
    return RunStartRecord(run_id=params.run_id, workflow_id=info.workflow_id, attempt=info.attempt)

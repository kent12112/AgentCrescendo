"""The durable run workflow.

Temporal records each step in the workflow's history. If a worker dies, another
worker replays that history to rebuild state, so this code must be deterministic:
no clocks, randomness, network, or database access here; those go in activities.
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

# Workflow code runs in Temporal's sandbox; passing these imports through tells the
# sandbox they are safe to share rather than re-importing them per workflow.
with workflow.unsafe.imports_passed_through():
    from .activities import RunStartRecord, record_run_start
    from .run_start import RUN_WORKFLOW_NAME, RunWorkflowInput


@workflow.defn(name=RUN_WORKFLOW_NAME)
class RunWorkflow:
    """One execution per run. The workflow ID (not this class) enforces that."""

    @workflow.run
    async def run(self, params: RunWorkflowInput) -> RunStartRecord:
        # Bounded from the start: a stuck activity times out and a failing one is
        # retried at most three times. W2-F02 adds heartbeats, cancellation, and
        # tuned limits.
        return await workflow.execute_activity(
            record_run_start,
            params,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

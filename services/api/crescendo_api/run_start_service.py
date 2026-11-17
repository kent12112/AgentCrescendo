"""Idempotent run start: persist the start command, then ask Temporal.

Order matters. We commit "starting + workflow_id" *before* calling Temporal:

    draft --(1) claim, commit--> starting --(2) Temporal start--> (3) started

- Crash/timeout after (1): the row says "starting". A retried request or the
  reconciler repeats (2) with the same workflow ID, and Temporal returns the
  existing execution if one was created. Nothing is lost, nothing is duplicated.
- Two concurrent requests: both may reach (2); Temporal's single-execution-per-ID
  rule makes them land on one execution.
- After (3): later requests return the saved row without calling Temporal.

The database never decides on its own that a workflow exists; only Temporal's
answer moves a run to "started".
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from crescendo_workers.run_start import workflow_id_for_run

from .models import Run
from .run_starter import RunStarter, RunStartUnavailable


class RunNotFound(Exception):
    pass


def claim_start(session: Session, run_id: str) -> Run:
    """Step 1: move a draft to "starting" and record its workflow ID.

    The single conditional UPDATE (status = 'draft') is the claim: whichever
    request commits first changes the row; any later or concurrent request
    matches zero rows and simply reads the existing start command.
    """
    session.execute(
        update(Run)
        .where(Run.id == run_id, Run.status == "draft")
        .values(
            status="starting",
            workflow_id=workflow_id_for_run(run_id),
            start_requested_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    run = session.get(Run, run_id)
    if run is None:
        raise RunNotFound(run_id)
    return run


def confirm_started(session: Session, run_id: str) -> Run:
    """Step 3: record that Temporal accepted the start. Conditional, so a
    concurrent confirm (or a later status change) is never overwritten."""
    session.execute(update(Run).where(Run.id == run_id, Run.status == "starting").values(status="started"))
    session.commit()
    run = session.get(Run, run_id)
    if run is None:
        raise RunNotFound(run_id)
    return run


async def start_run(session: Session, starter: RunStarter, run_id: str) -> Run:
    """Steps 1-3. Raises RunStartUnavailable (row stays "starting") if Temporal
    cannot confirm; calling again is safe.

    The database calls are synchronous, so they run in a worker thread and do
    not block the event loop that serves other requests.
    """
    run = await asyncio.to_thread(claim_start, session, run_id)
    if run.status == "started":
        return run
    await starter.start(run_id)
    return await asyncio.to_thread(confirm_started, session, run_id)


async def reconcile_pending_starts(
    session: Session, starter: RunStarter, older_than: timedelta = timedelta(seconds=30)
) -> list[str]:
    """Finish starts left in "starting" (e.g. the API crashed between steps 1 and 3).

    `older_than` skips starts an in-flight request is probably still finishing.
    Re-running step 2 is harmless even if that request does finish. Returns the
    run IDs confirmed now; failures stay "starting" for the next pass. Nothing
    schedules this yet; the W2-F06 reaper is the planned caller.
    """
    cutoff = datetime.now(timezone.utc) - older_than
    query = select(Run.id).where(Run.status == "starting", Run.start_requested_at <= cutoff)
    pending = await asyncio.to_thread(lambda: session.scalars(query.order_by(Run.start_requested_at)).all())
    confirmed = []
    for run_id in pending:
        try:
            await starter.start(run_id)
        except RunStartUnavailable:
            continue
        await asyncio.to_thread(confirm_started, session, run_id)
        confirmed.append(run_id)
    return confirmed

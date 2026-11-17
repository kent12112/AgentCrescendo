# Handoff: W2-F01 — Temporal run workflow with stable start IDs

- Date/time and timezone: November 17, 2026, US Eastern
- Author / session: Claude, VS Code session
- Intended recipient: the user (senior reviewer); review requested, not an assignment
- Base commit: `e8843ca`
- Change commit(s), or uncommitted paths: uncommitted (list below). Other
  uncommitted work in the tree (W1X-F02/F03) is not part of this task.
- State: complete (user-reviewed November 17, 2026)
- Ownership: released

## Goal and acceptance criteria

[Plan W2-F01](../implementation-plan.md): Temporal workflow/activities with stable
start IDs that prevent duplicate run starts. [Architecture](../architecture.md)
step 3: stable ID derived from the run ID, persisted start command, retries find
or start the same workflow. Observed: duplicate and concurrent starts give one
execution; a failed start is retried onto the same workflow.

## Changes and decisions

New worker package `services/workers/crescendo_workers/`:
- `run_start.py`: `workflow_id_for_run()` (`run-<uuid>`), `start_run_workflow()`
  with `USE_EXISTING` + `REJECT_DUPLICATE`; queue `coordinator`.
- `workflows.py`: `RunWorkflow`, one bounded activity call (30 s, 3 attempts).
- `activities.py`: `record_run_start`, a placeholder with no agent work.
- `worker.py`: `python -m crescendo_workers.worker`.

API:
- `routes/runs.py`: `POST /runs/{id}/start` (202 / 404 / 503).
- `run_start_service.py`: claim (`draft -> starting`, conditional UPDATE),
  Temporal start, confirm (`starting -> started`); `reconcile_pending_starts()`.
- `run_starter.py`: `RunStarter` interface, lazy cached `TemporalRunStarter`,
  errors mapped to `RunStartUnavailable`.
- `models.py`, `schemas.py`, `config.py`, migration `0003_run_start.py`:
  `workflow_id` (unique), `start_requested_at`, named `ck_runs_status`, Temporal
  address/namespace settings.

Other: `pyproject.toml` (temporalio dependency, workers package/tests),
`requirements-dev.lock`, `apps/web/features/drafts/types.ts`,
`scripts/temporal_dev_server.py`, [decision 0006](../decisions/0006-stable-run-start.md),
[learning note 17](../learning/17-stable-run-start.md).

## Evidence

Local (no paid providers):
- `.venv/bin/python -m pytest -q`: 603 passed, 4 skipped (the opt-in Temporal tests).
- `TEMPORAL_INTEGRATION=1 .venv/bin/python -m pytest -q services/workers/tests`:
  9 passed, twice (real Temporal CLI 1.10.1 / server 1.32.2 dev server). Covers
  concurrent duplicates, start after completion, random-ID control (2 executions),
  API double POST end to end.
- `npm run typecheck` (apps/web): passed.

Live local processes (dev server + worker + uvicorn on scratch SQLite):
- 10 concurrent POSTs: all 202, one workflow ID, 1 execution `COMPLETED`, the
  activity log line appeared once.
- Temporal stopped: 503 after 8.6 s, row `starting` with workflow ID. Restarted:
  two retries 202, same ID and original `start_requested_at`, 1 execution.

PostgreSQL 17 (throwaway container, removed): 0002 -> 0003 replaced the
auto-named `runs_status_check` with `ck_runs_status`; `alembic check` clean;
unknown status and duplicate `workflow_id` rejected; downgrade refused while a run
was `started`; downgrade/upgrade clean once all rows were drafts.

Not proven: multi-process API contention on PostgreSQL (the conditional UPDATE is
standard, but only SQLite/single-process contention was exercised); behavior
after Temporal retention expiry (see decision 0006); Compose has no Temporal
service yet (the script uses the SDK-downloaded dev server).

## Open issues and next action

- Review answers (user, November 17): keep `started` until W2-F03; ~8.6 s 503
  latency accepted; Temporal stays a script, Compose service deferred to W2-F02.
- W2-F01 checked in the plan. Next: W2-F02 (heartbeats, retries,
  cancellation, timeouts).

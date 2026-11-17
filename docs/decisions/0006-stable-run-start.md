# 0006: Stable run-start IDs and the start handshake

- Date: November 17, 2026
- Status: Accepted (user review, November 17, 2026)
- Task: W2-F01

## Context

`POST /runs/{id}/start` will be retried by browsers, clients, and (later) a
reconciler. Each retry must not create another run execution, because a second
execution would open another desktop, spend more model budget, and race the first
one on shared state.

## Decision

1. **The workflow ID is derived from the run ID**: `run-<uuid>`, normalized
   through `UUID()`. Temporal allows at most one execution per ID at a time.
2. **ID policies on start**: `USE_EXISTING` for a running execution (return it),
   `REJECT_DUPLICATE` for a closed one (never re-run a finished run under its
   ID). `WorkflowAlreadyStartedError` is treated as success.
3. **Persist the start command before calling Temporal.** A conditional update
   moves `draft -> starting` and stores `workflow_id` and `start_requested_at`.
   Only Temporal's acknowledgement moves `starting -> started`. A crash in between
   leaves a `starting` row; a retry or `reconcile_pending_starts()` re-issues the
   same start.
4. The API starts the workflow **by type name** (`"RunWorkflow"`), so it does not
   import deterministic workflow code.

## Alternatives rejected

- *Random workflow IDs plus a DB check.* The check and the start are not atomic;
  two concurrent requests both pass the check. The control test shows random IDs
  create two executions.
- *Start in Temporal first, then write the DB.* A crash after the start would
  leave a workflow the database does not know about.
- *Database row only (no Temporal ID rule).* Works for one database, but does not
  protect starts issued by other callers (reconciler, CLI) that skip the row lock.

## Consequences and limits

- `started` means "Temporal accepted it", not "running" or "finished". Real run
  state (running/completed/failed) is W2-F03.
- Temporal forgets closed workflows after the namespace retention period. If a
  row stayed `starting` longer than that (API crashed, nothing retried), a retry
  could start a second execution. Running the reconciler regularly closes that
  window; it has no scheduler yet (planned caller: W2-F06 reaper).
- An unreachable Temporal makes the start request take about 8.6 seconds before
  `503` (5-second RPC timeout plus SDK retries), observed live.
- Started runs can no longer be deleted (the delete route only matches drafts).
  Cancellation is W2-F02/W2-F08.

## Review outcome (November 17, 2026)

The user accepted: `started` as the status name until W2-F03; the ~8.6-second
`503` when Temporal is unreachable; keeping Temporal as
`scripts/temporal_dev_server.py` for now. A Temporal Compose service is deferred
to W2-F02, where workflow history must survive restarts.

# Handoff: approved-letter E2B live Writer and saved PDF

- Date/time and timezone: November 17, 2026, America/New_York.
- Author/session: Codex primary local session; no delegation.
- Intended recipient: user / next reviewer, review requested, not assigned.
- Base commit: `d9813ed`; no commits or pushes. All changes remain uncommitted
  alongside pre-existing Claude and earlier Codex work, which was preserved.
- State: requested live Writer integration implemented and live-tested.
- Ownership: released. Test servers/desktops shut down; the user's running servers
  were not stopped or used for test writes.

## Goal and acceptance criteria

Connect an approved letter to a real offline E2B desktop the user can watch in the
web page, type the approved text visibly in LibreOffice, export a PDF, verify it,
and save/download it from the website. Do not imply company browsing or durable
Temporal desktop orchestration is completed by this step.

## Changes and decisions

- Extract existing JOB-P01 pure settings/network/typing/PDF helpers into
  `packages/agent_runtime/crescendo_agent/writer_support.py`; the probe imports them
  and retains its CLI/fictional sample. Existing probe tests still pass.
- New `crescendo_agent/writer.py`: real E2B desktop with deny-all outbound IPv4,
  no installation/allowlist, private stream, 600-second kill timer. Run the five
  server-answer network proofs before sending letter text. Fresh Writer profile
  disables AutoCorrect/completion. Type in bounded chunks with real Enter presses;
  visible Save and Export Directly as PDF. No headless fallback. Parse/compare the
  PDF's words against the exact approved snapshot before publishing it.
- New `crescendo_api/writer_service.py`, `routes/writer.py`, `WriterExport` model,
  migration `0007_writer_exports.py`, E2B setting, and API shutdown ownership. A
  unique letter/version export and approved-version row lock prevent duplicate
  starts and serialize against edits. Keep all text/PDF data local except the
  approved snapshot typed on the accepted provider desktop. No new Groq calls.
- Statuses: starting/preparing/waiting_viewer/typing/exporting/cancelling/saved/
  failed/cancelled; report an orphaned process owner as interrupted. Actual character
  counts, explicit Start typing gate, cancellation checks, cleanup status, and
  retry only after confirmed cleanup or expiry. Three unexpired desktop/uncertain
  cleanup leases maximum in the supported single API process. PDFs are binary
  Postgres data, downloadable after the desktop closes and on later page visits.
- Viewer capabilities remain in memory, returned only by authenticated export
  endpoints with no-store. Distinct viewer cookies per port avoid collisions.
  Count successfully connected WebSockets so a delayed old close cannot clear a
  new connection after reload. Failed handshakes do not decrement that count.
- Same-origin Next writer routes, binary PDF proxy, `features/jobs/live-writer.tsx`,
  approved-letter UI integration, and writing/PDF process steps. Iframe uses only
  loopback capability URLs, no-referrer, and a script/same-origin sandbox. Editing
  is disabled during export and blocked authoritatively by the API.
- `scripts/smoke_job_search.py` now supports fake desktop or `--live-writer`, copies
  frontend source to temporary storage (excluding local env/cache), and reuses
  dependencies so test servers do not collide with the user's Next dev lock.
- Docs: README, status/plan, [decision 0012](../decisions/0012-live-writer-exports.md),
  clarification in 0011, and [learning note 14](../learning/14-live-writer.md).

## Evidence

- `.venv/bin/python -m pytest -q` with loopback permission: **921 passed, 4 skipped**,
  one existing Starlette/httpx deprecation warning. New coverage includes real PDF
  parsing/mismatch rejection, network gate before typing, visible key/export calls,
  cleanup on failure, approval/version/key/auth checks, waiting for begin, duplicate
  starts, cancellation before/during typing, retry snapshots, lease/capacity/restart
  behavior, edit protection, viewer cookies, and overlapping connection teardown.
- `npm run typecheck` and final `npm run build` in `apps/web`: passed. Existing
  outside-repository lockfile warning remains. No new packages required for users
  already running the desktop probe; otherwise install the documented extras.
- `.venv/bin/alembic upgrade head`: local PostgreSQL migrated to `0007 (head)`.
  `.venv/bin/alembic check`: **No new upgrade operations detected**. SQLite migration
  tests exercise 0007 upgrade/schema comparison/downgrade; existing data preserved.
- `.venv/bin/python scripts/smoke_job_search.py`: final **pass**, copied frontend,
  temporary SQLite, fictional jobs/resume, fake Groq and fake desktop only. Includes
  iframe, explicit start, reload reconnect, persisted progress, edit disabling,
  binary download, and preserved action errors across background polling. It does
  not establish E2B behavior. Artifacts: ignored `.demo-artifacts/job-search-smoke/`.
- `.venv/bin/python scripts/smoke_job_search.py --live-writer`: final **pass** with
  real E2B and fake Groq, fictional approved letter only. Actual blank LibreOffice
  canvas visible; page reload reconnected; explicit start triggered typing; visible
  PDF export and download succeeded; extracted words exactly match the approved
  snapshot; API recorded cleanup; saved result/download survived another reload.
  PDF: **one page, 12,572 bytes, approved snapshot 152 characters**. Inspected
  `writer-before.png`, `writer-typing.png`, and `writer-saved.png` under ignored
  `.demo-artifacts/writer-live-smoke/`; PDF is `writer-export.pdf`. No user resume or
  letter was sent to E2B during validation.
- First live attempt reached the real blank Writer but Start returned 409 during
  reload. Fixed the overlapping connect/disconnect event race and the UI poll
  erasing action errors; rerun passed. The test now waits for a rendered reloaded
  canvas before Start. Other observed fixture failures: unsupported FastAPI event
  hook (use lifespan), and relative test WebSocket URL hitting trusted-host rejection
  instead of the intended upstream branch. Both corrected and regression-tested.
- `git diff --check`: passed. No deployment, commits, or changes to personal letters.

## Open issues and next action

Refresh the letter workspace. Review/approve a draft, scroll to **Live writing &
PDF**, choose **Open live Writer**, wait for the blank document, then **Start typing**.
After export choose **Download Writer PDF**. `E2B_API_KEY` and desktop/jobs extras are
required. The existing local key was used only in memory for the fictional live
test and never printed. Restart the API after changing environment settings.

This bridge supports one local API process. Refresh reconnects while that process
owns the desktop; process restart loses the viewer and replacement waits for lease
expiry. Provider timer: 600 seconds; persisted lease: 660 seconds including creation/
cleanup uncertainty; viewer wait: 90 seconds; approved text maximum: 6,000 characters.
User stop is checked between chunks/SDK calls, not an instantaneous remote interrupt.
An unconfirmed cleanup continues to consume a lease. No durable Temporal desktop
scheduling/recovery claim; company research remains open. One live short ASCII
letter is evidence of this path, not a reliability benchmark for all letters or
image versions. Toolbar position (1024x768 default image) remains fragile; text
verification fails safely if rendering/typing changes the words. Retention/deletion
of letter/export snapshots is still a separate task.

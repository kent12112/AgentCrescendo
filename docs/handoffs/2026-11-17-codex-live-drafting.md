# Handoff: watch Writer during letter drafting, before approval

- Date/time: November 17, 2026, America/New_York.
- Author/session: Codex primary local session; no delegation.
- Intended recipient: user / next reviewer; review requested, not assigned.
- Base: `d9813ed`; no commits/pushes. All changes remain uncommitted alongside
  earlier user/Claude/Codex changes, preserved.
- State: requested flow correction implemented and verified.
- Ownership: released; isolated test servers stopped; both real desktops cleaned up.

## Goal and resulting behavior

User corrected the experience: live watching should happen when drafting a letter.
Previously Groq generated a draft before the user saw Writer, which only exported
approved text. The new sequence is **Draft live → Review & approve → Final PDF**.

The desktop opens/prepares first. When its blank Writer canvas is visible the user
chooses **Start drafting**. The host calls the model, validates/persists its draft,
and types that actual text on the same desktop, before review and approval. Name
placeholders remain in the preview. Completion opens text/source review; approval
restores the supplied name locally. Approved export remains available separately.

## Changes and decisions

- `WriterExport.purpose` (`draft`/`export`) and `drafting` phase, migration
  `0009_live_drafting.py`. Existing records default to export; SQLite upgrade/
  schema comparison/downgrade and local PostgreSQL migration passed.
- `WriterManager.start(..., generate=callback)` owns preparation, viewer gate,
  model generation, persisted text/checks, visible typing/verification and cleanup.
  Letter row lock/version claim prevents duplicate/competing generation; legacy
  synchronous generation refuses a live run. Same-letter uncertain leases gate
  later versions as well. No resume/credentials/identity supplied to the desktop.
- Draft text is saved as soon as the model finishes. Editing/approval waits for
  the desktop to finish. Desktop failure or cancellation retains completed text;
  retry of its unchanged preview reuses it without a model call. Stop before Start
  invokes no model; Stop during the bounded model request retains completed text
  and prevents subsequent typing. Hand-edited drafts cannot use the generated-
  preview route; review/approve them before export.
- Draft PDF is verified then discarded; final download endpoints reject previews.
  Final PDFs still snapshot an approved version and persist independently.
- New authenticated `/jobs/letters/{id}/draft-writer` POST plus explicit Next proxy
  allowlist entry. No viewer capability in normal letter/session payloads.
- Frontend generation opens live Writer, sequences selected letters through the
  API, returns to review, and preserves active-run reconnect after reload. Active
  status selects the desktop on reload; a deliberate pane switch stays mounted.
  Inputs collapse during drafting; retry remains accessible afterward. Consent
  explains Groq plus E2B redacted-draft preview. Updated progress ordering/copy.
- `scripts/smoke_job_search.py` verifies a desktop before any draft text exists,
  actual preview typing before review/approval, and final export. Mock mode tests
  two letters with controlled model failure/retry. Real mode tests one fictional
  Unicode draft plus its edited/approved export to avoid unnecessary paid desktops.
- [Decision 0014](../decisions/0014-draft-before-approval.md), earlier decision
  updates, README, plan, status and learning note 14 record the changed boundary.

## Evidence

- `.venv/bin/python -m pytest -q`: **937 passed, 4 skipped**, existing Starlette/httpx
  deprecation warning. Tests include waiting before any model call, version/consent/
  key/auth gates, idempotent live start, legacy-generation conflict, preserved text
  after desktop failure, retry without regeneration, model failure/retry, Stop
  during model execution, manual-edit preview rejection, no unapproved downloads,
  migration and all existing Writer/network/viewer behavior.
- `npm run typecheck`, `npm run build` in `apps/web`: passed. Existing external
  lockfile warning remains. Final copy change only clarifies that draft review
  opens after writing; it does not alter the lifecycle.
- `.venv/bin/alembic upgrade head`, `current`, `check`: local PostgreSQL at
  **0009 (head)**, **No new upgrade operations detected**. Existing data retained.
- `.venv/bin/python scripts/smoke_job_search.py --writer-stress`: **pass** with fake
  Groq/desktop, isolated frontend/FastAPI/SQLite. Two-letter draft-first flow,
  controlled provider failure/retry, consent, text/source review, edits/approval,
  printing/download, fullscreen, export reload/reconnect, edit lock, saved output,
  mobile search and stale-response guard passed.
- `.venv/bin/python scripts/smoke_job_search.py --live-writer --writer-stress`:
  **pass** with real E2B, fake Groq and fictional data only. Real canvas appears
  before generation; reload reconnects before Start drafting; 1,062-character
  placeholder draft types before review/approval. Captured ODT text exactly matches
  the Unicode draft; preview PDF download returns 409; cleanup confirmed. Draft
  timings: opening 9.795 s, preparation 40.870 s, viewer/reload wait 14.866 s, fake
  generation 0.495 s, typing **14.862 s**, verification/export 8.668 s, cleanup
  1.810 s; total **91.365 s**, typing throughput **71.5 characters/s**.
- Same real browser run edited/approved the draft and exported the 1,094-character
  final letter: typing **15.348 s**, complete export **78.102 s**; PDF words match
  under the existing narrow nonbreaking-hyphen comparison, cleanup confirmed, saved
  result/download survives reload. No user resume/letter or real Groq call used.
- Inspected integrated `draft-live.png`. Ignored artifacts:
  `.demo-artifacts/writer-performance-live/{draft-before.png,draft-live.png,
  fictional-draft.txt,draft-raw.odt,draft-raw.pdf,draft-metrics.json,writer-export.pdf,
  export-metrics.json}`. No provider capability or key included in this handoff.
- Observed/fixed UI failure: initial browser check reloaded an active approved
  export into its default review pane, hiding Start typing. Active-run transition
  now selects desktop; updated mock and real browser reruns passed.
- `git diff --check`: passed. No deployment, commit, or personal-data test writes.

## Limits and next action

Refresh the app, prepare/confirm inputs, choose **Draft … live**, wait for the blank
desktop, then **Start drafting**. Existing completed drafts remain available for
review; they are not regenerated automatically. Both provider keys and the desktop
extras are required for this web flow. Local migration is already applied; restart
any API launched without reload to load the new code.

The model returns a validated structured draft before keyboard typing starts;
this does not stream model tokens or reveal hidden reasoning. Real E2B evidence
uses a fake model; it proves orchestration/viewer/typing, not current Groq latency
or model quality. Cold desktop preparation still takes roughly 40 seconds. One
API process owns the run; restart loses the viewer and requires lease expiry before
replacement. Closing the browser stops starting later jobs, not the current worker.
Company research, durable Temporal recovery, and snapshot retention remain open.

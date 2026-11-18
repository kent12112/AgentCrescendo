# Handoff: Writer Unicode reliability, performance, and integrated desktop

- Date/time: November 17, 2026, America/New_York.
- Author/session: Codex primary local session; no delegation.
- Intended recipient: user / next reviewer; review requested, not assigned.
- Base commit: `d9813ed`. No commits/pushes; changes remain uncommitted alongside
  existing Claude/earlier Codex work, preserved.
- State: requested fix and UI improvements implemented and verified.
- Ownership: released. Isolated test servers shut down; provider cleanup confirmed.

## Goal and diagnosis

User reported the generic Writer export failure after typing began and requested
an integrated, faster desktop experience. Saved metadata showed 17/1,113 characters
typed, cleanup confirmed; first body chunk contains Unicode. No personal text was
printed, changed, or resent during diagnosis. Historical SDK exception was not
retained, so that particular exception cannot be recovered.

A full-length fictional reproduction of the old adapter failed with
`CommandExitException`, exit 1, at 557/1,088 characters. Controlled live commands
measured `locale charmap` as `ANSI_X3.4-1968` and xdotool reported an invalid
multibyte sequence for fixed Unicode punctuation. The same phrase succeeded with
`LC_ALL=C.UTF-8`. This is direct evidence of the typing bug matching the report.

## Changes and decisions

- `crescendo_agent/writer.py`: explicit UTF-8 on shell-quoted xdotool text input,
  clear held modifiers, bounded 15-second command timeout, 100-character chunks at
  20-ms delay (was nested 50/25-character calls at 50 ms). Keep real Enter presses,
  offline gate, visible saving/export, cancellation checkpoints and fresh-desktop
  retry. Never replay a partially failed command into the same document.
- Safe SDK category/operation errors replace generic typing failure; never persist
  SDK bodies, typed commands, or viewer tokens. `writer_service.py` persists phase
  times, total time and throughput. `WriterExport.diagnostics` is nullable JSON for
  legacy rows; migration `0008_writer_diagnostics.py` applied locally.
- Full Unicode typing exposed a PDF-only layout difference: approved `front‑end`
  becomes `front-end` in the extracted PDF. `writer_support.pdf_words_match` permits
  only that no-break property plus existing whitespace differences. Words, numbers,
  accents, quotes and other dashes remain strict. Raw `compare_text` is unchanged
  for diagnosis. Captured fictional ODT text exactly matched the original Unicode.
- `letter-workspace.tsx`, `live-writer.tsx`, `jobs.module.css`: approved letters open
  in a wide integrated desktop pane; review/source switch keeps the viewer mounted;
  fullscreen, connection/status/progress/download in the same stage. Inputs collapse
  after drafting, but pending/failed drafts keep retry controls available. Serialized
  polls discard superseded reads, skip unchanged state, back off in background tabs.
- `scripts/smoke_job_search.py --writer-stress`: full fictional Unicode letter,
  safe timings, terminal failure detection, pane-switch checks and fake fullscreen
  check. Real stress mode alone captures fictional ODT/PDF for verification; the
  production path never persists unverified PDFs.
- [Decision 0013](../decisions/0013-writer-unicode-and-workspace.md), README, status,
  plan, and [learning note 14](../learning/14-live-writer.md) updated.

## Evidence

- `.venv/bin/python -m pytest -q`: **930 passed, 4 skipped**. Existing Starlette/httpx
  deprecation warning. Focused Writer runtime/API/migration run: **25 passed**.
  Covers UTF-8/shell quoting, bounded commands, safe failure categories, phase
  diagnostics and migration downgrade, narrow hyphen equivalence and rejection of
  changed words/numbers/accents/quotes/other dashes.
- `npm run build` in `apps/web`: passed after final frontend changes, including
  TypeScript checking. Existing outside-repository lockfile warning remains.
- `.venv/bin/alembic upgrade head`, `current`, `check`: local PostgreSQL at
  **0008 (head)**, **No new upgrade operations detected**. Existing data preserved.
- `.venv/bin/python scripts/smoke_job_search.py --writer-stress`: mock-provider UI
  pass, including fullscreen, pane switching, reconnect, edit lock and saved output.
- `.venv/bin/python scripts/smoke_job_search.py --live-writer --writer-stress`:
  **pass**, isolated Next/FastAPI/SQLite, fake Groq, real E2B, fictional data only.
  Search, draft retry, approval, desktop reload/reconnect, explicit typing start,
  pane switching with edit lock, PDF download, cleanup and saved-result reload pass.
  Final timings: opening **7.468 s**, preparing **38.166 s**, viewer/reload waiting
  **8.502 s**, typing **15.334 s**, exporting **8.372 s**, cleanup **1.670 s**;
  total **79.512 s**, **1,094 characters**, **71.3 characters/s** while typing.
  PDF: **one page, 16,072 bytes**. Exact ODT word comparison passed; PDF differs
  only by U+2011's no-break property. Cleanup confirmed.
- Inspected `writer-typing.png` and integrated `writer-saved.png`; safe timing JSON,
  fictional approved text, raw ODT and verified PDF under ignored
  `.demo-artifacts/writer-performance-live/`. Baseline safe metadata at
  `.demo-artifacts/writer-performance/baseline.json`.
- Earlier Unicode runs correctly failed verification on the PDF hyphen difference
  before the narrowly scoped comparison fix. An early UI check found collapsed
  inputs hid retry; the details remain open while drafting needs retry. These
  observed failures are fixed and included in regression/live checks.
- `git diff --check`: passed. No deployment, personal-letter test writes or commits.

## Limits and next action

Refresh the approved letter, choose **Retry live Writer**, wait for the blank
document, then **Start typing**. The user's original approved snapshot is preserved.
Local PostgreSQL already has migration 0008. A non-reloading API must be restarted
to load the new code; the documented development command uses reload.

One full Unicode live pass is evidence for this image/fixture, not a reliability
benchmark. Cold preparation still took about 38 seconds. No new dependency, company
research, or durable orchestration was added. Existing single-process lease/restart
limits and toolbar/image sensitivity from decision 0012 remain. Stop is checked
between bounded remote calls; it is not an instantaneous remote interrupt.

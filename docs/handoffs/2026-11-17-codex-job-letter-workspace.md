# Handoff: JOB-F08 frontend and JOB-F05 connected letter drafting

- Date/time and timezone: November 17, 2026, America/New_York.
- Author / session: Codex, main local session; no delegation.
- Intended recipient: user / next reviewer; review requested, not assigned.
- Base commit: `d9813ed` (`claude/w1-f07-vision-scroll`).
- Change commits: none. Changes remain uncommitted alongside pre-existing Claude work.
- State: connected drafting slice implemented, tested, ready for review; broader
  researcher/live-desktop/PDF-storage acceptance remains open.
- Ownership: released. No servers from the smoke test remain running.

## Goal and acceptance criteria

User asked to finish Claude's frontend to see end-to-end job search, then clarified
that letter generation was not implemented and requested it from job description,
company, and resume. Deliver search → picks → source preview/consent → draft →
review/edit → approve → export with honest persisted states.

## Changes and decisions

- Preserve Claude's uncommitted job-search API, migration 0005, ranking/resume work,
  proxy, and UI. Finish that UI, make `/jobs` the landing page, keep drafts at
  `/drafts`, and add the shared job/letter navigation and process steps.
- Fix pagination using edited rather than submitted filters, old responses surviving
  resume removal, detail-response races, and controlled checkbox responsiveness.
  Expose posting-age filters, score components/countries, accessible file upload,
  empty/loading/error states, clear picks, and keyboard/mobile navigation.
- Add `crescendo_api/letters.py`, `routes/letters.py`, settings, `LetterSession` /
  `CoverLetter` models, migration 0006, same-origin Next letter routes, and
  `features/jobs/letter-*` UI. The server keeps credentials private and checks consent,
  posting existence/open state, at most three jobs, and input snapshot digest.
- Preview freezes redacted resume + posting/company + optional user company notes.
  Generation uses that snapshot after consent, not current mutable resume/postings.
  Identity is stored separately and name substitution occurs only on approval.
- One bounded synchronous Groq call per letter, no SDK retries. Conditional SQL claim
  stops concurrent active duplicates; completed requests reuse saved drafts. Partial
  results survive failures; interrupted rows can be retried after 120 seconds. This
  is not Temporal scheduling and is not exactly-once model billing after a crash.
- Source quotes are checked for existence and candidate numbers for exact spelling.
  Missing quotes, non-exact paraphrases, attribution problems, user notes, and unsourced
  wording get review flags. No semantic verification claim. Edits warn that original
  checks may be stale; version checks prevent overwriting another tab's edits.
- Approved letters download as text. Print view supports browser Save as PDF; PDFs
  are not stored and no offline Writer/E2B desktop is opened by this flow.
- Docs: README, `.env.example`, plan/status, [decision 0011](../decisions/0011-connected-letter-drafting.md),
  and [learning note](../learning/13-cover-letter-pipeline.md). Next dev generated
  `apps/web/AGENTS.md`; production build restored `next-env.d.ts` to its original state.

## Evidence

- `.venv/bin/python -m pytest -q`: **884 passed, 4 skipped**, one existing
  Starlette/httpx deprecation warning. Final run with loopback permission. The initial
  restricted run failed four existing socket tests at `bind`, with 880 passing.
- Focused API/migration suite: **25 passed**. Tests use real HTTP and temporary SQLite,
  fake paid boundary. Checks consent/digest/key enforcement, redaction, snapshots after
  source deletion/change, idempotent completed requests, active/stale generation,
  partial provider failure/retry, approval/download, stale edits, source flags, auth,
  and pick validation. An observed SQLite naive/aware ORM-evaluator failure was fixed
  by evaluating the generation claim in SQL rather than Python.
- `npm run typecheck` and final `npm run build` from `apps/web`: passed. Build's warning
  about a lockfile outside this Git repository remains; no build failure.
- `.venv/bin/python scripts/smoke_job_search.py`: passed (Microsoft Edge). Script starts
  its own Next dev/FastAPI servers, temporary SQLite, 55 fictional jobs, fictional resume,
  fake model only. Checks submitted-query pagination; upload/details; three-pick cap;
  preview/consent including reload; controlled partial failure/retry; source review;
  edit/approve; text download; print/PDF; reload/library; origin/UUID guards; mobile
  overflow/navigation; delayed pagination response after resume deletion. No page errors.
  Inspected desktop-letter and mobile-search screenshots. Initial smoke uncovered
  controlled checkbox lag and implicit textarea-label lookup; both fixed and rerun.
- Ignored browser artifacts: `.demo-artifacts/job-search-smoke/`. Printed fictional PDF
  has **one page**, with the approved signature present in extracted text.
- Local PostgreSQL: `.venv/bin/alembic current` initially `0005`;
  `.venv/bin/alembic upgrade head` succeeded; final `current`: `0006 (head)`;
  `.venv/bin/alembic check`: **No new upgrade operations detected**. Only additive
  letter tables; existing user rows were not changed by tests.
- Live Groq, fictional sources only, `openai/gpt-oss-120b`: first production-adapter
  run **10.5 s**, **200 words**, **11 sentences**, **6 source quotes found**. It embellished
  candidate claims beside real quotes, prompting stricter drafting instructions and
  paraphrase review flags. One subsequent production-adapter request returned the safe
  failure result; its cause was not classified. A final diagnostic request with the
  exact final prompt/request shape and same host schema/checking functions passed:
  `finish_reason=stop`, **11.2 s**, **183 words**, **8 quotes found**, **8 sentences flagged**
  for human review. This is provider/request evidence, not a live personal-resume UI run.
  Ignored artifacts: `.demo-artifacts/letter-live-fictional/` and
  `.demo-artifacts/letter-live-fictional-final/`. No user resume sent during validation.
- `git diff --check`: passed. No commits, pushes, deployments, or E2B sessions.

## Open issues and next action

- Start API and frontend from the root in separate terminals:
  `.venv/bin/uvicorn crescendo_api.main:app --host 127.0.0.1 --port 8000 --reload`
  and `npm --prefix apps/web run dev`. Open `http://127.0.0.1:3000/jobs`.
  The current local database is migrated. The configured Groq key was read only on the
  host and never printed. After changing key/model `.env` values, restart the API.
- Review the ranking and a real user's redacted preview before sending it. Contact
  removal is pattern-based; first resume line is treated as a name. Employers/schools
  remain and can identify a person. Name substitution is intentionally host-only.
- Company context is posting text plus optional user notes, not independent research.
  JOB-F04 and the offline Writer/live viewer/PDF-storage part of JOB-F05/F08 remain
  open. No tracker, semantic entailment checker, durable letter scheduler, or automatic
  data retention/deletion in this slice. Removing the resume leaves saved snapshots.
- Closing a tab may allow the active request to finish but does not start later jobs.
  Reopen Cover letters and continue. After an interrupted generation, wait two minutes
  before retrying. A crash between a paid response and persistence can duplicate cost.

# Handoff: SEARCH-TRACKER focused search and manual application history

- Date/time and timezone: November 18, 2026, America/New_York.
- Author/session: Codex primary, no delegation.
- Intended recipient: user / next reviewer; review requested, not assigned.
- Base commit: observed shared HEAD `77d759b`. The checkout started with extensive
  uncommitted work; another session advanced HEAD during implementation and included
  the initial search/tracker files. Codex did not stage, commit, push, or deploy.
- Paths: `apps/web/features/jobs/{job-search,job-card,job-shell,side-panels,
  use-job-search,application-tracker}.tsx/ts`, `types.ts`, `api.ts`, `jobs.module.css`,
  `apps/web/app/jobs/applications/page.tsx`, application/search API proxies;
  `services/api/crescendo_api/{application_models,applications,job_search,main}.py`,
  `routes/{applications,jobs}.py`, migration `0011`, migration `env.py`,
  `tests/test_applications_api.py`, `scripts/smoke_application_tracker.py`, README,
  plan/status, decision 0018, this handoff. Some are now in the shared HEAD and
  subsequent refinements remain uncommitted. Other sessions' changes preserved.
- State: complete, ready for user evaluation. Ownership released.

## Goal and resulting behavior

Simplify the webpage around Ashby search, researched Why-company answers, and
application tracking. The user explicitly instructed Codex to leave Claude's
Why-company files with that session. No letter/research/provider files were edited.

Search uses horizontal Find jobs / Why company? / Applications navigation, no
process checklist, collapsed advanced filters, and a shortlist shown only when
jobs are selected. Existing ranking, freshness, highlighted details, picks, and
resume handling remain. Search explicitly accepts Ashby, matching its cached index.
No latency improvement is claimed.

Mark applied saves manual history without submitting to a job board. The tracker
supports six statuses, applied/follow-up dates, notes, filters and removal, plus
saved posting text that survives crawl deletion. Search reads current tracking
state for badges/hide-applied before pagination. Duplicate creation does not reset
progress; optimistic versions reject stale edits/removal. See decision 0018 for
ready-status behavior, independent snapshots, and local calendar dates.

## Evidence

- `.venv/bin/python -m pytest -q services/api/tests/test_applications_api.py services/api/tests/test_jobs_api.py services/api/tests/test_migration.py`:
  **21 passed**. Real temporary SQLite and actual migration upgrade/downgrade/schema
  comparison. Tracker needs no resume/letter; covers expired snapshots, stale writes,
  duplicate creation, access/input validation, Ashby-only search, badges/pagination.
- `.venv/bin/python -m pytest -q` with loopback access: **971 passed, 4 skipped**;
  existing Starlette/httpx deprecation warning. Other sessions were editing their
  files concurrently; this count identifies the tested checkout, not an immutable
  release. Initial restricted run: 966 passed, 4 skipped, four existing preflight
  fixtures failed because their loopback sockets were denied. No product fix needed.
- `npm run typecheck` in `apps/web`: passed.
- `.venv/bin/python scripts/smoke_application_tracker.py --build` with loopback
  access: **passed**, real headless Edge + Next + FastAPI + temporary SQLite,
  fictional jobs/resume, no model/desktop calls or provider keys. Separate frontend
  copy preserves the user's dev server. Covers advanced filter visibility, saved
  shortlist, marking applied, hide-applied totals/pagination/URL reload, editable
  status/dates/notes, literal text rendering, filtering, posting deletion and saved
  description, same-origin guards, malformed requests, mobile overflow and removal.
  Production build passed in that isolated copy; temporary processes cleaned up.
- Inspected desktop search/tracker and mobile search/tracker screenshots under
  ignored `.demo-artifacts/application-tracker-smoke/`. Build and local server logs
  also there. These are fictional fixtures, not screenshots of the user's data.
- `.venv/bin/python -m alembic upgrade head`: passed on local PostgreSQL.
  Read-only inspection confirmed revision **0011** and the tracker table.
- `.venv/bin/python -m alembic check`: passed, no new upgrade operations.
- Read-only local requests: API `/health`, authenticated `/jobs/applications`, web
  `/jobs` and `/jobs/applications` all **HTTP 200**. No user records changed by these
  probes; the additive migration preserves existing jobs/resumes/drafts.
- `git diff --check`: passed.

## Observed failures and corrections

- A draft test assumed the cache could search Lever. Inspection showed
  `open_postings` intentionally defaults to Ashby. Restricted the public search
  parameter accordingly and aligned cache counts; no invented other-source support.
- Browser startup initially failed with sandbox `Operation not permitted` on a
  loopback bind; the authorized isolated rerun passed outside that restriction.
- First browser fixture selected the first result while expecting company 0;
  posting timestamps sort newest first. Changed it to select the named company.
- Browser selection exposed ambiguous select labels. Added distinct accessible
  names for Application status and Filter by status.
- Playwright JSON-encoded a string intended as malformed JSON. Sending raw bytes
  exercises the intended proxy parse failure (400); final check passed.

## Limits and next action

Open `http://127.0.0.1:3000/jobs`; mark a role after applying and use Applications
to maintain its history. Existing user API/frontend intentionally remain running.
No reminder delivery, submissions, new ATS crawl, speed benchmark, or live provider
evaluation was part of this task. Claude's separate Why-company handoff records its
quality/provider verification. `scripts/smoke_job_search.py` still targets historical
Writer UI; the new tracker smoke is independent. No review assignment or message
delivery to another session is assumed.

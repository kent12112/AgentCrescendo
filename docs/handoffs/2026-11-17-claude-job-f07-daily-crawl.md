# Handoff: JOB-F07 — daily Ashby crawl into Postgres

- Date/time and timezone: November 17, 2026, America/New_York.
- Author / session: Claude, VS Code session; no delegation.
- Intended recipient: the user (review requested); not an assignment.
- Base commit: `e8843ca`; earlier W1X/W2/JOB work is still uncommitted in the tree.
- Uncommitted paths (this task):
  - New: `services/api/migrations/versions/0004_job_postings.py`,
    `services/api/crescendo_api/job_store.py`, `services/api/tests/test_job_store.py`,
    `scripts/crawl_jobs_daily.py`, `scripts/install_jobs_schedule.py`,
    `docs/decisions/0008-job-storage-daily-crawl.md`, this handoff.
  - Changed: `services/api/crescendo_api/models.py` (JobCompany, JobPosting, JobCrawlRun),
    `services/api/tests/test_migration.py`, `packages/agent_runtime/crescendo_agent/job_cache.py`
    (`refresh_company_list`, failed-crawl retry wait, `save_companies(saved_at=)`),
    `packages/agent_runtime/tests/test_job_coverage.py`, `scripts/find_jobs.py` (reads Postgres;
    `--live`), `scripts/refresh_job_companies.py` (uses the shared refresh),
    `docs/implementation-plan.md`, `docs/status.md`.
  - Outside the repository: `~/Library/LaunchAgents/com.agentcrescendo.jobs-daily.plist`
    (installed and loaded; remove with `scripts/install_jobs_schedule.py --uninstall`).
  - Local database: migrated 0002 → 0004 (0003 from W2-F01 was pending).
- State: ready for review.
- Ownership: released.

## Goal and acceptance criteria

The user asked to focus on Ashby, keep postings from the last 30 days, and crawl daily
into a database (launchd chosen over a Temporal schedule). Acceptance:
- offline tests (SQLite plus a migration drift check)
- one live crawl into local Postgres
- a ranked search read from the database
- the launchd agent installed and observed running once

## Changes and decisions

See [decision 0008](../decisions/0008-job-storage-daily-crawl.md). In short:

- **Tables:**
  - `job_companies`: live / missing / error
  - `job_postings`: primary key (source, posting_id), with first-seen, last-seen and
    closed dates
  - `job_crawl_runs`
- **Sync rules (`job_store.sync_board_results`):**
  - Postings published in the last 30 days are inserted or updated (reopened if they had
    closed).
  - Postings no longer listed on a board that answered are closed.
  - A 404 closes all of that company's postings.
  - A timeout or 5xx changes nothing.
  - Rows older than 30 days are deleted.
  - NUL characters are stripped (Postgres rejects them).
  - The whole day's update is one transaction.
- **Daily script:**
  - starts Compose `db` if it's down
  - refreshes the company list incrementally (10-minute budget)
  - retries a failed Common Crawl crawl only after 7 days (`--retry-failed-days`)
  - fetches all boards, syncs, and records the run
- **Search:** `find_jobs.py` reads open Ashby postings from Postgres; `--live` keeps the
  previous fetch path.
- **Schedule:** launchd agent at 08:00 local time; a missed run happens once on wake. The
  log is `.cache/jobs/daily.log`.

## Evidence

- Offline: `.venv/bin/python -m pytest -q packages services`: 814 passed, 4 skipped.
  - `test_job_store.py`: 13 tests (SQLite) covering insert, update, close, reopen,
    timeout, 404, deletion after 30 days, NUL characters, duplicates, slug case.
  - The migration test checks the 0004 tables and indexes and downgrades to 0003.
  - `alembic check` reports no drift.
  - The refresh test covers deferral and the retry wait.
- Live run 1 (`.venv/bin/python scripts/crawl_jobs_daily.py`, by hand):
  - 4 Common Crawl crawls got HTTP 504 on every attempt (~10 minutes).
  - The board fetch and sync took under a minute: 3,137 companies (2,750 live, 387
    missing = 404), **19,643 postings inserted**, published Oct 19 – Nov 17, 82 MB.
    Recorded as `ok`.
  - The script then exited 1 on its final log line (`DetachedInstanceError`: the run row
    expired at commit). Fixed with `expire_on_commit=False`.
  - The 10 wasted minutes led to the 7-day retry wait.
- Search from Postgres:
  `find_jobs.py --resume <user's resume> --search "ai engineer" --country "united states" --no-senior --max-years 3 --json`.
  It took 3–4 s and returned 119 matches with the same top results as the live fetch
  (133 there included HN Greenhouse boards).
  - Two bugs fixed: `--json` crashed when nothing was fetched live, and the company count
    included missing companies.
- launchd: `scripts/install_jobs_schedule.py --run-now` installed the agent, and launchd
  started crawl run 2 (`state = running`). The run **exited 0** (`launchctl print`: last exit
  code = 0) and was recorded `ok` in 658 s.
  - The first live update pass gave **+16 new, 19,638 updated, 5 closed, 0 deleted**,
    about an hour after run 1.
  - 3 crawls that failed (504) are recorded in `failed_attempts` and deferred for 7 days.
    CC-MAIN-2026-21 was skipped by the budget, so the next run tries it once.
  - The next daily runs should take ~1–3 minutes.

## Open issues and next action

1. **Docker must be running at 08:00 (or on wake).** If it isn't, the run fails and says so
   in the log. Consider auto-starting Docker Desktop at login.
2. **Greenhouse and Lever aren't in the database.** Ashby only, at the user's request.
3. **Ranking follow-ups from JOB-F06:**
   - an exclude list for sales/support titles
   - the "Claude/Anthropic API" false gap
   - printing the location that matched first
4. **Web app:** JOB-F03 can now read `job_postings` through the API.
5. **No concurrency guard.** Two runs at once (manual plus launchd) would race. launchd
   never starts a second copy of its own job, but a manual run could overlap it. A
   Postgres advisory lock would close this.

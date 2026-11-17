# Decision: store job postings in Postgres, refreshed by a daily launchd crawl

Date: November 17, 2026. Decided by the user (Postgres now, Ashby only, a 30-day window,
launchd as the scheduler). Task: JOB-F07. Builds on [0007](0007-job-search-scenario.md).

## Context

JOB-F06 kept postings in per-board JSON files (`.cache/jobs/boards/`, 354 MB for
~3,300 boards). That had three limits:
- Each refresh overwrote a board's file, so nothing recorded when a posting appeared
  or closed.
- A first search without the cache fetched every board, taking ~17 minutes.
- The web app (JOB-F03) can't query files.

The user asked to focus on Ashby, keep postings from the last 30 days, and crawl daily
into a database.

## Decision

1. **The project's existing Postgres, through Alembic migration 0004.** Three tables:
   - `job_companies` (source, slug): `live` / `missing` (404) / `error`, last check
   - `job_postings` (source, posting_id): the normalized posting, plus `first_seen_at`,
     `last_seen_at`, `closed_at`
   - `job_crawl_runs`: one row per run, with status and counts, as evidence it ran
2. **The 30-day window is measured from `published_at`**, or from `first_seen_at` when a
   posting has no date. Older postings are not stored and are deleted on each run,
   whether open or closed.
3. **Only a board that answered can close postings.** A 404 closes the company's open
   postings and marks it `missing`. A timeout or 5xx marks it `error` and changes
   nothing else, so one bad network day can't wipe out real jobs.
4. **Searches read the database.** `find_jobs.py` reads open postings from Postgres;
   `--live` fetches boards as before. The ranking code is unchanged.
5. **macOS launchd runs `scripts/crawl_jobs_daily.py` at 08:00.** A missed run happens
   on wake. The script:
   - starts the Compose `db` service if it's down (Compose has no restart policy)
   - refreshes the Common Crawl company list incrementally (10-minute budget)
   - fetches every board, then syncs the results
6. **Job scripts read only `DATABASE_URL`** (`JobDbSettings`), not the API's
   `DEV_API_TOKEN`.

## Alternatives considered

- **Temporal Schedule.** Gives retries and history in the Temporal UI, but the dev server
  and a worker must always be running, and dev-server state is lost on restart until
  W2-F02 adds persistence. Revisit when the crawl becomes a product workflow.
- **Keep the JSON files.** No history, no queries; rejected by the user.
- **SQLite.** No server to run, but it would be a second database next to the project's
  Postgres. The web app needs Postgres anyway.

## Consequences

- A daily run fetches all ~3,100+ boards (~17 minutes at 8 workers), only through
  Ashby's public API.
- The crawl needs Docker running at 08:00 (or on wake); if not, the run fails and the
  log says why.
- `job_postings` stores untrusted page text. NUL characters are stripped, because
  Postgres rejects them. URLs are still rebuilt from checked IDs (JOB-F00).
- The posting file cache is now used only by `--live` and by extra boards
  (`--boards-file`, `--hn-months`).

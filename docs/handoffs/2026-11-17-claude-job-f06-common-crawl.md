# Handoff: JOB-F06 — Ashby companies from Common Crawl, local caches, country filter

- Date/time and timezone: November 17, 2026, America/New_York.
- Author / session: Claude, VS Code session; no delegation.
- Intended recipient: the user (review requested); not an assignment.
- Base commit: `e8843ca`; earlier W1X/W2/JOB work is still uncommitted in the tree.
- Uncommitted paths (this task):
  - New: `packages/agent_runtime/crescendo_agent/common_crawl.py`, `job_cache.py`,
    `packages/agent_runtime/tests/test_job_coverage.py`, `scripts/refresh_job_companies.py`,
    this handoff.
  - Changed: `job_sources.py` (`Posting.countries`, `normalize_country`, Ashby addresses),
    `job_match.py` (place names, `posting_countries`, `rank(country=...)`),
    `scripts/find_jobs.py`, `.gitignore` (`.cache/`), decision 0007 (update section),
    `docs/implementation-plan.md` (JOB-F06), `docs/status.md`.
- State: ready for review. Acceptance criteria met (below); the ranking itself still
  needs the user's judgment.
- Ownership: released.

## Goal and acceptance criteria

HN gave 281 companies over 12 months and 12 relevant roles; coverage was the limit
(JOB-F02 handoff). Goal: many more companies, free, with nothing about the user sent
out, and a US filter that excludes remote roles abroad. Acceptance: offline tests,
one live discovery run, a ranked run on the user's resume with more companies than HN.

## Changes and decisions

- **Discovery (`common_crawl.py`)**: reads Common Crawl's public CDX index for
  `jobs.ashbyhq.com/*` across the latest N monthly crawls. The first path segment
  of each URL is the slug, which must pass `CompanyBoard.parse`. Ashby routes and
  junk are refused, and slugs are lowercased.
  - Requests are sequential, with a 2 s pause between them.
  - 429/5xx/timeouts are retried after 15/30/60 s, honoring `Retry-After` up to 120 s.
  - 404 means no captures.
  - Each response is capped at 32 MB.
  - One crawl's failure doesn't lose the others.
  - A time budget is checked before each crawl.
  - `skip` lists crawls already read.
- **Background refresh (`scripts/refresh_job_companies.py`)**, at the user's request:
  discovery is no longer in the search path. It's incremental: crawls already read
  are skipped, results are merged into the saved list, and a failed crawl is retried
  next time. It has a 20-minute budget, and `--full` rebuilds from scratch.
  `find_jobs.py` only reads the saved list and warns after 45 days.
- **Caches (`job_cache.py`)** are JSON under the ignored `.cache/jobs/` (user agreed: no
  database until results reach the web app in JOB-F03).
  - `companies-ashby.json` holds the company list.
  - `boards/<source>-<slug>.json` holds each board's postings, reused for 24 h.
  - Only 404s are cached as failures.
  - Writes go through a temporary file plus `os.replace`.
  - Corrupt or foreign files count as misses.
- **Country filter**:
  - Ashby's `address.postalAddress.addressCountry` (primary and secondary locations)
    becomes `Posting.countries`, normalized ("USA" → "United States").
  - `posting_countries` adds place names found in the location text: US states and
    cities, about 20 countries, and Europe/APAC/LATAM regions. New Mexico ≠ Mexico,
    and lowercase "us" is not a country.
  - `--country` drops postings known to be elsewhere. Postings naming no country are
    kept and printed as "country not stated".
- **Posting age default 90 → 30 days**, at the user's request. `--max-age-days 90` brings
  older, still-open roles back.
- **Not built** (recorded in decision 0007):
  - Wayback CDX fallback (slow, junk-heavy; the stale cache covers outages)
  - Greenhouse discovery
  - Getro VC job boards
  - Workable / SmartRecruiters

## Evidence

- Offline: `.venv/bin/python -m pytest -q packages/agent_runtime/tests/test_job_coverage.py`:
  52 passed (`httpx.MockTransport`, fake clock, `tmp_path`). Full suite
  `.venv/bin/python -m pytest -q packages services`: 783 passed, 4 skipped.
- Live probes before building:
  - CC-MAIN-2026-43 has 1 index page for Ashby: ~3,800 URLs, 944 companies.
  - 150 random slugs fetched in 3 s: 141 live, 9 returned 404, 15 filtered matches.
  - Ashby's `isRemote` is true on Hybrid jobs, so `workplaceType` wins.
- Live run 1 (pre-split code, crawl inline, 90-day age):
  `find_jobs.py --resume <user's resume> --search "ai engineer" --crawls 6 --hn-months 12 --country "united states" --no-senior --max-years 3`.
  - Crawls 43 and 34 gave **3,137 Ashby companies**. Crawls 39, 30, 25 and 21 each
    failed with HTTP 504 four times in a row, about 6 minutes per failure. This is
    what motivated the budget and the background split.
  - 3,278 boards → 40,684 postings in **1,003 s** with no cache. 411 boards were
    unavailable (408 returned 404, 2 timed out, 1 was over the size limit).
  - **306 matches** (HN alone gave 12 earlier). 11 had no stated country.
    Xbow passed correctly: one of its 12 locations is "US East Coast".
- Live run 2 (current code, from cache, 30 days): same search. 3,275 boards came from
  the cache and 3 were fetched, **16 s total**: 21,873 postings, **133 matches**.
  - The top results are US AI-engineer roles (Commure, Blumen, Orbital, Blossom Health,
    Brainco, Clera, Coast, Skylo).
  - Results are saved in the ignored `.demo-artifacts/jobs-ranked-*.json`.
- `scripts/refresh_job_companies.py` was **not run live yet** (unit tests only).
  The saved list came from run 1.

## Open issues and next action

1. **Run the refresh**, in the background, to retry the 4 crawls that failed. The list
   should grow beyond 3,137. Command: `nohup python scripts/refresh_job_companies.py > .cache/jobs/refresh.log 2>&1 &`.
2. **Cache size: 354 MB**, mostly descriptions of up to 20k characters each. Fine
   locally; revisit with the Postgres move.
3. **Off-target titles** still pass the title filter, for example "Sales Engineer,
   Ambient AI". An exclude list (sales/support/solutions) is a small follow-up, as is
   the "Claude/Anthropic API" false gap.
4. **Only 3 locations print per row.** A US location further down the list (Xbow) is
   hidden; print the location that matched first.
5. **A first fetch without cache takes ~17 minutes** for ~3,300 boards. The background
   refresh could also prefetch boards.
6. User answers (November 17, 2026): the 30-day age default and keeping postings with
   no country are confirmed. **HN is now off by default** (`--hn-months 0`), so Greenhouse
   and Lever boards appear only with `--hn-months N` or `--boards-file` until Greenhouse
   discovery is added.

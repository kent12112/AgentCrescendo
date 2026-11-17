# Handoff: JOB-F00 — ATS posting sources

- Date/time and timezone: November 17, 2026, America/New_York.
- Author / session: Claude, VS Code session; no delegation.
- Intended recipient: the user (review requested); not an assignment.
- Base commit: `e8843ca`; earlier W1X/W2/JOB-F01 work is still uncommitted in the tree.
- Uncommitted paths (this task):
  - New: `packages/agent_runtime/crescendo_agent/job_sources.py`,
    `packages/agent_runtime/tests/test_job_sources.py`, `scripts/fetch_jobs.py`,
    this handoff.
  - Changed: `docs/decisions/0007-job-search-scenario.md` (update section),
    `docs/implementation-plan.md` (JOB-F00, JOB-F02), `docs/status.md`.
- State: complete for its stated check; ready for review.
- Ownership: released.

## Goal and acceptance criteria

Find postings without a search engine. Given `source:company` boards, fetch every
public posting from the ATS's own listing API and normalize it for matching
(JOB-F02). Acceptance: offline tests covering every response shape and failure,
plus one live fetch across all three platforms.

## Changes and decisions

- **`job_sources.py`**:
  - `CompanyBoard.parse("lever:palantir")` validates the slug before it enters a
    URL; slashes, `..`, queries, and unknown sources are refused.
  - `fetch_board` streams with a 20 s timeout and a 32 MB cap (largest seen
    ~15 MB), and doesn't follow redirects. It returns `BoardResult(error=...)`
    instead of raising.
  - `normalize` maps each ATS to one `Posting` shape: title, locations,
    workplace, department, type, published (UTC), compensation, and plain-text
    description (capped at 20k characters).
- **URLs are rebuilt**, never copied from responses: `job-boards.greenhouse.io/<slug>/jobs/<digits>`,
  `jobs.lever.co/<slug>/<uuid>`, `jobs.ashbyhq.com/<slug>/<uuid>`. A response's
  `absolute_url`/`jobUrl` can point anywhere, for example a company careers site,
  or a hostile one in the test fixture.
- **HTML → text** uses the standard library `HTMLParser`. It drops
  script/style, turns list items into `- ` lines, and unescapes Greenhouse's
  double-escaped `content`.
- **Skipped items**: Ashby `isListed: false`, blank titles (one seen live in
  OpenAI's board), malformed IDs, and duplicates are counted as `skipped`.
- **Placement**: the module is in `crescendo_agent` to avoid packaging changes.
  It is host-side and doesn't touch E2B. If a jobs service appears, it can move.

## Evidence

- `.venv/bin/python -m pytest -q packages/agent_runtime/tests/test_job_sources.py`: 31 passed
  (`httpx.MockTransport`, no network).
- `.venv/bin/python -m pytest -q packages services`: 683 passed, 4 skipped.
- Live, public APIs, no keys:
  `.venv/bin/python scripts/fetch_jobs.py greenhouse:anthropic lever:palantir ashby:openai greenhouse:no-such-board-xyz --title-contains engineer --show 3`
  - Greenhouse: 659 postings (232 engineer).
  - Lever: 301 (186).
  - Ashby: 839, with 1 skipped (blank title, confirmed).
  - Missing board: "No public job board with that name (HTTP 404)."
  - The companies were probe examples, not the user's choices.

## Open issues and next action

1. **Company list.** None exists yet. The user will name companies or describe
   the kind they want, and Claude finds each one's ATS and slug (a wrong guess is a
   harmless 404). `--boards-file` takes one `source:company` per line.
2. **Not covered**: Lever's EU host (`api.eu.lever.co`), Workable, SmartRecruiters,
   Recruitee, Workday; parallel fetching; caching (a 50-company list is about
   50 requests and up to several hundred MB per run, so cache before matching
   runs often).
3. **Next: JOB-F02.** Resume → reviewed profile, then rank postings on full text
   with matched requirements and gaps. Needs the resume path from the user.

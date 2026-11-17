# Handoff: JOB-F02 — find and rank jobs for a resume

- Date/time and timezone: November 17, 2026, America/New_York.
- Author / session: Claude, VS Code session; no delegation.
- Intended recipient: the user (review requested); not an assignment.
- Base commit: `e8843ca`; earlier W1X/W2/JOB work is still uncommitted in the tree.
- Uncommitted paths (this task):
  - New: `packages/agent_runtime/crescendo_agent/company_discovery.py`, `resume.py`,
    `job_match.py`, `packages/agent_runtime/tests/test_job_match.py`,
    `scripts/find_jobs.py`, this handoff.
  - Changed: `job_sources.py` (parallel `fetch_boards`, `workers=8`),
    `pyproject.toml` (`jobs` extra: pypdf, httpx), `requirements-dev.lock`
    (`pypdf==6.21.4`), `docs/implementation-plan.md`, `docs/status.md`.
- State: ready for review; not complete until a run on the user's real resume.
- Ownership: released.

## Goal and acceptance criteria

The user's flow: upload a resume, type a search such as "applied ai engineer", and get
relevant jobs ranked by a match score against the resume's keywords. Each job
shows a link, score, and job-search details. The user must not have to keep a
company list.

## Changes and decisions

- **Company discovery** (`company_discovery.py`). The latest N (default 3) "Ask HN:
  Who is hiring?" threads come from the official Algolia HN API. Only links shaped
  like Greenhouse, Lever, or Ashby boards are kept, each slug passes
  `CompanyBoard.parse`, and responses are capped at 8 MB. An optional
  `--boards-file` adds boards. Public ATS company lists and a paid search API stay
  deferred.
- **Resume** (`resume.py`). Reads PDF (pypdf), .txt, or .md locally; at most 10 MB,
  10 pages, 50k characters. Scanned PDFs with no text are reported, not guessed.
- **Ranking** (`job_match.py`). Local and deterministic, with no model, so it is free,
  private, and every score can be explained:
  - The `SKILLS` vocabulary (~85 skills, regex) is applied to the resume and to
    each posting.
  - `IMPLIES` adds skills a resume demonstrates without naming, e.g.
    RAG/OpenAI → LLMs, PyTorch → deep learning. It applies to the resume side only.
  - Title match is the share of search words in the title, with small synonym
    sets (ai ~ ml/llm, engineer ~ developer). Postings below 0.6 are dropped.
  - Score = 30% title + 70% × matched / (job skills + 2). The +2 keeps thin
    evidence (4 of 5 skills) from outranking strong evidence (10 of 13). Found in
    the first live run.
  - Also shown: years asked ("N+ years … experience" within one sentence),
    location, workplace, pay, and age. Filters: `--location`, `--remote`, and
    `--max-age-days` (default 90; a 333-day-old posting ranked #2 before this).
- **Privacy**: no resume text or search words leave the machine. Only the HN and ATS
  listing APIs are called, with fixed URLs.

## Evidence

- `.venv/bin/python -m pytest -q packages/agent_runtime/tests/test_job_match.py`: 25 passed.
  - Covers discovery parsing and failures, txt/pdf/bad files, and skill
    false-positive cases ("go to market", "insurance agents", "swift delivery",
    JavaScript ≠ Java).
  - Covers ranking, filters, and smoothing.
- `.venv/bin/python -m pytest -q packages services`: 708 passed, 4 skipped.
- Live, with a **fictional** sample resume (scratchpad, not committed):
  `scripts/find_jobs.py --resume sample_resume.md --search "applied ai engineer"`.
  - HN November/October/September 2026 gave 78 boards and 2,526 postings in 6–26 s.
  - With the 90-day filter: 1,624 postings, 54 title matches.
  - The top results were plausible applied-AI roles with explained matched skills
    and gaps.
- These are not evidence that the ranking suits the user. That needs their resume
  and their judgment.

### Run on the user's real resume (November 17, 2026)

The resume was read locally and is not copied into the repository. Findings and fixes:

- **Vocabulary gaps.** The first pass found 25 skills and missed Temporal, event-driven,
  observability, Bedrock, application security, Supabase, database design, React
  Native/iOS, payments, workflow automation, and Japanese. These were added as tight
  patterns with false-match tests ("Join Stripe!" is not payments work; "Bios" is
  not iOS). The resume now maps to 38 skills.
- **Unhelpful default list.** It was dominated by Senior/Lead roles asking 5+ years,
  roles abroad, and one role repeated per country. Added `--no-senior`,
  `--max-years`, repeatable any-of `--location`, and one row per
  (company, title) with all locations (`group_duplicates`). "Observability" matching
  many AI postings was checked against the text and is genuine ("evaluation,
  testing, and observability for AI systems").
- **Coverage is the bottleneck.** `--search "applied ai engineer"` with New York/US
  locations, `--no-senior`, and `--max-years 3`:
  - 3 HN months (78 boards): 1 match.
  - "ai engineer" over `--hn-months 12` (239 boards, 6,156 postings, 25 boards
    gone): 8 relevant New York/US roles, including an AI engineering internship.
  - The HN search page now asks for 40 hits so 12 months yields 12 threads (it
    also lists "wants to be hired" threads).
- Tests: 37 in `test_job_match.py`; full suite 720 passed, 4 skipped.

## Open issues and next action

1. **Company coverage**, the main limit for early-career AI roles in the US. Next options:
   a public ATS company list (free, needs a quality check), a curated NYC/AI company
   file via `--boards-file`, or a paid search API.
2. Keyword scoring cannot judge depth, seniority fit, or visa/location
   constraints beyond text filters. An optional model re-rank of the top N
   (on the host, showing what it would send) is a possible later step, and would
   send resume text to a provider, so it needs the user's consent.
3. Seniority comes from title words and "N+ years" text only; roles that state
   neither are kept.
4. HN covers mostly startups (~80 boards per 3 months). Coverage grows with
   `--boards-file` or a public ATS company list.
5. Not yet visual: the result is terminal plus JSON. The desktop agent opening the top
   postings (JOB-F01) and a results page are the visual steps.

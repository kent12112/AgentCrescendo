# Handoff: JOB-F03 job picker

- Date/time and timezone: November 17, 2026, evening EST
- Author / session: Claude (VS Code session)
- Intended recipient: the user, for review; not an assignment
- Base commit: `e8843ca`
- Change commit(s), or uncommitted paths: uncommitted
  `packages/agent_runtime/crescendo_agent/job_picker.py`, `scripts/pick_jobs.py`,
  `packages/agent_runtime/tests/test_job_picker.py`, plan, status, this handoff.
  Decision 0009 written in the same session.
- State: ready for review
- Ownership: released

## Goal and acceptance criteria

[Decision 0009](../decisions/0009-cover-letter-redacted-resume.md): the user picks up
to 3 ranked jobs per session, and each gets research and one cover letter. The picker
turns a `find_jobs.py --json` file into a checked selection that the researcher
(JOB-F04) and the writer (JOB-F05) read. Acceptance: offline tests, and a run against
real ranked lists in which no real posting is wrongly refused.

## Changes and decisions

- `job_picker.py` (pure, no network):
  - `posting_ref` accepts a URL only in the exact Greenhouse, Lever, or Ashby
    posting shape: https, known host, no query, fragment, port, or credentials,
    valid slug, ID digits (Greenhouse) or UUID (Lever, Ashby). Rebuilding the URL
    from the extracted board and ID must give the same URL.
  - Later steps fetch the posting again from that board and ID, so they never
    trust a URL from the file.
  - `clean` strips control and bidi characters and bounds length before any
    untrusted title, company, or location reaches the terminal (ANSI escape
    injection).
  - `parse_choice` accepts "1 4 7" or "1,4". It refuses non-numbers, rows not
    shown, duplicates, rows with failed links, and more than 3. The count is
    checked first, because it is the most useful message.
- `scripts/pick_jobs.py`: uses the newest `.demo-artifacts/jobs-ranked-*.json`
  (or `--ranked`) and shows the top 10 (`--show`).
  - Interactive prompt with 3 attempts, or `--pick` without a prompt (a bad
    `--pick` fails at once).
  - Enter or end of input cancels.
  - Saves `.demo-artifacts/jobs-picked-<id>.json` with the search, the source
    file, the time, and each job's rank, score, title, company, where, pay,
    skills, source, board, posting ID, and URL.
- Not changed: `find_jobs.py`, which has another session's uncommitted edits.
  The ranked JSON has no posting text, so F04/F05 must fetch the posting by board
  and ID.

## Evidence

Local only:
- `pytest packages/agent_runtime/tests/test_job_picker.py`: 45 passed.
- Full suite: 859 passed, 4 skipped.
- Real data: all 9 saved ranked lists → 779 rows (Ashby, Greenhouse, Lever), **0
  refused** by the URL check.
- `pick_jobs.py --ranked <real file> --show 5 --pick ""` printed five real
  matches and exited 1 ("Nothing picked; nothing saved").
- Not exercised by hand: the interactive prompt in a real terminal (tests use a
  fake stdin).

## Open issues and next action

- The user tries `python scripts/pick_jobs.py` interactively.
- Next: JOB-F04 company researcher, which reads `jobs-picked-*.json`.
- Possible later step: a "fetch one posting by board and ID" helper in
  `job_sources.py`, needed by F04/F05.

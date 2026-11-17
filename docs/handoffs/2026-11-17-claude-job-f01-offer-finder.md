# Handoff: JOB-F01 — offer finder

- Date/time and timezone: November 17, 2026, America/New_York.
- Author / session: Claude, VS Code session; no delegation.
- Intended recipient: the user (review requested); not an assignment.
- Base commit: `e8843ca`. W1X-F02/F03, W1-F10/F13, and W2-F01 work is still
  uncommitted in the same tree.
- Uncommitted paths (this task):
  - New: `packages/agent_runtime/crescendo_agent/offers.py`,
    `packages/agent_runtime/tests/test_offers.py`,
    `scripts/e2b_offer_finder_demo.py`, `scripts/smoke_offer_links.py`,
    `docs/decisions/0007-job-search-scenario.md`, this handoff.
  - Changed: `link_grounding.py` (`LINK_RECORDS`), `e2b_desktop.py`
    (`link_records()`), `docs/architecture.md` (scenario, acceptance item 1–2),
    `docs/implementation-plan.md` (job-search track, W4-F07), `docs/status.md`.
- State: ready for review; live demo not yet run.
- Ownership: released.

## Goal and acceptance criteria

First slice of the job-search scenario ([decision 0007](../decisions/0007-job-search-scenario.md)).
On a public company board, the model finds up to N postings that match a
one-line request. Every returned offer must be a posting link the browser
showed on that board. Titles and URLs come from the page, never the model.
Acceptance: offline tests, local Edge smoke, then live demo passes on Greenhouse
and Lever with the user watching.

## Changes and decisions

- **`E2BDesktop.link_records(ids)`**: host-only. It evaluates `LINK_RECORDS` on the
  current link snapshot and returns label, href, and desktop point for IDs in that
  snapshot. The model's view (`LINK_LABELS`) is unchanged, and the `visible_links()`
  call order is untouched, so existing snapshot tests are unaffected.
- **`offers.py`**:
  - `board_from_url` accepts https Greenhouse/Lever board roots only, with no
    query.
  - `posting_company` matches strict path patterns: Greenhouse
    `/<slug>/jobs/<digits>`, Lever `/<slug>/<uuid>`, not `/apply`.
  - `is_generic_label` refuses button words.
  - `parse_offer_answer` requires strict JSON. Its errors say how to fix the
    answer and go back to the model as denials.
  - `offer_validator` is a `finish_validator` that fills `accepted` with trusted
    records.
  - `offer_goal` builds the task text.
- **Demo**:
  - Grant: screenshot, scroll, click, read_visible_links, finish in public-web
    mode. No navigate and no type_text.
  - A startup check needs at least one posting link on the first screen before
    any model call.
  - `--save-screenshots` writes step PNGs, `evidence.png` (full resolution, so
    `screen_point` matches it), and `offers.json`.
- **Found by the smoke check**: Lever's APPLY button href is the posting URL itself.
  This is why labels are checked as well as destinations.

## Evidence

Local:

- `.venv/bin/python -m pytest -q packages/agent_runtime/tests/test_offers.py`: 49 passed.
  - Covers parsing and refusals.
  - Covers board/posting patterns, including lookalike hosts and `/apply`.
  - The real `run_vision_agent` loop refuses an APPLY citation, the model sees
    the denial, and the corrected answer is accepted.
  - Invented IDs are never accepted.
  - Covers demo grading.
- `.venv/bin/python -m pytest -q packages services`: 652 passed, 4 skipped (the existing
  Starlette warning).
- `.venv/bin/python scripts/smoke_offer_links.py` (local Edge, scripts off,
  GET Document/Stylesheet only, real public boards):
  - Greenhouse `anthropic`: 3 visible links, all postings.
  - Lever `palantir`: 10 visible links, of which 5 are postings and 5 APPLY
    buttons refused.
  - The boards were examples for the probe, not a choice of employer.
- A board render probe (scratch script, not committed) gave the results recorded
  in decision 0007.

Live: none.

## Open issues and next action

1. **Live run** (metered E2B + Groq):
   `.venv/bin/python scripts/e2b_offer_finder_demo.py --board <board> --looking-for "<request>" --watch --save-screenshots`
   Run once on Greenhouse and once on Lever. First live tests of:
   - whether the model follows the JSON finish format;
   - whether it cites title links rather than APPLY buttons;
   - how Greenhouse looks on E2B. Only 3 postings fit on the first screen, so
     the model must scroll.
2. Labels can run fields together (Lever's `FULL-TIMELONDON`), because
   `innerText` doesn't add spaces between inline blocks. This is cosmetic, and
   cards may want title-only text later.
3. Only offers on the current screen can be cited (the model sees only the latest
   list). If live runs show good matches being lost while scrolling, consider
   keeping earlier snapshots host-side.
4. Not covered: board filters and search (Greenhouse dropdowns need scripts),
   pagination, and multiple boards per run.

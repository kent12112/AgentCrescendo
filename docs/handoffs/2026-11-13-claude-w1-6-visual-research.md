# Handoff: W1-6 / W1-F09 — visual research on a public page

- Date/time and timezone: November 13–14, 2026, night (America/New_York).
- Author / session: Claude (Claude Code, VS Code session).
- Intended recipient: next Claude or Codex session; review requested, not an assignment.
- Base commit: `1949422` on branch `claude/w1-f07-vision-scroll`.
- Change commit(s), or uncommitted paths: see `git log` after this handoff's commit.
- State: complete; reviewed file by file with the user.
- Ownership: released.

## Goal and acceptance criteria

Plan W1-F09: navigate a permitted public page, observe screenshots, model-selected
scrolling, fresh observation, and a source-supported cited answer while the user
watches; record which tools supplied the answer evidence.

## Changes and decisions

- New `scripts/e2b_visual_research_demo.py`: host navigates to the Wikipedia Boston
  article; the model (scroll/finish only) answers the infobox GNIS feature ID.
  Pass = correct value, value present in the article text, and value drawn in the
  viewport at finish (browser layout check, never shown to the model). Citation =
  the page URL the host opened (user accepted). Stops with "SOURCE UNAVAILABLE"
  and no model calls if the article is missing (e.g. Wikipedia "Too many requests").
- `e2b_desktop.py`: request filter also continues GET stylesheets from permitted
  hosts (reverses an earlier deliberate block; user approved); `navigate()` waits
  for `load`; `open_e2b_desktop(lifetime_seconds=180)` configurable 60–600.
- `vision.py` / `vision_loop.py`: `downscale()` to a chosen width (saved PNG = model
  input); `RateLimited` keeps only the delay (provider text contains the org id);
  one bounded retry per step (≤15 s, within deadline) else status `rate_limited`;
  every tool asks for a `reason`, separated from the arguments before the gateway
  and recorded as untrusted display text (`Proposal`).
- `wait_for_viewer` moved to `live_view.py` and shared by both demos.
- `pyproject.toml`: Pillow declared in the `e2b` extra.
- Docs: decision 0001 (positioning vs Opticon, clicking, broad browsing order, no
  credentials); learning note 11; plan F09 checked and follow-ups W1X-F01/F02 added.

## Evidence

- `.venv/bin/python -m pytest -q` → 239 passed; `git diff --check` clean.
- Live (Claude): PASS `research-48e2…` (no reasons yet); PASS with reasons
  `research-e1b7…` (88.5 s agent time, 3 waits totalling 26 s). Failures seen:
  Groq 429 on step 3 before the fixes (`research-d037…`); Wikipedia error page
  (`research-a143…`), which led to the source check.
- User-watched live run: `research-dbe8…`, PASS `617565`, 82.4 s, waits 6/7/8 s.

## Open issues and next action

- Annotated reading copies are stale; refresh after review.
- Downscaling may hurt small-text reading on other pages; one page, one question.
- Wikipedia may throttle E2B's shared addresses; tests should tolerate it.
- Next: W1-3 network checks (gate for W1X-F02), then W1X-F01 clicking.

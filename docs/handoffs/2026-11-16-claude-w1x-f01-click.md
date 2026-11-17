# Handoff: W1X-F01 — click(x, y) with the real pointer

- Date/time and timezone: 2026-11-16, ~23:15 UTC
- Author / session: Claude (Claude Code, VS Code)
- Intended recipient: the user for review; Codex for optional review (not an assignment)
- Base commit: `f337055`
- Change commit(s), or uncommitted paths: uncommitted —
  `packages/security/crescendo_security/policy.py`, `packages/security/tests/test_policy.py`,
  `packages/agent_runtime/crescendo_agent/{desktop,e2b_desktop,vision,vision_loop}.py`,
  `packages/agent_runtime/tests/test_click.py` (new), `scripts/e2b_click_check.py` (new),
  `scripts/e2b_click_demo.py` (new), `docs/e2b-clicking.md` (new), `docs/status.md`,
  `docs/implementation-plan.md`, this handoff.
- State: in progress. Security acceptance is met live; the model-selected live case is not.
- Ownership: retained by Claude pending the user's decision below.

## Goal and acceptance criteria

[Plan W1X-F01](../implementation-plan.md): `click(x, y)` with the real desktop
pointer, authorized only inside the browser page area; every resulting request
still passes the browser filter and E2B firewall. Tests: click outside the page
area denied, POST form blocked, link to a blocked host blocked, download blocked.
Live case: follow a link between two pages.

## Changes and decisions

Full design and evidence: [clicking](../e2b-clicking.md). Key decisions:

- **Page area is a measured constant**, `(0,114)–(1024,700)`, used only while
  Chrome's window and viewport match the measurement. Calculating it from
  JavaScript was 7 px off. The bottom stops above a desktop dock that can launch a
  terminal.
- **Gateway** (`authorize(..., click_area=)`) checks the coordinates. The **adapter**
  checks what is under the point and refuses new-tab, download, frame, and
  image-map targets. Probes showed new tabs bypass our per-tab request filter and
  that `--block-new-web-contents` does not stop them.
- **Backstop** closes and records any new tab anyway. It is second line only: the
  tab's first request has already gone out.
- **Waiting uses Playwright calls**, never `time.sleep`; otherwise the request
  filter never runs and the tab hangs. Completion is the tab's navigation event,
  not a URL change. That bug was found live (two error pages share one URL).
- **Click tool is opt-in** (`GroqVision(allow_click=True)`), so the F07/F09
  demos keep their tool sets. The loop scales coordinates from the image the model
  saw to screen pixels and records both.
- **Grid overlay** (`grid=True`) was added at the user's choice to help the model
  aim. It did not help in two live runs.

## Evidence

Local: `.venv/bin/python -m pytest -q`, 311 passed (59 new, including gateway,
target check, adapter flows, coordinate mapping, and grid).

Live, model-free (`scripts/e2b_click_check.py`, run by Claude): run 1 failed on
the POST case (completion bug above, then fixed); run 2 passed all 12 checks
(table in the doc). Live probe screenshots and logs are in the session scratchpad
only, not committed.

Live, model (`scripts/e2b_click_demo.py`): 4 runs, all failed. In each run the
pointer went exactly where the model asked, but the model aimed 40–150 px off the
link, or at the wrong element. Every run hit Groq's rate limit after two or three
calls. Screenshots are in ignored `.demo-artifacts/click-*`.

## Open issues and next action

1. **User decision:** how to get a model-selected click to pass. Options:
   (a) numbered links: the model picks a number and we click that link's center;
   reliable, but it changes the tool from raw `click(x, y)`;
   (b) another vision provider with better pointing; this overlaps W1-F12;
   (c) accept the security evidence and record the model case as a known
   limitation.
2. The Groq rate limit allows only two or three screenshot steps per run. Any
   model-driven Week 1 work (W1-F12 too) needs a higher limit or longer waits.
3. W1X-F02: the request filter's host check goes through the `navigate` tool rule.
   A click-only grant would block every page load.

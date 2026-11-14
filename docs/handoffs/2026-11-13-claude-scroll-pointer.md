# Handoff: Scroll targets the real desktop pointer

- Date/time and timezone: November 13, 2026, evening (America/New_York).
- Author / session: Claude (Claude Code, VS Code session).
- Intended recipient: next Claude or Codex session; review requested, not an assignment.
- Base commit: `9130a21`.
- Change commit(s), or uncommitted paths: uncommitted —
  `packages/agent_runtime/crescendo_agent/e2b_desktop.py`,
  `packages/agent_runtime/tests/test_scroll.py`,
  `docs/learning/09-vision-action-loop.md`, `docs/learning/annotated/`,
  `docs/status.md`, this handoff. Builds on the uncommitted
  [F07 handoff](2026-11-13-claude-w1-f07-model-scroll.md) changes.
- State: complete.
- Ownership: released.

## Goal and acceptance criteria

Found while reviewing F07: `E2BDesktop.scroll()` positioned Playwright's
synthetic mouse, but E2B's `sandbox.scroll` (`xdotool click --repeat N 4|5`)
turns the wheel at the real X pointer. Goal: confirm live, then make scrolling
target page content deliberately.

## Changes and decisions

- New `SCROLL_POINTER = (512, 440)`: screen coordinates in the middle of Chrome's
  page area on the 1024x768 E2B display.
- `E2BDesktop` takes `pointer_provider` (wired to `sandbox.move_mouse`).
  `scroll()` moves the real pointer there, then turns the wheel. It raises
  before any action if either provider is missing. `page.mouse.move` removed.
- Decision: a fixed point, not one computed from the window geometry. Enough
  for one maximized window; revisit if layouts, popups, or clicking are added.

## Evidence

- Live probe (scratch script, one desktop, no model calls): real pointer
  (512, 384) before and after `page.mouse.move(200, 200)`; wheel over the taskbar
  (512, 10) left `scrollY` 0; wheel at (208, 322) scrolled 360 px.
- Local: `.venv/bin/python -m pytest -q` → 196 passed (new: pointer moves before
  the wheel and Playwright's mouse is unused; missing pointer provider fails closed;
  point lies inside the page area). `git diff --check` clean.
- Live: `.venv/bin/python scripts/e2b_vision_agent_demo.py --save-screenshots` →
  PASS, `scroll(down, 5)` then `finish("E1B374")`, 0 denials. In
  `.demo-artifacts/vision-a265df08f98e437c8ab6363cd460c46a/step-02.png` the pointer
  is visible at about (512, 440).

## Open issues and next action

- Fixed point assumes 1024x768 and a single maximized Chrome window.
- Next per status: W1-1 live viewer, then W1-6 public-page visual research.

# Handoff: W1-1 / W1-F08 — live viewer confirmed

- Date/time and timezone: November 13, 2026, evening (America/New_York).
- Author / session: Claude (Claude Code, VS Code session).
- Intended recipient: next Claude or Codex session; review requested, not an assignment.
- Base commit: `149db26` on branch `claude/w1-f07-vision-scroll`.
- Change commit(s), or uncommitted paths: uncommitted — `docs/status.md`,
  `docs/implementation-plan.md`, `docs/learning/09-vision-action-loop.md`,
  `docs/learning/10-live-desktop-view.md`,
  `docs/handoffs/2026-11-13-claude-w1-f07-model-scroll.md` (correction), this handoff.
  No code changes.
- State: complete for the fixture.
- Ownership: released.

## Goal and acceptance criteria

Status W1-1 / plan W1-F08: the authenticated live viewer renders the real
desktop and visibly follows agent actions.

## Changes and decisions

Documentation only. No viewer code was changed: the hop-by-hop probe found no
fault. Corrected the F07 records: the earlier wrong answer was `visual=51,174`
(already in `10-live-desktop-view.md`), not "unexplained".

## Evidence

- Scripted probe (Claude, one desktop, no model, no browser): bootstrap 307 with
  cookie; `vnc.html`/`app/ui.js`/`core/rfb.js` 200; WebSocket accepted
  (`binary`), first bytes `RFB 003.008`. Proves transport to x11vnc, not
  browser rendering or VNC password authentication.
- User-reported live run: `scripts/e2b_vision_agent_demo.py --watch
  --save-screenshots`. The user saw the real desktop before Enter and watched
  the scroll. PASS, answer `57D244`, 0 denials. Artifacts:
  `.demo-artifacts/vision-68ab4aaf488a44959c109ffcc1ac6b13/` (step-02 shows the
  target, pointer at about (512, 440)).
- `.venv/bin/python -m pytest -q` → 196 passed (unchanged code).

## Open issues and next action

- The original "failed to connect" cause was not reproduced; it is unconfirmed.
- Worst-case setup + viewer gate + Enter wait + agent deadline exceeds the
  180-second sandbox lifetime; consider raising the lifetime or shortening waits.
- One user-reported run on a fixture; no repeat or multi-viewer evidence.
- Next: W1-6 (plan W1-F09), visual research on a permitted public page while
  the user watches.

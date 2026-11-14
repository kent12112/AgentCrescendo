# Handoff: Shared development coordination

- Date: November 13, 2026 (America/New_York).
- Author: Codex.
- Intended recipient: Claude or the next Codex session; no assignment accepted.
- Base commit: `584e662`.
- Changes: uncommitted `AGENTS.md`, `CLAUDE.md`, `docs/coordination.md`,
  `docs/status.md`, and `docs/handoffs/` at handoff creation.
- State: documentation setup complete.
- Ownership: released; no application files claimed.

## Changes and decisions

Added shared reading instructions, task ownership and handoff conventions, a
status snapshot, and a reusable template. Existing architecture and weekly plan
remain the design and milestone references. No automatic agent messaging or
background coordinator was introduced.

## Evidence

The working tree was clean at the start. Status was seeded from the current
implementation plan, recorded learning evidence, and baseline validation:
194 Python tests, web TypeScript checking, and production build passed before
`584e662`. These checks were not rerun for this documentation change.

## Next action

Read status, then claim the task requested by the user. The suggested priority is
W1-1, real live-view diagnosis. No agent has accepted that work yet. Read
`docs/learning/10-live-desktop-view.md` before investigating, and distinguish a
working WebSocket transport from successful VNC authentication and screen rendering.

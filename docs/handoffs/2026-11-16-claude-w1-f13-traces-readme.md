# Handoff: W1-5 / W1-F13 — traces, Week 1 decision record, README

- Date/time and timezone: November 16, 2026, America/New_York.
- Author / session: Claude, VS Code session; no delegation.
- Intended recipient: Codex or user; review requested, not an assignment.
- Base commit: `811701a`.
- Uncommitted paths (this task): `docs/week1-traces.md` (new),
  `docs/decisions/0003-week1-outcome.md` (new), `README.md`, `docs/status.md`,
  `docs/implementation-plan.md`, this handoff. The W1-F10 changes from the
  [network handoff](2026-11-16-claude-w1-f10-network-completion.md) are also
  uncommitted in the same tree.
- State: complete.
- Ownership: released.

## Goal and acceptance criteria

W1-F13: annotated successful and failed traces, a Week 1 decision record, and a
README that separates CLI execution from the draft-only dashboard.

## Changes and decisions

- Traces come from saved live runs in the ignored `.demo-artifacts/` folder, not
  new runs. Picked one success (cited research) and two failures of different
  kinds: model aiming (pixel clicks) and provider throttling. Annotations were
  checked against the saved model-input screenshots. The success frame shows
  "GNIS feature ID 617565". In the failed click, the link sat at about (317, 602)
  and the model clicked (309, 448).
- Decision 0003 marks Week 1's exit as **not fully met**, because W1-F12 (the
  model comparison) was deferred by the user. It lists the decisions that carry
  forward and the conditions that reopen them.
- README: the "Current implementation" section is split into dashboard
  (draft-only) and agent (CLI only), with a new table of scripts and the keys
  each needs, and the "Next milestones" line is updated. Script descriptions
  come from each script's own docstring; extras and `.env` loading checked in
  `pyproject.toml` and the scripts.

## Evidence

Docs only. No code changed, no live runs, no tests needed. The facts in the
traces (statuses, times, rate-limit waits, coordinates) are copied from each
run's `result.json`. The "seven later passes" count comes from listing all
saved click runs.

## Open issues and next action

1. W1-F12: the user chooses the second candidate. When it runs, add a
   comparison section to decision 0003, or replace the record with a new one.
2. Screenshots referenced by the traces are local and ignored. If the user
   wants them kept, copy the five or so key frames into `docs/` deliberately.

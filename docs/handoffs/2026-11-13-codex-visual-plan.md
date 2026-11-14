# Handoff: Visual desktop plan and weekly feature tracking

- Date: November 13, 2026 (America/New_York).
- Author: Codex.
- Intended recipient: next Claude or Codex session; no assignment accepted.
- Base commit: `584e662`.
- Changes: uncommitted `docs/implementation-plan.md`, `docs/status.md`, and this handoff; earlier coordination files also remain uncommitted.
- State: documentation complete; ownership released.

## Changes and decisions

The user requested an explicit watchable visual desktop design inspired by the
Jonathan Mo experience they described, plus feature lists for every week.
The plan now describes real desktop streaming alongside the screenshot → model
proposal → authorization → scroll → fresh screenshot loop. It does not assume
details of the referenced person's implementation.

Added stable feature IDs and checkboxes for all six weeks. Checkmarks distinguish
existing implementation/local evidence and user-reported live evidence from open
end-to-end acceptance. Week 1 explicitly includes connecting the currently
separate text research and visual fixture loops; status task W1-6 tracks this gap.
Week 4 integrates live desktop viewing into the dashboard. Clicking/typing remain
outside required release scope to preserve the existing time budget.

## Evidence and next action

Documentation-only change; no application behavior changed or paid calls made.
`git diff --check` passed. A read-only Python check verified relative Markdown
links and 53 unique feature IDs across all six weeks. Next implementation
priority remains W1-1 live-view diagnosis, then W1-2
vision correctness. Do not treat a checklist entry as proof of a live result.

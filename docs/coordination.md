# Shared development workflow

Codex and Claude coordinate through saved repository files. Their chat histories
are separate. These files do not deliver notifications, wake sessions, enforce
locks, or implement the application's planned worker messaging system.

## Shared sources

| Source | Responsibility |
| --- | --- |
| [Architecture](architecture.md) | Design intent, boundaries, and tradeoffs |
| [Implementation plan](implementation-plan.md) | Weekly scope and exit criteria |
| [Status](status.md) | Current evidence, open tasks, owners, and next steps |
| [Handoffs](handoffs/) | Task-specific changes, review requests, and results |
| Code and tests | Actual implemented behavior and reproducible checks |

When documents and code disagree, record the discrepancy and verify behavior.
Do not silently change architecture or mark an exit criterion complete.

## Before editing

1. Read status and the relevant design, plan section, and handoff.
2. Inspect `git status --short` and relevant diffs. Existing changes may belong to
   the user or another agent; preserve them.
3. Claim the requested task in status with your agent name, session identifier
   if available, and files or directories you expect to edit. Do not claim work
   for the other agent. A review request is not an accepted assignment.
4. Re-read status immediately before claiming. If ownership overlaps, coordinate
   through the user before editing those files. Reviewers can inspect code
   without modifying files owned by the implementer.

Prefer one implementer and one reviewer per task. File-based claims are advisory
and are not atomic locks. For simultaneous implementation, use separate Git
branches/worktrees and integrate explicitly. Worktree files are separate copies:
exchange committed handoffs through Git or use an explicitly agreed shared path.
Do not assume a status update in one worktree is visible in another.

## At a handoff

1. Run checks appropriate to the change. Record exact commands, results, and
   what they do not prove; distinguish local mocks, live runs, and user reports.
2. Copy [the handoff template](handoffs/TEMPLATE.md) into a new file named
   `YYYY-MM-DD-agent-task.md`. Use a suffix for multiple handoffs on the same task.
3. Update status with the handoff link and current ownership. Release ownership
   when stopping; leave the task open if acceptance criteria remain unmet.
4. Tell the user which handoff is ready. The receiving agent must be prompted to
   read it; record acknowledgment or review results in a new handoff.

Keep handoffs concise and preserve earlier evidence. Include a base commit and
explicitly identify uncommitted changes. Never include API keys, traffic tokens,
private viewer URLs, or credential-bearing logs. Reference ignored screenshot
artifacts by local path when useful; do not commit them automatically.

Commit and push only within the user's authorized scope. On a shared checkout,
stage specific paths and inspect the staged diff so unrelated work is excluded.
Do not reset, discard, or overwrite another contributor's work.

## Prompt for a receiving session

> Read your repository instructions, docs/coordination.md, docs/status.md, and
> the relevant handoff. Check the current diff. Continue the requested task or
> review it, respect existing ownership, and record your findings and evidence.

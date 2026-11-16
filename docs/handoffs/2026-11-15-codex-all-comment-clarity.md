# Handoff: COMMENT-CLARITY-ALL — repository comment translations

- Date/time and timezone: November 15, 2026, America/New_York.
- Author / session: Codex, current session; no delegation.
- Intended recipient: user / next session; review requested, not an assignment.
- Base commit: `fc3d128`.
- Uncommitted paths: maintained source/tests/scripts/configuration, reading guide,
  status, and this handoff. Earlier demo rewrite and handoff remain uncommitted.
- State: complete.
- Ownership: released.

## Goal and acceptance criteria

Extend the user’s request for direct code translations without Learn labels to
all maintained annotated files, beyond the earlier single-demo rewrite.

## Changes and decisions

Reworked annotations in 76 further tracked files across Python, frontend,
migrations, and supported configuration. Removed Learn labels, closing-delimiter
narration, duplicate docstring explanations, and generic filler. Translated
assignments, conditions, calls, state initialization, and dictionary entries.
Retained external embedded-string and JSX line references to preserve literals.
Clarified sandbox factories and callbacks in open_e2b_desktop. Corrected an old
comment describing httpx.get as a dictionary lookup. Updated the reading guide.
Historical handoffs and generated/vendor/private files remain untouched. Strict
JSON is still explained in the reading guide rather than edited with comments.

## Evidence

Local checks only; no E2B/model calls:
- `.venv/bin/python -m pytest -q`: 239 passed; existing Starlette/httpx warning.
- In apps/web, `npm run typecheck` and `npm run build`: passed. Existing ignored
  parent-directory package-lock warning remains; corrected build has no CSS warnings.
- ast.dump comparisons: all 58 Python files unchanged, including literal values.
- TypeScript transpileModule with removeComments: emitted JS unchanged for 12 files.
- TOML parsed data, other configuration non-comment lines, and CSS rules after
  comment removal unchanged against /tmp/crescendo-comment-rewrite snapshots.
- Source/configuration scan: no Learn labels remain.
- `git diff --check`: passed.

Resolved tooling failures: wrapped CSS comments initially closed too soon,
causing optimizer warnings; corrected boundaries, verified unchanged CSS rules,
and rebuilt successfully. System Python lacked tomllib in comparison attempts;
project Python successfully performed the configuration comparison. No application
test failures. Temporary snapshots are ephemeral; normal tests remain reproducible.

## Open issues and next action

User can continue reading the desktop execution path. Comments are reading aids;
Week 1 live-provider/network gates are unchanged.

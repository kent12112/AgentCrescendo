# Handoff: REFACTOR — codebase organization

- Date/time and timezone: November 14, 2026 (America/New_York).
- Author / session: Codex, current session; no delegation.
- Intended recipient: user / next session; review requested, not an assignment.
- Base commit: `0912552`.
- Change commit(s), or uncommitted paths: README, web app page and features/drafts,
  API main/auth/routes, runtime e2b_desktop/browser_bootstrap, codebase guide,
  status, and this handoff. All changes uncommitted.
- State: complete.
- Ownership: released.

## Goal and acceptance criteria

Make the existing code easier to navigate and understand while preserving HTTP
contracts, draft interactions, runtime entry points, and remote startup behavior.

## Changes and decisions

- API main now assembles routers; auth is a shared dependency; system and draft
  routes have separate modules. Draft transactions remain in the small router.
- Dashboard route mounts a draft feature with separate workspace, list, state/
  request hook, and response types. Existing labels and interactions preserved.
- Moved fixed remote Chrome/CDP startup source strings out of the host adapter.
  Existing imports from e2b_desktop still work.
- Added docs/codebase.md with a tree, reading paths, and change-location guide.
  README now distinguishes the draft dashboard from implemented CLI agents.
- Kept package names, script paths, migrations, security logic, and planned
  infrastructure boundaries stable. No speculative orchestration scaffolding.
- Annotated learning copies remain historical; guide explicitly directs readers
  to live package source. No new functionality or new tests added.

## Evidence

Local checks:
- `.venv/bin/python -m pytest -q`: 239 passed, one Starlette/httpx deprecation warning.
- In apps/web: `npm run typecheck` and `npm run build`: passed, including a second
  run after extracting DraftList. Next warns about an ignored parent-directory
  package-lock.json outside this repository.
- Inline Python comparison against `git show HEAD:...`: all three browser program
  strings match byte-for-byte; original and refactored OpenAPI dictionaries match.
- `git diff --check`: clean.

No live E2B/model calls, PostgreSQL smoke run, or browser interaction run performed.
These checks establish local regression/build evidence, not live provider behavior.
No observed test failures during this refactor.

## Open issues and next action

Review the guide and module boundaries. Existing Week 1 networking, cleanup, and
model-comparison gates remain open; this refactor does not complete them.

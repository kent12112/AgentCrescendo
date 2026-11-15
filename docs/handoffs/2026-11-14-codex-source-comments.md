# Handoff: ANNOTATE — learning comments in executable source

- Date/time and timezone: November 14, 2026 (America/New_York).
- Author / session: Codex, current session; no delegation.
- Intended recipient: user / next session; review requested, not an assignment.
- Base commit: `0912552`, plus the preceding uncommitted refactor documented in
  `2026-11-14-codex-codebase-refactor.md`.
- Change commit(s), or uncommitted paths: application source, tests, scripts,
  migrations, supported configuration, README, codebase/learning guides, status,
  and this handoff. All changes remain uncommitted.
- State: complete.
- Ownership: released.

## Goal and acceptance criteria

User explicitly requested line-by-line explanations directly in executable source
and chose that option over separate reading copies. Preserve behavior and keep
configuration valid while explaining syntax, state, trust boundaries, and effects.

## Changes and decisions

- Added Learn comments throughout all 58 Python source/test/script files and the
  maintained TypeScript/TSX/MJS files, plus CSS and supported configuration.
- Preserved existing comments/docstrings. Blank separators need no annotation.
  Multi-line literal contents are explained by relative line number before the
  literal, preserving embedded remote programs, prompts, HTML, and JavaScript.
  JSX explanations are numbered before each tree so comments cannot become UI.
- Added configuration comments to pyproject.toml, compose.yaml, alembic.ini,
  .env.example, and the Mako migration template.
- Strict JSON does not accept comments; docs/learning/12-commented-source.md
  explains each line of package.json and tsconfig.json instead. Generated files,
  installed dependencies, lockfiles, private config/artifacts, and historical
  reading copies are excluded. Existing historical annotations now link to the
  current guide; they are not presented as current source.
- Linked the reading guide from README and the codebase guide. It explains the
  reading path, annotation numbering, and how to test understanding with cases.
- Temporary annotation helpers/snapshots were kept outside the repository under
  /tmp; they are tooling, not new application functionality.

## Evidence

All evidence is local; no metered E2B/model operations, PostgreSQL smoke run, or
interactive browser flow was performed.

- `.venv/bin/python -m pytest -q`: 239 passed after the final Python annotations;
  one existing Starlette/httpx deprecation warning.
- From apps/web, `npm run typecheck && npm run build`: passed after final frontend
  and CSS annotations. Existing ignored-parent-lockfile warning remains.
- Python AST comparison against the pre-annotation working-tree snapshots:
  all 58 files identical with locations omitted, including all literal values.
- TypeScript transpileModule comparison with removeComments=true: emitted
  JavaScript unchanged for all maintained TS/TSX/MJS source files.
- Inline Python checks: parsed TOML, INI, and example dotenv dictionaries equal;
  CSS equal after removing comments/whitespace; rendered Mako migration ASTs equal
  for both empty and nonempty migration bodies.
- Docker Compose comparison via `docker compose --project-name annotation-check
  --project-directory <repository> -f <before-or-after> config --format json`:
  identical parsed configuration, without starting containers.
- `git diff --check`: clean after removing trailing whitespace in a JSX note.

Observed tooling failures (resolved): the temporary configuration annotator first
mistook >= inside a quoted dependency requirement for an assignment; fixed its
key parsing before writing that file. A validation attempt imported unavailable
PyYAML; used Docker Compose's installed parser instead, without adding packages.
An early comment confused socket select with SQLAlchemy select; corrected during
wording review. No application test failures were observed.

Snapshot comparisons used /tmp/crescendo-annotation-baseline, which is ephemeral;
normal tests/builds remain reproducible through the project commands above.

## Open issues and next action

Read the source through the linked guide and use the matching tests to predict
outcomes. Keep explanations synchronized with code changes. These comments are
learning aids, not independent proof of security or live provider behavior.
Existing Week 1 network, cleanup, and model-comparison gates remain open.

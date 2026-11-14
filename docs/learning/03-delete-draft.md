# Review exercise: delete a saved draft

Date: November 13, 2026

Problem: saving drafts creates durable data, but the API previously had no way to remove an unwanted draft.

Contract: `DELETE /runs/{run_id}` requires the existing local bearer token. It deletes the matching draft, commits the transaction, and returns an empty `204` response. A missing draft returns `404`; a malformed UUID returns `422`. An unauthorized request returns `401` and preserves the draft.

## Implementation decision

Use one `DELETE … RETURNING` statement filtered by both ID and draft status. The returned ID establishes whether the statement deleted a row without a separate existence query. Commit before responding so a successful HTTP response follows the database commit. No schema migration is needed.

Repeated deletion returns `404`. The resulting database state is still idempotent: repeating the operation cannot remove additional drafts. Idempotence does not require identical response codes.

Scope: this removes one database draft. Execution, desktops, artifacts, and multi-user ownership are not connected; their cleanup and authorization need separate designs when introduced.

## Dashboard follow-up

The dashboard now exposes deletion with a native confirmation dialog. It keeps the draft visible until the API confirms deletion or reports it already absent (`404`). Errors preserve the displayed draft and allow retry or refresh. Delete buttons and refresh are disabled while deletion is pending.

The Next.js DELETE route requires the browser-facing origin to match and validates the UUID before constructing the upstream path. The server-only proxy forwards the credential and handles empty `204` responses without trying to parse JSON. This preserves the same local, single-user boundary as creation.

Tradeoff: native confirmation provides built-in keyboard behavior without a custom dialog, but its appearance is browser-controlled. Only one deletion runs at a time. The recent list may contain fewer than 25 drafts after deletion; refresh retrieves older entries.

Verification on November 13, 2026: frontend build and TypeScript checks passed. `scripts/smoke_dashboard_deletion.py` passed in headless Microsoft Edge against the real Next.js server, FastAPI, and PostgreSQL. It verified cancellation, foreign/missing origin rejection, invalid UUID rejection, a simulated failed deletion preserving data and restoring the button, and confirmed deletion persisting after reload. Temporary test data was cleaned up. This does not establish concurrent-tab behavior or all browser compatibility.

## Predicted failures and evidence

The behavioral tests deliberately use absent and incorrect credentials, delete the same ID twice, and submit a malformed ID. They also create two drafts and verify deleting one preserves the other. Follow-up reads use separate HTTP requests to check the committed state, rather than inspecting the endpoint's in-memory objects.

The automated tests run against temporary SQLite databases. All 86 Python tests passed, including the four deletion cases.

On November 13, 2026, a separate smoke test passed against the local PostgreSQL 17 service after `alembic upgrade head`. It used FastAPI's in-process TestClient with the real database session dependency and no dependency overrides. It verified an empty `204` response, committed deletion through a subsequent GET, preservation of a second draft, rejection of unauthenticated deletion with the draft preserved, repeated deletion returning `404`, and a malformed ID returning `422`. Both uniquely identified temporary drafts were cleaned up afterward.

This establishes basic PostgreSQL compatibility, not concurrency behavior, availability during database failures, or browser/network-server integration.

## Your review

Read the new endpoint in `services/api/crescendo_api/main.py` and the deletion tests at the end of `services/api/tests/test_runs.py`.

1. Trace what happens when authentication fails. Can the database mutation run?
2. Identify what restricts deletion to the requested row and what makes the change durable.
3. Explain why a repeated deletion returns `404` but still has an idempotent effect.
4. Check whether the tests would catch deleting every draft or forgetting to commit.
5. Decide whether API-only scope is acceptable for this change. What would a dashboard deletion flow need?

Review with a concrete finding: file/location, triggering input, observed or predicted consequence, and proposed correction. If you approve it, explain which evidence supports your approval.

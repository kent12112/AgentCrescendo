# First slice: from an intention to durable task data

## What you can trace

```text
Browser form
  → Next.js same-origin route
  → authenticated FastAPI endpoint
  → Pydantic validation
  → SQLAlchemy transaction
  → PostgreSQL draft row
  → response and refreshed draft list
```

This is the control plane's foundation. A saved goal is deliberately different from a running workflow: accepting a task must not implicitly grant an agent permission to act.

## Read these pieces in order

1. `services/api/crescendo_api/schemas.py`: input boundary, trimmed goal, bounded integer limits, and rejection of extra fields.
2. `services/api/crescendo_api/models.py`: durable representation and database constraints.
3. `services/api/crescendo_api/main.py`: authentication dependency, create transaction, list/read endpoints, and honest capabilities.
4. `services/api/migrations/versions/0001_runs.py`: explicit schema version rather than silently changing tables at API startup.
5. `apps/web/app/api/backend.ts`: server-only credential forwarding and bounded upstream requests.

## Predict, then test

* Submit `max_workers: 4`. Where should rejection happen? Does any row get inserted?
* Submit `max_workers: true`. Why should a boolean not count as one worker?
* Add `permissions: ["purchase"]` to the request. Why reject it instead of ignoring it?
* Stop and restart the API after saving a draft. Why does the draft survive? What if the state lived in a Python dictionary?
* Stop PostgreSQL and try saving. Confirm the UI reports failure instead of pretending to succeed.
* Submit the same valid request twice. This initial endpoint creates two drafts. How would an idempotency key change the contract, and what should happen if the same key carries a different body?

## Explain the boundaries

Pydantic improves request semantics. Database constraints protect persisted values. Neither currently enforces runtime spending: that needs atomic admission and accounting once agents can execute.

The local API token stays on the server; it is not a production user identity. Same-origin write checks reduce browser cross-origin misuse but do not turn the local proxy into an authenticated multi-user service.

The migration test uses SQLite for convenience. PostgreSQL uses different storage, types, and concurrency behavior; a real PostgreSQL smoke test is still necessary.

## Your hands-on exercise

After running the app, implement a user-provided `constraints` text field end to end: request schema, database migration, response, and form. Decide its length limit, behavior for existing drafts, and whether whitespace-only input is meaningful. Add one behavioral test that captures your decision. Explain why editing the ORM model alone does not migrate an existing database.

Do this exercise after inspecting the current slice; it is intentionally not preimplemented.

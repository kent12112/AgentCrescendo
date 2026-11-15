# Codebase guide

For the line-by-line comments now in the executable source, see the
[commented-source reading guide](learning/12-commented-source.md). It explains
annotation conventions, the reading order, and strict JSON configuration.

The repository has two working entry paths: persisted task drafts in the dashboard,
and standalone desktop-agent demos. They are not connected to each other yet.
The architecture describes the intended system; status records implemented evidence.

## Structure and responsibilities

```text
apps/web/
  app/                        Next.js route entry points, layout, global styles
    page.tsx                  Mounts the draft workspace
    api/                      Server-side proxy; keeps the API token off the client
  features/drafts/
    workspace.tsx             Draft form and page layout
    draft-list.tsx            Loading, empty state, and saved draft rendering
    use-drafts.ts             Form state, HTTP requests, notices, create/delete flow
    types.ts                  Client response type (not runtime validation)
services/api/
  crescendo_api/
    main.py                   FastAPI app and router registration
    auth.py                   Shared local bearer-token dependency
    routes/system.py          Health and dashboard capabilities
    routes/runs.py            Draft create/list/read/delete endpoints
    schemas.py                Pydantic request/response contracts
    models.py                 SQLAlchemy table definitions
    database.py               Engine and request-scoped sessions
    config.py                 Validated settings
  migrations/                 Alembic history; do not rewrite applied migrations
  tests/                      API contract and migration checks
packages/
  agent_runtime/crescendo_agent/
    loop.py, vision_loop.py   Bounded text and screenshot observe/act loops
    model.py, groq_model.py   Text model contract and Groq adapter
    vision.py                 Screenshots, vision proposals, Groq vision adapter
    desktop.py                Text observations and tool gateway
    e2b_desktop.py            Policy-filtered browser, desktop actions, lifetime
    browser_bootstrap.py      Fixed remote Chrome/CDP startup programs
    page_search.py            Bounded text passage search
    live_view.py              Authenticated local desktop-view proxy
    e2b_preflight.py           Provider networking checks
    local_env.py              Local CLI environment loading
  security/crescendo_security/
    policy.py                 Task identity, capabilities, destination checks
scripts/                      Runnable demos, setup, smoke checks
  e2b_visual_research_demo.py  Public-page screenshot research example
  e2b_vision_agent_demo.py     Controlled model-selected scroll fixture
  groq_e2b_demo.py             Text research example
  smoke_*.py                  Explicit integration checks (not pytest discovery)
docs/                         Design, plan, evidence, learning notes, handoffs
```

Tests live beside their Python package in `tests/`. `pyproject.toml` discovers all
three packages and test directories. Keep the existing package names and run
scripts from the repository root after installing the project.

## Read the dashboard path

1. `apps/web/app/page.tsx` mounts `features/drafts/workspace.tsx`.
2. `use-drafts.ts` sends same-origin requests to `/api/runs`.
3. `app/api/runs/` uses `app/api/backend.ts` to forward authenticated requests.
4. `crescendo_api/main.py` registers the system and draft routers.
5. `routes/runs.py` validates through `schemas.py` and persists through
   `models.py` and `database.py`.

Draft deletion remains a single conditional database statement. Authentication
is attached to the whole runs router so each draft endpoint requires the token.
`/health` remains public; `/capabilities` requires authentication.

## Read the agent path

Start at `scripts/e2b_visual_research_demo.py`, then follow `vision_loop.py`,
`vision.py`, `desktop.py`, `policy.py`, and `e2b_desktop.py`. The demo configures
permissions and owns the run; the loop requests model proposals; authorization
checks whether an action can execute; the adapter performs desktop operations.
Model reasons and page content remain untrusted data.

`browser_bootstrap.py` contains Python source strings executed inside the remote
sandbox. Keeping them separate makes the host adapter easier to read without
changing the remote programs. Their existing imports through `e2b_desktop` remain
available. The adapter owns sandbox/browser cleanup.

## Where to make changes

| Change | Start here |
| --- | --- |
| Draft fields or limits | API `schemas.py`, `models.py`, migrations, web draft types/form |
| Draft UI | `features/drafts/workspace.tsx` and `draft-list.tsx` |
| Draft loading/saving/deletion | `features/drafts/use-drafts.ts` |
| HTTP behavior | API `routes/`, with API tests |
| Model prompts or proposal parsing | `groq_model.py` or `vision.py` |
| Agent stop/retry behavior | `loop.py` or `vision_loop.py` |
| Tool authority or permitted destinations | Security `policy.py` and its tests |
| Browser filtering or desktop actions | `e2b_desktop.py` and runtime tests |
| Actual live evidence | Explicit smoke scripts and task-specific handoffs |

Run `.venv/bin/python -m pytest -q` from the root, then `npm run typecheck` and
`npm run build` from `apps/web`. These local checks do not prove live E2B networking
or provider cleanup. Live demos consume provider resources; follow their linked
learning notes and keep credentials and viewer URLs out of saved evidence.

Annotated files under `docs/learning/annotated/` are historical reading copies,
not imported modules. Use the package source above for current behavior.

## Refactor decisions

Keep the existing top-level application/package boundaries and executable script
paths. Split concrete responsibilities rather than adding layers for planned
Temporal workers or moving persistence before it is shared. Keep draft HTTP
transactions inside the small resource router for now. Existing tests cover the
moved behavior; no new behavior is introduced by these extractions.

# AgentCrescendo

A general-purpose workspace where agents operating isolated computers coordinate everyday tasks. Built as a learning project focused on applied AI, reliable distributed execution, and externally enforced agent permissions.

**Current implementation: local task drafts.** The dashboard submits a goal and limits to FastAPI, which persists the draft in PostgreSQL. Execution, E2B desktops, Temporal, messaging, automatic retention, and model calls are not connected yet. There are no simulated agent runs or invented results.

## Run locally

Requirements: Python 3.11+, Node.js 20.9+, Docker Desktop running, and enough free disk space for dependencies and a PostgreSQL image. No model or E2B keys are needed for this slice.

From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.lock
pip install --no-deps -e .
python scripts/setup_local.py
docker compose up -d db
alembic upgrade head
uvicorn crescendo_api.main:app --host 127.0.0.1 --port 8000 --reload
```

On this machine, Python 3.11 is available at `/Users/kento/anaconda3/bin/python3.11`; the default `python3` is 3.9 and is too old for this project.

In a second terminal:

```bash
cd apps/web
npm install
npm run dev
```

Open **http://127.0.0.1:3000**. Save a task draft, reload, and confirm it remains. FastAPI's schema is available at **http://127.0.0.1:8000/docs**. Database containers may take a few seconds to become ready; check `docker compose ps` if migration cannot connect.

The development and build scripts use Next.js's Webpack option because Turbopack's CSS worker could not bind its internal port in the coding environment. This does not change the application framework.

The setup script creates ignored `.env` and `apps/web/.env.local` files with the same random local API token. It refuses to overwrite existing configuration. Never use `NEXT_PUBLIC_` for this token or commit the environment files. An example configuration is provided in `.env.example`; its placeholder token is rejected.

This is a single-user, loopback-only development setup. The backend token protects the API, while the Next.js server proxies same-origin requests. It is not multi-user authentication: anyone with access to the local frontend has access to its drafts. Do not expose these servers through a tunnel or public deployment. Production identity and run ownership remain to be implemented.

## Verify

```bash
source .venv/bin/activate
pytest -q
cd apps/web
npm run typecheck
npm run build
```

Backend tests use temporary SQLite databases so protocol validation and migration checks can run without Docker. They do not establish PostgreSQL-specific behavior; run the migration and draft smoke test against PostgreSQL as well.

Draft limits: 1–3 workers, 30–600 seconds, and a model budget of 1–500 US cents. These are validated configuration values, not active execution controls yet. Unknown request fields are rejected. The API only creates `draft` runs and reports execution as unavailable. Retention is not automated in this slice; development drafts remain until deleted from the database.

Saved drafts can be deleted using the dashboard's Delete button, which asks for confirmation, or through the authenticated `DELETE /runs/{run_id}` API in FastAPI's `/docs`. Success returns `204` with an empty body; a missing draft returns `404`, including a repeated deletion. See the [draft deletion review exercise](docs/learning/03-delete-draft.md).

For the optional browser smoke test, start both local servers and PostgreSQL, install the project's Playwright extra and Microsoft Edge, then run `.venv/bin/python scripts/smoke_dashboard_deletion.py` from the repository root. It creates and cleans up one temporary draft while checking cancellation, proxy validation, failed deletion, and deletion surviving reload.

To stop the database without deleting saved drafts:

```bash
docker compose stop db
```

## Project map

| Path | Purpose |
|---|---|
| `apps/web/` | Next.js / TypeScript / Tailwind dashboard and server-side API proxy |
| `services/api/crescendo_api/` | FastAPI schemas, local authentication, SQLAlchemy models, endpoints |
| `services/api/migrations/` | Versioned Alembic database changes |
| `services/api/tests/` | Authentication, request limits, persistence, and migration checks |
| `compose.yaml` | Local PostgreSQL, bound to loopback |
| `docs/` | Architecture, plan, and learning exercises |

## Design and learning

* [Visual architecture and technical decisions](docs/visual-architecture.md)
* [Full architecture](docs/architecture.md)
* [Six-week implementation and learning plan](docs/implementation-plan.md)
* [First learning exercise: durable task drafts](docs/learning/01-task-drafts.md)

Next milestone: one isolated E2B desktop, scoped tool admission, verified destination restrictions, and a bounded research loop. Choose a model through a measured comparison before committing to a default.

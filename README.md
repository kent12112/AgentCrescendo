# AgentCrescendo

A general-purpose workspace where agents operating isolated computers coordinate everyday tasks. Built as a learning project focused on applied AI, reliable distributed execution, and externally enforced agent permissions.

**Current implementation:** two separate parts that are not connected yet.

- **Dashboard (draft-only).** The local Next.js dashboard saves and deletes task drafts through FastAPI and PostgreSQL. It does not start, run, or watch agents. Saved limits such as workers and budget are validated but not enforced on any run.
- **Agent (CLI only).** Python scripts run one agent on a real E2B cloud desktop with a Groq vision model. It researches Wikipedia from screenshots, scrolls, clicks links, and gives a cited answer. You can watch it in a local live viewer. See [Run the agent from the command line](#run-the-agent-from-the-command-line).

Temporal, durable runs, multi-agent messaging, connecting the dashboard to execution, and automatic retention remain planned.

Start with the [codebase guide](docs/codebase.md) for the file structure, reading order, and execution paths. See [current status](docs/status.md) for observed results and remaining checks.

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

## Run the agent from the command line

These scripts are separate from the dashboard. Most of them create a metered E2B desktop, and the model demos also make paid Groq requests. They need `E2B_API_KEY`, and the model demos need `GROQ_API_KEY`. Set them in your shell, or in the ignored root `.env`, which the scripts load without overwriting values already set. Install the optional dependencies first:

```bash
pip install -e '.[e2b,groq]'
```

Run each from the repository root with `.venv/bin/python scripts/<name>`.

| Script | What it does | Needs |
|---|---|---|
| `e2b_visual_research_demo.py --watch` | Finds a value in the Boston article from screenshots and scrolling, then answers. Graded on whether the value was on screen at finish. | E2B, Groq |
| `e2b_click_demo.py --watch` | Clicks from the Boston article to Massachusetts using browser-measured link IDs. | E2B, Groq |
| `e2b_vision_agent_demo.py --watch` | Model-selected scrolling on a controlled test page. | E2B, Groq |
| `groq_e2b_demo.py --trace` | Text-only research loop: page text instead of screenshots. | E2B, Groq |
| `e2b_preflight.py` | Network-layer checks: what the desktop can and cannot reach. | E2B |
| `e2b_network_browser_check.py` | Browser checks: subrequests, redirects, and meta refresh are blocked. | E2B |
| `e2b_click_check.py` | Click safety checks with the real pointer; no model. | E2B |
| `e2b_termination_check.py` | Confirms E2B really destroys desktops. | E2B |
| `smoke_*.py` | Local browser checks with no E2B, model, or paid calls. | Microsoft Edge |

`--watch` opens a private local viewer and waits for you before the agent starts. `--save-screenshots` (research and click demos) writes the model's input images and `result.json` under the ignored `.demo-artifacts/` folder.

What the agent may do is fixed in code: an exact host allowlist, a short tool list with no code execution, and network limits enforced outside the model. Known limits are recorded in [network preflight](docs/e2b-preflight.md). Annotated runs, including failures, are in [Week 1 traces](docs/week1-traces.md).

## Project map

| Path | Purpose |
|---|---|
| `apps/web/` | Next.js / TypeScript / Tailwind dashboard and server-side API proxy |
| `services/api/crescendo_api/` | API assembly, authentication, resource routes, schemas, and persistence |
| `apps/web/features/drafts/` | Draft UI, state/request handling, and response types |
| `packages/agent_runtime/crescendo_agent/` | Text/vision loops, model adapters, E2B desktop and live viewer |
| `packages/security/crescendo_security/` | Task grants, tool authorization, destination policy |
| `scripts/` | Local setup, runnable demos, and explicit smoke checks |
| `services/api/migrations/` | Versioned Alembic database changes |
| `services/api/tests/` | Authentication, request limits, persistence, and migration checks |
| `compose.yaml` | Local PostgreSQL, bound to loopback |
| `docs/` | Architecture, plan, and learning exercises |

## Design and learning

The executable source includes line-by-line learning comments. Start with the
[commented-source guide](docs/learning/12-commented-source.md) for a reading path
and explanations of JSON configuration, which cannot contain comments.

* [Visual architecture and technical decisions](docs/visual-architecture.md)
* [Full architecture](docs/architecture.md)
* [Six-week implementation and learning plan](docs/implementation-plan.md)
* [First learning exercise: durable task drafts](docs/learning/01-task-drafts.md)

Next milestones: choose and run the deferred two-model comparison, then add durable execution (Week 2). Week 1's outcome and open items are in [decision 0003](docs/decisions/0003-week1-outcome.md).

# AgentCrescendo

A general-purpose workspace where agents operating isolated computers coordinate everyday tasks. Built as a learning project focused on applied AI, reliable distributed execution, and externally enforced agent permissions.

**Current implementation:** a local job-search and cover-letter workspace, plus separate live desktop demos.

- **Job workspace.** Upload a resume, search and rank stored postings, select up to three jobs, preview the resume with identity removed, and explicitly confirm before Groq drafts letters from the resume, job description, company name, and optional company notes. Review source quotes/flags, edit, approve, and download text. Open a real offline E2B Writer desktop, watch it type the approved letter, and download the verified PDF saved in local PostgreSQL. Company notes are user-supplied context; independent company browser research remains open.
- **Task drafts.** The original draft dashboard remains at `/drafts`. Run start records a stable Temporal workflow, whose activity is still a placeholder; it does not execute desktop agents. Draft worker/budget limits do not control letter generation.
- **Applications.** In Ashby job search, choose **Mark applied** after submitting an
  application yourself. Open **Applications** (`/jobs/applications`) to update its
  status, applied date, notes, and follow-up date. The saved posting survives crawl
  cleanup. Search can hide applied jobs. Tracking stays local and needs no provider
  key; it does not submit applications or send reminders.
- **Agent (CLI only).** Python scripts run one agent on a real E2B cloud desktop with a Groq vision model. It researches Wikipedia from screenshots, scrolls, clicks links, and gives a cited answer. You can watch it in a local live viewer. See [Run the agent from the command line](#run-the-agent-from-the-command-line).

Durable desktop runs, multi-agent messaging, company research desktops, and automatic retention remain planned. The connected Writer export is currently owned by one local API process.

Start with the [codebase guide](docs/codebase.md) for the file structure, reading order, and execution paths. See [current status](docs/status.md) for observed results and remaining checks.

## Run locally

Requirements: Python 3.11+, Node.js 20.9+, Docker Desktop running, and enough free disk space for dependencies and a PostgreSQL image. Searching needs no provider keys; drafting needs Groq, and live Writer needs E2B.

From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.lock
pip install --no-deps -e .
pip install -e '.[jobs,groq]'
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

Open **http://127.0.0.1:3000/jobs**. Job search reads the daily crawl's stored postings. FastAPI's schema is available at **http://127.0.0.1:8000/docs**. Database containers may take a few seconds to become ready; check `docker compose ps` if migration cannot connect.

For live cover-letter drafting, set `GROQ_API_KEY` and `E2B_API_KEY` in the root `.env`,
install `pip install -e '.[e2b,jobs]'`, and restart the API. The optional
`LETTER_MODEL` defaults to `openai/gpt-oss-120b`. Then:

1. Upload a PDF, `.txt`, or `.md` resume, search, and select up to three jobs.
2. Choose **Write cover letters**, enter your full name, and optionally add company context.
3. Review the prepared inputs. The first resume line is treated as the name line;
   contact-pattern removal is imperfect, so inspect the whole preview before confirming.
4. Agree to Groq drafting and live preview of the generated redacted draft on E2B,
   then choose **Draft letters live**. The desktop opens first. When the blank Writer
   document is visible, choose **Start drafting**. Groq creates the draft and Writer
   types it on the same screen, before review or approval. Jobs run one at a time.
5. When typing finishes, review the quotes and flags, edit, approve, and download `.txt`. **Print / save PDF**
   opens the browser's print view.
6. For a final Writer PDF of your approved version, open **Live desktop** and choose
   **Open live Writer**, then **Start typing**. Choose **Download Writer PDF** after
   the export. The PDF's
   extracted words must match the approved letter before it is saved in Postgres.

Drafting opens the wide **Live desktop** view; completion opens **Letter & sources**
for review. Active desktops reopen after a reload. Use **Expand desktop** for full
screen. Typing uses explicit UTF-8 keyboard input for smart punctuation and accents;
saved exports include safe phase timings for diagnosing a failed operation.
PDF verification ignores line wrapping and LibreOffice's representation of a
nonbreaking hyphen as an ordinary hyphen; other text changes still fail verification.

Live Writer supports letters up to 6,000 characters and at most three active desktop
leases. **Stop live Writer** cancels an export and requests cleanup. Page reload
reconnects while the same API process owns the desktop. After an API restart, wait
for the abandoned lease to expire before retrying; saved PDFs remain available.
The provider kills desktops after ten minutes. If cleanup is uncertain, the UI waits
for lease expiry before allowing a replacement. See
[the live Writer decision](docs/decisions/0012-live-writer-exports.md).

Letter sessions can be reopened from **Cover letters**, including after a reload. The
local API worker owns each live draft and bounded model call; it is not the Temporal
desktop workflow. If the browser closes, the active run continues, but later letters
wait for **Continue / retry drafting**. After an API restart, a live run is interrupted
and retry waits for its desktop lease to expire. An unchanged saved draft can retry
failed desktop typing without another model call. Quote matches
prove only that the quote occurs in the source; they do not prove the sentence's meaning.
Paraphrases, unsourced wording, missing quotes, and invented candidate numbers are flagged.
The writer chooses a specific connection between the company's product, users, or
working practices and concrete resume experience, then explains the contribution
that experience could support. Add product details and exact culture excerpts in
**Company context** when the posting is sparse; websites are not researched
automatically. A sentence can cite both resume and company evidence, shown together
in source review. Those quote matches do not verify the argument. Create a new
letter session to try the revised writer; completed drafts are reused unchanged.
Nothing applies to a job or sends a letter. Removing the resume does not delete saved
letter sessions or their snapshots. See [the implementation decision](docs/decisions/0011-connected-letter-drafting.md).

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

Task-draft limits: 1–3 workers, 30–600 seconds, and a model budget of 1–500 US cents.
These are validated configuration values, not active desktop execution controls or
letter-generation budgets. Unknown fields are rejected. The task dashboard saves
`draft` runs; the start API only records a placeholder Temporal activity. Retention
is not automated; development records remain until deleted from the database.

Saved drafts can be deleted using the dashboard's Delete button, which asks for confirmation, or through the authenticated `DELETE /runs/{run_id}` API in FastAPI's `/docs`. Success returns `204` with an empty body; a missing draft returns `404`, including a repeated deletion. See the [draft deletion review exercise](docs/learning/03-delete-draft.md).

For the isolated job/letter browser check, install the project's Playwright extra and
Microsoft Edge, then run `.venv/bin/python scripts/smoke_job_search.py`. It starts its
own servers with temporary SQLite, fictional jobs/resume, and a fake model; no user
database changes or paid calls. Screenshots and a fictional printed PDF are written
to ignored `.demo-artifacts/job-search-smoke/`. This uses a separate frontend copy,
so it does not share your normal dev lock or environment files. For a real E2B
viewer/typing/PDF check with a fictional approved letter, run
`.venv/bin/python scripts/smoke_job_search.py --live-writer`. It uses the configured
E2B key and metered desktop time; Groq stays fake. Artifacts are saved under ignored
`.demo-artifacts/writer-live-smoke/`.
Add `--writer-stress` for a full-length fictional letter with typographic punctuation;
live stress artifacts and timing metrics go to `.demo-artifacts/writer-performance-live/`.

For the task-draft browser smoke, start both local servers and PostgreSQL, then run
`.venv/bin/python scripts/smoke_dashboard_deletion.py`. It uses `/drafts` and creates
and cleans up one temporary draft.

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
| `e2b_public_browse_demo.py --watch` | Public-web mode: no host list and no URL typing; reaches boston.gov from Wikipedia by clicking a link. | E2B, Groq |
| `e2b_vision_agent_demo.py --watch` | Model-selected scrolling on a controlled test page. | E2B, Groq |
| `groq_e2b_demo.py --trace` | Text-only research loop: page text instead of screenshots. | E2B, Groq |
| `e2b_preflight.py [--public]` | Network-layer checks: what the desktop can and cannot reach (allowlist or public-web mode). | E2B |
| `e2b_network_browser_check.py [--public]` | Browser checks: subrequests, redirects, private and rebinding destinations blocked. | E2B |
| `e2b_click_check.py` | Click safety checks with the real pointer; no model. | E2B |
| `e2b_termination_check.py` | Confirms E2B really destroys desktops. | E2B |
| `smoke_*.py` | Local browser checks with no E2B, model, or paid calls. | Microsoft Edge |

`--watch` opens a private local viewer and waits for you before the agent starts. `--save-screenshots` (research and click demos) writes the model's input images and `result.json` under the ignored `.demo-artifacts/` folder.

What the agent may do is fixed in code: an exact host allowlist, or public-web mode (any public site, private addresses denied, movement by clicking links only), a short tool list with no code execution, and network limits enforced outside the model. Known limits are recorded in [network preflight](docs/e2b-preflight.md). Annotated runs, including failures, are in [Week 1 traces](docs/week1-traces.md).

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

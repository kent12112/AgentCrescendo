# Handoff: local application startup

- Date/time and timezone: November 18, 2026, America/New_York.
- Author/session: Codex primary; no delegation.
- Intended recipient: user / next session; operational record, no assignment.
- Base commit: `d9813ed`.
- Uncommitted paths: this handoff and `docs/status.md`; earlier changes preserved.
- State: complete. Ownership released; local servers intentionally remain running.

## Goal and changes

User requested running locally. Existing configuration and dependencies were
present. No application source, credentials, provider resources, or schedules changed.

## Evidence

- Initial sandbox localhost probe failed with `Operation not permitted`; retried
  the local checks outside the sandbox. Docker was stopped; opened it using
  `/usr/bin/open -a Docker`.
- `/usr/local/bin/docker compose up -d --wait db`: healthy, exit 0.
- `.venv/bin/alembic upgrade head`: exit 0.
- `.venv/bin/python -m uvicorn crescendo_api.main:app --host 127.0.0.1 --port 8000 --reload`:
  running, tool session `38204`.
- `/usr/local/bin/node /usr/local/lib/node_modules/npm/bin/npm-cli.js run dev`
  in `apps/web`: ready on port 3000, tool session `2861`.
- Python urllib HTTP checks: `http://127.0.0.1:8000/health` and
  `http://127.0.0.1:3000/jobs` both returned 200.

## Limits and next action

Open `http://127.0.0.1:3000/jobs`. Startup checks establish page/API availability;
no search, model, or desktop flow was exercised and no test suite rerun. Frontend
reported an existing external lockfile warning; startup succeeded.

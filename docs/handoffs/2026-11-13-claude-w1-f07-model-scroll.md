# Handoff: W1-F07 — model-selected scroll on the visual fixture

- Date/time and timezone: November 13, 2026, evening (America/New_York).
- Author / session: Claude (Claude Code, VS Code session).
- Intended recipient: next Claude or Codex session; review requested, not an assignment.
- Base commit: `9130a21`.
- Change commit(s), or uncommitted paths: uncommitted —
  `scripts/e2b_vision_agent_demo.py`, `scripts/e2b_preflight.py`,
  `scripts/e2b_browser_smoke.py`, `scripts/groq_e2b_demo.py`,
  `scripts/e2b_vision_demo.py`, new
  `packages/agent_runtime/crescendo_agent/local_env.py`, `.env.example`,
  `docs/status.md`, `docs/implementation-plan.md`,
  `docs/learning/09-vision-action-loop.md`, this handoff.
- State: complete for the fixture acceptance check.
- Ownership: released.

## Goal and acceptance criteria

Plan W1-F07 / status W1-2: the model chooses bounded scroll actions and correctly
finishes the visual task; saved model-input PNGs are inspected and the live
result recorded.

## Changes and decisions

- `--save-screenshots` also writes `result.json` (model, status, answer, expected
  top/target codes, denial count, trace), before the pass/fail exit. The earlier
  saved run had PNGs but no answer, so it could not be diagnosed.
- New `crescendo_agent.local_env.load_local_env()` loads the repo `.env`
  (git-ignored) with `override=False`; it is a no-op when `PYTEST_CURRENT_TEST`
  is set, so tests that execute script `main()` never see real keys. The five
  live scripts call it at the start of `main()`. `.env.example` lists
  `E2B_API_KEY` and `GROQ_API_KEY` with blank values.

## Evidence

- Local: `.venv/bin/python -m pytest -q` → 194 passed; `git diff --check` clean.
  With keys unset in the shell, the demo read the E2B key from `.env` and
  stopped on the missing Groq key (before the user filled it).
- Live (run by Claude): `.venv/bin/python scripts/e2b_vision_agent_demo.py
  --save-screenshots` → `PASS`, model `qwen/qwen3.8-27b`, ~27 s wall time,
  0 denials. Trace: `scroll(down, 5)` then `finish("C5BC0B")`; expected target
  `C5BC0B`, distractor `F14ACE`.
- Inspected artifacts (ignored, local only):
  `.demo-artifacts/vision-5bba9334e8e24cd7a2fc707868f6d5ca/step-01.png` shows only
  the top code; `step-02.png` shows `After scrolling` / `C5BC0B`; `result.json`
  matches.

Limits: a single run on a controlled fixture; no repeat-rate, token/cost, or
public-page evidence; provider termination not independently checked.

## Open issues and next action

- Earlier reported wrong answer (`.demo-artifacts/vision-9e57…`) is unexplained;
  its PNGs show correct observation but no answer was saved.
- Optional: repeat the run a few times to estimate reliability before W1-4/W1-F12.
- Next per status: W1-1 live viewer, then W1-6 public-page visual research.

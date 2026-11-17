# Handoff: SOURCE-STARTUP — Wikipedia startup evidence and recovery

- Date/time and timezone: November 16, 2026, America/New_York.
- Author / session: Codex, user-reported “Wikimedia Error” follow-up.
- Intended recipient: user; future review session (not an assignment).
- Base commit: `f337055856f028c85aeca91decaa69ed8108ccdb`.
- Changes: uncommitted. Updated `crescendo_agent/e2b_desktop.py`,
  `scripts/e2b_click_demo.py`, the existing timeout CLI test's source fixture,
  clicking/status docs; added `test_click_source_loading.py`, learning record 15,
  and this handoff. All prior uncommitted work was preserved.
- State: complete for startup recovery/diagnostics; original external failure
  was not reproduced and its cause remains unknown.
- Ownership: released by Codex.

## Goal and acceptance criteria

Handle a missing Boston source before model execution: bounded recovery for
temporary failures, preserve article validation, save the error evidence, and
make zero model calls when the source remains unavailable.

## Changes and decisions

- The adapter retains only final HTTP status and `Retry-After` for `navigate`,
  clearing them before each admitted navigation. It does not retain full headers
  or change request authorization, destinations, or network policy.
- The click demo requires HTTP 2xx plus the article element. A correct URL alone,
  a 404 containing article markup, or an HTTP 200 error page is insufficient.
- Startup retries the same authorized GET once for 429/5xx or a navigation
  timeout, waiting through Playwright so request-filter callbacks keep running.
  Default wait is five seconds; numeric server delays must be finite and between
  zero and 15 seconds. Refusals, other browser errors, missing source markup,
  unknown status, and longer/unparseable delays are not retried.
- Under `--save-screenshots`, startup failures save `source-01.png`/`source-02.png`,
  `source-attempts.json`, and a `source_unavailable` result with `model_calls: 0`.
  Screenshot capture is best effort if the desktop itself is unavailable.
  Successful final results also include source attempt metadata. Model-input
  `step-*.png` behavior is unchanged.

## Evidence

User-reported failure: “Wikimedia Error” before model calls. The supplied ignored
folder `.demo-artifacts/click-b1c668e22d59479b9cfcb07911d6b015/` had no files.
The earlier callback only saved images after source validation. No original
HTTP status or error body is available; do not guess a specific root cause.

Local:

```sh
.venv/bin/python -m pytest -q packages/agent_runtime/tests/test_click_source_loading.py packages/agent_runtime/tests/test_vision_timeouts.py packages/agent_runtime/tests/test_e2b_desktop.py
.venv/bin/python -m pytest -q
git diff --check
```

Focused: 75 passed. Full suite: 379 passed; one existing Starlette/httpx
deprecation warning. Diff check passed. Controlled tests exercise successful
loading, 503/429 recovery, repeated failure, refusals, missing/invalid article
responses, browser timeouts/errors, unacceptable server waits, metadata reset,
saved startup evidence, cleanup, and zero model/click calls on startup failure.

Live, under the user's existing bounded E2B/Groq test approval:

- Model-free E2B source probe: HTTP 200, “Boston - Wikipedia”, article present.
  No Groq calls. Artifact:
  `.demo-artifacts/source-probe-7064bf5850ec494185bc0af1fafd0579/`.
- `.venv/bin/python scripts/e2b_click_demo.py --save-screenshots --max-steps 3`:
  complete PASS. Source HTTP 200 on attempt 1. ID 39 → screen `(317, 602)`,
  recorded Boston → Massachusetts navigation and final answer “Massachusetts”.
  Agent time 24.3 seconds including one 17-second model rate-limit retry; no
  denied clicks or new tabs. Source metadata and final result were inspected.
  Artifact: `.demo-artifacts/click-86e09d556bc3494fb5f41a914444065a/`.

The live checks verify successful source loading and the unchanged click flow.
Source-error recovery is verified with controlled responses, not a reproduced
live Wikimedia failure. Diagnostic artifacts remain ignored and uncommitted.

## Open issues and next action

No required code work remains for this fix. We cannot ensure Wikipedia or Groq
availability or classify the original failure from its title. If it recurs,
inspect the new source status and diagnostic image. Access refusals stay refused;
there is no automatic source substitution or destination expansion. No commit
or push was made.

See [learning record](../learning/15-source-startup.md) and
[clicking](../e2b-clicking.md#startup-source-failures).

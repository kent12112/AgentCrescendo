# Handoff: VISION-TIMEOUT — bounded inference recovery

- Date/time and timezone: November 16, 2026, America/New_York.
- Author / session: Codex, user-reported `groq.APITimeoutError` follow-up.
- Intended recipient: user; future review session (not an assignment).
- Base commit: `f337055856f028c85aeca91decaa69ed8108ccdb`.
- Changes: uncommitted. Updated `crescendo_agent/{vision,vision_loop,loop,model}.py`,
  `scripts/e2b_click_demo.py`, clicking/status docs; added
  `packages/agent_runtime/tests/test_vision_timeouts.py`, learning record 14,
  and this handoff. Earlier click/security/grounding changes remain intact.
- State: complete; ready for review.
- Ownership: released by Codex.

## Goal and acceptance criteria

Recover from a transient Groq inference timeout without replaying desktop actions.
Stop cleanly after the retry budget is exhausted; preserve deadline admission,
diagnostic results, and cleanup. Distinguish provider failure from a task answer.

## Changes and decisions

- The client previously used `timeout=30`, `max_retries=0`. Only HTTP 429 was
  caught by the loop. Groq `APITimeoutError` escaped before result serialization.
- The adapter translates SDK timeouts into sanitized `ModelTimedOut` signals.
  A live check also exposed HTTP 503 over capacity, so transient HTTP 5xx errors
  now become sanitized `ModelUnavailable` signals with numeric `Retry-After`
  or a two-second fallback backoff. Raw request/error details do not enter traces.
- The loop owns two inference attempts total per step, shared across all three
  transient failure types. SDK retries remain disabled. The retry input keeps
  the same screenshot, inventory, and transcript; provider-error trace entries
  are appended afterward. Earlier clicks are never replayed by this retry path.
- The deadline is checked before every attempt and after errors/returned
  proposals. It still does not forcibly interrupt in-flight SDK operations.
- Exhausted failures return `model_timeout` or `model_unavailable`; rate limits
  retain `rate_limited`. The CLI prints a clear explanation, saves diagnostics
  with `--save-screenshots`, and unwinds desktop/viewer context managers.
- The click demo uses `--request-timeout 45` by default, configurable to a
  positive value at most 60. Other adapter consumers keep the 30-second default.
- Updated shared transcript/result Literal annotations for measured link lists,
  provider errors, and the new terminal statuses.

## Evidence

Local:

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest -q packages/agent_runtime/tests/test_vision_timeouts.py
git diff --check
.venv/bin/python scripts/e2b_click_demo.py --help
```

Full suite: 362 passed, one existing Starlette/httpx deprecation warning. Diff
check passed; CLI help exposes the validated timeout option. Failure-injection
coverage uses the actual Groq SDK with an in-memory HTTP transport, plus mocked
loop/CLI tests. It checks read timeouts, HTTP 500/502/503/504, identical retry
inputs, no click replay, repeated/mixed failures, backoff/deadline limits,
saved failure results, and desktop cleanup. No live provider calls occur in
those tests.

Live (under the user's existing approval for bounded E2B/Groq tests):

```sh
.venv/bin/python scripts/e2b_click_demo.py --save-screenshots --max-steps 3
```

- First run, after timeout handling but before server-error handling: Groq
  returned HTTP 503 saying `qwen/qwen3.8-27b` was over capacity. The unhandled
  503 was a real failure, not a passing test. Screenshot-only diagnostic folder:
  `.demo-artifacts/click-c97c5a43954347088800f2862290d88d/`.
- Final run on the completed implementation: PASS, 54.5 seconds including one
  17-second rate-limit wait. ID 39 → screen `(317, 602)`, recorded Boston →
  Massachusetts navigation, final answer “Massachusetts”, no denied clicks or
  new tabs. Artifact:
  `.demo-artifacts/click-711fb3c6229348d488458eae8462a353/`.

The live pass verifies normal operation after the changes. Timeout/server-error
recovery itself is verified by controlled SDK/loop/CLI fault injection; the
final live run did not reproduce an actual timeout or server-error retry.

## Open issues and next action

No required work remains for this fix. Provider capacity is outside the runtime's
control. The observed 503 is consistent with temporary provider pressure, but
does not establish the cause of the user's earlier timeout. Groq's public status
page reported operational during the failed request. Do not infer a broad outage
or promise that retries always recover. No commit or push was made.

See [learning record](../learning/14-model-request-timeouts.md),
[Groq SDK timeout documentation](https://github.com/groq/groq-python#timeouts), and
[Groq status](https://groqstatus.com/).

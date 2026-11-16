# Handoff: W1-F11 — provider-side desktop termination

- Date/time and timezone: 2026-11-16, ~22:40 UTC
- Author / session: Claude (Claude Code, VS Code)
- Intended recipient: the user for review; Codex for optional review (not an assignment)
- Base commit: `4d55b97`
- Change commit(s), or uncommitted paths: uncommitted —
  `packages/agent_runtime/crescendo_agent/e2b_desktop.py`,
  `packages/agent_runtime/tests/test_e2b_desktop.py`,
  `scripts/e2b_termination_check.py` (new),
  `packages/agent_runtime/tests/test_termination_check.py` (new),
  `docs/e2b-termination.md` (new), `docs/e2b-browser.md`,
  `docs/implementation-plan.md` (W1-F11 line only; the W1-F10 tick was already
  an uncommitted user change), `docs/status.md`, this handoff.
- State: complete, ready for review
- Ownership: released

## Goal and acceptance criteria

[Plan W1-F11](../implementation-plan.md): confirm provider-side termination after
normal completion and a deliberate failure; document the lifetime fallback and
cleanup limits. This also supplies the "provider termination evidence" part of
status task W1-5.

## Changes and decisions

- **Explicit timeout action.** `open_e2b_desktop()` now passes
  `lifecycle={"on_timeout": "kill"}`. Before, it relied on E2B's current default
  for an omitted value. The other option, `pause`, would keep the desktop instead
  of destroying it. The test asserts the new argument.
- **Control-plane verification.** The new check confirms termination with
  `Sandbox.get_info(id)`, where a 404 means destroyed. It does not use
  `is_running()`, which only pings the guest's health endpoint, so a 502 there
  could also mean a network problem.
- **Abandoned-process scenario.** A child process exits with `os._exit(0)` inside
  the desktop block, so no `finally` or `kill()` runs. The parent requires the
  orphan to still be `running` before it waits, so our own cleanup cannot pass
  as the timer.
- **Not changed:** the adapter does not retry `kill()`, check its return value,
  or refuse `E2B_DEBUG`. These are documented as limits in
  [termination](../e2b-termination.md), not fixed.

## Evidence

Local: `.venv/bin/python -m pytest -q` → 261 passed (9 new). Fake provider only;
no network.

Live (run by Claude from this machine, metered E2B, no model calls):
`.venv/bin/python scripts/e2b_termination_check.py`

- Run 1: normal and failure passed. The abandon child's page lacked "Boston",
  the parent killed the desktop and failed as designed. Cause unconfirmed.
- Run 2 (`--scenario abandon`): passed. The orphan was `running` after the child
  exited, E2B reported `on_timeout: kill`, and it was gone ~2 s after `end_at`.
- Run 3 (all): every scenario passed. Abandon was gone ~1 s after `end_at`.
- Afterwards, `Sandbox.list()` returned 0 sandboxes.

Logs are not committed. They are in this session's scratchpad (not durable);
the doc table holds the results. Not shown: billing stop time, reliability over
many runs, or behavior when the E2B API is unreachable.

## Open issues and next action

- Review questions: should the adapter retry `kill()` once, or log a `False`
  (already gone) result? Should the adapter refuse `E2B_DEBUG`?
- The run 1 Wikipedia failure suggests three quick page loads can hit a
  rate limit or error page; watch for it in W1-F12 model comparisons.
- Remaining Week 1: W1-3/F10 subchecks (redirects, DNS rebinding, subrequests)
  per status, W1-F12 model comparison, W1-F13 traces and README.

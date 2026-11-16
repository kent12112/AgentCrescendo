# E2B desktop termination (W1-F11)

This page records how our desktops are destroyed, what was observed live, and
where cleanup can still fail. It is evidence for plan item W1-F11.

## Three ways a desktop ends

In the locked-room picture, the room (desktop) is rented by the minute. There
are two ways it gets closed:

1. **We close it.** `open_e2b_desktop()` calls `sandbox.kill()` in a `finally`
   block ([e2b_desktop.py](../packages/agent_runtime/crescendo_agent/e2b_desktop.py)),
   so it runs on normal exit and when an exception escapes the `with` block.
2. **The landlord closes it.** Every desktop is created with a lifetime
   (`timeout=lifetime_seconds`, default 180 s, visual research demo 300 s) and
   `lifecycle={"on_timeout": "kill"}`. When the lifetime ends, E2B destroys the
   desktop even if our process has died. This is the fallback.

`on_timeout` used to be omitted. E2B's current default for an omitted value is
`kill`, but the other option, `pause`, keeps the desktop's state and lets it be
resumed. A paused desktop is not destroyed. The adapter now sets `kill`
explicitly, and the live run confirmed that E2B recorded it.

## How termination is verified

`scripts/e2b_termination_check.py` asks E2B's **control-plane API** for the
sandbox by ID (`Sandbox.get_info(id)`). A 404 (`SandboxNotFoundException`)
counts as destroyed. A `paused` state counts as a failure.

The older smoke check uses `is_running()`. That only pings a health endpoint
inside the guest and treats a 502 as "not running", so a network problem looks
the same as a destroyed desktop. The control-plane lookup is stronger evidence.

| Scenario | What happens | Who must destroy it |
| --- | --- | --- |
| `normal` | Load Wikipedia, leave the block normally | Our `finally: kill()` |
| `failure` | Load Wikipedia, raise `DeliberateFailure` inside the block | Our `finally: kill()` |
| `abandon` | A child process loads Wikipedia, then calls `os._exit(0)`, which skips every `finally` | E2B's lifetime timer (60 s) |

In `abandon`, the parent first checks that the orphaned desktop is still
`running`, so a quick "gone" cannot come from our own cleanup. If the child
fails before abandoning, the parent kills the desktop and reports a failure.

Run it (creates three metered desktops, no model calls, about two minutes):

```sh
.venv/bin/python scripts/e2b_termination_check.py            # all scenarios
.venv/bin/python scripts/e2b_termination_check.py --scenario abandon
```

The script refuses to run with `E2B_DEBUG=true`, because in debug mode the SDK's
`kill()` returns `True` without contacting E2B.

## Live results, November 16, 2026 (UTC)

SDKs: `e2b` 2.63.0, `e2b-desktop` 2.7.2. Run from this machine by Claude.

| Run | normal | failure | abandon |
| --- | --- | --- | --- |
| 1, 22:31Z | Pass: 404 on first lookup | Pass: 404 on first lookup | Not reached: child's page did not contain "Boston"; parent killed the desktop and failed (guard worked) |
| 2, 22:32Z (abandon only) | — | — | Pass: running after child exit; `on_timeout: kill`; gone ~2 s after `end_at` |
| 3, 22:34Z (all) | Pass: 404 on first lookup | Pass: 404 on first lookup | Pass: running after child exit; `on_timeout: kill`; gone ~1 s after `end_at` |

After run 3, `Sandbox.list()` returned zero sandboxes on the account.

The run 1 child failure is unexplained. Run 1 was the third Wikipedia load in
under a minute, so a rate-limit page is a plausible cause, but this was not
confirmed. The error now prints the start of the page text.

What this shows: in these runs, `kill()` removed the desktop from E2B's API
right away, and an orphaned desktop was removed within a few seconds of its
scheduled end. What it does not show: when billing actually stopped (no invoice
was checked), how reliable this is over many runs (two passing runs per
scenario), or what happens when the API is unreachable.

## Cleanup limits

- **An orphan costs up to a full lifetime.** If the process dies right after
  creating the desktop, E2B keeps it for the whole lifetime: 180 s by default,
  300 s in the visual research demo, 600 s at most.
- **The lifetime starts at creation and is never extended.** It must cover
  setup, any viewer wait, and the agent run. A run that takes longer loses its
  desktop mid-task. Nothing calls `set_timeout`. Longer runs need the Week 2
  heartbeat and reaper design, not a bigger fixed lifetime.
- **`kill()` has no retry.** If the kill request raises (network or API error),
  that exception propagates from the `finally` block. Python chains the
  original error to it as `__context__`, but callers see the kill error first.
  The desktop then lives until its lifetime ends.
- **A kill that finds nothing is silent.** `kill()` returns `False` for a 404
  (for example, after the lifetime already ended), and the adapter does not
  check the return value. This is harmless for cleanup but hides the overrun.
- **Deadlines do not interrupt in-flight SDK calls** (see W1-F04). A hung call
  can keep the process, and therefore the desktop, alive until the lifetime ends.
- **Debug mode disables kill.** With `E2B_DEBUG=true`, the SDK skips the kill
  request and still reports success. Only this check script refuses debug mode.
  The adapter does not.
- **No reaper yet.** There is no process that lists and kills leftover desktops.
  The provider timer is the only backstop. The architecture's reaper is Week 2
  work (W2-F08).

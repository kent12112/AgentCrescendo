# Review exercise: let the model propose a scroll

The previous vision demo used a host-selected scroll. This slice adds a separate
bounded vision loop with two offered tools: `scroll(direction, amount)` and
`finish(answer)`. It does not expose clicking, typing, navigation, shell commands,
or arbitrary SDK operations. The existing text agent remains separate.

Each step captures the authorized desktop screenshot, sends that image plus a
short goal/action/denial history to Groq, parses exactly one complete function
proposal, and checks the gateway before executing it. Scroll arguments still
require an explicit grant, direction up/down, and integer wheel amount 1–5.
Invalid proposals that reach the gateway produce a denial the model sees on its
next decision. Malformed provider response envelopes fail the run without action.
The adapter independently checks scrolling authority before invoking E2B.

Only the newest screenshot is attached to each model request. Text history retains
capture dimensions, proposals, denials, and completed scroll messages; no image
bytes are printed or persisted. This avoids resending prior screenshots but does
not establish total token savings or preserve a replayable visual trace.

The demo has at most five decisions and a 120-second deadline. The helper accepts
at most ten steps and a deadline no longer than 120 seconds. It checks the deadline
before capture, before model invocation, and before action admission. An already
running SDK operation can overrun; the deadline is not a hard interrupt. Each
model request retains the 30-second timeout, zero SDK retries, and 512-token cap.
The desktop context attempts cleanup after normal, limited, and exceptional exits.

Run with keys exported in your terminal:

```sh
.venv/bin/python scripts/e2b_vision_agent_demo.py
```

This uses one metered E2B desktop and up to five real model calls. A trusted local
fixture displays one random code at the top and another under `After scrolling`.
The goal asks for the latter code without putting either code into model text.
The host does not schedule a scroll. Success requires the model to finish with the
target code. Inspect the printed action trace to confirm which scrolls it proposed
and which completed. A failed run still prints its terminal result when it returns
normally; provider/capture exceptions propagate after cleanup.

On November 13, 2026, all 179 Python cases passed, as did `--help` and
`git diff --check`. New tests cover invalid/ungranted proposals, fresh screenshots,
denial feedback, completed-action history, exact step limits, late model proposals,
structured image/tool requests, malformed response rejection, and demo cleanup on
provider failure. These tests use mocks and scripted proposals. The model-selected
live E2B result remains pending.

Prior live evidence: the host-driven scroll demo read `A00949` before scrolling and
`5D4ED4` afterward. Both descriptions made unsupported claims about extra image
panels despite one supplied screenshot per call. This motivates short structured
tool proposals, but does not establish that the model will stop hallucinating.

Tradeoffs: wheel movement depends on the desktop and the current fixed focus
position is fixture-specific. A successful SDK return does not prove useful screen
movement; the next screenshot supplies evidence for the model. The model can repeat
unhelpful actions until a bound stops it. There is no autonomous browser task,
multi-window focus policy, persistent screenshot artifact, or independent provider
termination check in this slice. Code recognition is evidence for this controlled
task, not a general computer-use reliability benchmark.

Live attempt failed before model invocation: the relay received connections but
could not connect to Chrome's loopback debugger. The logs do not establish why
Chrome did not listen; a D-Bus warning is not proof of the cause. Startup previously
checked process liveness after 0.5 seconds, then relied on a 20-second relay wait.
The launcher now monitors its child and probes debugger port 9222 directly for up
to 45 seconds before starting the relay (SDK command timeout: 50 seconds). A late
process exit reports its code/log; direct readiness timeout names the port and
includes the browser log. Relay readiness remains a separate bounded check.
No automatic sandbox recreation or paid retries were added. All 181 Python tests
passed, including a simulated 30-second launch and a direct-debugger timeout.
This improves readiness handling and diagnosis; the underlying live startup cause
and the model-controlled scroll result remain unverified pending a retry.

Live model-selected result (November 13, 2026, run by Claude in the VS Code
session): `scripts/e2b_vision_agent_demo.py --save-screenshots` with
`qwen/qwen3.8-27b` passed in about 27 seconds of wall time. The model saw step 1
(only top code `F14ACE` visible), proposed `scroll(down, 5)` on its own, saw step
2 (`After scrolling`, target `C5BC0B`), and finished with `C5BC0B`. No denials.
Both saved PNGs were inspected and match the trace, so the answer is supported
by the image actually supplied, not the distractor. `--save-screenshots` now also
writes `result.json` (answer, both expected codes, trace) beside the PNGs, pass or
fail. Live scripts load keys from the git-ignored `.env` via
`crescendo_agent.local_env` (shell exports win; skipped under pytest).

Limits: one run on a controlled two-section fixture; a single maximum-size scroll
happened to land on the target. This does not measure repeat reliability, token
usage or cost, multi-step scrolling, or public pages. The earlier reported wrong
answer (`.demo-artifacts/vision-9e57…`, whose PNGs show correct observation) had
no saved answer, so its cause remains unknown. Provider termination was not
independently checked.

Scroll pointer fix (November 13, 2026): `E2BDesktop.scroll()` called Playwright's
`page.mouse.move(200, 200)` and then E2B's `sandbox.scroll`. They are different
mice. Playwright sends synthetic events inside Chrome; E2B runs
`xdotool click --repeat N 5`, which turns the wheel at the real X pointer. A live
probe on one desktop (no model calls) showed: real pointer (512, 384) before and
after `page.mouse.move`; wheel with the pointer over the taskbar left `scrollY` at
0; wheel with the pointer at (208, 322) over the page scrolled 360 px. Earlier runs
worked only because the pointer starts at the screen centre, which is over the
page. `scroll()` now moves the real pointer with `sandbox.move_mouse` to
`SCROLL_POINTER = (512, 440)` (middle of the page area on the 1024x768 display)
and refuses to scroll if no pointer function is configured. A repeat live F07
run passed (`E1B374`) with the pointer visible at about (512, 440) in step 2.
The point is fixed for this display and single-window layout; it is not a
general window-focus policy.

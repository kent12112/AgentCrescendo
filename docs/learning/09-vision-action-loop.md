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

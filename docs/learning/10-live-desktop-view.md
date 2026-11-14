# Watch the model operate its real E2B desktop

From the repository root, with E2B_API_KEY and GROQ_API_KEY exported:

```sh
.venv/bin/python scripts/e2b_vision_agent_demo.py --watch
```

The browser opens to a temporary localhost viewer. Once the actual desktop is
visible, press Enter in the terminal within 45 seconds. The model then sees its
first screenshot and can scroll or finish. Watch the page move and compare it
with the printed action trace. The viewer disconnects when the run ends and its
desktop is cleaned up. The browser tab can remain open, but its server is stopped.

This uses one metered desktop and up to five model calls. Opening the viewer and
waiting also consume desktop lifetime; the existing 180-second sandbox lifetime
still applies, including setup and the viewer wait. The agent's separate
120-second deadline begins after the viewer wait. This is not a 120-second overall
desktop lifetime guarantee.

The new WebSocket dependency is included in the `[e2b]` extra and development lock.
If working from a separately installed environment, install the existing extras:

```sh
.venv/bin/python -m pip install -e '.[e2b,groq]'
```

## Architecture and access boundary

E2B's noVNC server streams the real remote display. The user sees that stream;
the model independently receives screenshots through its vision requests.

```text
Browser → loopback HTTP/WebSocket proxy → private E2B noVNC service
Model   ← screenshot capture           ← same E2B desktop
Model   → proposed scroll → gateway    → same E2B desktop
```

The sandbox continues using `allow_public_traffic=False`. The host starts VNC
with `require_auth=True`. A proxy bound only to `127.0.0.1` forwards requests to
this sandbox's fixed viewer host, adding the traffic-access header on both HTTP
and WebSocket connections. No browser-supplied credentials/cookies are forwarded.
Upstream redirects are not followed, and errors return generic messages.

A random local bootstrap URL sets an HttpOnly SameSite=Strict cookie. The viewer
checks that cookie for assets and checks both cookie and exact local Origin for
WebSocket upgrades. Host checks reject DNS rebinding through other hostnames.
The temporary link grants local access; it is not intended to be shared. Proxy
access logs are disabled. The E2B traffic token is never placed in the browser.
The separate VNC password is passed to the local noVNC client in its URL; this is
not the E2B API key or traffic token. Responses disable caching and referrers.

The viewer opens with noVNC's view-only setting to avoid accidental interaction.
That is a client preference, not an independently enforced VNC authorization
boundary; the local user is trusted. This is not a public or multi-user viewer.
It does not expose Chrome's debugger port through the local proxy. No custom
frontend or simulated desktop replaces E2B's actual display.

Cleanup stops the loopback server and VNC stream before the outer desktop context
closes the browser and attempts sandbox kill. Stream/server setup failure still
unwinds through sandbox cleanup. Active WebSocket relays cancel their counterpart
on disconnect, with bounded cleanup. No automatic paid retry is added.

## Verification

Tests cover temporary-session authentication, trusted hosts, fixed upstream
destination, upstream-only traffic credentials, sanitized errors and redirects,
WebSocket Origin checks, binary messages in both directions, viewer permission,
setup-failure cleanup, and waiting before model execution. The default demo path
remains available without a viewer.

`scripts/smoke_live_view.py` starts the real local server and opens Edge against a
simulated upstream. It verified browser cookies, HTTP asset loading, a binary
WebSocket round trip, and shutdown. It uses no model or E2B resources and does not
claim to verify the remote VNC protocol or E2B authentication end to end. The first
real `--watch` run remains pending user execution.

Local result on November 13, 2026: all 191 Python cases passed. The Edge proxy
smoke test passed, and `git diff --check` passed. No paid E2B or model calls were
made while implementing this viewer.

## Follow-up connection diagnosis

The user reported a noVNC Connect screen and "failed to connect to the server",
but could not determine whether this occurred before Enter or after sandbox
cleanup. The terminal trace alone did not establish successful live viewing.
`--watch` now waits up to 30 seconds for the upstream WebSocket transport before
prompting for Enter. Connection failures report fixed diagnostic codes/status
numbers rather than exception text. The model is not invoked when this gate fails.
Transport readiness still does not prove VNC authentication or screen rendering;
confirm the actual page visually before Enter. Expired viewer links cannot reconnect
after the local server/sandbox are stopped. The cookie and origin checks remain.

A separate live run returned `visual=51,174` instead of its target code. The next
diagnostic run can preserve exactly the PNGs delivered to the model:

```sh
.venv/bin/python scripts/e2b_vision_agent_demo.py --watch --save-screenshots
```

Images are written in a unique ignored `.demo-artifacts/vision-...` directory,
whose path is printed before sandbox startup. They remain after cleanup for local
inspection. No VNC credentials or API keys are written into the artifact metadata;
the images contain whatever was visible on the controlled remote screen. They
are not automatically uploaded or committed.

The code-reading demo also requires a finish answer to have exactly six hexadecimal
characters. A malformed finish receives format feedback and another screenshot
within the existing step/deadline limit. The validator never receives the expected
code; it cannot establish factual correctness. The final external check now compares
the entire answer with the target code rather than accepting a substring match.

All 194 Python tests and the local proxy browser smoke check passed after this
revision. The remote connection cause and incorrect-code cause remain unconfirmed
until the diagnostic run supplies evidence. No automatic paid retries were added.

References: [E2B desktop streaming](https://github.com/e2b-dev/desktop),
[WebSocket client API](https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html).

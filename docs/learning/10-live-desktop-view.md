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

## Live result (November 13, 2026)

A scripted probe (one desktop, no model calls, no browser) checked each hop
through the local proxy: the bootstrap link returned 307 and set the session
cookie; `vnc.html`, `app/ui.js`, and `core/rfb.js` returned 200; a WebSocket
opened with the local Origin and cookie was accepted with the `binary`
subprotocol, and the first upstream bytes were `RFB 003.008`, the VNC server
greeting. The proxy, E2B routing, traffic token, and x11vnc were all working.

The user then ran `scripts/e2b_vision_agent_demo.py --watch --save-screenshots`
and reported seeing the real remote desktop before pressing Enter, and seeing
the page scroll to "After scrolling" live. The same run passed F07: the model
chose `scroll(down, 5)` and finished with the target code (`57D244`), with 0
denials. The artifacts are in `.demo-artifacts/vision-68ab4aaf488a44959c109ffcc1ac6b13/`.

The earlier "failed to connect" report predates the 30-second connection gate.
Its cause was not reproduced and remains unconfirmed; timing (viewing before
readiness or after cleanup) is plausible but unproven. A first attempt in this
session failed before desktop creation with E2B 401 because an old
`E2B_API_KEY` exported in the user's shell overrode `.env`.

Limit: worst-case setup (~15 s) + connection gate (30 s) + Enter wait (45 s) +
agent deadline (120 s) exceeds the 180-second sandbox lifetime. Normal runs fit,
but a slow run could lose the desktop mid-task.

References: [E2B desktop streaming](https://github.com/e2b-dev/desktop),
[WebSocket client API](https://websockets.readthedocs.io/en/stable/reference/asyncio/client.html).

## Asset connection recovery (November 16, 2026)

The user reported a `_CONNECTION_ERROR` while `wait_for_viewer` was waiting.
This suffix matches `UPSTREAM_ASSET_CONNECTION_ERROR`: failure fetching a viewer
file, before the model loop. The old proxy collapsed all HTTP transport errors
into that one code and made every asset failure fatal, including an optional
favicon. A controlled check reproduced fatal readiness from a failed favicon
even though the essential HTML loaded. This does not prove which file or network
condition caused the user's original failure.

The viewer now owns one HTTP client for its lifetime, with a bounded pool and
explicit cleanup. Each asset GET can retry one transport failure after 250 ms.
Required HTML, JavaScript, and CSS failures still fail the connection gate;
optional icon/image failures return an error for that file without invalidating
viewer readiness. HTTP refusals and redirects are not retried or followed.
Error codes distinguish connect/read/pool timeouts, connection/proxy failures,
and protocol errors without exposing raw exception text or credentials.

The click demo saves `status: viewer_unavailable`, safe error codes, source
metadata, `model_calls: 0`, and a best-effort `viewer-desktop.png` when the gate
fails under `--save-screenshots`. That PNG shows the underlying E2B desktop,
not the person's local browser. Context managers still close the viewer/desktop.
The person must still see the desktop and press Enter before the agent starts.

Verification:

- 393 Python tests passed, including controlled asset failures, bounded retries,
  pool lifetime, authorization, safe failure output, and pre-model cleanup.
- `scripts/smoke_live_view.py` passed with real local Edge and a simulated
  upstream. A sandboxed attempt first failed to bind loopback; rerunning with
  the appropriate local execution permission passed.
- A real Edge/E2B check completed VNC authentication and rendered actual desktop
  pixels despite one injected essential JavaScript connection failure and two
  injected optional favicon failures. The resulting screenshot was inspected
  and visibly shows “VIEWER CONNECTION PROBE”. No model or Wikipedia calls.
  Artifact: `.demo-artifacts/viewer-probe-dc827275cba34d15aee25dbfb21449cf/`.
- The first probe's connection event preceded its first screen frame, producing
  a black screenshot. The final verifier waits for painted canvas pixels as
  well as connection state. Connection alone remains insufficient rendering
  evidence.

Repeat the controlled live check with:

```sh
.venv/bin/python scripts/e2b_live_view_check.py
```

This creates one metered E2B desktop and uses installed Microsoft Edge. It logs
sanitized file paths/status categories only. It uses a controlled page and
controlled local transport failures, so it checks the viewer independently of
Wikipedia and model availability. It does not establish general viewer
reliability or reproduce the user's original network failure.

See [handoff](../handoffs/2026-11-16-codex-viewer-connection.md) and
[HTTPX connection-pooling guidance](https://www.python-httpx.org/async/).

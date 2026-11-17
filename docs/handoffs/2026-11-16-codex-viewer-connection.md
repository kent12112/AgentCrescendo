# Handoff: VIEWER-CONNECTION — viewer asset recovery and diagnostics

- Date/time and timezone: November 16, 2026, America/New_York.
- Author / session: Codex, user-reported `_CONNECTION_ERROR` at the viewer gate.
- Intended recipient: user; future review session (not an assignment).
- Base commit: `f337055856f028c85aeca91decaa69ed8108ccdb`.
- Changes: uncommitted. Updated `crescendo_agent/live_view.py`,
  `scripts/e2b_click_demo.py`, status/clicking/viewer learning docs; added
  `test_live_view_recovery.py`, `scripts/e2b_live_view_check.py`, and this handoff.
  Earlier click, source, timeout, and security work was preserved.
- State: complete for the reproduced false failure and viewer recovery changes;
  exact original upstream network failure remains unconfirmed.
- Ownership: released by Codex.

## Goal and acceptance criteria

Make viewer startup robust to a temporary file transport failure and prevent
optional icon failures from aborting an otherwise usable stream. Preserve
authentication and the pre-model viewing/Enter gate. Save safe diagnostics on a
real gate failure and verify an actual rendered E2B desktop in a local browser.

## Changes and decisions

- The reported suffix matches the proxy's asset-download error code. Previously
  all HTTP transport errors, even a failed favicon, poisoned readiness. Every
  asset also created a new HTTP client instead of reusing connections.
- One async HTTP client now lives with the app and closes on shutdown. It uses
  at most eight connections; fixed host, private traffic header, no redirects,
  and existing cookie/Origin/Host checks remain.
- Each static GET retries transport failure once after 250 ms. It does not retry
  HTTP refusal/redirect responses. Essential HTML/JS/CSS still fail readiness;
  optional images/icons cannot invalidate the gate.
- Diagnostics report fixed connect/read/pool timeout and connection/proxy/
  protocol categories, never raw exceptions or credentials.
- Click-demo gate failure now exits with a clear message and, when requested,
  saves `viewer_unavailable`, safe error codes, source metadata, zero model
  calls, and `viewer-desktop.png`. The image is the remote desktop, not the
  person's browser. Viewer/desktop contexts still clean up.
- Added a model-free, Wikipedia-independent live check using real local Edge,
  E2B, controlled asset faults, VNC connection state, and painted canvas pixels.
  Successful rendering is confirmed by inspecting the saved image as well.

## Evidence

Local commands:

```sh
.venv/bin/python -m pytest -q packages/agent_runtime/tests/test_live_view.py packages/agent_runtime/tests/test_live_view_recovery.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/smoke_live_view.py
git diff --check
```

29 viewer tests passed; full suite 393 passed with one existing Starlette/httpx
deprecation warning. Diff check passed. The local Edge/loopback smoke passed
against a simulated upstream. Its first attempt hit sandbox socket-binding
restrictions; the approved local execution passed. No E2B/model calls in the
local smoke or unit tests.

Controlled reproduction before the fix: HTML returned 200, favicon raised a
connection error, and the gate received `UPSTREAM_ASSET_CONNECTION_ERROR`.
This demonstrates the false-fatal bug, not the original failure's exact cause.

Live, within the user's existing bounded E2B test authorization:

- First real Edge/E2B probe loaded all assets and connected. Its immediate
  screenshot was black, so connection state alone was insufficient frame
  evidence. Artifact:
  `.demo-artifacts/viewer-probe-435b398a69fa40b7b625e421ab423619/`.
- Strengthened probe on the fix: one injected connection failure for
  `/core/rfb.js`, plus two persistent optional favicon failures. The required
  file recovered; VNC authenticated, desktop pixels rendered, and no fatal
  viewer errors were recorded. 84 upstream asset requests succeeded. Saved
  screenshot visibly shows the controlled “VIEWER CONNECTION PROBE” page.
  No model/Wikipedia calls. Artifact:
  `.demo-artifacts/viewer-probe-dc827275cba34d15aee25dbfb21449cf/`.
- The probe was promoted into `scripts/e2b_live_view_check.py`; it returns
  failure unless VNC connects, desktop pixels paint, and no fatal gate error
  occurs. It prints sanitized metadata and saves ignored diagnostic images and
  request status/category data. No private viewer URLs or credentials are saved.

Repeat the real controlled check with:

```sh
.venv/bin/python scripts/e2b_live_view_check.py
```

This uses one metered E2B desktop and installed Microsoft Edge. Images remain
ignored/uncommitted. Production modules were unchanged after the full suite;
the promoted check script also passed Python compilation.

## Open issues and next action

No required work remains for this fix. The original network exception/file is
unconfirmed, and a local Edge check does not establish every default browser or
network works. Persistent essential file failures still stop with zero model
calls. The person must visually confirm the actual desktop before Enter.
No commit or push was made.

See [viewer learning/evidence](../learning/10-live-desktop-view.md#asset-connection-recovery-november-16-2026)
and [HTTPX pooling guidance](https://www.python-httpx.org/async/).

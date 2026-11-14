# ANNOTATED READING COPY — not executed, not imported, may drift from the source.
# Source: packages/agent_runtime/crescendo_agent/e2b_desktop.py (9130a21 + uncommitted pointer fix, Nov 13 2026).
# Line numbers in [brackets] after line 159 are from BEFORE the pointer fix; the fix shifted them by ~8.
# ONLY the parts on the F07 vision path are copied (source line numbers in [brackets]).
# Omitted text-agent parts: page_links [13-37], WIKIPEDIA_CONTENT [141-157],
# observe/search_page/_read_content/navigate [234-311].
#
# Big picture: E2B gives us a Linux desktop in the cloud. We start Chrome on it, expose
# Chrome's remote-control port through a small relay, connect Playwright to it from your
# Mac, and use E2B's own API for full-desktop screenshots and mouse-wheel scrolling.

"""Text-only Chrome in E2B, controlled through a private CDP connection."""  # [1] CDP = Chrome DevTools Protocol (Chrome's remote-control API).
from contextlib import contextmanager  # [2] Turns a generator function into a `with` block (used by open_e2b_desktop).
import shlex  # [3] Safely quotes text for a shell command line.
from typing import Any  # [4] "Any type".
from urllib.parse import urldefrag, urljoin, urlsplit  # [5] URL helpers (urlsplit is used in setup below).

from crescendo_security.policy import TaskGrant, ToolCall, authorize  # [7] Permission types and the check (file 4).

from .desktop import Observation, PageLink  # [9] Types used by the text agent.
from .page_search import search_passages  # [10] Text search helper (text agent).


# ---------------------------------------------------------------------------
# [39-70] START_BROWSER: a Python script sent as TEXT and run INSIDE the cloud desktop.
# It starts Chrome and waits until Chrome's remote-control port (9222) answers.
# ---------------------------------------------------------------------------
START_BROWSER = '''
import os, shutil, subprocess, time, urllib.request
from pathlib import Path
# Find the first Chrome/Chromium program installed on the desktop image:
binary = next((path for name in (
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"
) if (path := shutil.which(name))), None)
# None found -> fail loudly:
if binary is None:
    raise RuntimeError("No Chrome/Chromium executable found in the E2B template")
# Chrome flags: no OS sandbox (container), small /dev/shm workaround, skip first-run popups,
# no background traffic, remote control on port 9222, a throwaway profile, start on a blank page:
args = [binary, "--no-sandbox", "--disable-dev-shm-usage", "--no-first-run",
        "--no-default-browser-check", "--disable-background-networking",
        "--remote-debugging-port=9222", "--user-data-dir=/tmp/crescendo-chrome",
        "about:blank"]
# Start Chrome on the visible display (:0), logging to a file, detached from this script:
with open("/tmp/crescendo-chrome.log", "wb") as log:
    child = subprocess.Popen(args, stdout=log, stderr=log,
                             env={**os.environ, "DISPLAY": ":0"}, start_new_session=True)
# Give Chrome up to 45 seconds:
deadline = time.monotonic() + 45
# An HTTP client that ignores any proxy settings (talk straight to localhost):
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
while True:
    # Did Chrome already exit? (poll() returns its exit code, or None if still running)
    code = child.poll()
    if code is not None:
        # Report the code plus the last 4000 characters of Chrome's log:
        raise RuntimeError("Chrome exited during startup (code " + str(code) + "): " +
                           Path("/tmp/crescendo-chrome.log").read_text(errors="replace")[-4000:])
    try:
        # Is the remote-control port answering yet?
        with opener.open("http://127.0.0.1:9222/json/version", timeout=1):
            break  # Yes -> Chrome is ready.
    except OSError as exc:
        # Not yet. Out of time? -> fail with the error and the log:
        if time.monotonic() >= deadline:
            raise RuntimeError("Chrome debugger port 9222 did not become ready within 45 seconds. " +
                               "Last error: " + repr(exc) + "\\n" +
                               Path("/tmp/crescendo-chrome.log").read_text(errors="replace")[-4000:]) from exc
        # Otherwise wait 0.2 s and check again:
        time.sleep(0.2)
'''

# [72-116] RELAY: another script run INSIDE the desktop.
# Chrome's debugger listens on loopback. Relay it to a private E2B service port.
# The relay carries browser control only; it is not an outbound browsing proxy.
# Why: Chrome only listens on 127.0.0.1 (inside the desktop). E2B can expose a port to
# us (with a secret access token), so this relay forwards port 9223 -> Chrome's 9222.
RELAY = r'''
import select, socket, socketserver

# Rewrite one incoming HTTP request before passing it to Chrome:
def chrome_request(data):
    # Split headers from body, then headers into lines:
    head, body = data.split(b"\r\n\r\n", 1)
    lines = head.split(b"\r\n")
    # E2B has authenticated the external request already. Chrome's debugger
    # accepts only IP/localhost Host headers (including WebSocket upgrades).
    # Drop the Host header and E2B's secret token header (Chrome must never see the token):
    headers = [line for line in lines[1:]
               if line.partition(b":")[0].strip().lower()
               not in (b"host", b"e2b-traffic-access-token")]
    # Rebuild: original request line, a localhost Host header, remaining headers, body:
    return b"\r\n".join([lines[0], b"Host: 127.0.0.1:9222", *headers]) + b"\r\n\r\n" + body

# Handles one incoming connection:
class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        # Give up on a silent client after 10 s:
        self.request.settimeout(10)
        data = b""
        # Read until the end of the HTTP headers (blank line):
        while b"\r\n\r\n" not in data:
            chunk = self.request.recv(4096)
            # Client hung up -> stop:
            if not chunk:
                return
            data += chunk
            # Headers over 64 KB -> refuse (protects memory):
            if len(data) > 65536:
                return
        # Connect to Chrome and send the rewritten request:
        with socket.create_connection(("127.0.0.1", 9222), timeout=10) as upstream:
            upstream.sendall(chrome_request(data))
            # Then just pipe bytes both ways (this carries the WebSocket control channel):
            peers = [self.request, upstream]
            while True:
                # Wait up to 60 s for either side to send something:
                ready, _, _ = select.select(peers, [], [], 60)
                # Idle 60 s -> close:
                if not ready:
                    return
                for source in ready:
                    data = source.recv(65536)
                    # Either side closed -> close:
                    if not data:
                        return
                    # Forward to the other side:
                    target = upstream if source is self.request else self.request
                    target.sendall(data)
# A server that handles each connection in its own thread and can reuse the port quickly:
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
# Listen on port 9223 forever:
if __name__ == "__main__":
    Server(("0.0.0.0", 9223), Handler).serve_forever()
'''

# [118-137] WAIT_READY: run INSIDE the desktop after starting the relay.
# Waits up to 20 s for the RELAY port (9223) to answer, otherwise fails with both logs.
WAIT_READY = '''
import time, urllib.request
from pathlib import Path
# 20-second budget:
deadline = time.monotonic() + 20
# Proxy-free HTTP client:
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
while True:
    try:
        # Does the relay answer (and reach Chrome)?
        with opener.open("http://127.0.0.1:9223/json/version", timeout=1):
            break  # Yes -> ready.
    except OSError as exc:
        # Out of time -> collect the tail of each log and fail:
        if time.monotonic() >= deadline:
            logs = []
            for name in ("chrome", "relay"):
                path = Path("/tmp/crescendo-" + name + ".log")
                logs.append(name + ": " + (path.read_text(errors="replace")[-4000:]
                            if path.exists() else "no log file"))
            raise RuntimeError("Chrome debugger did not become ready. Last error: " +
                               repr(exc) + "\\n" + "\\n".join(logs)) from exc
        # Otherwise retry in 0.2 s:
        time.sleep(0.2)
'''


# [159-164] NEW (pointer fix): where to put the REAL desktop pointer before scrolling.
# Real desktop (screen) coordinates for wheel scrolling: the middle of Chrome's page
# area on E2B's 1024x768 display (content spans roughly y=114..768).
SCROLL_POINTER = (512, 440)  # (x, y) in SCREEN pixels, not page pixels. Middle of the page area.


class E2BDesktop:  # [160] Our wrapper around one cloud desktop. Every action goes through authorize() again.
    def __init__(self, page: Any, session: Any, grant: TaskGrant, *, max_chars=4000, screenshot_provider=None, scroll_provider=None, pointer_provider=None, viewer_provider=None):  # [161] Inputs: the Playwright tab, a CDP session, the permission slip, and E2B functions passed in (so tests can fake them).
        self.page = page  # [162] The Playwright browser tab we control.
        self.session = session  # [163] Low-level Chrome control channel for that tab.
        self.grant = grant  # [164] The permission slip.
        self.max_chars = max_chars  # [165] Text-agent limit on page text length.
        self._screenshot_provider = screenshot_provider  # [166] Function that returns a full-desktop PNG (E2B's sandbox.screenshot).
        self._scroll_provider = scroll_provider  # [167] Function that turns the mouse wheel (E2B's sandbox.scroll).
        self._pointer_provider = pointer_provider  # NEW: function that moves the real desktop pointer (E2B's sandbox.move_mouse).
        self._viewer_provider = viewer_provider  # [168] Function that opens the live viewer.
        self.visited: list[str] = []  # [169] URLs visited (text agent).
        self.blocked_requests: list[str] = []  # [170] URLs the browser tried to load but we blocked.
        self._blocked_document_frames: set[str] = set()  # [171] Frames whose page load we blocked.
        self._navigation_failure: Observation | None = None  # [172] Text-agent bookkeeping.
        session.on("Fetch.requestPaused", self._request_paused)  # [173] "Chrome, before ANY request leaves, pause it and call _request_paused."
        session.send("Fetch.enable", {"patterns": [  # [174] Turn that interception on...
            {"urlPattern": "*", "requestStage": "Request"},  # [175] ...for every URL, before the request is sent.
        ]})  # [176]

    def capture_screen(self):  # [178] Take one screenshot of the WHOLE desktop (not just the web page).
        from .vision import Screenshot  # [179] Imported here to avoid a circular import between the two modules.

        decision = authorize(self.grant, ToolCall("screenshot"))  # [181] Is "screenshot" on the permission slip?
        if not decision.allowed:  # [182] No ->
            raise ValueError(decision.reason)  # [183] refuse (this is a programming error, not a model mistake).
        if self._screenshot_provider is None:  # [184] Nothing wired up to take screenshots?
            raise RuntimeError("Desktop screenshot provider is not configured.")  # [185] Fail clearly.
        # Ensure the controlled tab is foregrounded before full-desktop capture.
        self.page.bring_to_front()  # [187] Make our tab the visible one.
        image = self._screenshot_provider()  # [188] Ask E2B for the PNG bytes.
        # E2B filesystem.read(format="bytes") returns bytearray in this SDK.
        # Normalize at the provider boundary; Screenshot stays immutable bytes.
        if isinstance(image, bytearray):  # [191] E2B gives a mutable bytearray...
            image = bytes(image)  # [192] ...convert to immutable bytes.
        return Screenshot(image)  # [193] Wrap it; Screenshot validates it's a sane PNG (file 3).

    def scroll(self, direction: str, amount: int) -> None:  # [195] Turn the mouse wheel.
        decision = authorize(self.grant, ToolCall("scroll", {"direction": direction, "amount": amount}))  # [196] Check AGAIN here (defence in depth: the loop already checked).
        if not decision.allowed:  # [197] Refused?
            raise ValueError(decision.reason)  # [198] Stop.
        if self._scroll_provider is None or self._pointer_provider is None:  # Wheel or pointer function missing?
            raise RuntimeError("Desktop scroll and pointer providers are not configured.")  # Refuse: never scroll at an unknown pointer position.
        self.page.bring_to_front()  # Our tab should be in front.
        # Move the REAL desktop pointer over page content first, so the wheel
        # targets the page rather than a panel or another window.
        # HISTORY: this used to be page.mouse.move(200, 200). That is Playwright's synthetic
        # mouse INSIDE Chrome and does not move the real pointer. A live probe (Nov 13) showed
        # the real pointer stayed at (512, 384), and the wheel over the taskbar did not scroll.
        self._pointer_provider(*SCROLL_POINTER)  # E2B runs `xdotool mousemove --sync 512 440` on the desktop.
        self._scroll_provider(direction=direction, amount=amount)  # E2B runs `xdotool click --repeat <amount> 4|5` (4 = wheel up, 5 = down) at that pointer.

    def live_view(self):  # [208] Open the live viewer (only with --watch).
        decision = authorize(self.grant, ToolCall("view_desktop"))  # [209] Is viewing permitted?
        if not decision.allowed:  # [210] No ->
            raise ValueError(decision.reason)  # [211] refuse.
        if self._viewer_provider is None:  # [212] Not wired up?
            raise RuntimeError("Desktop viewer is not configured.")  # [213] Fail clearly.
        return self._viewer_provider()  # [214] Open it (returns a `with`-able viewer).

    def _request_paused(self, event):  # [216] Called for EVERY request Chrome wants to make (set up in __init__).
        request = event["request"]  # [217] Details of the request.
        url = request["url"]  # [218] Where it wants to go.
        try:  # [219] Reuse the navigate rules from file 4 for this URL...
            allowed = authorize(self.grant, ToolCall("navigate", {"url": url})).allowed  # [220] ...is the host allowlisted, https, no port?
        except ValueError:  # [221] Any parsing surprise...
            allowed = False  # [222] ...means block.
        # No scripts, images, styles, downloads, or non-GET requests in this slice.
        if allowed and request["method"] == "GET" and event["resourceType"] == "Document":  # [224] Only allowed hosts, only plain GETs, only whole pages.
            self.session.send("Fetch.continueRequest", {"requestId": event["requestId"]})  # [225] Let it through.
        else:  # [226] Everything else (in F07 that's everything, since allowed_hosts is empty):
            self.blocked_requests.append(url)  # [227] Remember what was blocked.
            if event["resourceType"] == "Document" and event.get("frameId"):  # [228] Was it a page load in some frame?
                self._blocked_document_frames.add(event["frameId"])  # [229] Remember that frame.
            self.session.send("Fetch.failRequest", {  # [230] Tell Chrome to fail the request...
                "requestId": event["requestId"], "errorReason": "BlockedByClient",  # [231] ...as "blocked by client".
            })  # [232]


@contextmanager  # Makes `with open_e2b_desktop(grant) as desktop:` work (setup before `yield`, cleanup after).
def open_e2b_desktop(grant: TaskGrant, *, sandbox_type=None, playwright_factory=None):  # [313] Create, hand out, and always destroy one desktop. Tests inject fakes.
    """Own the desktop lifetime, including cleanup after initialization failure."""  # [314]
    import httpx  # [315] HTTP client used for one setup request below.

    if sandbox_type is None:  # [317] Real use (no fake)...
        from e2b_desktop import Sandbox  # [318] ...use E2B's desktop SDK (reads E2B_API_KEY).
        sandbox_type = Sandbox  # [319]
    if playwright_factory is None:  # [320] Real use...
        from playwright.sync_api import sync_playwright  # [321] ...use real Playwright.
        playwright_factory = sync_playwright  # [322]
    sandbox = sandbox_type.create(timeout=180, network={  # [323] PAID STEP: create the cloud desktop. E2B kills it after 180 s regardless (safety net).
        "deny_out": ["0.0.0.0/0"],  # [324] Firewall: block ALL outbound internet by default...
        "allow_out": sorted(grant.allowed_hosts),  # [325] ...except the allowlisted hosts (none in F07).
        "allow_public_traffic": False,  # [326] Exposed ports need E2B's secret access token.
    })  # [327]
    try:  # [328] From here on, ANY failure still reaches `sandbox.kill()` in the outer finally.
        sandbox.commands.run("python3 -c " + shlex.quote(START_BROWSER), timeout=50)  # [329] Run START_BROWSER inside the desktop (≤50 s).
        relay = sandbox.commands.run(  # [330] Start RELAY inside the desktop...
            "python3 -u -c " + shlex.quote(RELAY) + " > /tmp/crescendo-relay.log 2>&1",  # [331] ...logging to a file...
            background=True, timeout=0,  # [332] ...in the background, with no time limit (it serves forever).
        )  # [333]
        relay.disconnect()  # [334] Stop listening to its output; the relay keeps running.
        sandbox.commands.run("python3 -c " + shlex.quote(WAIT_READY), timeout=25)  # [335] Wait until the relay works (≤25 s).
        host = sandbox.get_host(9223)  # [336] E2B gives a public hostname that routes to port 9223 inside the desktop.
        headers = {"e2b-traffic-access-token": sandbox.traffic_access_token}  # [337] The secret that lets us (and only us) through.
        # Only send the sandbox token to its own authenticated control endpoint.
        response = httpx.get(f"https://{host}/json/version", headers=headers, timeout=15)  # [339] Ask Chrome (via relay) for its control address.
        response.raise_for_status()  # [340] Non-2xx -> error.
        path = urlsplit(response.json()["webSocketDebuggerUrl"]).path  # [341] Keep only the path part, e.g. /devtools/browser/<id>.
        if not path.startswith("/devtools/browser/"):  # [342] Sanity check: it must look like Chrome's control path.
            raise ValueError("Unexpected Chrome debugger endpoint")  # [343] Otherwise refuse to connect.
        with playwright_factory() as playwright:  # [344] Start Playwright locally on your Mac.
            browser = playwright.chromium.connect_over_cdp(  # [345] Attach to the REMOTE Chrome over the relay...
                f"wss://{host}{path}", headers=headers, timeout=20000,  # [346] ...secure WebSocket, with the token, 20 s timeout.
            )  # [347]
            try:  # [348] Make sure the browser connection is closed afterwards.
                context = browser.new_context(  # [349] A fresh, isolated browsing profile with...
                    java_script_enabled=False, service_workers="block", accept_downloads=False,  # [350] ...no JavaScript, no service workers, no downloads.
                )  # [351]
                page = context.new_page()  # [352] Open a tab in it.
                desktop = E2BDesktop(page, context.new_cdp_session(page), grant,  # [353] Build our wrapper around that tab...
                                     screenshot_provider=lambda: sandbox.screenshot(format="bytes"),  # [354] ...screenshots come from E2B (whole desktop)...
                                     scroll_provider=sandbox.scroll,  # [355] ...wheel scrolling comes from E2B...
                                     pointer_provider=sandbox.move_mouse,  # NEW: ...and so does moving the real pointer...
                                     viewer_provider=lambda: _open_live_view(sandbox))  # [356] ...and the live viewer too.
                yield desktop  # [357] Hand the desktop to the `with` body (the demo runs here). Resumes when that body ends or errors.
            finally:  # [358] Always:
                browser.close()  # [359] Disconnect from Chrome.
    finally:  # [360] Always, even if setup failed halfway:
        sandbox.kill()  # [361] Destroy the paid desktop. (Whether E2B actually terminated it is not independently verified.)


def _open_live_view(sandbox):  # [364] Small helper: open the live viewer for this sandbox.
    from .live_view import open_live_view  # [365] Imported lazily (optional dependency).

    return open_live_view(sandbox)  # [367] Returns the viewer object.

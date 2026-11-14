"""Text-only Chrome in E2B, controlled through a private CDP connection."""
from contextlib import contextmanager
import shlex
from typing import Any
from urllib.parse import urldefrag, urljoin, urlsplit

from crescendo_security.policy import TaskGrant, ToolCall, authorize

from .desktop import Observation, PageLink
from .page_search import search_passages


def page_links(url: str, candidates: list[dict], *, limit=20, max_chars=2000) -> tuple[PageLink, ...]:
    """Bound untrusted links; inclusion never grants navigation authority."""
    links = []
    seen = {urldefrag(url)[0]}
    remaining = max_chars
    for item in candidates:
        if len(links) >= limit:
            break
        try:
            destination = urldefrag(urljoin(url, item["url"]))[0]
            parts = urlsplit(destination)
            if parts.scheme != "https" or not parts.hostname:
                continue
        except ValueError:
            continue
        if destination in seen or len(destination) > 512:
            continue
        seen.add(destination)
        label = " ".join(item["label"].split())[:80] or destination
        cost = len(label) + len(destination)
        if cost > remaining:
            continue
        remaining -= cost
        links.append(PageLink(label, destination))
    return tuple(links)

START_BROWSER = '''
import os, shutil, subprocess, time, urllib.request
from pathlib import Path
binary = next((path for name in (
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"
) if (path := shutil.which(name))), None)
if binary is None:
    raise RuntimeError("No Chrome/Chromium executable found in the E2B template")
args = [binary, "--no-sandbox", "--disable-dev-shm-usage", "--no-first-run",
        "--no-default-browser-check", "--disable-background-networking",
        "--remote-debugging-port=9222", "--user-data-dir=/tmp/crescendo-chrome",
        "about:blank"]
with open("/tmp/crescendo-chrome.log", "wb") as log:
    child = subprocess.Popen(args, stdout=log, stderr=log,
                             env={**os.environ, "DISPLAY": ":0"}, start_new_session=True)
deadline = time.monotonic() + 45
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
while True:
    code = child.poll()
    if code is not None:
        raise RuntimeError("Chrome exited during startup (code " + str(code) + "): " +
                           Path("/tmp/crescendo-chrome.log").read_text(errors="replace")[-4000:])
    try:
        with opener.open("http://127.0.0.1:9222/json/version", timeout=1):
            break
    except OSError as exc:
        if time.monotonic() >= deadline:
            raise RuntimeError("Chrome debugger port 9222 did not become ready within 45 seconds. " +
                               "Last error: " + repr(exc) + "\\n" +
                               Path("/tmp/crescendo-chrome.log").read_text(errors="replace")[-4000:]) from exc
        time.sleep(0.2)
'''

# Chrome's debugger listens on loopback. Relay it to a private E2B service port.
# The relay carries browser control only; it is not an outbound browsing proxy.
RELAY = r'''
import select, socket, socketserver

def chrome_request(data):
    head, body = data.split(b"\r\n\r\n", 1)
    lines = head.split(b"\r\n")
    # E2B has authenticated the external request already. Chrome's debugger
    # accepts only IP/localhost Host headers (including WebSocket upgrades).
    headers = [line for line in lines[1:]
               if line.partition(b":")[0].strip().lower()
               not in (b"host", b"e2b-traffic-access-token")]
    return b"\r\n".join([lines[0], b"Host: 127.0.0.1:9222", *headers]) + b"\r\n\r\n" + body

class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(10)
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = self.request.recv(4096)
            if not chunk:
                return
            data += chunk
            if len(data) > 65536:
                return
        with socket.create_connection(("127.0.0.1", 9222), timeout=10) as upstream:
            upstream.sendall(chrome_request(data))
            peers = [self.request, upstream]
            while True:
                ready, _, _ = select.select(peers, [], [], 60)
                if not ready:
                    return
                for source in ready:
                    data = source.recv(65536)
                    if not data:
                        return
                    target = upstream if source is self.request else self.request
                    target.sendall(data)
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
if __name__ == "__main__":
    Server(("0.0.0.0", 9223), Handler).serve_forever()
'''

WAIT_READY = '''
import time, urllib.request
from pathlib import Path
deadline = time.monotonic() + 20
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
while True:
    try:
        with opener.open("http://127.0.0.1:9223/json/version", timeout=1):
            break
    except OSError as exc:
        if time.monotonic() >= deadline:
            logs = []
            for name in ("chrome", "relay"):
                path = Path("/tmp/crescendo-" + name + ".log")
                logs.append(name + ": " + (path.read_text(errors="replace")[-4000:]
                            if path.exists() else "no log file"))
            raise RuntimeError("Chrome debugger did not become ready. Last error: " +
                               repr(exc) + "\\n" + "\\n".join(logs)) from exc
        time.sleep(0.2)
'''

# Work on a detached copy: never mutate the page the agent is browsing. The
# filtered copy supplies both text and links; URL properties honor document.baseURI.
WIKIPEDIA_CONTENT = """root => {
    const copy = root.cloneNode(true);
    copy.querySelectorAll('nav, [role="navigation"], .infobox, .navbox, .sidebar, .metadata, script, style')
        .forEach(node => node.remove());
    const walker = document.createTreeWalker(copy, NodeFilter.SHOW_TEXT);
    const chunks = [];
    while (walker.nextNode()) {
        const text = walker.currentNode.textContent.trim();
        if (text) chunks.push(text);
    }
    return {
        text: chunks.join(' '),
        links: Array.from(copy.querySelectorAll('a[href]')).slice(0, 400).map(a => ({
            label: (a.textContent || '').slice(0, 160), url: a.href
        }))
    };
}"""


class E2BDesktop:
    def __init__(self, page: Any, session: Any, grant: TaskGrant, *, max_chars=4000, screenshot_provider=None, scroll_provider=None, viewer_provider=None):
        self.page = page
        self.session = session
        self.grant = grant
        self.max_chars = max_chars
        self._screenshot_provider = screenshot_provider
        self._scroll_provider = scroll_provider
        self._viewer_provider = viewer_provider
        self.visited: list[str] = []
        self.blocked_requests: list[str] = []
        self._blocked_document_frames: set[str] = set()
        self._navigation_failure: Observation | None = None
        session.on("Fetch.requestPaused", self._request_paused)
        session.send("Fetch.enable", {"patterns": [
            {"urlPattern": "*", "requestStage": "Request"},
        ]})

    def capture_screen(self):
        from .vision import Screenshot

        decision = authorize(self.grant, ToolCall("screenshot"))
        if not decision.allowed:
            raise ValueError(decision.reason)
        if self._screenshot_provider is None:
            raise RuntimeError("Desktop screenshot provider is not configured.")
        # Ensure the controlled tab is foregrounded before full-desktop capture.
        self.page.bring_to_front()
        image = self._screenshot_provider()
        # E2B filesystem.read(format="bytes") returns bytearray in this SDK.
        # Normalize at the provider boundary; Screenshot stays immutable bytes.
        if isinstance(image, bytearray):
            image = bytes(image)
        return Screenshot(image)

    def scroll(self, direction: str, amount: int) -> None:
        decision = authorize(self.grant, ToolCall("scroll", {"direction": direction, "amount": amount}))
        if not decision.allowed:
            raise ValueError(decision.reason)
        if self._scroll_provider is None:
            raise RuntimeError("Desktop scroll provider is not configured.")
        self.page.bring_to_front()
        # Place the pointer within browser content so wheel events target the page,
        # rather than a desktop panel or another window. This is a fixed fixture
        # position, not a general multi-window focus policy.
        self.page.mouse.move(200, 200)
        self._scroll_provider(direction=direction, amount=amount)

    def live_view(self):
        decision = authorize(self.grant, ToolCall("view_desktop"))
        if not decision.allowed:
            raise ValueError(decision.reason)
        if self._viewer_provider is None:
            raise RuntimeError("Desktop viewer is not configured.")
        return self._viewer_provider()

    def _request_paused(self, event):
        request = event["request"]
        url = request["url"]
        try:
            allowed = authorize(self.grant, ToolCall("navigate", {"url": url})).allowed
        except ValueError:
            allowed = False
        # No scripts, images, styles, downloads, or non-GET requests in this slice.
        if allowed and request["method"] == "GET" and event["resourceType"] == "Document":
            self.session.send("Fetch.continueRequest", {"requestId": event["requestId"]})
        else:
            self.blocked_requests.append(url)
            if event["resourceType"] == "Document" and event.get("frameId"):
                self._blocked_document_frames.add(event["frameId"])
            self.session.send("Fetch.failRequest", {
                "requestId": event["requestId"], "errorReason": "BlockedByClient",
            })

    def observe(self) -> Observation:
        observation = self._read_content()
        if len(observation.text) > self.max_chars:
            return Observation(observation.url, observation.text[:self.max_chars] + "\n[Page text truncated]", observation.links)
        return observation

    def search_page(self, query: str) -> Observation:
        if self._navigation_failure is not None:
            return self._navigation_failure
        if self.page.url == "about:blank":
            return Observation(None, "No page is open. Navigate to a permitted source first.")
        observation = self._read_content()
        return Observation(observation.url, search_passages(observation.text, query))

    def _read_content(self) -> Observation:
        if self._navigation_failure is not None:
            return self._navigation_failure
        url = self.page.url
        if url == "about:blank":
            return Observation(None, "Blank desktop. No page is open.")
        content = self.page.locator("body")
        text = None
        candidates = None
        if urlsplit(url).hostname == "en.wikipedia.org":
            article = self.page.locator("#mw-content-text .mw-parser-output")
            if article.count():
                extracted = article.first.evaluate(WIKIPEDIA_CONTENT)
                if extracted["text"].strip():
                    text, candidates = extracted["text"], extracted["links"]
        for selector in (() if text is not None else ("main", '[role="main"]', "article")):
            regions = self.page.locator(selector)
            if regions.count() == 0:
                continue
            candidate = regions.first
            candidate_text = candidate.inner_text(timeout=10000)
            if candidate_text.strip():
                content, text = candidate, candidate_text
                break
        if text is None:
            text = content.inner_text(timeout=10000)
        # Automation evaluates this fixed expression even with page scripts disabled.
        # a.href resolves relative links and honors document.baseURI. Never evaluate
        # code supplied by the model or page text.
        if candidates is None:
            candidates = content.locator("a[href]").evaluate_all("""anchors =>
                anchors.slice(0, 400).map(a => ({
                    label: (a.innerText || a.textContent || '').slice(0, 160),
                    url: a.href
                }))""")
        return Observation(url, text, page_links(url, candidates))

    def navigate(self, url: str) -> None:
        from playwright.sync_api import Error as PlaywrightError

        decision = authorize(self.grant, ToolCall("navigate", {"url": url}))
        if not decision.allowed:
            raise ValueError(decision.reason)
        self._blocked_document_frames.clear()
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
        except PlaywrightError as error:
            # Only a blocked main-frame document explains a recoverable policy
            # failure. Images and iframe blocks must not hide unrelated errors.
            if "net::ERR_BLOCKED_BY_CLIENT" not in str(error):
                raise
            frame = self.session.send("Page.getFrameTree")["frameTree"]["frame"]["id"]
            if frame not in self._blocked_document_frames:
                raise
            self._navigation_failure = Observation(
                None,
                "Navigation blocked by browser policy. No page content was read. "
                "Choose another permitted source or finish with available information.",
            )
            return
        self._navigation_failure = None
        self.visited.append(self.page.url)


@contextmanager
def open_e2b_desktop(grant: TaskGrant, *, sandbox_type=None, playwright_factory=None):
    """Own the desktop lifetime, including cleanup after initialization failure."""
    import httpx

    if sandbox_type is None:
        from e2b_desktop import Sandbox
        sandbox_type = Sandbox
    if playwright_factory is None:
        from playwright.sync_api import sync_playwright
        playwright_factory = sync_playwright
    sandbox = sandbox_type.create(timeout=180, network={
        "deny_out": ["0.0.0.0/0"],
        "allow_out": sorted(grant.allowed_hosts),
        "allow_public_traffic": False,
    })
    try:
        sandbox.commands.run("python3 -c " + shlex.quote(START_BROWSER), timeout=50)
        relay = sandbox.commands.run(
            "python3 -u -c " + shlex.quote(RELAY) + " > /tmp/crescendo-relay.log 2>&1",
            background=True, timeout=0,
        )
        relay.disconnect()
        sandbox.commands.run("python3 -c " + shlex.quote(WAIT_READY), timeout=25)
        host = sandbox.get_host(9223)
        headers = {"e2b-traffic-access-token": sandbox.traffic_access_token}
        # Only send the sandbox token to its own authenticated control endpoint.
        response = httpx.get(f"https://{host}/json/version", headers=headers, timeout=15)
        response.raise_for_status()
        path = urlsplit(response.json()["webSocketDebuggerUrl"]).path
        if not path.startswith("/devtools/browser/"):
            raise ValueError("Unexpected Chrome debugger endpoint")
        with playwright_factory() as playwright:
            browser = playwright.chromium.connect_over_cdp(
                f"wss://{host}{path}", headers=headers, timeout=20000,
            )
            try:
                context = browser.new_context(
                    java_script_enabled=False, service_workers="block", accept_downloads=False,
                )
                page = context.new_page()
                desktop = E2BDesktop(page, context.new_cdp_session(page), grant,
                                     screenshot_provider=lambda: sandbox.screenshot(format="bytes"),
                                     scroll_provider=sandbox.scroll,
                                     viewer_provider=lambda: _open_live_view(sandbox))
                yield desktop
            finally:
                browser.close()
    finally:
        sandbox.kill()


def _open_live_view(sandbox):
    from .live_view import open_live_view

    return open_live_view(sandbox)

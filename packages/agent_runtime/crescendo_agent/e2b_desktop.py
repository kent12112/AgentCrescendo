"""Policy-filtered Chrome, text observations, and desktop actions in E2B."""
# Import from contextlib: contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Import shlex: quotes fixed remote Python source safely for a shell command.
import shlex
# Import from typing: Any (marks a deliberately unconstrained type, often at an SDK boundary).
from typing import Any
# Import from urllib.parse: urldefrag (removes fragment identifiers when deduplicating
# destinations); urljoin (resolves relative links against the current page address); urlsplit
# (parses scheme, hostname, port, and path instead of guessing from substrings).
from urllib.parse import urldefrag, urljoin, urlsplit

# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping); authorize
# (checks task grants and argument bounds before a proposed tool can execute).
from crescendo_security.policy import TaskGrant, ToolCall, authorize

# Import from .browser_bootstrap: RELAY (the fixed remote CDP TCP relay program); START_BROWSER (the
# fixed remote Chrome launch/readiness program); WAIT_READY (the fixed remote relay-readiness
# check).
from .browser_bootstrap import RELAY, START_BROWSER, WAIT_READY
# Import from .desktop: Observation (holds current page URL, bounded text, and observed links);
# PageLink (holds one observed label and destination).
from .desktop import Observation, PageLink
# Import from .page_search: search_passages (finds a bounded selection of lexical matches in
# current-page text).
from .page_search import search_passages


# Define page_links with parameters url, candidates, limit, max_chars.
def page_links(url: str, candidates: list[dict], *, limit=20, max_chars=2000) -> tuple[PageLink, ...]:
    """Bound untrusted links; inclusion never grants navigation authority."""
    # Set links to an empty list.
    links = []
    # Set seen to {urldefrag(url)[0]}.
    seen = {urldefrag(url)[0]}
    # Set remaining to max_chars.
    remaining = max_chars
    # Iterate over candidates, binding item for each item.
    for item in candidates:
        # Check whether the length of links is at least limit.
        if len(links) >= limit:
            # Stop this loop.
            break
        # Try the following operations; matching except clauses handle failures.
        try:
            # Set destination to urldefrag(urljoin(url, item['url']))[0].
            destination = urldefrag(urljoin(url, item["url"]))[0]
            # Set parts to urlsplit(destination).
            parts = urlsplit(destination)
            # Check whether parts.scheme does not equal 'https' or not (parts.hostname).
            if parts.scheme != "https" or not parts.hostname:
                # Skip this item and continue with the next iteration.
                continue
        # Handle ValueError; unmatched errors propagate.
        except ValueError:
            # Skip this item and continue with the next iteration.
            continue
        # Check whether destination is in seen or the length of destination is greater than 512.
        if destination in seen or len(destination) > 512:
            # Skip this item and continue with the next iteration.
            continue
        # Add destination to seen.
        seen.add(destination)
        # Set label to ' '.join(item['label'].split())[:80] or destination.
        label = " ".join(item["label"].split())[:80] or destination
        # Set cost to the length of label plus the length of destination.
        cost = len(label) + len(destination)
        # Check whether cost is greater than remaining.
        if cost > remaining:
            # Skip this item and continue with the next iteration.
            continue
        # Update remaining using its previous value minus cost.
        remaining -= cost
        # Append PageLink(label, destination) to links.
        links.append(PageLink(label, destination))
    # Return links collected into a tuple.
    return tuple(links)

# Work on a detached copy: never mutate the page the agent is browsing. The
# filtered copy supplies both text and links; URL properties honor document.baseURI.
# Store the text used by WIKIPEDIA_CONTENT.
# string line 1: Use this literal content: root => {.
# string line 2: Clone the page subtree so text cleanup does not modify the visible page.
# string line 3: Use this literal content: copy.querySelectorAll('nav, [role="navigation"],
# .infobox, .navbox, .sidebar, .metadata, script, style').
# string line 4: Remove excluded navigation/metadata elements from the detached copy.
# string line 5: Walk text nodes in the selected document without executing page-supplied code.
# string line 6: Declare a JavaScript binding for chunks = [];.
# string line 7: Use this literal content: while (walker.nextNode()) {.
# string line 8: Declare a JavaScript binding for text = walker.currentNode.textContent.trim();.
# string line 9: Use this literal content: if (text) chunks.push(text);.
# string line 10: Close this embedded-language block or expression.
# string line 11: Return the fixed expression result to the host automation.
# string line 12: Use this literal content: text: chunks.join(' '),.
# string line 13: Use this literal content: links:
# Array.from(copy.querySelectorAll('a[href]')).slice(0, 400).map(a => ({.
# string line 14: Use this literal content: label: (a.textContent || '').slice(0, 160), url: a.href.
# string line 15: Close this embedded-language block or expression.
# string line 16: Close this embedded-language block or expression.
# string line 17: Close this embedded-language block or expression.
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


# Real desktop (screen) coordinates for wheel scrolling: the middle of Chrome's page
# area on E2B's 1024x768 display (content spans roughly y=114..768). E2B's scroll
# turns the wheel wherever the real X pointer is; Playwright's page.mouse is
# synthetic and does not move that pointer (live-checked November 13, 2026).
# Set SCROLL_POINTER to (512, 440).
SCROLL_POINTER = (512, 440)

# Chrome resource types the request filter may continue (permitted hosts, GET only).
# Set ALLOWED_RESOURCE_TYPES to an immutable set of {'Document', 'Stylesheet'}.
ALLOWED_RESOURCE_TYPES = frozenset({"Document", "Stylesheet"})


# Define E2BDesktop.
class E2BDesktop:
    # Define __init__ with parameters self, page, session, grant, max_chars, screenshot_provider,
    # scroll_provider, pointer_provider, viewer_provider.
    def __init__(self, page: Any, session: Any, grant: TaskGrant, *, max_chars=4000, screenshot_provider=None, scroll_provider=None, pointer_provider=None, viewer_provider=None):
        # Set self.page to page.
        self.page = page
        # Set self.session to session.
        self.session = session
        # Set self.grant to grant.
        self.grant = grant
        # Set self.max_chars to max_chars.
        self.max_chars = max_chars
        # Set self._screenshot_provider to screenshot_provider.
        self._screenshot_provider = screenshot_provider
        # Set self._scroll_provider to scroll_provider.
        self._scroll_provider = scroll_provider
        # Set self._pointer_provider to pointer_provider.
        self._pointer_provider = pointer_provider
        # Set self._viewer_provider to viewer_provider.
        self._viewer_provider = viewer_provider
        # Set self.visited to an empty list.
        self.visited: list[str] = []
        # Set self.blocked_requests to an empty list.
        self.blocked_requests: list[str] = []
        # Set self._blocked_document_frames to set().
        self._blocked_document_frames: set[str] = set()
        # Set self._navigation_failure to None.
        self._navigation_failure: Observation | None = None
        # Call session.on with 'Fetch.requestPaused', self._request_paused.
        session.on("Fetch.requestPaused", self._request_paused)
        # Call session.send with 'Fetch.enable', {'patterns': [{'urlPattern': '*', 'requestStage':
        # 'Request'}]}.
        session.send("Fetch.enable", {"patterns": [
            # Add this item to the surrounding list: {"urlPattern": "*", "requestStage":
            # "Request"},.
            {"urlPattern": "*", "requestStage": "Request"},
        ]})

    # Define capture_screen with parameters self.
    def capture_screen(self):
        # Import from .vision: Screenshot (validates the PNG container and dimensions at the image
        # boundary).
        from .vision import Screenshot

        # Set decision to authorize(self.grant, ToolCall('screenshot')).
        decision = authorize(self.grant, ToolCall("screenshot"))
        # Check whether not (decision.allowed).
        if not decision.allowed:
            # Raise ValueError(decision.reason) to stop the normal path.
            raise ValueError(decision.reason)
        # Check whether self._screenshot_provider is None.
        if self._screenshot_provider is None:
            # Raise RuntimeError('Desktop screenshot provider is not configured.') to stop the
            # normal path.
            raise RuntimeError("Desktop screenshot provider is not configured.")
        # Ensure the controlled tab is foregrounded before full-desktop capture.
        # Call self.page.bring_to_front with no arguments.
        self.page.bring_to_front()
        # Set image to self._screenshot_provider().
        image = self._screenshot_provider()
        # E2B filesystem.read(format="bytes") returns bytearray in this SDK.
        # Normalize at the provider boundary; Screenshot stays immutable bytes.
        # Check whether whether image is an instance of bytearray.
        if isinstance(image, bytearray):
            # Set image to bytes(image).
            image = bytes(image)
        # Return Screenshot(image).
        return Screenshot(image)

    # Define scroll with parameters self, direction, amount.
    def scroll(self, direction: str, amount: int) -> None:
        # Set decision to authorize(self.grant, ToolCall('scroll', {'direction': direction,
        # 'amount': amount})).
        decision = authorize(self.grant, ToolCall("scroll", {"direction": direction, "amount": amount}))
        # Check whether not (decision.allowed).
        if not decision.allowed:
            # Raise ValueError(decision.reason) to stop the normal path.
            raise ValueError(decision.reason)
        # Check whether self._scroll_provider is None or self._pointer_provider is None.
        if self._scroll_provider is None or self._pointer_provider is None:
            # Raise RuntimeError('Desktop scroll and pointer providers are not configured.') to stop
            # the normal path.
            raise RuntimeError("Desktop scroll and pointer providers are not configured.")
        # Call self.page.bring_to_front with no arguments.
        self.page.bring_to_front()
        # Move the REAL desktop pointer over page content first, so the wheel
        # targets the page rather than a panel or another window. A live probe
        # showed the wheel over the taskbar does not scroll the page. This is a
        # fixed position, not a general multi-window focus policy.
        # Call self._pointer_provider with *SCROLL_POINTER.
        self._pointer_provider(*SCROLL_POINTER)
        # Call self._scroll_provider with no arguments.
        self._scroll_provider(direction=direction, amount=amount)

    # Define live_view with parameters self.
    def live_view(self):
        # Set decision to authorize(self.grant, ToolCall('view_desktop')).
        decision = authorize(self.grant, ToolCall("view_desktop"))
        # Check whether not (decision.allowed).
        if not decision.allowed:
            # Raise ValueError(decision.reason) to stop the normal path.
            raise ValueError(decision.reason)
        # Check whether self._viewer_provider is None.
        if self._viewer_provider is None:
            # Raise RuntimeError('Desktop viewer is not configured.') to stop the normal path.
            raise RuntimeError("Desktop viewer is not configured.")
        # Return self._viewer_provider().
        return self._viewer_provider()

    # Define _request_paused with parameters self, event.
    def _request_paused(self, event):
        # Set request to event['request'].
        request = event["request"]
        # Set url to request['url'].
        url = request["url"]
        # Try the following operations; matching except clauses handle failures.
        try:
            # Set allowed to authorize(self.grant, ToolCall('navigate', {'url': url})).allowed.
            allowed = authorize(self.grant, ToolCall("navigate", {"url": url})).allowed
        # Handle ValueError; unmatched errors propagate.
        except ValueError:
            # Set allowed to False.
            allowed = False
        # Pages and their stylesheets only, and only from permitted hosts: no
        # scripts, images, fonts, downloads, or non-GET requests. Stylesheets let
        # the vision model see the page laid out as a person would; any further
        # requests a stylesheet makes are paused and checked here as well.
        # Check whether allowed and request['method'] equals 'GET' and event['resourceType'] is in
        # ALLOWED_RESOURCE_TYPES.
        if allowed and request["method"] == "GET" and event["resourceType"] in ALLOWED_RESOURCE_TYPES:
            # Call self.session.send with 'Fetch.continueRequest', {'requestId':
            # event['requestId']}.
            self.session.send("Fetch.continueRequest", {"requestId": event["requestId"]})
        # Run this alternative only when the preceding conditional did not select its first branch.
        else:
            # Append url to self.blocked_requests.
            self.blocked_requests.append(url)
            # Check whether event['resourceType'] equals 'Document' and event['frameId'], or None if
            # absent.
            if event["resourceType"] == "Document" and event.get("frameId"):
                # Add event['frameId'] to self._blocked_document_frames.
                self._blocked_document_frames.add(event["frameId"])
            # Call self.session.send with 'Fetch.failRequest', {'requestId': event['requestId'],
            # 'errorReason': 'BlockedByClient'}.
            self.session.send("Fetch.failRequest", {
                # Include requestId, errorReason in this dictionary.
                "requestId": event["requestId"], "errorReason": "BlockedByClient",
            })

    # Define observe with parameters self.
    def observe(self) -> Observation:
        # Set observation to self._read_content().
        observation = self._read_content()
        # Check whether the length of observation.text is greater than self.max_chars.
        if len(observation.text) > self.max_chars:
            # Return Observation(observation.url, observation.text[:self.max_chars] + '\n[Page text
            # truncated]', observation.links).
            return Observation(observation.url, observation.text[:self.max_chars] + "\n[Page text truncated]", observation.links)
        # Return observation.
        return observation

    # Define search_page with parameters self, query.
    def search_page(self, query: str) -> Observation:
        # Check whether self._navigation_failure is not None.
        if self._navigation_failure is not None:
            # Return self._navigation_failure.
            return self._navigation_failure
        # Check whether self.page.url equals 'about:blank'.
        if self.page.url == "about:blank":
            # Return Observation(None, 'No page is open. Navigate to a permitted source first.').
            return Observation(None, "No page is open. Navigate to a permitted source first.")
        # Set observation to self._read_content().
        observation = self._read_content()
        # Return Observation(observation.url, search_passages(observation.text, query)).
        return Observation(observation.url, search_passages(observation.text, query))

    # Define _read_content with parameters self.
    def _read_content(self) -> Observation:
        # Check whether self._navigation_failure is not None.
        if self._navigation_failure is not None:
            # Return self._navigation_failure.
            return self._navigation_failure
        # Set url to self.page.url.
        url = self.page.url
        # Check whether url equals 'about:blank'.
        if url == "about:blank":
            # Return Observation(None, 'Blank desktop. No page is open.').
            return Observation(None, "Blank desktop. No page is open.")
        # Set content to self.page.locator('body').
        content = self.page.locator("body")
        # Set text to None.
        text = None
        # Set candidates to None.
        candidates = None
        # Check whether urlsplit(url).hostname equals 'en.wikipedia.org'.
        if urlsplit(url).hostname == "en.wikipedia.org":
            # Set article to self.page.locator('#mw-content-text .mw-parser-output').
            article = self.page.locator("#mw-content-text .mw-parser-output")
            # Check whether article.count().
            if article.count():
                # Set extracted to article.first.evaluate(WIKIPEDIA_CONTENT).
                extracted = article.first.evaluate(WIKIPEDIA_CONTENT)
                # Check whether extracted['text'] with surrounding whitespace removed.
                if extracted["text"].strip():
                    # Set (text, candidates) to (extracted['text'], extracted['links']).
                    text, candidates = extracted["text"], extracted["links"]
        for selector in (() if text is not None else ("main", '[role="main"]', "article")):
            # Set regions to self.page.locator(selector).
            regions = self.page.locator(selector)
            # Check whether regions.count() equals 0.
            if regions.count() == 0:
                # Skip this item and continue with the next iteration.
                continue
            # Set candidate to regions.first.
            candidate = regions.first
            # Set candidate_text to candidate.inner_text(timeout=10000).
            candidate_text = candidate.inner_text(timeout=10000)
            # Check whether candidate_text with surrounding whitespace removed.
            if candidate_text.strip():
                # Set (content, text) to (candidate, candidate_text).
                content, text = candidate, candidate_text
                # Stop this loop.
                break
        # Check whether text is None.
        if text is None:
            # Set text to content.inner_text(timeout=10000).
            text = content.inner_text(timeout=10000)
        # Automation evaluates this fixed expression even with page scripts disabled.
        # a.href resolves relative links and honors document.baseURI. Never evaluate
        # code supplied by the model or page text.
        # Check whether candidates is None.
        if candidates is None:
            # Set candidates to the result of content.locator('a[href]').evaluate_all using the
            # arguments below.
            # string line 1: Use this literal content: anchors =>.
            # string line 2: Use this literal content: anchors.slice(0, 400).map(a => ({.
            # string line 3: Use this literal content: label: (a.innerText || a.textContent ||
            # '').slice(0, 160),.
            # string line 4: Use this literal content: url: a.href.
            # string line 5: Close this embedded-language block or expression.
            candidates = content.locator("a[href]").evaluate_all("""anchors =>
                anchors.slice(0, 400).map(a => ({
                    label: (a.innerText || a.textContent || '').slice(0, 160),
                    url: a.href
                }))""")
        # Return Observation(url, text, page_links(url, candidates)).
        return Observation(url, text, page_links(url, candidates))

    # Define navigate with parameters self, url.
    def navigate(self, url: str) -> None:
        # Import from playwright.sync_api: Error as PlaywrightError (the SDK browser exception used
        # to distinguish policy navigation failures).
        from playwright.sync_api import Error as PlaywrightError

        # Set decision to authorize(self.grant, ToolCall('navigate', {'url': url})).
        decision = authorize(self.grant, ToolCall("navigate", {"url": url}))
        # Check whether not (decision.allowed).
        if not decision.allowed:
            # Raise ValueError(decision.reason) to stop the normal path.
            raise ValueError(decision.reason)
        # Call self._blocked_document_frames.clear with no arguments.
        self._blocked_document_frames.clear()
        # Try the following operations; matching except clauses handle failures.
        try:
            # "load" waits until stylesheets have been applied or blocked, so the
            # next screenshot shows the drawn page rather than a blank tab.
            # Call self.page.goto with url.
            self.page.goto(url, wait_until="load", timeout=20000)
        # Handle PlaywrightError as error; unmatched errors propagate.
        except PlaywrightError as error:
            # Only a blocked main-frame document explains a recoverable policy
            # failure. Images and iframe blocks must not hide unrelated errors.
            # Check whether 'net::ERR_BLOCKED_BY_CLIENT' is not in error converted to a string.
            if "net::ERR_BLOCKED_BY_CLIENT" not in str(error):
                # Raise None (no value) to stop the normal path.
                raise
            # Set frame to self.session.send('Page.getFrameTree')['frameTree']['frame']['id'].
            frame = self.session.send("Page.getFrameTree")["frameTree"]["frame"]["id"]
            # Check whether frame is not in self._blocked_document_frames.
            if frame not in self._blocked_document_frames:
                # Raise None (no value) to stop the normal path.
                raise
            # Set self._navigation_failure to Observation(None, 'Navigation blocked by browser
            # policy. No page content was read. Choose another permitted source or finish with
            # available information.').
            self._navigation_failure = Observation(
                None,
                "Navigation blocked by browser policy. No page content was read. "
                "Choose another permitted source or finish with available information.",
            )
            # Return without a value.
            return
        # Set self._navigation_failure to None.
        self._navigation_failure = None
        # Append self.page.url to self.visited.
        self.visited.append(self.page.url)


# Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
@contextmanager
# Define open_e2b_desktop with parameters grant, sandbox_type, playwright_factory, lifetime_seconds.
def open_e2b_desktop(grant: TaskGrant, *, sandbox_type=None, playwright_factory=None, lifetime_seconds=180):
    """Own the desktop lifetime, including cleanup after initialization failure.

    `lifetime_seconds` is E2B's own kill timer: a safety net if our cleanup never
    runs. It covers setup, any viewer wait, and the agent run.
    """
    # Import httpx: makes HTTP requests or supplies mock HTTP transports in tests.
    import httpx

    # Check whether the exact type of lifetime_seconds is not int or not (60 is at most
    # lifetime_seconds and is at most 600).
    if type(lifetime_seconds) is not int or not 60 <= lifetime_seconds <= 600:
        # Raise ValueError('lifetime_seconds must be an integer from 60 to 600.') to stop the normal
        # path.
        raise ValueError("lifetime_seconds must be an integer from 60 to 600.")
    # If no sandbox implementation was supplied, use the real E2B SDK; tests can supply a fake.
    if sandbox_type is None:
        # Import from e2b_desktop: Sandbox (creates the provider desktop and exposes its
        # lifecycle/control API).
        from e2b_desktop import Sandbox
        # Use the imported Sandbox class as the factory for creating the desktop.
        sandbox_type = Sandbox
    # If no browser-control factory was supplied, use the real synchronous Playwright factory.
    if playwright_factory is None:
        # Import from playwright.sync_api: sync_playwright (owns a synchronous Playwright
        # browser-control session).
        from playwright.sync_api import sync_playwright
        # Save the Playwright factory so it can be called below.
        playwright_factory = sync_playwright
    # Set sandbox to sandbox_type.create(timeout=lifetime_seconds, network={'deny_out':
    # ['0.0.0.0/0'], 'allow_out': sorted(grant.allowed_hosts), 'allow_public_traffic': False}).
    sandbox = sandbox_type.create(timeout=lifetime_seconds, network={
        # Configure the provider to deny outbound IPv4 traffic by default.
        "deny_out": ["0.0.0.0/0"],
        # List the task’s permitted hosts as outbound exceptions.
        "allow_out": sorted(grant.allowed_hosts),
        # Require authenticated access to the sandbox’s exposed ports.
        "allow_public_traffic": False,
    })
    # Try the following operations; matching except clauses handle failures. The finally block runs
    # on every exit.
    try:
        # Call sandbox.commands.run with 'python3 -c ' plus shlex.quote(START_BROWSER).
        sandbox.commands.run("python3 -c " + shlex.quote(START_BROWSER), timeout=50)
        # Set relay to sandbox.commands.run('python3 -u -c ' + shlex.quote(RELAY) + ' >
        # /tmp/crescendo-relay.log 2>&1', background=True, timeout=0).
        relay = sandbox.commands.run(
            "python3 -u -c " + shlex.quote(RELAY) + " > /tmp/crescendo-relay.log 2>&1",
            # Pass keyword background = True.
            background=True, timeout=0,
        )
        # Call relay.disconnect with no arguments.
        relay.disconnect()
        # Call sandbox.commands.run with 'python3 -c ' plus shlex.quote(WAIT_READY).
        sandbox.commands.run("python3 -c " + shlex.quote(WAIT_READY), timeout=25)
        # Set host to sandbox.get_host(9223).
        host = sandbox.get_host(9223)
        # Set headers to {'e2b-traffic-access-token': sandbox.traffic_access_token}.
        headers = {"e2b-traffic-access-token": sandbox.traffic_access_token}
        # Only send the sandbox token to its own authenticated control endpoint.
        # Set response to httpx.get(f'https://{host}/json/version', headers=headers, timeout=15).
        response = httpx.get(f"https://{host}/json/version", headers=headers, timeout=15)
        # Call response.raise_for_status with no arguments.
        response.raise_for_status()
        # Set path to urlsplit(response.json()['webSocketDebuggerUrl']).path.
        path = urlsplit(response.json()["webSocketDebuggerUrl"]).path
        # Check whether not (path.startswith('/devtools/browser/')).
        if not path.startswith("/devtools/browser/"):
            # Raise ValueError('Unexpected Chrome debugger endpoint') to stop the normal path.
            raise ValueError("Unexpected Chrome debugger endpoint")
        # Use playwright_factory() as playwright; leave the context and run its cleanup when this
        # block ends.
        with playwright_factory() as playwright:
            # Set browser to playwright.chromium.connect_over_cdp(f'wss://{host}{path}',
            # headers=headers, timeout=20000).
            browser = playwright.chromium.connect_over_cdp(
                # Pass keyword headers = headers.
                f"wss://{host}{path}", headers=headers, timeout=20000,
            )
            # Try the following operations; matching except clauses handle failures. The finally
            # block runs on every exit.
            try:
                # Set context to browser.new_context(java_script_enabled=False,
                # service_workers='block', accept_downloads=False).
                context = browser.new_context(
                    # Pass keyword java_script_enabled = False.
                    java_script_enabled=False, service_workers="block", accept_downloads=False,
                )
                # Set page to context.new_page().
                page = context.new_page()
                # Set desktop to the result of E2BDesktop using the arguments below.
                desktop = E2BDesktop(page, context.new_cdp_session(page), grant,
                                     # Supply a callback that captures PNG bytes when called.
                                     screenshot_provider=lambda: sandbox.screenshot(format="bytes"),
                                     # Supply the sandbox’s scroll method without calling it yet.
                                     scroll_provider=sandbox.scroll,
                                     # Supply the sandbox’s mouse-movement method without calling it yet.
                                     pointer_provider=sandbox.move_mouse,
                                     # Supply a callback that opens a live viewer when called.
                                     viewer_provider=lambda: _open_live_view(sandbox))
                # Give desktop to the caller and pause here until execution resumes.
                yield desktop
            # Always run cleanup, whether the operation succeeds, returns, or raises.
            finally:
                browser.close()
    # Always run cleanup, whether the operation succeeds, returns, or raises.
    finally:
        # Ask the provider to terminate sandbox.
        sandbox.kill()


# Define _open_live_view with parameters sandbox.
def _open_live_view(sandbox):
    # Import from .live_view: open_live_view (owns the authenticated loopback viewer and VNC stream
    # lifetime).
    from .live_view import open_live_view

    # Return open_live_view(sandbox).
    return open_live_view(sandbox)

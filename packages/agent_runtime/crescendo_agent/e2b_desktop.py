# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Policy-filtered Chrome, text observations, and desktop actions in E2B."""
# Learn: From contextlib, import contextmanager (turns a generator into a with-block resource lifetime).
from contextlib import contextmanager
# Learn: Import shlex: quotes fixed remote Python source safely for a shell command.
import shlex
# Learn: From typing, import Any (marks a deliberately unconstrained type, often at an SDK boundary).
from typing import Any
# Learn: From urllib.parse, import urldefrag (removes fragment identifiers when deduplicating destinations);
# urljoin (resolves relative links against the current page address); urlsplit (parses scheme, hostname,
# port, and path instead of guessing from substrings).
from urllib.parse import urldefrag, urljoin, urlsplit

# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping); authorize (checks task
# grants and argument bounds before a proposed tool can execute).
from crescendo_security.policy import TaskGrant, ToolCall, authorize

# Learn: From .browser_bootstrap, import RELAY (the fixed remote CDP TCP relay program); START_BROWSER (the
# fixed remote Chrome launch/readiness program); WAIT_READY (the fixed remote relay-readiness check).
from .browser_bootstrap import RELAY, START_BROWSER, WAIT_READY
# Learn: From .desktop, import Observation (holds current page URL, bounded text, and observed links);
# PageLink (holds one observed label and destination).
from .desktop import Observation, PageLink
# Learn: From .page_search, import search_passages (finds a bounded selection of lexical matches in
# current-page text).
from .page_search import search_passages


# Learn: Define page_links(url, candidates, limit, max_chars). The body runs when called, not when defined.
def page_links(url: str, candidates: list[dict], *, limit=20, max_chars=2000) -> tuple[PageLink, ...]:
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    """Bound untrusted links; inclusion never grants navigation authority."""
    # Learn: Set links to a new list (empty); the bounded observed links; listing a link does not grant
    # permission to open it.
    links = []
    # Learn: Set seen to a set of urldefrag(url)[0] (unique members); the values already encountered, used
    # to avoid duplicates.
    seen = {urldefrag(url)[0]}
    # Learn: Set remaining to max_chars; the remaining character budget for link output.
    remaining = max_chars
    # Learn: Iterate over candidates, binding item for each item.
    for item in candidates:
        # Learn: Take this branch only if the number of items/characters in links is at least limit.
        if len(links) >= limit:
            # Learn: Exit the nearest loop immediately; continue with the code after it.
            break
        # Learn: Try the following operations; matching except clauses handle failures.
        try:
            # Learn: Set destination to urldefrag(urljoin(url, item['url']))[0].
            destination = urldefrag(urljoin(url, item["url"]))[0]
            # Learn: Set parts to urlsplit(destination); the structured URL fields; use hostname and port
            # for destination checks.
            parts = urlsplit(destination)
            # Learn: Take this branch only if parts.scheme does not equal 'https' OR not (parts.hostname).
            if parts.scheme != "https" or not parts.hostname:
                # Learn: Skip the rest of this iteration and retry from the next loop iteration.
                continue
        # Learn: Handle ValueError; unmatched errors propagate.
        except ValueError:
            # Learn: Skip the rest of this iteration and retry from the next loop iteration.
            continue
        # Learn: Take this branch only if destination is in seen OR the number of items/characters in
        # destination is greater than 512.
        if destination in seen or len(destination) > 512:
            # Learn: Skip the rest of this iteration and retry from the next loop iteration.
            continue
        # Learn: Stage an object or add a value to this collection on seen; inputs: destination.
        seen.add(destination)
        # Learn: Set label to ' '.join(item['label'].split())[:80] OR destination.
        label = " ".join(item["label"].split())[:80] or destination
        # Learn: Set cost to the number of items/characters in label plus the number of items/characters in
        # destination.
        cost = len(label) + len(destination)
        # Learn: Take this branch only if cost is greater than remaining.
        if cost > remaining:
            # Learn: Skip the rest of this iteration and retry from the next loop iteration.
            continue
        # Learn: Update remaining using its previous value minus cost.
        remaining -= cost
        # Learn: Append one item to the ordered collection on links; inputs: PageLink(label, destination).
        links.append(PageLink(label, destination))
    # Learn: Return tuple(links) to the caller and stop this function.
    return tuple(links)

# Work on a detached copy: never mutate the page the agent is browsing. The
# filtered copy supplies both text and links; URL properties honor document.baseURI.
# Learn: Set WIKIPEDIA_CONTENT to 'root => {\n const copy = root.cloneNode(true);\n
# copy.querySelectorAll(\'nav, [role="naviga....
# Learn string line 1: Literal prompt, documentation, or fixture content: root => {. It remains unchanged at
# runtime.
# Learn string line 2: Clone the page subtree so text cleanup does not modify the visible page.
# Learn string line 3: Literal prompt, documentation, or fixture content: copy.querySelectorAll('nav,
# [role="navigation"], .infobox, .navbox, .sidebar, .metadata, script, style'). It remains unchanged at
# runtime.
# Learn string line 4: Remove excluded navigation/metadata elements from the detached copy.
# Learn string line 5: Walk text nodes in the selected document without executing page-supplied code.
# Learn string line 6: Declare a JavaScript binding for chunks = [];.
# Learn string line 7: Literal prompt, documentation, or fixture content: while (walker.nextNode()) {. It
# remains unchanged at runtime.
# Learn string line 8: Declare a JavaScript binding for text = walker.currentNode.textContent.trim();.
# Learn string line 9: Literal prompt, documentation, or fixture content: if (text) chunks.push(text);. It
# remains unchanged at runtime.
# Learn string line 10: Close this embedded-language block or expression.
# Learn string line 11: Return the fixed expression result to the host automation.
# Learn string line 12: Literal prompt, documentation, or fixture content: text: chunks.join(' '),. It
# remains unchanged at runtime.
# Learn string line 13: Literal prompt, documentation, or fixture content: links:
# Array.from(copy.querySelectorAll('a[href]')).slice(0, 400).map(a => ({. It remains unchanged at runtime.
# Learn string line 14: Literal prompt, documentation, or fixture content: label: (a.textContent ||
# '').slice(0, 160), url: a.href. It remains unchanged at runtime.
# Learn string line 15: Close this embedded-language block or expression.
# Learn string line 16: Close this embedded-language block or expression.
# Learn string line 17: Close this embedded-language block or expression.
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
# Learn: Set SCROLL_POINTER to the tuple (512, 440) (positional values).
SCROLL_POINTER = (512, 440)

# Chrome resource types the request filter may continue (permitted hosts, GET only).
# Learn: Set ALLOWED_RESOURCE_TYPES to frozenset({'Document', 'Stylesheet'}).
ALLOWED_RESOURCE_TYPES = frozenset({"Document", "Stylesheet"})


# Learn: Define E2BDesktop. Indented methods and attributes belong to this class.
class E2BDesktop:
    # Learn: Define __init__(page, session, grant, max_chars, screenshot_provider, scroll_provider,
    # pointer_provider, viewer_provider). This initializes or validates each new instance.
    def __init__(self, page: Any, session: Any, grant: TaskGrant, *, max_chars=4000, screenshot_provider=None, scroll_provider=None, pointer_provider=None, viewer_provider=None):
        # Learn: Set self.page to page; the browser tab controlled by Playwright.
        self.page = page
        # Learn: Set self.session to session; the database unit of work or browser CDP session, as selected
        # by this function.
        self.session = session
        # Learn: Set self.grant to grant; the task identity and fixed tool/host permissions; model output
        # cannot expand these.
        self.grant = grant
        # Learn: Set self.max_chars to max_chars.
        self.max_chars = max_chars
        # Learn: Set self._screenshot_provider to screenshot_provider.
        self._screenshot_provider = screenshot_provider
        # Learn: Set self._scroll_provider to scroll_provider.
        self._scroll_provider = scroll_provider
        # Learn: Set self._pointer_provider to pointer_provider.
        self._pointer_provider = pointer_provider
        # Learn: Set self._viewer_provider to viewer_provider.
        self._viewer_provider = viewer_provider
        # Learn: Set self.visited to a new list (empty); the successful navigation destinations observed by
        # the adapter.
        self.visited: list[str] = []
        # Learn: Set self.blocked_requests to a new list (empty); the browser requests rejected by the
        # request filter.
        self.blocked_requests: list[str] = []
        # Learn: Set self._blocked_document_frames to set().
        self._blocked_document_frames: set[str] = set()
        # Learn: Set self._navigation_failure to None (no value).
        self._navigation_failure: Observation | None = None
        # Learn: Call session.on with the arguments shown.
        session.on("Fetch.requestPaused", self._request_paused)
        # Learn: Send this protocol command or message to the selected peer on session; inputs:
        # 'Fetch.enable', a new dictionary with keys 'patterns'.
        session.send("Fetch.enable", {"patterns": [
            # Learn: Add this item to the surrounding list: {"urlPattern": "*", "requestStage": "Request"},.
            {"urlPattern": "*", "requestStage": "Request"},
        # Learn: Close this list literal; delimiters group the values into one object.
        ]})

    # Learn: Define capture_screen(). The body runs when called, not when defined.
    def capture_screen(self):
        # Learn: From .vision, import Screenshot (validates the PNG container and dimensions at the image
        # boundary).
        from .vision import Screenshot

        # Learn: Set decision to authorize(self.grant, ToolCall('screenshot')); the gateway allow/deny
        # result and its explanation. Check the proposed action against the fixed task grant before any
        # effect.
        decision = authorize(self.grant, ToolCall("screenshot"))
        # Learn: Take this branch only if not (decision.allowed).
        if not decision.allowed:
            # Learn: Raise ValueError(decision.reason) to stop the normal path.
            raise ValueError(decision.reason)
        # Learn: Take this branch only if self._screenshot_provider is None (no value).
        if self._screenshot_provider is None:
            # Learn: Raise RuntimeError('Desktop screenshot provider is not configured.') to stop the normal
            # path.
            raise RuntimeError("Desktop screenshot provider is not configured.")
        # Ensure the controlled tab is foregrounded before full-desktop capture.
        # Learn: Foreground the controlled tab before screenshot or wheel input on self.page.
        self.page.bring_to_front()
        # Learn: Set image to self._screenshot_provider().
        image = self._screenshot_provider()
        # E2B filesystem.read(format="bytes") returns bytearray in this SDK.
        # Normalize at the provider boundary; Screenshot stays immutable bytes.
        # Learn: Take this branch only if image has type bytearray (including subclasses).
        if isinstance(image, bytearray):
            # Learn: Set image to bytes(image).
            image = bytes(image)
        # Learn: Return Screenshot(image) to the caller and stop this function.
        return Screenshot(image)

    # Learn: Define scroll(direction, amount). The body runs when called, not when defined.
    def scroll(self, direction: str, amount: int) -> None:
        # Learn: Set decision to authorize(self.grant, ToolCall('scroll', {'direction': direction, 'amount':
        # amount})); the gateway allow/deny result and its explanation. Check the proposed action against
        # the fixed task grant before any effect.
        decision = authorize(self.grant, ToolCall("scroll", {"direction": direction, "amount": amount}))
        # Learn: Take this branch only if not (decision.allowed).
        if not decision.allowed:
            # Learn: Raise ValueError(decision.reason) to stop the normal path.
            raise ValueError(decision.reason)
        # Learn: Take this branch only if self._scroll_provider is None (no value) OR self._pointer_provider
        # is None (no value).
        if self._scroll_provider is None or self._pointer_provider is None:
            # Learn: Raise RuntimeError('Desktop scroll and pointer providers are not configured.') to stop
            # the normal path.
            raise RuntimeError("Desktop scroll and pointer providers are not configured.")
        # Learn: Foreground the controlled tab before screenshot or wheel input on self.page.
        self.page.bring_to_front()
        # Move the REAL desktop pointer over page content first, so the wheel
        # targets the page rather than a panel or another window. A live probe
        # showed the wheel over the taskbar does not scroll the page. This is a
        # fixed position, not a general multi-window focus policy.
        # Learn: Call self._pointer_provider with the arguments shown.
        self._pointer_provider(*SCROLL_POINTER)
        # Learn: Call self._scroll_provider with the arguments shown.
        self._scroll_provider(direction=direction, amount=amount)

    # Learn: Define live_view(). The body runs when called, not when defined.
    def live_view(self):
        # Learn: Set decision to authorize(self.grant, ToolCall('view_desktop')); the gateway allow/deny
        # result and its explanation. Check the proposed action against the fixed task grant before any
        # effect.
        decision = authorize(self.grant, ToolCall("view_desktop"))
        # Learn: Take this branch only if not (decision.allowed).
        if not decision.allowed:
            # Learn: Raise ValueError(decision.reason) to stop the normal path.
            raise ValueError(decision.reason)
        # Learn: Take this branch only if self._viewer_provider is None (no value).
        if self._viewer_provider is None:
            # Learn: Raise RuntimeError('Desktop viewer is not configured.') to stop the normal path.
            raise RuntimeError("Desktop viewer is not configured.")
        # Learn: Return self._viewer_provider() to the caller and stop this function.
        return self._viewer_provider()

    # Learn: Define _request_paused(event). The body runs when called, not when defined.
    def _request_paused(self, event):
        # Learn: Set request to event['request'].
        request = event["request"]
        # Learn: Set url to request['url']; the destination or current page address.
        url = request["url"]
        # Learn: Try the following operations; matching except clauses handle failures.
        try:
            # Learn: Set allowed to authorize(self.grant, ToolCall('navigate', {'url': url})).allowed.
            allowed = authorize(self.grant, ToolCall("navigate", {"url": url})).allowed
        # Learn: Handle ValueError; unmatched errors propagate.
        except ValueError:
            # Learn: Set allowed to False.
            allowed = False
        # Pages and their stylesheets only, and only from permitted hosts: no
        # scripts, images, fonts, downloads, or non-GET requests. Stylesheets let
        # the vision model see the page laid out as a person would; any further
        # requests a stylesheet makes are paused and checked here as well.
        # Learn: Take this branch only if allowed AND request['method'] equals 'GET' AND
        # event['resourceType'] is in ALLOWED_RESOURCE_TYPES.
        if allowed and request["method"] == "GET" and event["resourceType"] in ALLOWED_RESOURCE_TYPES:
            # Learn: Send this protocol command or message to the selected peer on self.session; inputs:
            # 'Fetch.continueRequest', a new dictionary with keys 'requestId'.
            self.session.send("Fetch.continueRequest", {"requestId": event["requestId"]})
        # Learn: Run this alternative only when the preceding conditional did not select its first branch.
        else:
            # Learn: Append one item to the ordered collection on self.blocked_requests; inputs: url.
            self.blocked_requests.append(url)
            # Learn: Take this branch only if event['resourceType'] equals 'Document' AND event['frameId']
            # with None as the missing-key default.
            if event["resourceType"] == "Document" and event.get("frameId"):
                # Learn: Stage an object or add a value to this collection on self._blocked_document_frames;
                # inputs: event['frameId'].
                self._blocked_document_frames.add(event["frameId"])
            # Learn: Send this protocol command or message to the selected peer on self.session; inputs:
            # 'Fetch.failRequest', a new dictionary with keys 'requestId', 'errorReason'.
            self.session.send("Fetch.failRequest", {
                # Learn: Define this named mapping field: "requestId": event["requestId"], "errorReason":
                # "BlockedByClient",. The key selects the schema/configuration value.
                "requestId": event["requestId"], "errorReason": "BlockedByClient",
            # Learn: Close this dict literal; delimiters group the values into one object.
            })

    # Learn: Define observe(). The body runs when called, not when defined.
    def observe(self) -> Observation:
        # Learn: Set observation to self._read_content().
        observation = self._read_content()
        # Learn: Take this branch only if the number of items/characters in observation.text is greater than
        # self.max_chars.
        if len(observation.text) > self.max_chars:
            # Learn: Return Observation(observation.url, observation.text[:self.max_chars] + '\n[Page text
            # truncated]', observation.links) to the caller and stop this function.
            return Observation(observation.url, observation.text[:self.max_chars] + "\n[Page text truncated]", observation.links)
        # Learn: Return observation to the caller and stop this function.
        return observation

    # Learn: Define search_page(query). The body runs when called, not when defined.
    def search_page(self, query: str) -> Observation:
        # Learn: Take this branch only if self._navigation_failure is not None (no value).
        if self._navigation_failure is not None:
            # Learn: Return self._navigation_failure to the caller and stop this function.
            return self._navigation_failure
        # Learn: Take this branch only if self.page.url equals 'about:blank'.
        if self.page.url == "about:blank":
            # Learn: Return Observation(None, 'No page is open. Navigate to a permitted source first.') to
            # the caller and stop this function.
            return Observation(None, "No page is open. Navigate to a permitted source first.")
        # Learn: Set observation to self._read_content().
        observation = self._read_content()
        # Learn: Return Observation(observation.url, search_passages(observation.text, query)) to the caller
        # and stop this function.
        return Observation(observation.url, search_passages(observation.text, query))

    # Learn: Define _read_content(). The body runs when called, not when defined.
    def _read_content(self) -> Observation:
        # Learn: Take this branch only if self._navigation_failure is not None (no value).
        if self._navigation_failure is not None:
            # Learn: Return self._navigation_failure to the caller and stop this function.
            return self._navigation_failure
        # Learn: Set url to self.page.url; the destination or current page address.
        url = self.page.url
        # Learn: Take this branch only if url equals 'about:blank'.
        if url == "about:blank":
            # Learn: Return Observation(None, 'Blank desktop. No page is open.') to the caller and stop this
            # function.
            return Observation(None, "Blank desktop. No page is open.")
        # Learn: Set content to self.page.locator('body'); the selected page region or content to write.
        content = self.page.locator("body")
        # Learn: Set text to None (no value).
        text = None
        # Learn: Set candidates to None (no value); the bounded raw link candidates from the page.
        candidates = None
        # Learn: Take this branch only if urlsplit(url).hostname equals 'en.wikipedia.org'.
        if urlsplit(url).hostname == "en.wikipedia.org":
            # Learn: Set article to self.page.locator('#mw-content-text .mw-parser-output').
            article = self.page.locator("#mw-content-text .mw-parser-output")
            # Learn: Take this branch only if article.count().
            if article.count():
                # Learn: Set extracted to article.first.evaluate(WIKIPEDIA_CONTENT).
                extracted = article.first.evaluate(WIKIPEDIA_CONTENT)
                # Learn: Take this branch only if extracted['text'].strip().
                if extracted["text"].strip():
                    # Learn: Set (text, candidates) to the tuple (extracted['text'], extracted['links'])
                    # (positional values).
                    text, candidates = extracted["text"], extracted["links"]
        # Learn: Iterate over the tuple () (positional values) when text is not None (no value), otherwise
        # the tuple ('main', '[role="main"]', 'article') (positio..., binding selector for each item.
        for selector in (() if text is not None else ("main", '[role="main"]', "article")):
            # Learn: Set regions to self.page.locator(selector).
            regions = self.page.locator(selector)
            # Learn: Take this branch only if regions.count() equals 0.
            if regions.count() == 0:
                # Learn: Skip the rest of this iteration and retry from the next loop iteration.
                continue
            # Learn: Set candidate to regions.first.
            candidate = regions.first
            # Learn: Set candidate_text to candidate.inner_text(timeout=10000).
            candidate_text = candidate.inner_text(timeout=10000)
            # Learn: Take this branch only if candidate_text.strip().
            if candidate_text.strip():
                # Learn: Set (content, text) to the tuple (candidate, candidate_text) (positional values).
                content, text = candidate, candidate_text
                # Learn: Exit the nearest loop immediately; continue with the code after it.
                break
        # Learn: Take this branch only if text is None (no value).
        if text is None:
            # Learn: Set text to content.inner_text(timeout=10000).
            text = content.inner_text(timeout=10000)
        # Automation evaluates this fixed expression even with page scripts disabled.
        # a.href resolves relative links and honors document.baseURI. Never evaluate
        # code supplied by the model or page text.
        # Learn: Take this branch only if candidates is None (no value).
        if candidates is None:
            # Learn: Set candidates to content.locator('a[href]').evaluate_all("anchors =>\n
            # anchors.slice(0, 400).map(a => ({\n label: (a.innerText || a.textContent || ''...; the bounded
            # raw link candidates from the page.
            # Learn string line 1: Literal prompt, documentation, or fixture content: anchors =>. It remains
            # unchanged at runtime.
            # Learn string line 2: Literal prompt, documentation, or fixture content: anchors.slice(0,
            # 400).map(a => ({. It remains unchanged at runtime.
            # Learn string line 3: Literal prompt, documentation, or fixture content: label: (a.innerText ||
            # a.textContent || '').slice(0, 160),. It remains unchanged at runtime.
            # Learn string line 4: Literal prompt, documentation, or fixture content: url: a.href. It
            # remains unchanged at runtime.
            # Learn string line 5: Close this embedded-language block or expression.
            candidates = content.locator("a[href]").evaluate_all("""anchors =>
                anchors.slice(0, 400).map(a => ({
                    label: (a.innerText || a.textContent || '').slice(0, 160),
                    url: a.href
                }))""")
        # Learn: Return Observation(url, text, page_links(url, candidates)) to the caller and stop this
        # function.
        return Observation(url, text, page_links(url, candidates))

    # Learn: Define navigate(url). The body runs when called, not when defined.
    def navigate(self, url: str) -> None:
        # Learn: From playwright.sync_api, import Error as PlaywrightError (the SDK browser exception used
        # to distinguish policy navigation failures).
        from playwright.sync_api import Error as PlaywrightError

        # Learn: Set decision to authorize(self.grant, ToolCall('navigate', {'url': url})); the gateway
        # allow/deny result and its explanation. Check the proposed action against the fixed task grant
        # before any effect.
        decision = authorize(self.grant, ToolCall("navigate", {"url": url}))
        # Learn: Take this branch only if not (decision.allowed).
        if not decision.allowed:
            # Learn: Raise ValueError(decision.reason) to stop the normal path.
            raise ValueError(decision.reason)
        # Learn: Call self._blocked_document_frames.clear with no arguments.
        self._blocked_document_frames.clear()
        # Learn: Try the following operations; matching except clauses handle failures.
        try:
            # "load" waits until stylesheets have been applied or blocked, so the
            # next screenshot shows the drawn page rather than a blank tab.
            # Learn: Navigate this tab and wait using the explicit load/timeout policy on self.page; inputs:
            # url.
            self.page.goto(url, wait_until="load", timeout=20000)
        # Learn: Handle PlaywrightError as error; unmatched errors propagate.
        except PlaywrightError as error:
            # Only a blocked main-frame document explains a recoverable policy
            # failure. Images and iframe blocks must not hide unrelated errors.
            # Learn: Take this branch only if 'net::ERR_BLOCKED_BY_CLIENT' is not in str(error).
            if "net::ERR_BLOCKED_BY_CLIENT" not in str(error):
                # Learn: Raise None (no value) to stop the normal path.
                raise
            # Learn: Set frame to self.session.send('Page.getFrameTree')['frameTree']['frame']['id'].
            frame = self.session.send("Page.getFrameTree")["frameTree"]["frame"]["id"]
            # Learn: Take this branch only if frame is not in self._blocked_document_frames.
            if frame not in self._blocked_document_frames:
                # Learn: Raise None (no value) to stop the normal path.
                raise
            # Learn: Set self._navigation_failure to Observation(None, 'Navigation blocked by browser
            # policy. No page content was read. Choose another permitted source or finish with av....
            self._navigation_failure = Observation(
                # Learn: Supply the next argument to Observation: None,.
                None,
                # Learn: Supply literal text 'Navigation blocked by browser policy. No page content was
                # read. Choose another permitted source or finish with available infor...; adjacent string
                # literals are concatenated without adding whitespace.
                "Navigation blocked by browser policy. No page content was read. "
                # Learn: Supply the next argument to Observation: "Choose another permitted source or finish
                # with available information.",.
                "Choose another permitted source or finish with available information.",
            # Learn: Close the argument list for Observation; the grouped expression remains one call.
            )
            # Learn: Return None (no value) to the caller and stop this function.
            return
        # Learn: Set self._navigation_failure to None (no value).
        self._navigation_failure = None
        # Learn: Append one item to the ordered collection on self.visited; inputs: self.page.url.
        self.visited.append(self.page.url)


# Learn: Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
@contextmanager
# Learn: Define open_e2b_desktop(grant, sandbox_type, playwright_factory, lifetime_seconds). The body runs
# when called, not when defined.
def open_e2b_desktop(grant: TaskGrant, *, sandbox_type=None, playwright_factory=None, lifetime_seconds=180):
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    # Learn string line 1: Literal prompt, documentation, or fixture content: Own the desktop lifetime,
    # including cleanup after initialization failure.. It remains unchanged at runtime.
    # Learn string line 3: Literal prompt, documentation, or fixture content: `lifetime_seconds` is E2B's
    # own kill timer: a safety net if our cleanup never. It remains unchanged at runtime.
    # Learn string line 4: Literal prompt, documentation, or fixture content: runs. It covers setup, any
    # viewer wait, and the agent run.. It remains unchanged at runtime.
    """Own the desktop lifetime, including cleanup after initialization failure.

    `lifetime_seconds` is E2B's own kill timer: a safety net if our cleanup never
    runs. It covers setup, any viewer wait, and the agent run.
    """
    # Learn: Import httpx: makes HTTP requests or supplies mock HTTP transports in tests.
    import httpx

    # Learn: Take this branch only if the exact Python type of lifetime_seconds is not int OR not (60 is at
    # most lifetime_seconds is at most 600).
    if type(lifetime_seconds) is not int or not 60 <= lifetime_seconds <= 600:
        # Learn: Raise ValueError('lifetime_seconds must be an integer from 60 to 600.') to stop the normal
        # path.
        raise ValueError("lifetime_seconds must be an integer from 60 to 600.")
    # Learn: Take this branch only if sandbox_type is None (no value).
    if sandbox_type is None:
        # Learn: From e2b_desktop, import Sandbox (creates the provider desktop and exposes its
        # lifecycle/control API).
        from e2b_desktop import Sandbox
        # Learn: Set sandbox_type to Sandbox.
        sandbox_type = Sandbox
    # Learn: Take this branch only if playwright_factory is None (no value).
    if playwright_factory is None:
        # Learn: From playwright.sync_api, import sync_playwright (owns a synchronous Playwright
        # browser-control session).
        from playwright.sync_api import sync_playwright
        # Learn: Set playwright_factory to sync_playwright.
        playwright_factory = sync_playwright
    # Learn: Set sandbox to sandbox_type.create(timeout=lifetime_seconds, network={'deny_out':
    # ['0.0.0.0/0'], 'allow_out': sorted(grant.allowed_hosts), 'allow_p...; the E2B desktop instance; its
    # owner must attempt cleanup. Create the requested SDK resource or provider response.
    sandbox = sandbox_type.create(timeout=lifetime_seconds, network={
        # Learn: Define this named mapping field: "deny_out": ["0.0.0.0/0"],. The key selects the
        # schema/configuration value.
        "deny_out": ["0.0.0.0/0"],
        # Learn: Define this named mapping field: "allow_out": sorted(grant.allowed_hosts),. The key selects
        # the schema/configuration value.
        "allow_out": sorted(grant.allowed_hosts),
        # Learn: Define this named mapping field: "allow_public_traffic": False,. The key selects the
        # schema/configuration value.
        "allow_public_traffic": False,
    # Learn: Close this dict literal; delimiters group the values into one object.
    })
    # Learn: Try the following operations; matching except clauses handle failures. The finally block runs
    # on every exit.
    try:
        # Learn: Run the fixed command or operation with the supplied bounds on sandbox.commands; inputs:
        # 'python3 -c ' plus shlex.quote(START_BROWSER).
        sandbox.commands.run("python3 -c " + shlex.quote(START_BROWSER), timeout=50)
        # Learn: Set relay to sandbox.commands.run('python3 -u -c ' + shlex.quote(RELAY) + ' >
        # /tmp/crescendo-relay.log 2>&1', background=True, timeout=0). Run the fixed command or operation
        # with the supplied bounds.
        relay = sandbox.commands.run(
            # Learn: Supply literal text ' > /tmp/crescendo-relay.log 2>&1'; adjacent string literals are
            # concatenated without adding whitespace.
            "python3 -u -c " + shlex.quote(RELAY) + " > /tmp/crescendo-relay.log 2>&1",
            # Learn: Pass keyword background = True.
            background=True, timeout=0,
        # Learn: Close the argument list for sandbox.commands.run; the grouped expression remains one call.
        )
        # Learn: Call relay.disconnect with no arguments.
        relay.disconnect()
        # Learn: Run the fixed command or operation with the supplied bounds on sandbox.commands; inputs:
        # 'python3 -c ' plus shlex.quote(WAIT_READY).
        sandbox.commands.run("python3 -c " + shlex.quote(WAIT_READY), timeout=25)
        # Learn: Set host to sandbox.get_host(9223); the parsed destination hostname rather than a substring
        # of the URL.
        host = sandbox.get_host(9223)
        # Learn: Set headers to a new dictionary with keys 'e2b-traffic-access-token'; the headers
        # explicitly supplied at this trust boundary.
        headers = {"e2b-traffic-access-token": sandbox.traffic_access_token}
        # Only send the sandbox token to its own authenticated control endpoint.
        # Learn: Set response to httpx[an f-string that substitutes the expressions in {...} into the text]
        # with None as the missing-key default; the returned HTTP or model-provider response. Read a
        # key/row, using the supplied default when applicable.
        response = httpx.get(f"https://{host}/json/version", headers=headers, timeout=15)
        # Learn: Raise on an unsuccessful HTTP status before parsing expected content on response.
        response.raise_for_status()
        # Learn: Set path to urlsplit(response.json()['webSocketDebuggerUrl']).path.
        path = urlsplit(response.json()["webSocketDebuggerUrl"]).path
        # Learn: Take this branch only if not (path.startswith('/devtools/browser/')).
        if not path.startswith("/devtools/browser/"):
            # Learn: Raise ValueError('Unexpected Chrome debugger endpoint') to stop the normal path.
            raise ValueError("Unexpected Chrome debugger endpoint")
        # Learn: Enter playwright_factory() as playwright. The context manager controls setup/exit; inspect
        # it for the actual cleanup behavior.
        with playwright_factory() as playwright:
            # Learn: Set browser to playwright.chromium.connect_over_cdp(f'wss://{host}{path}',
            # headers=headers, timeout=20000); the browser connection or WebSocket peer used in this scope.
            # Connect Playwright to the authenticated Chrome DevTools endpoint.
            browser = playwright.chromium.connect_over_cdp(
                # Learn: Pass keyword headers = headers.
                f"wss://{host}{path}", headers=headers, timeout=20000,
            # Learn: Close the argument list for playwright.chromium.connect_over_cdp; the grouped
            # expression remains one call.
            )
            # Learn: Try the following operations; matching except clauses handle failures. The finally
            # block runs on every exit.
            try:
                # Learn: Set context to browser.new_context(java_script_enabled=False,
                # service_workers='block', accept_downloads=False); the browser context or framework request
                # context used here. Create an isolated browser context using the explicit script/download
                # settings.
                context = browser.new_context(
                    # Learn: Pass keyword java_script_enabled = False.
                    java_script_enabled=False, service_workers="block", accept_downloads=False,
                # Learn: Close the argument list for browser.new_context; the grouped expression remains one
                # call.
                )
                # Learn: Set page to context.new_page(); the browser tab controlled by Playwright. Create
                # the browser tab controlled by this adapter.
                page = context.new_page()
                # Learn: Set desktop to E2BDesktop(page, context.new_cdp_session(page), grant,
                # screenshot_provider=lambda : sandbox.screenshot(format='bytes'), scroll_provi....
                desktop = E2BDesktop(page, context.new_cdp_session(page), grant,
                                     # Learn: Pass keyword screenshot_provider = lambda :
                                     # sandbox.screenshot(format='bytes').
                                     screenshot_provider=lambda: sandbox.screenshot(format="bytes"),
                                     # Learn: Pass keyword scroll_provider = sandbox.scroll.
                                     scroll_provider=sandbox.scroll,
                                     # Learn: Pass keyword pointer_provider = sandbox.move_mouse.
                                     pointer_provider=sandbox.move_mouse,
                                     # Learn: Pass keyword viewer_provider = lambda :
                                     # _open_live_view(sandbox).
                                     viewer_provider=lambda: _open_live_view(sandbox))
                # Learn: Yield desktop to the with-block/request; resume here for cleanup afterward.
                yield desktop
            # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
            finally:
                # Learn: Close this owned connection, stream, file, or browser resource on browser.
                browser.close()
    # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
    finally:
        # Learn: Ask E2B to terminate the sandbox; successful return alone is not independent termination
        # evidence on sandbox.
        sandbox.kill()


# Learn: Define _open_live_view(sandbox). The body runs when called, not when defined.
def _open_live_view(sandbox):
    # Learn: From .live_view, import open_live_view (owns the authenticated loopback viewer and VNC stream
    # lifetime).
    from .live_view import open_live_view

    # Learn: Return open_live_view(sandbox) to the caller and stop this function.
    return open_live_view(sandbox)

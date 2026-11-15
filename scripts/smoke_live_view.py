# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Real browser/local proxy smoke check with a simulated upstream, no paid calls."""
# Learn: Import asyncio: runs concurrent async tasks for streaming and coordination.
import asyncio
# Learn: From contextlib, import asynccontextmanager (turns an async generator into an async with-block
# resource lifetime).
from contextlib import asynccontextmanager
# Learn: From unittest.mock, import Mock (supplies configurable fake attributes and call recording); patch
# (temporarily replaces dependencies and restores them afterward).
from unittest.mock import Mock, patch

# Learn: Import httpx: makes HTTP requests or supplies mock HTTP transports in tests.
import httpx
# Learn: From playwright.sync_api, import sync_playwright (owns a synchronous Playwright browser-control
# session); expect (waits for and asserts browser UI conditions).
from playwright.sync_api import sync_playwright, expect

# Learn: From crescendo_agent, import live_view (a dependency used below).
from crescendo_agent import live_view

# Learn: Set HTML to b'<h1 id="status">Connecting to fixture</h1><script>\nconst ws = new
# WebSocket(\'ws://\' + l....
# Learn string line 1: Literal fixture markup rendered in the test browser; this is data to Python.
# Learn string line 2: Declare a JavaScript binding for ws = new WebSocket('ws://' + location.host +
# '/websockify', ['binary']);.
# Learn string line 3: Literal prompt, documentation, or fixture content: ws.binaryType = 'arraybuffer';. It
# remains unchanged at runtime.
# Learn string line 4: Literal prompt, documentation, or fixture content: ws.onopen = () => ws.send(new
# Uint8Array([82, 70, 66]));. It remains unchanged at runtime.
# Learn string line 5: Literal prompt, documentation, or fixture content: ws.onmessage = event => {
# document.querySelector('#status').textContent = new TextDecoder().decode(event.data); };. It remains
# unchanged at runtime.
# Learn string line 6: Literal fixture markup rendered in the test browser; this is data to Python.
HTML = b'''<h1 id="status">Connecting to fixture</h1><script>
const ws = new WebSocket('ws://' + location.host + '/websockify', ['binary']);
ws.binaryType = 'arraybuffer';
ws.onopen = () => ws.send(new Uint8Array([82, 70, 66]));
ws.onmessage = event => { document.querySelector('#status').textContent = new TextDecoder().decode(event.data); };
</script>'''


# Learn: Define main(). The body runs when called, not when defined.
def main():
    # Learn: Set sandbox to Mock(); the E2B desktop instance; its owner must attempt cleanup.
    sandbox = Mock()
    # Learn: Set sandbox.stream.get_url.return_value to 'https://fixture.e2b.app/vnc.html'.
    sandbox.stream.get_url.return_value = "https://fixture.e2b.app/vnc.html"
    # Learn: Set sandbox.stream.get_auth_key.return_value to 'fixture-vnc-password'.
    sandbox.stream.get_auth_key.return_value = "fixture-vnc-password"
    # Learn: Set sandbox.traffic_access_token to 'fixture-traffic-token'.
    sandbox.traffic_access_token = "fixture-traffic-token"
    # Learn: Set original to live_view.create_viewer_app.
    original = live_view.create_viewer_app

    # Learn: Define upstream(request). The body runs when called, not when defined.
    def upstream(request):
        # Learn: Assert that request.headers['e2b-traffic-access-token'] equals
        # sandbox.traffic_access_token. If false, this check fails with AssertionError.
        assert request.headers["e2b-traffic-access-token"] == sandbox.traffic_access_token
        # Learn: Return httpx.Response(200, content=HTML, headers={'content-type': 'text/html'}) to the
        # caller and stop this function.
        return httpx.Response(200, content=HTML, headers={"content-type": "text/html"})

    # Learn: Define create(). The body runs when called, not when defined.
    def create(*args, **kwargs):
        # Learn: Return original(*args, transport=httpx.MockTransport(upstream), **kwargs) to the caller and
        # stop this function.
        return original(*args, transport=httpx.MockTransport(upstream), **kwargs)

    # Learn: Define Remote. This test double replaces an external dependency.
    class Remote:
        # Learn: Set subprotocol to 'binary'.
        subprotocol = "binary"
        # Learn: Define __init__(). This initializes or validates each new instance.
        def __init__(self):
            # Learn: Set self.queue to asyncio.Queue().
            self.queue = asyncio.Queue()
        # Learn: Define an async function send(message). Awaited calls can yield control to other work. The
        # body runs when called, not when defined.
        async def send(self, message):
            # Learn: Await completion without blocking the event loop: Call self.queue.put with the
            # arguments shown.
            await self.queue.put(message)
        # Learn: Define __aiter__(). The body runs when called, not when defined.
        def __aiter__(self):
            # Learn: Return self to the caller and stop this function.
            return self
        # Learn: Define an async function __anext__(). Awaited calls can yield control to other work. The
        # body runs when called, not when defined.
        async def __anext__(self):
            # Learn: Return await self.queue.get() to the caller and stop this function.
            return await self.queue.get()

    # Learn: Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @asynccontextmanager
    # Learn: Define an async function connect(url). Awaited calls can yield control to other work. The body
    # runs when called, not when defined.
    async def connect(url, **kwargs):
        # Learn: Assert that url equals 'wss://fixture.e2b.app/websockify'. If false, this check fails with
        # AssertionError.
        assert url == "wss://fixture.e2b.app/websockify"
        # Learn: Assert that kwargs['additional_headers']['e2b-traffic-access-token'] equals
        # sandbox.traffic_access_token. If false, this check fails with AssertionError.
        assert kwargs["additional_headers"]["e2b-traffic-access-token"] == sandbox.traffic_access_token
        # Learn: Yield Remote() to the with-block/request; resume here for cleanup afterward.
        yield Remote()

    # Learn: Enter patch.object(live_view, 'create_viewer_app', create), patch.object(live_view, 'connect',
    # connect). The context manager controls setup/exit; inspect it for the actual cleanup behavior.
    with patch.object(live_view, "create_viewer_app", create), patch.object(live_view, "connect", connect):
        # Learn: Enter live_view.open_live_view(sandbox) as viewer. The context manager controls setup/exit;
        # inspect it for the actual cleanup behavior.
        with live_view.open_live_view(sandbox) as viewer:
            # Learn: Enter sync_playwright() as p. The context manager controls setup/exit; inspect it for
            # the actual cleanup behavior.
            with sync_playwright() as p:
                # Learn: Set browser to p.chromium.launch(channel='msedge', headless=True); the browser
                # connection or WebSocket peer used in this scope.
                browser = p.chromium.launch(channel="msedge", headless=True)
                # Learn: Try the following operations; matching except clauses handle failures. The finally
                # block runs on every exit.
                try:
                    # Learn: Set page to browser.new_page(); the browser tab controlled by Playwright.
                    # Create the browser tab controlled by this adapter.
                    page = browser.new_page()
                    # Learn: Navigate this tab and wait using the explicit load/timeout policy on page;
                    # inputs: viewer.url.
                    page.goto(viewer.url)
                    # Learn: Call expect(page.locator('#status')).to_have_text with the arguments shown.
                    expect(page.locator("#status")).to_have_text("RFB")
                    # Learn: Call viewer.wait_connected with no arguments.
                    viewer.wait_connected()
                    # Learn: Assert that 'fixture-traffic-token' is not in page.content(). If false, this
                    # check fails with AssertionError.
                    assert "fixture-traffic-token" not in page.content()
                    # Learn: Display diagnostic/result text without treating it as verified model evidence;
                    # inputs: 'PASS: browser session authenticated and binary WebSocket round trip
                    # completed'.
                    print("PASS: browser session authenticated and binary WebSocket round trip completed")
                # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
                finally:
                    # Learn: Close this owned connection, stream, file, or browser resource on browser.
                    browser.close()
        # Learn: Verify the fake dependency ran exactly once with these arguments on sandbox.stream.start.
        sandbox.stream.start.assert_called_once_with(require_auth=True)
        # Learn: Verify the fake dependency ran exactly once with these arguments on sandbox.stream.stop.
        sandbox.stream.stop.assert_called_once_with()
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: 'PASS:
    # local viewer and stream cleanup completed'.
    print("PASS: local viewer and stream cleanup completed")
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'Simulated upstream only; real E2B/noVNC connection still requires live verification'.
    print("Simulated upstream only; real E2B/noVNC connection still requires live verification")


# Learn: Take this branch only if __name__ equals '__main__'. The __main__ guard keeps imports from
# launching the CLI.
if __name__ == "__main__":
    # Learn: Call main with no arguments.
    main()

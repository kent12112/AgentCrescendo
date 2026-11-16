"""Real browser/local proxy smoke check with a simulated upstream, no paid calls."""
# Import asyncio: runs concurrent async tasks for streaming and coordination.
import asyncio
# Import from contextlib: asynccontextmanager (turns an async generator into an async with-block
# resource lifetime).
from contextlib import asynccontextmanager
# Import from unittest.mock: Mock (supplies configurable fake attributes and call recording); patch
# (temporarily replaces dependencies and restores them afterward).
from unittest.mock import Mock, patch

# Import httpx: makes HTTP requests or supplies mock HTTP transports in tests.
import httpx
# Import from playwright.sync_api: sync_playwright (owns a synchronous Playwright browser-control
# session); expect (waits for and asserts browser UI conditions).
from playwright.sync_api import sync_playwright, expect

# Import from crescendo_agent: live_view (a dependency used below).
from crescendo_agent import live_view

# Set HTML to b'<h1 id="status">Connecting to fixture</h1><script>\nconst ws = new
# WebSocket(\'ws://\' + location.host + \'/websockify\', [\'binary\']);\nws.binaryType =
# \'arraybuffer\';\nws.onopen = () => ws.send(new Uint8Array([82, 70, 66]));\nws.onmessage = event
# => { document.querySelector(\'#status\').textContent = new TextDecoder().decode(event.data);
# };\n</script>'.
# string line 1: Literal fixture markup rendered in the test browser; this is data to Python.
# string line 2: Declare a JavaScript binding for ws = new WebSocket('ws://' + location.host +
# '/websockify', ['binary']);.
# string line 3: Use this literal content: ws.binaryType = 'arraybuffer';.
# string line 4: Use this literal content: ws.onopen = () => ws.send(new Uint8Array([82, 70, 66]));.
# string line 5: Use this literal content: ws.onmessage = event => {
# document.querySelector('#status').textContent = new TextDecoder().decode(event.data); };.
# string line 6: Literal fixture markup rendered in the test browser; this is data to Python.
HTML = b'''<h1 id="status">Connecting to fixture</h1><script>
const ws = new WebSocket('ws://' + location.host + '/websockify', ['binary']);
ws.binaryType = 'arraybuffer';
ws.onopen = () => ws.send(new Uint8Array([82, 70, 66]));
ws.onmessage = event => { document.querySelector('#status').textContent = new TextDecoder().decode(event.data); };
</script>'''


# Define main with no parameters.
def main():
    # Set sandbox to Mock().
    sandbox = Mock()
    # Set sandbox.stream.get_url.return_value to 'https://fixture.e2b.app/vnc.html'.
    sandbox.stream.get_url.return_value = "https://fixture.e2b.app/vnc.html"
    # Set sandbox.stream.get_auth_key.return_value to 'fixture-vnc-password'.
    sandbox.stream.get_auth_key.return_value = "fixture-vnc-password"
    # Set sandbox.traffic_access_token to 'fixture-traffic-token'.
    sandbox.traffic_access_token = "fixture-traffic-token"
    # Set original to live_view.create_viewer_app.
    original = live_view.create_viewer_app

    # Define upstream with parameters request.
    def upstream(request):
        # Assert that request.headers['e2b-traffic-access-token'] equals
        # sandbox.traffic_access_token. If false, this check fails with AssertionError.
        assert request.headers["e2b-traffic-access-token"] == sandbox.traffic_access_token
        # Return httpx.Response(200, content=HTML, headers={'content-type': 'text/html'}).
        return httpx.Response(200, content=HTML, headers={"content-type": "text/html"})

    # Define create with no parameters.
    def create(*args, **kwargs):
        # Return original(*args, transport=httpx.MockTransport(upstream), **kwargs).
        return original(*args, transport=httpx.MockTransport(upstream), **kwargs)

    # Define Remote.
    class Remote:
        # Set subprotocol to 'binary'.
        subprotocol = "binary"
        # Define __init__ with parameters self.
        def __init__(self):
            # Set self.queue to asyncio.Queue().
            self.queue = asyncio.Queue()
        # Define send with parameters self, message.
        async def send(self, message):
            # Await completion without blocking the event loop: Call self.queue.put with the
            # arguments shown.
            await self.queue.put(message)
        # Define __aiter__ with parameters self.
        def __aiter__(self):
            # Return self.
            return self
        # Define __anext__ with parameters self.
        async def __anext__(self):
            # Return await self.queue.get().
            return await self.queue.get()

    # Wrap the generator as a context manager: yield enters the with-block and exit resumes cleanup.
    @asynccontextmanager
    # Define connect with parameters url.
    async def connect(url, **kwargs):
        # Assert that url equals 'wss://fixture.e2b.app/websockify'. If false, this check fails with
        # AssertionError.
        assert url == "wss://fixture.e2b.app/websockify"
        # Assert that kwargs['additional_headers']['e2b-traffic-access-token'] equals
        # sandbox.traffic_access_token. If false, this check fails with AssertionError.
        assert kwargs["additional_headers"]["e2b-traffic-access-token"] == sandbox.traffic_access_token
        # Give Remote() to the caller and pause here until execution resumes.
        yield Remote()

    # Use patch.object(live_view, 'create_viewer_app', create), patch.object(live_view, 'connect',
    # connect); leave the context and run its cleanup when this block ends.
    with patch.object(live_view, "create_viewer_app", create), patch.object(live_view, "connect", connect):
        # Use live_view.open_live_view(sandbox) as viewer; leave the context and run its cleanup
        # when this block ends.
        with live_view.open_live_view(sandbox) as viewer:
            # Use sync_playwright() as p; leave the context and run its cleanup when this block
            # ends.
            with sync_playwright() as p:
                # Set browser to p.chromium.launch(channel='msedge', headless=True).
                browser = p.chromium.launch(channel="msedge", headless=True)
                # Try the following operations; matching except clauses handle failures. The finally
                # block runs on every exit.
                try:
                    # Set page to browser.new_page().
                    page = browser.new_page()
                    # Call page.goto with viewer.url.
                    page.goto(viewer.url)
                    # Call expect(page.locator('#status')).to_have_text with 'RFB'.
                    expect(page.locator("#status")).to_have_text("RFB")
                    # Call viewer.wait_connected with no arguments.
                    viewer.wait_connected()
                    # Assert that 'fixture-traffic-token' is not in page.content(). If false, this
                    # check fails with AssertionError.
                    assert "fixture-traffic-token" not in page.content()
                    # Print 'PASS: browser session authenticated and binary WebSocket round trip
                    # completed'.
                    print("PASS: browser session authenticated and binary WebSocket round trip completed")
                # Always run cleanup, whether the operation succeeds, returns, or raises.
                finally:
                    browser.close()
        # Call sandbox.stream.start.assert_called_once_with with no arguments.
        sandbox.stream.start.assert_called_once_with(require_auth=True)
        # Call sandbox.stream.stop.assert_called_once_with with no arguments.
        sandbox.stream.stop.assert_called_once_with()
    # Print 'PASS: local viewer and stream cleanup completed'.
    print("PASS: local viewer and stream cleanup completed")
    # Print 'Simulated upstream only; real E2B/noVNC connection still requires live verification'.
    print("Simulated upstream only; real E2B/noVNC connection still requires live verification")


# Check whether __name__ equals '__main__'.
if __name__ == "__main__":
    # Call main with no arguments.
    main()

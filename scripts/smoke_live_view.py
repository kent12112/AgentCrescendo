"""Real browser/local proxy smoke check with a simulated upstream, no paid calls."""
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import Mock, patch

import httpx
from playwright.sync_api import sync_playwright, expect

from crescendo_agent import live_view

HTML = b'''<h1 id="status">Connecting to fixture</h1><script>
const ws = new WebSocket('ws://' + location.host + '/websockify', ['binary']);
ws.binaryType = 'arraybuffer';
ws.onopen = () => ws.send(new Uint8Array([82, 70, 66]));
ws.onmessage = event => { document.querySelector('#status').textContent = new TextDecoder().decode(event.data); };
</script>'''


def main():
    sandbox = Mock()
    sandbox.stream.get_url.return_value = "https://fixture.e2b.app/vnc.html"
    sandbox.stream.get_auth_key.return_value = "fixture-vnc-password"
    sandbox.traffic_access_token = "fixture-traffic-token"
    original = live_view.create_viewer_app

    def upstream(request):
        assert request.headers["e2b-traffic-access-token"] == sandbox.traffic_access_token
        return httpx.Response(200, content=HTML, headers={"content-type": "text/html"})

    def create(*args, **kwargs):
        return original(*args, transport=httpx.MockTransport(upstream), **kwargs)

    class Remote:
        subprotocol = "binary"
        def __init__(self):
            self.queue = asyncio.Queue()
        async def send(self, message):
            await self.queue.put(message)
        def __aiter__(self):
            return self
        async def __anext__(self):
            return await self.queue.get()

    @asynccontextmanager
    async def connect(url, **kwargs):
        assert url == "wss://fixture.e2b.app/websockify"
        assert kwargs["additional_headers"]["e2b-traffic-access-token"] == sandbox.traffic_access_token
        yield Remote()

    with patch.object(live_view, "create_viewer_app", create), patch.object(live_view, "connect", connect):
        with live_view.open_live_view(sandbox) as viewer:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="msedge", headless=True)
                try:
                    page = browser.new_page()
                    page.goto(viewer.url)
                    expect(page.locator("#status")).to_have_text("RFB")
                    viewer.wait_connected()
                    assert "fixture-traffic-token" not in page.content()
                    print("PASS: browser session authenticated and binary WebSocket round trip completed")
                finally:
                    browser.close()
        sandbox.stream.start.assert_called_once_with(require_auth=True)
        sandbox.stream.stop.assert_called_once_with()
    print("PASS: local viewer and stream cleanup completed")
    print("Simulated upstream only; real E2B/noVNC connection still requires live verification")


if __name__ == "__main__":
    main()

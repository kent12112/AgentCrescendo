"""Local Chromium fixture: no E2B, model calls, or external page responses.

Requires Playwright and installed Microsoft Edge. Run from the repository root.
"""
import base64

from playwright.sync_api import sync_playwright

from crescendo_agent.e2b_desktop import E2BDesktop
from crescendo_agent.loop import run_agent
from crescendo_agent.model import ScriptedModel
from crescendo_security.policy import TaskGrant, ToolCall


class FixtureSession:
    """Supply controlled responses only after the real interceptor allows them."""

    def __init__(self, session):
        self.session = session
        self.requests = {}

    def on(self, name, callback):
        def handle(event):
            self.requests[event["requestId"]] = event["request"]["url"]
            callback(event)
        self.session.on(name, handle)

    def send(self, name, params=None):
        if name != "Fetch.continueRequest":
            return self.session.send(name, params or {})
        # Chrome handles this synthetic HTTP redirect itself, emitting a new
        # Fetch.requestPaused event for the forbidden destination.
        if self.requests[params["requestId"]].endswith("/redirect"):
            response = {
                "requestId": params["requestId"], "responseCode": 302,
                "responseHeaders": [{"name": "Location", "value": "https://forbidden.example/"}],
            }
        else:
            response = {
                "requestId": params["requestId"], "responseCode": 200,
                "responseHeaders": [{"name": "Content-Type", "value": "text/html"}],
                "body": base64.b64encode(b"<html><body>Boston recovery facts</body></html>").decode(),
            }
        return self.session.send("Fetch.fulfillRequest", response)


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            context = browser.new_context(java_script_enabled=False, service_workers="block")
            page = context.new_page()
            session = FixtureSession(context.new_cdp_session(page))
            grant = TaskGrant("redirect-fixture", frozenset({"navigate", "finish"}),
                              frozenset({"allowed.example"}))
            desktop = E2BDesktop(page, session, grant)
            recovery_url = "https://allowed.example/recovery"
            model = ScriptedModel([
                ToolCall("navigate", {"url": "https://allowed.example/redirect"}),
                ToolCall("navigate", {"url": recovery_url}),
                ToolCall("finish", {"answer": "Boston recovery facts", "sources": [recovery_url]}),
            ])
            result = run_agent("Research Boston", grant, desktop, model)
            assert result.status == "finished"
            assert "https://forbidden.example/" in desktop.blocked_requests
            assert desktop.visited == [recovery_url]
            assert any("Navigation blocked by browser policy" in e.text for e in model.seen[1])
            assert desktop.observe().text == "Boston recovery facts"
            print("PASS: real Chromium redirect request blocked by interceptor")
            print("PASS: agent observed the block, opened another source, and finished")
            print("Controlled local responses; E2B networking remains unverified by this test")
        finally:
            browser.close()


if __name__ == "__main__":
    main()

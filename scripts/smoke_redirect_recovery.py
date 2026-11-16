"""Local Chromium fixture: no E2B, model calls, or external page responses.

Requires Playwright and installed Microsoft Edge. Run from the repository root.
"""
# Import base64: encodes PNG bytes as text for a model image data URL.
import base64

# Import from playwright.sync_api: sync_playwright (owns a synchronous Playwright browser-control
# session).
from playwright.sync_api import sync_playwright

# Import from crescendo_agent.e2b_desktop: E2BDesktop (a dependency used below).
from crescendo_agent.e2b_desktop import E2BDesktop
# Import from crescendo_agent.loop: run_agent (runs the bounded text observation/action loop).
from crescendo_agent.loop import run_agent
# Import from crescendo_agent.model: ScriptedModel (a dependency used below).
from crescendo_agent.model import ScriptedModel
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping).
from crescendo_security.policy import TaskGrant, ToolCall


# Define FixtureSession.
class FixtureSession:
    """Supply controlled responses only after the real interceptor allows them."""

    # Define __init__ with parameters self, session.
    def __init__(self, session):
        # Set self.session to session.
        self.session = session
        # Set self.requests to an empty dictionary.
        self.requests = {}

    # Define on with parameters self, name, callback.
    def on(self, name, callback):
        # Define handle with parameters event.
        def handle(event):
            # Set self.requests[event['requestId']] to event['request']['url'].
            self.requests[event["requestId"]] = event["request"]["url"]
            # Call callback with event.
            callback(event)
        # Call self.session.on with name, handle.
        self.session.on(name, handle)

    # Define send with parameters self, name, params.
    def send(self, name, params=None):
        # Check whether name does not equal 'Fetch.continueRequest'.
        if name != "Fetch.continueRequest":
            # Return self.session.send(name, params or {}).
            return self.session.send(name, params or {})
        # Chrome handles this synthetic HTTP redirect itself, emitting a new
        # Fetch.requestPaused event for the forbidden destination.
        # Check whether self.requests[params['requestId']].endswith('/redirect').
        if self.requests[params["requestId"]].endswith("/redirect"):
            # Build response from the entries below.
            response = {
                # Include requestId, responseCode in this dictionary.
                "requestId": params["requestId"], "responseCode": 302,
                # Include responseHeaders, name, value in this dictionary.
                "responseHeaders": [{"name": "Location", "value": "https://forbidden.example/"}],
            }
        # Run this alternative only when the preceding conditional did not select its first branch.
        else:
            # Build response from the entries below.
            response = {
                # Include requestId, responseCode in this dictionary.
                "requestId": params["requestId"], "responseCode": 200,
                # Include responseHeaders, name, value in this dictionary.
                "responseHeaders": [{"name": "Content-Type", "value": "text/html"}],
                # Include body in this dictionary.
                "body": base64.b64encode(b"<html><body>Boston recovery facts</body></html>").decode(),
            }
        # Return self.session.send('Fetch.fulfillRequest', response).
        return self.session.send("Fetch.fulfillRequest", response)


# Define main with no parameters.
def main():
    # Use sync_playwright() as playwright; leave the context and run its cleanup when this block
    # ends.
    with sync_playwright() as playwright:
        # Set browser to playwright.chromium.launch(channel='msedge', headless=True).
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Set context to browser.new_context(java_script_enabled=False,
            # service_workers='block').
            context = browser.new_context(java_script_enabled=False, service_workers="block")
            # Set page to context.new_page().
            page = context.new_page()
            # Set session to FixtureSession(context.new_cdp_session(page)).
            session = FixtureSession(context.new_cdp_session(page))
            # Set grant to TaskGrant('redirect-fixture', frozenset({'navigate', 'finish'}),
            # frozenset({'allowed.example'})).
            grant = TaskGrant("redirect-fixture", frozenset({"navigate", "finish"}),
                              # Call frozenset with the arguments shown.
                              frozenset({"allowed.example"}))
            # Set desktop to E2BDesktop(page, session, grant).
            desktop = E2BDesktop(page, session, grant)
            # Set recovery_url to 'https://allowed.example/recovery'.
            recovery_url = "https://allowed.example/recovery"
            # Set model to the result of ScriptedModel using the arguments below.
            model = ScriptedModel([
                # Call ToolCall with the arguments shown.
                ToolCall("navigate", {"url": "https://allowed.example/redirect"}),
                # Call ToolCall with the arguments shown.
                ToolCall("navigate", {"url": recovery_url}),
                # Call ToolCall with the arguments shown.
                ToolCall("finish", {"answer": "Boston recovery facts", "sources": [recovery_url]}),
            ])
            # Set result to run_agent('Research Boston', grant, desktop, model).
            result = run_agent("Research Boston", grant, desktop, model)
            # Assert that result.status equals 'finished'. If false, this check fails with
            # AssertionError.
            assert result.status == "finished"
            # Assert that 'https://forbidden.example/' is in desktop.blocked_requests. If false,
            # this check fails with AssertionError.
            assert "https://forbidden.example/" in desktop.blocked_requests
            # Assert that desktop.visited equals a new list containing recovery_url. If false, this
            # check fails with AssertionError.
            assert desktop.visited == [recovery_url]
            # Assert that any(('Navigation blocked by browser policy' in e.text for e in
            # model.seen[1])). If false, this check fails with AssertionError.
            assert any("Navigation blocked by browser policy" in e.text for e in model.seen[1])
            # Assert that desktop.observe().text equals 'Boston recovery facts'. If false, this
            # check fails with AssertionError.
            assert desktop.observe().text == "Boston recovery facts"
            # Print 'PASS: real Chromium redirect request blocked by interceptor'.
            print("PASS: real Chromium redirect request blocked by interceptor")
            # Print 'PASS: agent observed the block, opened another source, and finished'.
            print("PASS: agent observed the block, opened another source, and finished")
            # Print 'Controlled local responses; E2B networking remains unverified by this test'.
            print("Controlled local responses; E2B networking remains unverified by this test")
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            browser.close()


# Check whether __name__ equals '__main__'.
if __name__ == "__main__":
    # Call main with no arguments.
    main()

# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
# Learn string line 1: Literal prompt, documentation, or fixture content: Local Chromium fixture: no E2B,
# model calls, or external page responses.. It remains unchanged at runtime.
# Learn string line 3: Literal prompt, documentation, or fixture content: Requires Playwright and installed
# Microsoft Edge. Run from the repository root.. It remains unchanged at runtime.
"""Local Chromium fixture: no E2B, model calls, or external page responses.

Requires Playwright and installed Microsoft Edge. Run from the repository root.
"""
# Learn: Import base64: encodes PNG bytes as text for a model image data URL.
import base64

# Learn: From playwright.sync_api, import sync_playwright (owns a synchronous Playwright browser-control
# session).
from playwright.sync_api import sync_playwright

# Learn: From crescendo_agent.e2b_desktop, import E2BDesktop (a dependency used below).
from crescendo_agent.e2b_desktop import E2BDesktop
# Learn: From crescendo_agent.loop, import run_agent (runs the bounded text observation/action loop).
from crescendo_agent.loop import run_agent
# Learn: From crescendo_agent.model, import ScriptedModel (a dependency used below).
from crescendo_agent.model import ScriptedModel
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping).
from crescendo_security.policy import TaskGrant, ToolCall


# Learn: Define FixtureSession. Indented methods and attributes belong to this class.
class FixtureSession:
    # Learn: Document this module, class, or function with a docstring; it is not an action or a model
    # instruction.
    """Supply controlled responses only after the real interceptor allows them."""

    # Learn: Define __init__(session). This initializes or validates each new instance.
    def __init__(self, session):
        # Learn: Set self.session to session; the database unit of work or browser CDP session, as selected
        # by this function.
        self.session = session
        # Learn: Set self.requests to a new dictionary (empty).
        self.requests = {}

    # Learn: Define on(name, callback). The body runs when called, not when defined.
    def on(self, name, callback):
        # Learn: Define handle(event). The body runs when called, not when defined.
        def handle(event):
            # Learn: Set self.requests[event['requestId']] to event['request']['url'].
            self.requests[event["requestId"]] = event["request"]["url"]
            # Learn: Call callback with the arguments shown.
            callback(event)
        # Learn: Call self.session.on with the arguments shown.
        self.session.on(name, handle)

    # Learn: Define send(name, params). The body runs when called, not when defined.
    def send(self, name, params=None):
        # Learn: Take this branch only if name does not equal 'Fetch.continueRequest'.
        if name != "Fetch.continueRequest":
            # Learn: Return self.session.send(name, params or {}) to the caller and stop this function.
            return self.session.send(name, params or {})
        # Chrome handles this synthetic HTTP redirect itself, emitting a new
        # Fetch.requestPaused event for the forbidden destination.
        # Learn: Take this branch only if self.requests[params['requestId']].endswith('/redirect').
        if self.requests[params["requestId"]].endswith("/redirect"):
            # Learn: Set response to a new dictionary with keys 'requestId', 'responseCode',
            # 'responseHeaders'; the returned HTTP or model-provider response.
            response = {
                # Learn: Define this named mapping field: "requestId": params["requestId"], "responseCode":
                # 302,. The key selects the schema/configuration value.
                "requestId": params["requestId"], "responseCode": 302,
                # Learn: Define this named mapping field: "responseHeaders": [{"name": "Location", "value":
                # "https://forbidden.example/"}],. The key selects the schema/configuration value.
                "responseHeaders": [{"name": "Location", "value": "https://forbidden.example/"}],
            # Learn: Close this dict literal; delimiters group the values into one object.
            }
        # Learn: Run this alternative only when the preceding conditional did not select its first branch.
        else:
            # Learn: Set response to a new dictionary with keys 'requestId', 'responseCode',
            # 'responseHeaders', 'body'; the returned HTTP or model-provider response.
            response = {
                # Learn: Define this named mapping field: "requestId": params["requestId"], "responseCode":
                # 200,. The key selects the schema/configuration value.
                "requestId": params["requestId"], "responseCode": 200,
                # Learn: Define this named mapping field: "responseHeaders": [{"name": "Content-Type",
                # "value": "text/html"}],. The key selects the schema/configuration value.
                "responseHeaders": [{"name": "Content-Type", "value": "text/html"}],
                # Learn: Define this named mapping field: "body": base64.b64encode(b"<html><body>Boston
                # recovery facts</body></html>").decode(),. The key selects the schema/configuration value.
                "body": base64.b64encode(b"<html><body>Boston recovery facts</body></html>").decode(),
            # Learn: Close this dict literal; delimiters group the values into one object.
            }
        # Learn: Return self.session.send('Fetch.fulfillRequest', response) to the caller and stop this
        # function.
        return self.session.send("Fetch.fulfillRequest", response)


# Learn: Define main(). The body runs when called, not when defined.
def main():
    # Learn: Enter sync_playwright() as playwright. The context manager controls setup/exit; inspect it for
    # the actual cleanup behavior.
    with sync_playwright() as playwright:
        # Learn: Set browser to playwright.chromium.launch(channel='msedge', headless=True); the browser
        # connection or WebSocket peer used in this scope.
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        # Learn: Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Learn: Set context to browser.new_context(java_script_enabled=False, service_workers='block');
            # the browser context or framework request context used here. Create an isolated browser context
            # using the explicit script/download settings.
            context = browser.new_context(java_script_enabled=False, service_workers="block")
            # Learn: Set page to context.new_page(); the browser tab controlled by Playwright. Create the
            # browser tab controlled by this adapter.
            page = context.new_page()
            # Learn: Set session to FixtureSession(context.new_cdp_session(page)); the database unit of work
            # or browser CDP session, as selected by this function.
            session = FixtureSession(context.new_cdp_session(page))
            # Learn: Set grant to TaskGrant('redirect-fixture', frozenset({'navigate', 'finish'}),
            # frozenset({'allowed.example'})); the task identity and fixed tool/host permissions; model
            # output cannot expand these.
            grant = TaskGrant("redirect-fixture", frozenset({"navigate", "finish"}),
                              # Learn: Call frozenset with the arguments shown.
                              frozenset({"allowed.example"}))
            # Learn: Set desktop to E2BDesktop(page, session, grant).
            desktop = E2BDesktop(page, session, grant)
            # Learn: Set recovery_url to 'https://allowed.example/recovery'.
            recovery_url = "https://allowed.example/recovery"
            # Learn: Set model to ScriptedModel([ToolCall('navigate', {'url':
            # 'https://allowed.example/redirect'}), ToolCall('navigate', {'url': recovery_url}), ToolC...;
            # the provider adapter or scripted test model used to propose actions.
            model = ScriptedModel([
                # Learn: Call ToolCall with the arguments shown.
                ToolCall("navigate", {"url": "https://allowed.example/redirect"}),
                # Learn: Call ToolCall with the arguments shown.
                ToolCall("navigate", {"url": recovery_url}),
                # Learn: Call ToolCall with the arguments shown.
                ToolCall("finish", {"answer": "Boston recovery facts", "sources": [recovery_url]}),
            # Learn: Close this list literal; delimiters group the values into one object.
            ])
            # Learn: Set result to run_agent('Research Boston', grant, desktop, model); the operation
            # outcome for subsequent checks or reporting.
            result = run_agent("Research Boston", grant, desktop, model)
            # Learn: Assert that result.status equals 'finished'. If false, this check fails with
            # AssertionError.
            assert result.status == "finished"
            # Learn: Assert that 'https://forbidden.example/' is in desktop.blocked_requests. If false, this
            # check fails with AssertionError.
            assert "https://forbidden.example/" in desktop.blocked_requests
            # Learn: Assert that desktop.visited equals a new list containing recovery_url. If false, this
            # check fails with AssertionError.
            assert desktop.visited == [recovery_url]
            # Learn: Assert that any(('Navigation blocked by browser policy' in e.text for e in
            # model.seen[1])). If false, this check fails with AssertionError.
            assert any("Navigation blocked by browser policy" in e.text for e in model.seen[1])
            # Learn: Assert that desktop.observe().text equals 'Boston recovery facts'. If false, this check
            # fails with AssertionError.
            assert desktop.observe().text == "Boston recovery facts"
            # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
            # 'PASS: real Chromium redirect request blocked by interceptor'.
            print("PASS: real Chromium redirect request blocked by interceptor")
            # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
            # 'PASS: agent observed the block, opened another source, and finished'.
            print("PASS: agent observed the block, opened another source, and finished")
            # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
            # 'Controlled local responses; E2B networking remains unverified by this test'.
            print("Controlled local responses; E2B networking remains unverified by this test")
        # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Learn: Close this owned connection, stream, file, or browser resource on browser.
            browser.close()


# Learn: Take this branch only if __name__ equals '__main__'. The __main__ guard keeps imports from
# launching the CLI.
if __name__ == "__main__":
    # Learn: Call main with no arguments.
    main()

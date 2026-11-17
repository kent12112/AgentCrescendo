"""Local Chromium run of the browser network check: no E2B, no model, no internet.

Runs `collect()` and `judge()` from scripts/e2b_network_browser_check.py against
real Microsoft Edge and the real request filter (E2BDesktop._request_paused).
Requests the filter ALLOWS are answered locally instead of being sent: the
Wikipedia stylesheet gets a tiny CSS body, and /wiki/wikt:Boston gets a 301 to
Wiktionary, so the redirect case is exercised deterministically. Requests the
filter BLOCKS never reach this stand-in at all.

Requires Playwright and installed Microsoft Edge. Run from the repository root.
"""
import base64
import importlib.util
from pathlib import Path

from playwright.sync_api import sync_playwright

from crescendo_agent.e2b_desktop import E2BDesktop
from crescendo_security.policy import TaskGrant

spec = importlib.util.spec_from_file_location(
    "e2b_network_browser_check", Path(__file__).with_name("e2b_network_browser_check.py"))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class LocalResponses:
    """Stand in for the internet, only after the real filter said "continue"."""

    def __init__(self, session):
        self.session, self.urls = session, {}

    def on(self, name, callback):
        def handle(event):
            self.urls[event["requestId"]] = event["request"]["url"]
            callback(event)
        self.session.on(name, handle)

    def send(self, name, params=None):
        if name != "Fetch.continueRequest":
            return self.session.send(name, params or {})
        url = self.urls[params["requestId"]]
        if url == check.REDIRECT_SOURCE:
            status, headers, body = 301, [{"name": "Location", "value": "https://en.wiktionary.org/wiki/Boston"}], b""
        elif url == check.ALLOWED_CSS:
            status, headers, body = 200, [{"name": "Content-Type", "value": "text/css"}], b"body{margin:0}"
        else:
            status, headers, body = 200, [{"name": "Content-Type", "value": "text/html"}], b"<p>stand-in</p>"
        return self.session.send("Fetch.fulfillRequest", {
            "requestId": params["requestId"], "responseCode": status,
            "responseHeaders": headers, "body": base64.b64encode(body).decode()})


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        try:
            context = browser.new_context(java_script_enabled=False, service_workers="block",
                                          accept_downloads=False)
            page = context.new_page()
            grant = TaskGrant("subrequest-fixture", frozenset({"navigate"}), frozenset({"en.wikipedia.org"}))
            desktop = E2BDesktop(page, LocalResponses(context.new_cdp_session(page)), grant)
            evidence = check.collect(desktop)
        finally:
            browser.close()
    print(evidence)
    passed, lines = check.judge(evidence)
    print("\n".join(lines))
    if not passed:
        raise SystemExit("Local browser subrequest check failed.")
    print("Local browser subrequest check passed. No E2B, model, or internet requests were made.")


if __name__ == "__main__":
    main()

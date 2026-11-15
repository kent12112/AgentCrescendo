# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
# Learn string line 1: Literal prompt, documentation, or fixture content: Run from the repository root with
# API :8000 and frontend :3000 running.. It remains unchanged at runtime.
# Learn string line 3: Literal prompt, documentation, or fixture content: Requires the optional Playwright
# dependency and installed Microsoft Edge.. It remains unchanged at runtime.
# Learn string line 4: Literal prompt, documentation, or fixture content: Creates one temporary draft and
# removes it in cleanup. Uses local .env settings.. It remains unchanged at runtime.
"""Run from the repository root with API :8000 and frontend :3000 running.

Requires the optional Playwright dependency and installed Microsoft Edge.
Creates one temporary draft and removes it in cleanup. Uses local .env settings.
"""

# Learn: From uuid, import uuid4 (generates independent random UUID identifiers).
from uuid import uuid4

# Learn: Import httpx: makes HTTP requests or supplies mock HTTP transports in tests.
import httpx
# Learn: From playwright.sync_api, import expect (waits for and asserts browser UI conditions);
# sync_playwright (owns a synchronous Playwright browser-control session).
from playwright.sync_api import expect, sync_playwright

# Learn: From crescendo_api.config, import get_settings (loads and caches validated local configuration).
from crescendo_api.config import get_settings


# Learn: Define main(). The body runs when called, not when defined.
def main():
    # Learn: Set origin to 'http://127.0.0.1:3000'; the browser origin being checked before accepting a
    # write or WebSocket.
    origin = "http://127.0.0.1:3000"
    # Learn: Set goal to 'Dashboard deletion browser check ' plus str(uuid4()); the user task text.
    goal = "Dashboard deletion browser check " + str(uuid4())
    # Learn: Set headers to a new dictionary with keys 'Authorization'; the headers explicitly supplied at
    # this trust boundary.
    headers = {"Authorization": "Bearer " + get_settings().dev_api_token.get_secret_value()}
    # Learn: Enter httpx.Client(base_url='http://127.0.0.1:8000', headers=headers) as api. The context
    # manager controls setup/exit; inspect it for the actual cleanup behavior.
    with httpx.Client(base_url="http://127.0.0.1:8000", headers=headers) as api:
        # Learn: Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Learn: Enter sync_playwright() as p. The context manager controls setup/exit; inspect it for
            # the actual cleanup behavior.
            with sync_playwright() as p:
                # Learn: Set browser to p.chromium.launch(channel='msedge', headless=True); the browser
                # connection or WebSocket peer used in this scope.
                browser = p.chromium.launch(channel="msedge", headless=True)
                # Learn: Set page to browser.new_page(); the browser tab controlled by Playwright. Create
                # the browser tab controlled by this adapter.
                page = browser.new_page()
                # Learn: Navigate this tab and wait using the explicit load/timeout policy on page; inputs:
                # origin.
                page.goto(origin)
                # Learn: Call page.get_by_role('textbox', name='Your task', exact=True).fill with the
                # arguments shown.
                page.get_by_role("textbox", name="Your task", exact=True).fill(goal)
                # Learn: Call page.get_by_role('button', name='Save task draft').click with no arguments.
                page.get_by_role("button", name="Save task draft").click()
                # Learn: Set row to page.locator('article').filter(has_text=goal).
                row = page.locator("article").filter(has_text=goal)
                # Learn: Call expect(row).to_be_visible with no arguments.
                expect(row).to_be_visible()
                # Learn: Set run_id to next((r['id'] for r in api.get('/runs').json() if r['goal'] ==
                # goal)).
                run_id = next(r["id"] for r in api.get("/runs").json() if r["goal"] == goal)
                # Learn: Set button to row.get_by_role('button', name='Delete draft: ' + goal, exact=True).
                button = row.get_by_role("button", name="Delete draft: " + goal, exact=True)
                # Learn: Call page.once with the arguments shown.
                page.once("dialog", lambda d: d.dismiss())
                # Learn: Call button.click with no arguments.
                button.click()
                # Learn: Call expect(row).to_be_visible with no arguments.
                expect(row).to_be_visible()
                # Learn: Assert that api.get('/runs/' + run_id).status_code equals 200. If false, this check
                # fails with AssertionError.
                assert api.get("/runs/" + run_id).status_code == 200
                # Learn: Display diagnostic/result text without treating it as verified model evidence;
                # inputs: 'PASS: cancel preserves draft'.
                print("PASS: cancel preserves draft")

                # Learn: Set url to origin plus '/api/runs/' plus run_id; the destination or current page
                # address.
                url = origin + "/api/runs/" + run_id
                # Learn: Iterate over the tuple ({'Origin': 'http://untrusted.example'}, {}) (positional
                # values), binding request_headers for each item.
                for request_headers in ({"Origin": "http://untrusted.example"}, {}):
                    # Learn: Assert that page.request.delete(url, headers=request_headers).status equals
                    # 403. If false, this check fails with AssertionError.
                    assert page.request.delete(url, headers=request_headers).status == 403
                # Learn: Assert that api.get('/runs/' + run_id).status_code equals 200. If false, this check
                # fails with AssertionError.
                assert api.get("/runs/" + run_id).status_code == 200
                # Learn: Assert that page.request.delete(origin + '/api/runs/not-a-uuid', headers={'Origin':
                # origin}).status equals 422. If false, this check fails with AssertionError.
                assert page.request.delete(
                    # Learn: Pass keyword headers = a new dictionary with keys 'Origin'.
                    origin + "/api/runs/not-a-uuid", headers={"Origin": origin}
                # Learn: Supply the next argument to page.request.delete: ).status == 422.
                ).status == 422
                # Learn: Display diagnostic/result text without treating it as verified model evidence;
                # inputs: 'PASS: origin and UUID validation preserve data'.
                print("PASS: origin and UUID validation preserve data")

                # Learn: Set pattern to '**/api/runs/' plus run_id.
                pattern = "**/api/runs/" + run_id
                # Learn: Call page.route with the arguments shown.
                page.route(pattern, lambda route: route.fulfill(
                    # Learn: Pass keyword status = 503.
                    status=503, json={"detail": "Simulated API failure"}
                # Learn: Close the argument list for route.fulfill; the grouped expression remains one call.
                ))
                # Learn: Call page.once with the arguments shown.
                page.once("dialog", lambda d: d.accept())
                # Learn: Call button.click with no arguments.
                button.click()
                # Learn: Call expect(page.locator('.error[role=alert]')).to_contain_text with the arguments
                # shown.
                expect(page.locator(".error[role=alert]")).to_contain_text("Simulated API failure")
                # Learn: Call expect(row).to_be_visible with no arguments.
                expect(row).to_be_visible()
                # Learn: Call expect(button).to_be_enabled with no arguments.
                expect(button).to_be_enabled()
                # Learn: Assert that api.get('/runs/' + run_id).status_code equals 200. If false, this check
                # fails with AssertionError.
                assert api.get("/runs/" + run_id).status_code == 200
                # Learn: Call page.unroute with the arguments shown.
                page.unroute(pattern)
                # Learn: Display diagnostic/result text without treating it as verified model evidence;
                # inputs: 'PASS: failed delete shows error and preserves draft'.
                print("PASS: failed delete shows error and preserves draft")

                # Learn: Call page.once with the arguments shown.
                page.once("dialog", lambda d: d.accept())
                # Learn: Call button.click with no arguments.
                button.click()
                # Learn: Call expect(row).to_have_count with the arguments shown.
                expect(row).to_have_count(0)
                # Learn: Call expect(page.get_by_role('status')).to_contain_text with the arguments shown.
                expect(page.get_by_role("status")).to_contain_text("Draft deleted.")
                # Learn: Assert that api.get('/runs/' + run_id).status_code equals 404. If false, this check
                # fails with AssertionError.
                assert api.get("/runs/" + run_id).status_code == 404
                # Learn: Call page.reload with no arguments.
                page.reload()
                # Learn: Call expect(page.get_by_role('button', name='Refresh', exact=True)).to_be_visible
                # with no arguments.
                expect(page.get_by_role("button", name="Refresh", exact=True)).to_be_visible()
                # Learn: Call expect(page.locator('article').filter(has_text=goal)).to_have_count with the
                # arguments shown.
                expect(page.locator("article").filter(has_text=goal)).to_have_count(0)
                # Learn: Display diagnostic/result text without treating it as verified model evidence;
                # inputs: 'PASS: deletion through proxy persists after reload'.
                print("PASS: deletion through proxy persists after reload")
                # Learn: Close this owned connection, stream, file, or browser resource on browser.
                browser.close()
        # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Learn: Set response to api['/runs'] with None as the missing-key default; the returned HTTP or
            # model-provider response. Read a key/row, using the supplied default when applicable.
            response = api.get("/runs")
            # Learn: Raise on an unsuccessful HTTP status before parsing expected content on response.
            response.raise_for_status()
            # Learn: Iterate over response.json(), binding run for each item.
            for run in response.json():
                # Learn: Take this branch only if run['goal'] equals goal.
                if run["goal"] == goal:
                    # Learn: Assert that api.delete('/runs/' + run['id']).status_code is in the tuple (204,
                    # 404) (positional values). If false, this check fails with AssertionError.
                    assert api.delete("/runs/" + run["id"]).status_code in (204, 404)
            # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
            # 'CLEANUP: temporary draft removed'.
            print("CLEANUP: temporary draft removed")


# Learn: Take this branch only if __name__ equals '__main__'. The __main__ guard keeps imports from
# launching the CLI.
if __name__ == "__main__":
    # Learn: Call main with no arguments.
    main()

"""Run from the repository root with API :8000 and frontend :3000 running.

Requires the optional Playwright dependency and installed Microsoft Edge.
Creates one temporary draft and removes it in cleanup. Uses local .env settings.
"""

# Import from uuid: uuid4 (generates independent random UUID identifiers).
from uuid import uuid4

# Import httpx: makes HTTP requests or supplies mock HTTP transports in tests.
import httpx
# Import from playwright.sync_api: expect (waits for and asserts browser UI conditions);
# sync_playwright (owns a synchronous Playwright browser-control session).
from playwright.sync_api import expect, sync_playwright

# Import from crescendo_api.config: get_settings (loads and caches validated local configuration).
from crescendo_api.config import get_settings


# Define main with no parameters.
def main():
    # Set origin to 'http://127.0.0.1:3000'.
    origin = "http://127.0.0.1:3000"
    # Set goal to 'Dashboard deletion browser check ' plus a new random UUID converted to a string.
    goal = "Dashboard deletion browser check " + str(uuid4())
    # Set headers to {'Authorization': 'Bearer ' + get_settings().dev_api_token.get_secret_value()}.
    headers = {"Authorization": "Bearer " + get_settings().dev_api_token.get_secret_value()}
    # Use httpx.Client(base_url='http://127.0.0.1:8000', headers=headers) as api; leave the context
    # and run its cleanup when this block ends.
    with httpx.Client(base_url="http://127.0.0.1:8000", headers=headers) as api:
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Use sync_playwright() as p; leave the context and run its cleanup when this block
            # ends.
            with sync_playwright() as p:
                # Set browser to p.chromium.launch(channel='msedge', headless=True).
                browser = p.chromium.launch(channel="msedge", headless=True)
                # Set page to browser.new_page().
                page = browser.new_page()
                # Call page.goto with origin.
                page.goto(origin)
                # Call page.get_by_role('textbox', name='Your task', exact=True).fill with goal.
                page.get_by_role("textbox", name="Your task", exact=True).fill(goal)
                # Call page.get_by_role('button', name='Save task draft').click with no arguments.
                page.get_by_role("button", name="Save task draft").click()
                # Set row to page.locator('article').filter(has_text=goal).
                row = page.locator("article").filter(has_text=goal)
                # Call expect(row).to_be_visible with no arguments.
                expect(row).to_be_visible()
                # Set run_id to next((r['id'] for r in api.get('/runs').json() if r['goal'] ==
                # goal)).
                run_id = next(r["id"] for r in api.get("/runs").json() if r["goal"] == goal)
                # Set button to row.get_by_role('button', name='Delete draft: ' + goal, exact=True).
                button = row.get_by_role("button", name="Delete draft: " + goal, exact=True)
                # Call page.once with 'dialog', a function that returns d.dismiss() when called.
                page.once("dialog", lambda d: d.dismiss())
                # Call button.click with no arguments.
                button.click()
                # Call expect(row).to_be_visible with no arguments.
                expect(row).to_be_visible()
                # Assert that api.get('/runs/' + run_id).status_code equals 200. If false, this
                # check fails with AssertionError.
                assert api.get("/runs/" + run_id).status_code == 200
                # Print 'PASS: cancel preserves draft'.
                print("PASS: cancel preserves draft")

                # Set url to origin plus '/api/runs/' plus run_id.
                url = origin + "/api/runs/" + run_id
                # Iterate over the tuple ({'Origin': 'http://untrusted.example'}, {}) (positional
                # values), binding request_headers for each item.
                for request_headers in ({"Origin": "http://untrusted.example"}, {}):
                    # Assert that page.request.delete(url, headers=request_headers).status equals
                    # 403. If false, this check fails with AssertionError.
                    assert page.request.delete(url, headers=request_headers).status == 403
                # Assert that api.get('/runs/' + run_id).status_code equals 200. If false, this
                # check fails with AssertionError.
                assert api.get("/runs/" + run_id).status_code == 200
                # Assert that page.request.delete(origin + '/api/runs/not-a-uuid',
                # headers={'Origin': origin}).status equals 422. If false, this check fails with
                # AssertionError.
                assert page.request.delete(
                    # Pass keyword headers = a new dictionary with keys 'Origin'.
                    origin + "/api/runs/not-a-uuid", headers={"Origin": origin}
                ).status == 422
                # Print 'PASS: origin and UUID validation preserve data'.
                print("PASS: origin and UUID validation preserve data")

                # Set pattern to '**/api/runs/' plus run_id.
                pattern = "**/api/runs/" + run_id
                # Call page.route with pattern, a function that returns route.fulfill(status=503,
                # json={'detail': 'Simulated API failure'}) when called.
                page.route(pattern, lambda route: route.fulfill(
                    # Pass keyword status = 503.
                    status=503, json={"detail": "Simulated API failure"}
                ))
                # Call page.once with 'dialog', a function that returns d.accept() when called.
                page.once("dialog", lambda d: d.accept())
                # Call button.click with no arguments.
                button.click()
                # Call expect(page.locator('.error[role=alert]')).to_contain_text with 'Simulated
                # API failure'.
                expect(page.locator(".error[role=alert]")).to_contain_text("Simulated API failure")
                # Call expect(row).to_be_visible with no arguments.
                expect(row).to_be_visible()
                # Call expect(button).to_be_enabled with no arguments.
                expect(button).to_be_enabled()
                # Assert that api.get('/runs/' + run_id).status_code equals 200. If false, this
                # check fails with AssertionError.
                assert api.get("/runs/" + run_id).status_code == 200
                # Call page.unroute with pattern.
                page.unroute(pattern)
                # Print 'PASS: failed delete shows error and preserves draft'.
                print("PASS: failed delete shows error and preserves draft")

                # Call page.once with 'dialog', a function that returns d.accept() when called.
                page.once("dialog", lambda d: d.accept())
                # Call button.click with no arguments.
                button.click()
                # Call expect(row).to_have_count with 0.
                expect(row).to_have_count(0)
                # Call expect(page.get_by_role('status')).to_contain_text with 'Draft deleted.'.
                expect(page.get_by_role("status")).to_contain_text("Draft deleted.")
                # Assert that api.get('/runs/' + run_id).status_code equals 404. If false, this
                # check fails with AssertionError.
                assert api.get("/runs/" + run_id).status_code == 404
                # Call page.reload with no arguments.
                page.reload()
                # Call expect(page.get_by_role('button', name='Refresh', exact=True)).to_be_visible
                # with no arguments.
                expect(page.get_by_role("button", name="Refresh", exact=True)).to_be_visible()
                # Call expect(page.locator('article').filter(has_text=goal)).to_have_count with 0.
                expect(page.locator("article").filter(has_text=goal)).to_have_count(0)
                # Print 'PASS: deletion through proxy persists after reload'.
                print("PASS: deletion through proxy persists after reload")
                browser.close()
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Set response to api['/runs'], or None if absent.
            response = api.get("/runs")
            # Call response.raise_for_status with no arguments.
            response.raise_for_status()
            # Iterate over response.json(), binding run for each item.
            for run in response.json():
                # Check whether run['goal'] equals goal.
                if run["goal"] == goal:
                    # Assert that api.delete('/runs/' + run['id']).status_code is in the tuple (204,
                    # 404) (positional values). If false, this check fails with AssertionError.
                    assert api.delete("/runs/" + run["id"]).status_code in (204, 404)
            # Print 'CLEANUP: temporary draft removed'.
            print("CLEANUP: temporary draft removed")


# Check whether __name__ equals '__main__'.
if __name__ == "__main__":
    # Call main with no arguments.
    main()

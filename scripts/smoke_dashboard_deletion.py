"""Run from the repository root with API :8000 and frontend :3000 running.

Requires the optional Playwright dependency and installed Microsoft Edge.
Creates one temporary draft and removes it in cleanup. Uses local .env settings.
"""

from uuid import uuid4

import httpx
from playwright.sync_api import expect, sync_playwright

from crescendo_api.config import get_settings


def main():
    origin = "http://127.0.0.1:3000"
    goal = "Dashboard deletion browser check " + str(uuid4())
    headers = {"Authorization": "Bearer " + get_settings().dev_api_token.get_secret_value()}
    with httpx.Client(base_url="http://127.0.0.1:8000", headers=headers) as api:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page()
                page.goto(origin)
                page.get_by_role("textbox", name="Your task", exact=True).fill(goal)
                page.get_by_role("button", name="Save task draft").click()
                row = page.locator("article").filter(has_text=goal)
                expect(row).to_be_visible()
                run_id = next(r["id"] for r in api.get("/runs").json() if r["goal"] == goal)
                button = row.get_by_role("button", name="Delete draft: " + goal, exact=True)
                page.once("dialog", lambda d: d.dismiss())
                button.click()
                expect(row).to_be_visible()
                assert api.get("/runs/" + run_id).status_code == 200
                print("PASS: cancel preserves draft")

                url = origin + "/api/runs/" + run_id
                for request_headers in ({"Origin": "http://untrusted.example"}, {}):
                    assert page.request.delete(url, headers=request_headers).status == 403
                assert api.get("/runs/" + run_id).status_code == 200
                assert page.request.delete(
                    origin + "/api/runs/not-a-uuid", headers={"Origin": origin}
                ).status == 422
                print("PASS: origin and UUID validation preserve data")

                pattern = "**/api/runs/" + run_id
                page.route(pattern, lambda route: route.fulfill(
                    status=503, json={"detail": "Simulated API failure"}
                ))
                page.once("dialog", lambda d: d.accept())
                button.click()
                expect(page.locator(".error[role=alert]")).to_contain_text("Simulated API failure")
                expect(row).to_be_visible()
                expect(button).to_be_enabled()
                assert api.get("/runs/" + run_id).status_code == 200
                page.unroute(pattern)
                print("PASS: failed delete shows error and preserves draft")

                page.once("dialog", lambda d: d.accept())
                button.click()
                expect(row).to_have_count(0)
                expect(page.get_by_role("status")).to_contain_text("Draft deleted.")
                assert api.get("/runs/" + run_id).status_code == 404
                page.reload()
                expect(page.get_by_role("button", name="Refresh", exact=True)).to_be_visible()
                expect(page.locator("article").filter(has_text=goal)).to_have_count(0)
                print("PASS: deletion through proxy persists after reload")
                browser.close()
        finally:
            response = api.get("/runs")
            response.raise_for_status()
            for run in response.json():
                if run["goal"] == goal:
                    assert api.delete("/runs/" + run["id"]).status_code in (204, 404)
            print("CLEANUP: temporary draft removed")


if __name__ == "__main__":
    main()

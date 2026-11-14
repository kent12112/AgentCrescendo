"""Demonstrate bounded page search in installed Edge, without paid calls."""
from playwright.sync_api import sync_playwright

from crescendo_agent.e2b_desktop import E2BDesktop
from crescendo_agent.loop import run_agent
from crescendo_agent.model import ScriptedModel
from crescendo_security.policy import TaskGrant, ToolCall


def main():
    url = "https://allowed.example/boston"
    html = "<main><h1>Boston research fixture</h1>" + "<p>Unrelated history and geography.</p>" * 250
    html += "<h2>Demographics</h2><p>Population at the 2020 census: 675,647 residents.</p></main>"
    grant = TaskGrant("search-fixture", frozenset({"search_page", "finish"}), frozenset({"allowed.example"}))
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            context = browser.new_context(java_script_enabled=False, service_workers="block")
            context.route("**/*", lambda route: route.fulfill(status=200, content_type="text/html", body=html))
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded")
            desktop = E2BDesktop(page, context.new_cdp_session(page), grant)
            preview = desktop.observe()
            assert "675,647" not in preview.text
            model = ScriptedModel([
                ToolCall("search_page", {"query": "population 2020"}),
                ToolCall("finish", {"answer": "675,647 residents at the 2020 census", "sources": [url]}),
            ])
            result = run_agent("What was Boston's population in 2020?", grant, desktop, model)
            assert result.status == "finished"
            observation = [entry for entry in model.seen[1] if entry.kind == "observation"][-1]
            assert "2020 census: 675,647 residents" in observation.text
            assert url in observation.text
            assert len(observation.text) < 1300
            print("PASS: fact absent from 4,000-character preview, found by search")
            print("Preview characters:", len(preview.text))
            print("Search observation characters (including URL):", len(observation.text))
            print("Observation delivered to the scripted model:\n" + observation.text)
            print("No paid calls. Character counts are not token measurements or total-run cost savings.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()

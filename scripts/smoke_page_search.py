"""Demonstrate bounded page search in installed Edge, without paid calls."""
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


# Define main with no parameters.
def main():
    # Set url to 'https://allowed.example/boston'.
    url = "https://allowed.example/boston"
    # Set html to '<main><h1>Boston research fixture</h1>' plus '<p>Unrelated history and
    # geography.</p>' times 250.
    html = "<main><h1>Boston research fixture</h1>" + "<p>Unrelated history and geography.</p>" * 250
    # Update html using its previous value plus '<h2>Demographics</h2><p>Population at the 2020
    # census: 675,647 residents.</p></main>'.
    html += "<h2>Demographics</h2><p>Population at the 2020 census: 675,647 residents.</p></main>"
    # Set grant to TaskGrant('search-fixture', frozenset({'search_page', 'finish'}),
    # frozenset({'allowed.example'})).
    grant = TaskGrant("search-fixture", frozenset({"search_page", "finish"}), frozenset({"allowed.example"}))
    # Use sync_playwright() as p; leave the context and run its cleanup when this block ends.
    with sync_playwright() as p:
        # Set browser to p.chromium.launch(channel='msedge', headless=True).
        browser = p.chromium.launch(channel="msedge", headless=True)
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Set context to browser.new_context(java_script_enabled=False,
            # service_workers='block').
            context = browser.new_context(java_script_enabled=False, service_workers="block")
            # Call context.route with '**/*', a function that returns route.fulfill(status=200,
            # content_type='text/html', body=html) when called.
            context.route("**/*", lambda route: route.fulfill(status=200, content_type="text/html", body=html))
            # Set page to context.new_page().
            page = context.new_page()
            # Call page.goto with url.
            page.goto(url, wait_until="domcontentloaded")
            # Set desktop to E2BDesktop(page, context.new_cdp_session(page), grant).
            desktop = E2BDesktop(page, context.new_cdp_session(page), grant)
            # Set preview to desktop.observe().
            preview = desktop.observe()
            # Assert that '675,647' is not in preview.text. If false, this check fails with
            # AssertionError.
            assert "675,647" not in preview.text
            # Set model to ScriptedModel([ToolCall('search_page', {'query': 'population 2020'}),
            # ToolCall('finish', {'answer': '675,647 residents at the 2020 census', 'sources':
            # [url]})]).
            model = ScriptedModel([
                # Call ToolCall with the arguments shown.
                ToolCall("search_page", {"query": "population 2020"}),
                # Call ToolCall with the arguments shown.
                ToolCall("finish", {"answer": "675,647 residents at the 2020 census", "sources": [url]}),
            ])
            # Set result to run_agent("What was Boston's population in 2020?", grant, desktop,
            # model).
            result = run_agent("What was Boston's population in 2020?", grant, desktop, model)
            # Assert that result.status equals 'finished'. If false, this check fails with
            # AssertionError.
            assert result.status == "finished"
            # Set observation to [entry for entry in model.seen[1] if entry.kind ==
            # 'observation'][-1].
            observation = [entry for entry in model.seen[1] if entry.kind == "observation"][-1]
            # Assert that '2020 census: 675,647 residents' is in observation.text. If false, this
            # check fails with AssertionError.
            assert "2020 census: 675,647 residents" in observation.text
            # Assert that url is in observation.text. If false, this check fails with
            # AssertionError.
            assert url in observation.text
            # Assert that the number of items/characters in observation.text is less than 1300. If
            # false, this check fails with AssertionError.
            assert len(observation.text) < 1300
            # Print 'PASS: fact absent from 4,000-character preview, found by search'.
            print("PASS: fact absent from 4,000-character preview, found by search")
            # Print 'Preview characters:', the length of preview.text.
            print("Preview characters:", len(preview.text))
            # Print 'Search observation characters (including URL):', the length of
            # observation.text.
            print("Search observation characters (including URL):", len(observation.text))
            # Print 'Observation delivered to the scripted model:\n' plus observation.text.
            print("Observation delivered to the scripted model:\n" + observation.text)
            # Print 'No paid calls. Character counts are not token measurements or total-run cost
            # savings.'.
            print("No paid calls. Character counts are not token measurements or total-run cost savings.")
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            browser.close()


# Check whether __name__ equals '__main__'.
if __name__ == "__main__":
    # Call main with no arguments.
    main()

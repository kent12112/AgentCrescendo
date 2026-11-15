# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Demonstrate bounded page search in installed Edge, without paid calls."""
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


# Learn: Define main(). The body runs when called, not when defined.
def main():
    # Learn: Set url to 'https://allowed.example/boston'; the destination or current page address.
    url = "https://allowed.example/boston"
    # Learn: Set html to '<main><h1>Boston research fixture</h1>' plus '<p>Unrelated history and
    # geography.</p>' times 250.
    html = "<main><h1>Boston research fixture</h1>" + "<p>Unrelated history and geography.</p>" * 250
    # Learn: Update html using its previous value plus '<h2>Demographics</h2><p>Population at the 2020
    # census: 675,647 residents.</p></main>'.
    html += "<h2>Demographics</h2><p>Population at the 2020 census: 675,647 residents.</p></main>"
    # Learn: Set grant to TaskGrant('search-fixture', frozenset({'search_page', 'finish'}),
    # frozenset({'allowed.example'})); the task identity and fixed tool/host permissions; model output
    # cannot expand these.
    grant = TaskGrant("search-fixture", frozenset({"search_page", "finish"}), frozenset({"allowed.example"}))
    # Learn: Enter sync_playwright() as p. The context manager controls setup/exit; inspect it for the
    # actual cleanup behavior.
    with sync_playwright() as p:
        # Learn: Set browser to p.chromium.launch(channel='msedge', headless=True); the browser connection
        # or WebSocket peer used in this scope.
        browser = p.chromium.launch(channel="msedge", headless=True)
        # Learn: Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Learn: Set context to browser.new_context(java_script_enabled=False, service_workers='block');
            # the browser context or framework request context used here. Create an isolated browser context
            # using the explicit script/download settings.
            context = browser.new_context(java_script_enabled=False, service_workers="block")
            # Learn: Call context.route with the arguments shown.
            context.route("**/*", lambda route: route.fulfill(status=200, content_type="text/html", body=html))
            # Learn: Set page to context.new_page(); the browser tab controlled by Playwright. Create the
            # browser tab controlled by this adapter.
            page = context.new_page()
            # Learn: Navigate this tab and wait using the explicit load/timeout policy on page; inputs: url.
            page.goto(url, wait_until="domcontentloaded")
            # Learn: Set desktop to E2BDesktop(page, context.new_cdp_session(page), grant).
            desktop = E2BDesktop(page, context.new_cdp_session(page), grant)
            # Learn: Set preview to desktop.observe().
            preview = desktop.observe()
            # Learn: Assert that '675,647' is not in preview.text. If false, this check fails with
            # AssertionError.
            assert "675,647" not in preview.text
            # Learn: Set model to ScriptedModel([ToolCall('search_page', {'query': 'population 2020'}),
            # ToolCall('finish', {'answer': '675,647 residents at the 2020 c...; the provider adapter or
            # scripted test model used to propose actions.
            model = ScriptedModel([
                # Learn: Call ToolCall with the arguments shown.
                ToolCall("search_page", {"query": "population 2020"}),
                # Learn: Call ToolCall with the arguments shown.
                ToolCall("finish", {"answer": "675,647 residents at the 2020 census", "sources": [url]}),
            # Learn: Close this list literal; delimiters group the values into one object.
            ])
            # Learn: Set result to run_agent("What was Boston's population in 2020?", grant, desktop,
            # model); the operation outcome for subsequent checks or reporting.
            result = run_agent("What was Boston's population in 2020?", grant, desktop, model)
            # Learn: Assert that result.status equals 'finished'. If false, this check fails with
            # AssertionError.
            assert result.status == "finished"
            # Learn: Set observation to [entry for entry in model.seen[1] if entry.kind ==
            # 'observation'][-1].
            observation = [entry for entry in model.seen[1] if entry.kind == "observation"][-1]
            # Learn: Assert that '2020 census: 675,647 residents' is in observation.text. If false, this
            # check fails with AssertionError.
            assert "2020 census: 675,647 residents" in observation.text
            # Learn: Assert that url is in observation.text. If false, this check fails with AssertionError.
            assert url in observation.text
            # Learn: Assert that the number of items/characters in observation.text is less than 1300. If
            # false, this check fails with AssertionError.
            assert len(observation.text) < 1300
            # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
            # 'PASS: fact absent from 4,000-character preview, found by search'.
            print("PASS: fact absent from 4,000-character preview, found by search")
            # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
            # 'Preview characters:', the number of items/characters in preview.text.
            print("Preview characters:", len(preview.text))
            # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
            # 'Search observation characters (including URL):', the number of items/characters in
            # observation.text.
            print("Search observation characters (including URL):", len(observation.text))
            # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
            # 'Observation delivered to the scripted model:\n' plus observation.text.
            print("Observation delivered to the scripted model:\n" + observation.text)
            # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
            # 'No paid calls. Character counts are not token measurements or total-run cost savings.'.
            print("No paid calls. Character counts are not token measurements or total-run cost savings.")
        # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Learn: Close this owned connection, stream, file, or browser resource on browser.
            browser.close()


# Learn: Take this branch only if __name__ equals '__main__'. The __main__ guard keeps imports from
# launching the CLI.
if __name__ == "__main__":
    # Learn: Call main with no arguments.
    main()

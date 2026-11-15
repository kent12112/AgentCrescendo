# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
# Learn string line 1: Literal prompt, documentation, or fixture content: Check content extraction in
# installed Edge using local HTML fixtures.. It remains unchanged at runtime.
# Learn string line 3: Literal prompt, documentation, or fixture content: Requires Playwright; no E2B or
# model calls. Route fulfillment supplies page HTML.. It remains unchanged at runtime.
"""Check content extraction in installed Edge using local HTML fixtures.

Requires Playwright; no E2B or model calls. Route fulfillment supplies page HTML.
"""
# Learn: From playwright.sync_api, import sync_playwright (owns a synchronous Playwright browser-control
# session).
from playwright.sync_api import sync_playwright

# Learn: From crescendo_agent.e2b_desktop, import E2BDesktop (a dependency used below).
from crescendo_agent.e2b_desktop import E2BDesktop
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant


# Learn: Define main(). The body runs when called, not when defined.
def main():
    # Learn: Set url to 'https://allowed.example/boston'; the destination or current page address.
    url = "https://allowed.example/boston"
    # Learn: Set grant to TaskGrant('content-fixture', frozenset({'navigate'}),
    # frozenset({'allowed.example'})); the task identity and fixed tool/host permissions; model output
    # cannot expand these.
    grant = TaskGrant("content-fixture", frozenset({"navigate"}), frozenset({"allowed.example"}))
    # Learn: Set navigation to '<nav>' plus 'Menu item ' times 600 plus '<a href="/menu">Menu</a></nav>'.
    navigation = '<nav>' + ('Menu item ' * 600) + '<a href="/menu">Menu</a></nav>'
    # Learn: Set article to '<p>Boston is the capital of Massachusetts.</p><a
    # href="/massachusetts">Massachusetts</a>'.
    article = '<p>Boston is the capital of Massachusetts.</p><a href="/massachusetts">Massachusetts</a>'
    # Learn: Set wiki to '<main>' plus navigation plus '<div id="mw-content-text"><div
    # class="mw-parser-output"><table class="infobox"><tr><td>' plus 'Infobox detail ' times 600 plus '<a
    # href="/infobox">Infobox link</a></td></tr></table>' plus article plus '</div></div></main>'.
    wiki = ('<main>' + navigation + '<div id="mw-content-text"><div class="mw-parser-output">'
            # Learn: Supply literal text 'Infobox detail '; adjacent string literals are concatenated
            # without adding whitespace.
            '<table class="infobox"><tr><td>' + ('Infobox detail ' * 600)
            # Learn: Continue the expression + '<a href="/infobox">Infobox link</a></td></tr></table>';
            # brackets keep it part of the statement above.
            + '<a href="/infobox">Infobox link</a></td></tr></table>'
            # Learn: Continue the expression + article + '</div></div></main>'); brackets keep it part of
            # the statement above.
            + article + '</div></div></main>')
    # Learn: Set fixtures to a new list containing the tuple ('main', navigation + '<main>' + article +
    # '</main>', True) (positional values), the tuple ('role', navigation + '<div rol....
    fixtures = [
        # Learn: Add this item to the surrounding list: ("main", navigation + '<main>' + article +
        # '</main>', True),.
        ("main", navigation + '<main>' + article + '</main>', True),
        # Learn: Add this item to the surrounding list: ("role", navigation + '<div role="main">' + article
        # + '</div>', True),.
        ("role", navigation + '<div role="main">' + article + '</div>', True),
        # Learn: Add this item to the surrounding list: ("article", navigation + '<article>' + article +
        # '</article>', True),.
        ("article", navigation + '<article>' + article + '</article>', True),
        # Learn: Add this item to the surrounding list: ("empty main", '<main> </main>' + article, False),.
        ("empty main", '<main> </main>' + article, False),
        # Learn: Add this item to the surrounding list: ("body", article, False),.
        ("body", article, False),
        # Learn: Add this item to the surrounding list: ("Wikipedia nested menus and infobox", wiki, True),.
        ("Wikipedia nested menus and infobox", wiki, True),
        # Learn: Add this item to the surrounding list: ("Wikipedia empty article fallback", '<div
        # id="mw-content-text"><div class="mw-parser-output"> </div></div>'.
        ("Wikipedia empty article fallback", '<div id="mw-content-text"><div class="mw-parser-output"> </div></div>'
         # Learn: Add this item to the surrounding tuple: + '<main>' + article + '</main>', False),.
         + '<main>' + article + '</main>', False),
    # Learn: Close this list literal; delimiters group the values into one object.
    ]
    # Learn: Enter sync_playwright() as p. The context manager controls setup/exit; inspect it for the
    # actual cleanup behavior.
    with sync_playwright() as p:
        # Learn: Set browser to p.chromium.launch(channel='msedge', headless=True); the browser connection
        # or WebSocket peer used in this scope.
        browser = p.chromium.launch(channel="msedge", headless=True)
        # Learn: Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Learn: Iterate over fixtures, binding (name, html, has_navigation) for each item.
            for name, html, has_navigation in fixtures:
                # Learn: Set fixture_url to 'https://en.wikipedia.org/boston' when
                # name.startswith('Wikipedia'), otherwise url.
                fixture_url = "https://en.wikipedia.org/boston" if name.startswith("Wikipedia") else url
                # Learn: Set context to browser.new_context(java_script_enabled=False,
                # service_workers='block'); the browser context or framework request context used here.
                # Create an isolated browser context using the explicit script/download settings.
                context = browser.new_context(java_script_enabled=False, service_workers="block")
                # Learn: Try the following operations; matching except clauses handle failures. The finally
                # block runs on every exit.
                try:
                    # Learn: Call context.route with the arguments shown.
                    context.route("**/*", lambda route, request, html=html: route.fulfill(
                        # Learn: Pass keyword status = 200.
                        status=200, content_type="text/html", body=html))
                    # Learn: Set page to context.new_page(); the browser tab controlled by Playwright.
                    # Create the browser tab controlled by this adapter.
                    page = context.new_page()
                    # Learn: Navigate this tab and wait using the explicit load/timeout policy on page;
                    # inputs: fixture_url.
                    page.goto(fixture_url, wait_until="domcontentloaded")
                    # Fixture loading is separate from extraction; this test
                    # verifies DOM selection, not gateway or network enforcement.
                    # Learn: Set old_text to page.locator('body').inner_text()[:4000].
                    old_text = page.locator("body").inner_text()[:4000]
                    # Learn: Set desktop to E2BDesktop(page, context.new_cdp_session(page), grant).
                    desktop = E2BDesktop(page, context.new_cdp_session(page), grant)
                    # Learn: Set observation to desktop.observe().
                    observation = desktop.observe()
                    # Learn: Assert that 'Boston is the capital of Massachusetts.' is in observation.text.
                    # If false, this check fails with AssertionError.
                    assert "Boston is the capital of Massachusetts." in observation.text
                    # Learn: Assert that 'Menu item' is not in observation.text. If false, this check fails
                    # with AssertionError.
                    assert "Menu item" not in observation.text
                    # Learn: Assert that 'Infobox detail' is not in observation.text. If false, this check
                    # fails with AssertionError.
                    assert "Infobox detail" not in observation.text
                    # Learn: Take this branch only if name equals 'Wikipedia nested menus and infobox'.
                    if name == "Wikipedia nested menus and infobox":
                        # Learn: Assert that 'Boston is the capital' is not in
                        # page.locator('main').inner_text()[:4000]. If false, this check fails with
                        # AssertionError.
                        assert "Boston is the capital" not in page.locator("main").inner_text()[:4000]
                        # Learn: Assert that page.locator('.infobox').count() equals 1. If false, this check
                        # fails with AssertionError.
                        assert page.locator(".infobox").count() == 1
                        # Learn: Assert that 'Infobox detail' is in page.locator('.infobox').inner_text().
                        # If false, this check fails with AssertionError.
                        assert "Infobox detail" in page.locator(".infobox").inner_text()
                    # Learn: Assert that a list built from observation.links by the comprehension equals a
                    # new list containing fixture_url.rsplit('/', 1)[0] plus '/massachusetts'. If false,
                    # this check fails with AssertionError.
                    assert [link.url for link in observation.links] == [
                        # Learn: Call fixture_url.rsplit with the arguments shown.
                        fixture_url.rsplit("/", 1)[0] + "/massachusetts"]
                    # Learn: Take this branch only if has_navigation.
                    if has_navigation:
                        # Learn: Assert that 'Boston is the capital' is not in old_text. If false, this
                        # check fails with AssertionError.
                        assert "Boston is the capital" not in old_text
                    # Learn: Display diagnostic/result text without treating it as verified model evidence;
                    # inputs: an f-string that substitutes the expressions in {...} into the text.
                    print(f"PASS: {name}: relevant text and links retained")
                # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
                finally:
                    # Learn: Close this owned connection, stream, file, or browser resource on context.
                    context.close()
        # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            # Learn: Close this owned connection, stream, file, or browser resource on browser.
            browser.close()
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: 'No E2B
    # or model resources used; live website extraction remains to be checked'.
    print("No E2B or model resources used; live website extraction remains to be checked")


# Learn: Take this branch only if __name__ equals '__main__'. The __main__ guard keeps imports from
# launching the CLI.
if __name__ == "__main__":
    # Learn: Call main with no arguments.
    main()

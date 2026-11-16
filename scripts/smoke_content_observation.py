"""Check content extraction in installed Edge using local HTML fixtures.

Requires Playwright; no E2B or model calls. Route fulfillment supplies page HTML.
"""
# Import from playwright.sync_api: sync_playwright (owns a synchronous Playwright browser-control
# session).
from playwright.sync_api import sync_playwright

# Import from crescendo_agent.e2b_desktop: E2BDesktop (a dependency used below).
from crescendo_agent.e2b_desktop import E2BDesktop
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant


# Define main with no parameters.
def main():
    # Set url to 'https://allowed.example/boston'.
    url = "https://allowed.example/boston"
    # Set grant to TaskGrant('content-fixture', frozenset({'navigate'}),
    # frozenset({'allowed.example'})).
    grant = TaskGrant("content-fixture", frozenset({"navigate"}), frozenset({"allowed.example"}))
    # Set navigation to '<nav>' plus 'Menu item ' times 600 plus '<a href="/menu">Menu</a></nav>'.
    navigation = '<nav>' + ('Menu item ' * 600) + '<a href="/menu">Menu</a></nav>'
    # Set article to '<p>Boston is the capital of Massachusetts.</p><a
    # href="/massachusetts">Massachusetts</a>'.
    article = '<p>Boston is the capital of Massachusetts.</p><a href="/massachusetts">Massachusetts</a>'
    # Set wiki to '<main>' plus navigation plus '<div id="mw-content-text"><div
    # class="mw-parser-output"><table class="infobox"><tr><td>' plus 'Infobox detail ' times 600
    # plus '<a href="/infobox">Infobox link</a></td></tr></table>' plus article plus
    # '</div></div></main>'.
    wiki = ('<main>' + navigation + '<div id="mw-content-text"><div class="mw-parser-output">'
            '<table class="infobox"><tr><td>' + ('Infobox detail ' * 600)
            # Continue the expression + '<a href="/infobox">Infobox link</a></td></tr></table>';
            # brackets keep it part of the statement above.
            + '<a href="/infobox">Infobox link</a></td></tr></table>'
            # Continue the expression + article + '</div></div></main>'); brackets keep it part of
            # the statement above.
            + article + '</div></div></main>')
    # Build fixtures from the entries below.
    fixtures = [
        # Add this item to the surrounding list: ("main", navigation + '<main>' + article +
        # '</main>', True),.
        ("main", navigation + '<main>' + article + '</main>', True),
        # Add this item to the surrounding list: ("role", navigation + '<div role="main">' + article
        # + '</div>', True),.
        ("role", navigation + '<div role="main">' + article + '</div>', True),
        # Add this item to the surrounding list: ("article", navigation + '<article>' + article +
        # '</article>', True),.
        ("article", navigation + '<article>' + article + '</article>', True),
        # Add this item to the surrounding list: ("empty main", '<main> </main>' + article, False),.
        ("empty main", '<main> </main>' + article, False),
        # Add this item to the surrounding list: ("body", article, False),.
        ("body", article, False),
        # Add this item to the surrounding list: ("Wikipedia nested menus and infobox", wiki,
        # True),.
        ("Wikipedia nested menus and infobox", wiki, True),
        # Add this item to the surrounding list: ("Wikipedia empty article fallback", '<div
        # id="mw-content-text"><div class="mw-parser-output"> </div></div>'.
        ("Wikipedia empty article fallback", '<div id="mw-content-text"><div class="mw-parser-output"> </div></div>'
         # Add this item to the surrounding tuple: + '<main>' + article + '</main>', False),.
         + '<main>' + article + '</main>', False),
    ]
    # Use sync_playwright() as p; leave the context and run its cleanup when this block ends.
    with sync_playwright() as p:
        # Set browser to p.chromium.launch(channel='msedge', headless=True).
        browser = p.chromium.launch(channel="msedge", headless=True)
        # Try the following operations; matching except clauses handle failures. The finally block
        # runs on every exit.
        try:
            # Iterate over fixtures, binding (name, html, has_navigation) for each item.
            for name, html, has_navigation in fixtures:
                # Set fixture_url to 'https://en.wikipedia.org/boston' if
                # name.startswith('Wikipedia'), otherwise url.
                fixture_url = "https://en.wikipedia.org/boston" if name.startswith("Wikipedia") else url
                # Set context to browser.new_context(java_script_enabled=False,
                # service_workers='block').
                context = browser.new_context(java_script_enabled=False, service_workers="block")
                # Try the following operations; matching except clauses handle failures. The finally
                # block runs on every exit.
                try:
                    # Call context.route with '**/*', a function that returns
                    # route.fulfill(status=200, content_type='text/html', body=html) when called.
                    context.route("**/*", lambda route, request, html=html: route.fulfill(
                        # Pass keyword status = 200.
                        status=200, content_type="text/html", body=html))
                    # Set page to context.new_page().
                    page = context.new_page()
                    # Call page.goto with fixture_url.
                    page.goto(fixture_url, wait_until="domcontentloaded")
                    # Fixture loading is separate from extraction; this test
                    # verifies DOM selection, not gateway or network enforcement.
                    # Set old_text to page.locator('body').inner_text()[:4000].
                    old_text = page.locator("body").inner_text()[:4000]
                    # Set desktop to E2BDesktop(page, context.new_cdp_session(page), grant).
                    desktop = E2BDesktop(page, context.new_cdp_session(page), grant)
                    # Set observation to desktop.observe().
                    observation = desktop.observe()
                    # Assert that 'Boston is the capital of Massachusetts.' is in observation.text.
                    # If false, this check fails with AssertionError.
                    assert "Boston is the capital of Massachusetts." in observation.text
                    # Assert that 'Menu item' is not in observation.text. If false, this check fails
                    # with AssertionError.
                    assert "Menu item" not in observation.text
                    # Assert that 'Infobox detail' is not in observation.text. If false, this check
                    # fails with AssertionError.
                    assert "Infobox detail" not in observation.text
                    # Check whether name equals 'Wikipedia nested menus and infobox'.
                    if name == "Wikipedia nested menus and infobox":
                        # Assert that 'Boston is the capital' is not in
                        # page.locator('main').inner_text()[:4000]. If false, this check fails with
                        # AssertionError.
                        assert "Boston is the capital" not in page.locator("main").inner_text()[:4000]
                        # Assert that page.locator('.infobox').count() equals 1. If false, this
                        # check fails with AssertionError.
                        assert page.locator(".infobox").count() == 1
                        # Assert that 'Infobox detail' is in page.locator('.infobox').inner_text().
                        # If false, this check fails with AssertionError.
                        assert "Infobox detail" in page.locator(".infobox").inner_text()
                    # Assert that a list built from observation.links by the comprehension equals a
                    # new list containing fixture_url.rsplit('/', 1)[0] plus '/massachusetts'. If
                    # false, this check fails with AssertionError.
                    assert [link.url for link in observation.links] == [
                        # Call fixture_url.rsplit with the arguments shown.
                        fixture_url.rsplit("/", 1)[0] + "/massachusetts"]
                    # Check whether has_navigation.
                    if has_navigation:
                        # Assert that 'Boston is the capital' is not in old_text. If false, this
                        # check fails with AssertionError.
                        assert "Boston is the capital" not in old_text
                    # Print f'PASS: {name}: relevant text and links retained'.
                    print(f"PASS: {name}: relevant text and links retained")
                # Always run cleanup, whether the operation succeeds, returns, or raises.
                finally:
                    context.close()
        # Always run cleanup, whether the operation succeeds, returns, or raises.
        finally:
            browser.close()
    # Print 'No E2B or model resources used; live website extraction remains to be checked'.
    print("No E2B or model resources used; live website extraction remains to be checked")


# Check whether __name__ equals '__main__'.
if __name__ == "__main__":
    # Call main with no arguments.
    main()

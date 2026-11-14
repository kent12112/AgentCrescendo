"""Check content extraction in installed Edge using local HTML fixtures.

Requires Playwright; no E2B or model calls. Route fulfillment supplies page HTML.
"""
from playwright.sync_api import sync_playwright

from crescendo_agent.e2b_desktop import E2BDesktop
from crescendo_security.policy import TaskGrant


def main():
    url = "https://allowed.example/boston"
    grant = TaskGrant("content-fixture", frozenset({"navigate"}), frozenset({"allowed.example"}))
    navigation = '<nav>' + ('Menu item ' * 600) + '<a href="/menu">Menu</a></nav>'
    article = '<p>Boston is the capital of Massachusetts.</p><a href="/massachusetts">Massachusetts</a>'
    wiki = ('<main>' + navigation + '<div id="mw-content-text"><div class="mw-parser-output">'
            '<table class="infobox"><tr><td>' + ('Infobox detail ' * 600)
            + '<a href="/infobox">Infobox link</a></td></tr></table>'
            + article + '</div></div></main>')
    fixtures = [
        ("main", navigation + '<main>' + article + '</main>', True),
        ("role", navigation + '<div role="main">' + article + '</div>', True),
        ("article", navigation + '<article>' + article + '</article>', True),
        ("empty main", '<main> </main>' + article, False),
        ("body", article, False),
        ("Wikipedia nested menus and infobox", wiki, True),
        ("Wikipedia empty article fallback", '<div id="mw-content-text"><div class="mw-parser-output"> </div></div>'
         + '<main>' + article + '</main>', False),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        try:
            for name, html, has_navigation in fixtures:
                fixture_url = "https://en.wikipedia.org/boston" if name.startswith("Wikipedia") else url
                context = browser.new_context(java_script_enabled=False, service_workers="block")
                try:
                    context.route("**/*", lambda route, request, html=html: route.fulfill(
                        status=200, content_type="text/html", body=html))
                    page = context.new_page()
                    page.goto(fixture_url, wait_until="domcontentloaded")
                    # Fixture loading is separate from extraction; this test
                    # verifies DOM selection, not gateway or network enforcement.
                    old_text = page.locator("body").inner_text()[:4000]
                    desktop = E2BDesktop(page, context.new_cdp_session(page), grant)
                    observation = desktop.observe()
                    assert "Boston is the capital of Massachusetts." in observation.text
                    assert "Menu item" not in observation.text
                    assert "Infobox detail" not in observation.text
                    if name == "Wikipedia nested menus and infobox":
                        assert "Boston is the capital" not in page.locator("main").inner_text()[:4000]
                        assert page.locator(".infobox").count() == 1
                        assert "Infobox detail" in page.locator(".infobox").inner_text()
                    assert [link.url for link in observation.links] == [
                        fixture_url.rsplit("/", 1)[0] + "/massachusetts"]
                    if has_navigation:
                        assert "Boston is the capital" not in old_text
                    print(f"PASS: {name}: relevant text and links retained")
                finally:
                    context.close()
        finally:
            browser.close()
    print("No E2B or model resources used; live website extraction remains to be checked")


if __name__ == "__main__":
    main()

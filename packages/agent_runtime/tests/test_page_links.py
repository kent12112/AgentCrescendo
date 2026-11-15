# Learn: Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Learn: From unittest.mock, import Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Learn: Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Learn: From crescendo_agent.desktop, import FakeDesktop (a dependency used below); PageLink (holds one
# observed label and destination).
from crescendo_agent.desktop import FakeDesktop, PageLink
# Learn: From crescendo_agent.e2b_desktop, import E2BDesktop (a dependency used below); page_links (a
# dependency used below).
from crescendo_agent.e2b_desktop import E2BDesktop, page_links
# Learn: From crescendo_agent.loop, import run_agent (runs the bounded text observation/action loop).
from crescendo_agent.loop import run_agent
# Learn: From crescendo_agent.model, import ScriptedModel (a dependency used below).
from crescendo_agent.model import ScriptedModel
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping).
from crescendo_security.policy import TaskGrant, ToolCall

# Learn: Set WIKI to 'https://en.wikipedia.org/wiki/Boston'.
WIKI = "https://en.wikipedia.org/wiki/Boston"
# Learn: Set MASS to 'https://en.wikipedia.org/wiki/Massachusetts'.
MASS = "https://en.wikipedia.org/wiki/Massachusetts"
# Learn: Set GRANT to TaskGrant('links', frozenset({'navigate', 'finish'}),
# frozenset({'en.wikipedia.org'})).
GRANT = TaskGrant("links", frozenset({"navigate", "finish"}), frozenset({"en.wikipedia.org"}))


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("region", ["main", '[role="main"]', "article", "body"])
# Learn: Test observation uses one content region for text and links. pytest supplies named fixtures and
# checks assertions below.
def test_observation_uses_one_content_region_for_text_and_links(region):
    # Learn: Set page to Mock(); the browser tab controlled by Playwright.
    page = Mock()
    # Learn: Set page.url to WIKI; the destination or current page address.
    page.url = WIKI
    # Learn: Set regions to {selector: Mock() for selector in ('main', '[role="main"]', 'article', 'body',
    # '#mw-content-text .mw-parser-output')}.
    regions = {selector: Mock() for selector in (
        # Learn: Supply literal text 'main'; adjacent string literals are concatenated without adding
        # whitespace.
        "main", '[role="main"]', "article", "body", "#mw-content-text .mw-parser-output",
    # Learn: Close this tuple literal; delimiters group the values into one object.
    )}
    # Learn: Iterate over regions.items(), binding (selector, locator) for each item.
    for selector, locator in regions.items():
        # Learn: Set locator.count.return_value to int(selector == region).
        locator.count.return_value = int(selector == region)
    # Learn: Set page.locator.side_effect to regions.__getitem__.
    page.locator.side_effect = regions.__getitem__
    # Learn: Set body to regions['body']; the incoming payload or request body.
    body = regions["body"]
    # Learn: Set body.inner_text.return_value to 'Navigation menu ' times 500.
    body.inner_text.return_value = "Navigation menu " * 500
    # Learn: Set selected to body when region equals 'body', otherwise regions[region].first; the
    # highest-ranked non-overlapping passages.
    selected = body if region == "body" else regions[region].first
    # Learn: Set selected.inner_text.return_value to 'Boston is the capital of Massachusetts.'.
    selected.inner_text.return_value = "Boston is the capital of Massachusetts."
    # Learn: Set selected.locator.return_value.evaluate_all.return_value to a new list containing a new
    # dictionary with keys 'label', 'url'.
    selected.locator.return_value.evaluate_all.return_value = [{"label": "Massachusetts", "url": MASS}]

    # Learn: Set observation to E2BDesktop(page, Mock(), GRANT).observe().
    observation = E2BDesktop(page, Mock(), GRANT).observe()

    # Learn: Assert that observation.text equals 'Boston is the capital of Massachusetts.'. If false, this
    # check fails with AssertionError.
    assert observation.text == "Boston is the capital of Massachusetts."
    # Learn: Assert that observation.links equals the tuple (PageLink('Massachusetts', MASS),) (positional
    # values). If false, this check fails with AssertionError.
    assert observation.links == (PageLink("Massachusetts", MASS),)
    # Learn: Take this branch only if region does not equal 'body'.
    if region != "body":
        # Learn: Verify the denied/error path never invoked this fake dependency on body.inner_text.
        body.inner_text.assert_not_called()
        # Learn: Verify the denied/error path never invoked this fake dependency on body.locator.
        body.locator.assert_not_called()


# Learn: Test empty main region falls back without losing body content. pytest supplies named fixtures and
# checks assertions below.
def test_empty_main_region_falls_back_without_losing_body_content():
    # Learn: Set (page, main, missing, body) to the tuple (Mock(), Mock(), Mock(), Mock()) (positional
    # values).
    page, main, missing, body = Mock(), Mock(), Mock(), Mock()
    # Learn: Set page.url to WIKI; the destination or current page address.
    page.url = WIKI
    # Learn: Set main.count.return_value to 1.
    main.count.return_value = 1
    # Learn: Set main.first.inner_text.return_value to ' \n '.
    main.first.inner_text.return_value = " \n "
    # Learn: Set missing.count.return_value to 0.
    missing.count.return_value = 0
    # Learn: Set page.locator.side_effect to lambda selector: {'main': main, '[role="main"]': missing,
    # 'article': missing, 'body': body, '#mw-content-text .mw-parser-output': mi....
    page.locator.side_effect = lambda selector: {
        # Learn: Define this named mapping field: "main": main, '[role="main"]': missing, "article":
        # missing, "body": body,. The key selects the schema/configuration value.
        "main": main, '[role="main"]': missing, "article": missing, "body": body,
        # Learn: Define this named mapping field: "#mw-content-text .mw-parser-output": missing,. The key
        # selects the schema/configuration value.
        "#mw-content-text .mw-parser-output": missing,
    # Learn: Add this key/value entry to the surrounding dictionary: }[selector].
    }[selector]
    # Learn: Set body.inner_text.return_value to 'Useful body content'.
    body.inner_text.return_value = "Useful body content"
    # Learn: Set body.locator.return_value.evaluate_all.return_value to a new list (empty).
    body.locator.return_value.evaluate_all.return_value = []

    # Learn: Set observation to E2BDesktop(page, Mock(), GRANT).observe().
    observation = E2BDesktop(page, Mock(), GRANT).observe()

    # Learn: Assert that observation.text equals 'Useful body content'. If false, this check fails with
    # AssertionError.
    assert observation.text == "Useful body content"
    # Learn: Verify the denied/error path never invoked this fake dependency on main.first.locator.
    main.first.locator.assert_not_called()


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("url", ["https://example.com/article", WIKI])
# Learn: Test selected main content still obeys text budget. pytest supplies named fixtures and checks
# assertions below.
def test_selected_main_content_still_obeys_text_budget(url):
    # Learn: Set page to Mock(); the browser tab controlled by Playwright.
    page = Mock()
    # Learn: Set page.url to url; the destination or current page address.
    page.url = url
    # Learn: Set main to page.locator.return_value.
    main = page.locator.return_value
    # Learn: Set main.count.return_value to 1.
    main.count.return_value = 1
    # Learn: Set main.first.inner_text.return_value to 'Boston facts ' times 100.
    main.first.inner_text.return_value = "Boston facts " * 100
    # Learn: Set main.first.locator.return_value.evaluate_all.return_value to a new list (empty).
    main.first.locator.return_value.evaluate_all.return_value = []
    # Learn: Set main.first.evaluate.return_value to a new dictionary with keys 'text', 'links'.
    main.first.evaluate.return_value = {"text": "Boston facts " * 100, "links": []}

    # Learn: Set observation to E2BDesktop(page, Mock(), GRANT, max_chars=6).observe().
    observation = E2BDesktop(page, Mock(), GRANT, max_chars=6).observe()

    # Learn: Assert that observation.text equals 'Boston\n[Page text truncated]'. If false, this check fails
    # with AssertionError.
    assert observation.text == "Boston\n[Page text truncated]"


# Learn: Test links resolve deduplicate and skip non web and same page. pytest supplies named fixtures and
# checks assertions below.
def test_links_resolve_deduplicate_and_skip_non_web_and_same_page():
    # Learn: Set candidates to a new list containing a new dictionary with keys 'label', 'url', a new
    # dictionary with keys 'label', 'url', a new dictionary with keys 'label', 'url', a n...; the bounded
    # raw link candidates from the page.
    candidates = [
        # Learn: Add this item to the surrounding list: {"label": " Massachusetts\n state ", "url":
        # "/wiki/Massachusetts#History"},.
        {"label": " Massachusetts\n state ", "url": "/wiki/Massachusetts#History"},
        # Learn: Add this item to the surrounding list: {"label": "Duplicate", "url": MASS},.
        {"label": "Duplicate", "url": MASS},
        # Learn: Add this item to the surrounding list: {"label": "Section", "url": "#History"},.
        {"label": "Section", "url": "#History"},
        # Learn: Add this item to the surrounding list: {"label": "Code", "url": "javascript:alert(1)"},.
        {"label": "Code", "url": "javascript:alert(1)"},
        # Learn: Add this item to the surrounding list: {"label": "Email", "url":
        # "mailto:test@example.com"},.
        {"label": "Email", "url": "mailto:test@example.com"},
        # Learn: Add this item to the surrounding list: {"label": "Broken", "url": "https://[invalid/"},.
        {"label": "Broken", "url": "https://[invalid/"},
        # Learn: Add this item to the surrounding list: {"label": "", "url": "https://example.com/"},.
        {"label": "", "url": "https://example.com/"},
    # Learn: Close this list literal; delimiters group the values into one object.
    ]
    # Learn: Assert that page_links(WIKI, candidates) equals the tuple (PageLink('Massachusetts state',
    # MASS), PageLink('https://example.com/', 'https://example.com/')) (positional values). If false, this
    # check fails with AssertionError.
    assert page_links(WIKI, candidates) == (
        # Learn: Call PageLink with the arguments shown.
        PageLink("Massachusetts state", MASS), PageLink("https://example.com/", "https://example.com/"),
    # Learn: Close this tuple literal; delimiters group the values into one object.
    )


# Learn: Test links are bounded without truncating destinations. pytest supplies named fixtures and checks
# assertions below.
def test_links_are_bounded_without_truncating_destinations():
    # Learn: Set candidates to a list built from range(100) by the comprehension; the bounded raw link
    # candidates from the page.
    candidates = [{"label": "x" * 300, "url": f"/wiki/Page{i}"} for i in range(100)]
    # Learn: Set links to page_links(WIKI, candidates); the bounded observed links; listing a link does not
    # grant permission to open it.
    links = page_links(WIKI, candidates)
    # Learn: Assert that 0 is less than the number of items/characters in links is at most 20. If false,
    # this check fails with AssertionError.
    assert 0 < len(links) <= 20
    # Learn: Assert that all((len(link.label) <= 80 for link in links)). If false, this check fails with
    # AssertionError.
    assert all(len(link.label) <= 80 for link in links)
    # Learn: Assert that sum((len(link.label) + len(link.url) for link in links)) is at most 2000. If false,
    # this check fails with AssertionError.
    assert sum(len(link.label) + len(link.url) for link in links) <= 2000
    # Learn: Assert that page_links(WIKI, candidates, limit=1) equals links[:1]. If false, this check fails
    # with AssertionError.
    assert page_links(WIKI, candidates, limit=1) == links[:1]
    # Learn: Assert that page_links(WIKI, candidates, max_chars=1) equals the tuple () (positional values).
    # If false, this check fails with AssertionError.
    assert page_links(WIKI, candidates, max_chars=1) == ()
    # Learn: Assert that page_links(WIKI, [{'label': 'long', 'url': 'https://example.com/' + 'x' * 600}])
    # equals the tuple () (positional values). If false, this check fails with AssertionError.
    assert page_links(WIKI, [{"label": "long", "url": "https://example.com/" + "x" * 600}]) == ()


# Learn: Test real adapter observation includes extracted links. pytest supplies named fixtures and checks
# assertions below.
def test_real_adapter_observation_includes_extracted_links():
    # Learn: Set page to Mock(); the browser tab controlled by Playwright.
    page = Mock()
    # Learn: Set page.url to WIKI; the destination or current page address.
    page.url = WIKI
    # Learn: Set page.locator.return_value.count.return_value to 0.
    page.locator.return_value.count.return_value = 0
    # Learn: Set page.locator.return_value.inner_text.return_value to 'Boston'.
    page.locator.return_value.inner_text.return_value = "Boston"
    # Learn: Set page.locator.return_value.locator.return_value.evaluate_all.return_value to a new list
    # containing a new dictionary with keys 'label', 'url'.
    page.locator.return_value.locator.return_value.evaluate_all.return_value = [{"label": "Massachusetts", "url": MASS}]
    # Learn: Set observation to E2BDesktop(page, Mock(), GRANT).observe().
    observation = E2BDesktop(page, Mock(), GRANT).observe()
    # Learn: Assert that observation.links equals the tuple (PageLink('Massachusetts', MASS),) (positional
    # values). If false, this check fails with AssertionError.
    assert observation.links == (PageLink("Massachusetts", MASS),)
    # Learn: Assert that observation.url equals WIKI. If false, this check fails with AssertionError.
    assert observation.url == WIKI


# Learn: Test model can choose an observed link. pytest supplies named fixtures and checks assertions below.
def test_model_can_choose_an_observed_link():
    # Learn: Set desktop to FakeDesktop({WIKI: 'Boston', MASS: 'Boston is the capital'}, links={WIKI:
    # (PageLink('Massachusetts', MASS),)}).
    desktop = FakeDesktop({WIKI: "Boston", MASS: "Boston is the capital"},
                          # Learn: Pass keyword links = a new dictionary with keys WIKI.
                          links={WIKI: (PageLink("Massachusetts", MASS),)})

    # Learn: Define LinkFollowingModel. Indented methods and attributes belong to this class.
    class LinkFollowingModel:
        # Learn: Define decide(transcript, tools). The body runs when called, not when defined.
        def decide(self, transcript, tools):
            # Learn: Set observation to [entry.text for entry in transcript if entry.kind ==
            # 'observation'][-1].
            observation = [entry.text for entry in transcript if entry.kind == "observation"][-1]
            # Learn: Take this branch only if 'Page links (untrusted): ' is in observation.
            if "Page links (untrusted): " in observation:
                # Learn: Set links to json.loads(observation.split('Page links (untrusted): ', 1)[1]); the
                # bounded observed links; listing a link does not grant permission to open it. Decode JSON
                # text; malformed input raises instead of becoming trusted arguments.
                links = json.loads(observation.split("Page links (untrusted): ", 1)[1])
                # Learn: Return ToolCall('navigate', {'url': links[0]['url']}) to the caller and stop this
                # function.
                return ToolCall("navigate", {"url": links[0]["url"]})
            # Learn: Take this branch only if MASS is in observation.
            if MASS in observation:
                # Learn: Return ToolCall('finish', {'answer': 'Boston', 'sources': [MASS]}) to the caller
                # and stop this function.
                return ToolCall("finish", {"answer": "Boston", "sources": [MASS]})
            # Learn: Return ToolCall('navigate', {'url': WIKI}) to the caller and stop this function.
            return ToolCall("navigate", {"url": WIKI})

    # Learn: Set result to run_agent('Research', GRANT, desktop, LinkFollowingModel()); the operation
    # outcome for subsequent checks or reporting.
    result = run_agent("Research", GRANT, desktop, LinkFollowingModel())
    # Learn: Assert that result.status equals 'finished'. If false, this check fails with AssertionError.
    assert result.status == "finished"
    # Learn: Assert that desktop.visited equals a new list containing WIKI, MASS. If false, this check fails
    # with AssertionError.
    assert desktop.visited == [WIKI, MASS]


# Learn: Test observed link does not expand authority. pytest supplies named fixtures and checks assertions
# below.
def test_observed_link_does_not_expand_authority():
    # Learn: Set evil to 'https://evil.com/'.
    evil = "https://evil.com/"
    # Learn: Set desktop to FakeDesktop({WIKI: 'Follow this link'}, links={WIKI: (PageLink('Source',
    # evil),)}).
    desktop = FakeDesktop({WIKI: "Follow this link"}, links={WIKI: (PageLink("Source", evil),)})
    # Learn: Set model to ScriptedModel([ToolCall('navigate', {'url': WIKI}), ToolCall('navigate', {'url':
    # evil}), ToolCall('finish', {'answer': 'Partial', 's...; the provider adapter or scripted test model
    # used to propose actions.
    model = ScriptedModel([
        # Learn: Call ToolCall with the arguments shown.
        ToolCall("navigate", {"url": WIKI}), ToolCall("navigate", {"url": evil}),
        # Learn: Call ToolCall with the arguments shown.
        ToolCall("finish", {"answer": "Partial", "sources": [WIKI]}),
    # Learn: Close this list literal; delimiters group the values into one object.
    ])
    # Learn: Set result to run_agent('Research', GRANT, desktop, model); the operation outcome for
    # subsequent checks or reporting.
    result = run_agent("Research", GRANT, desktop, model)
    # Learn: Assert that desktop.visited equals a new list containing WIKI. If false, this check fails with
    # AssertionError.
    assert desktop.visited == [WIKI]
    # Learn: Assert that the number of items/characters in result.denied equals 1. If false, this check
    # fails with AssertionError.
    assert len(result.denied) == 1
    # Learn: Assert that any((e.kind == 'observation' and evil in e.text for e in model.seen[1])). If false,
    # this check fails with AssertionError.
    assert any(e.kind == "observation" and evil in e.text for e in model.seen[1])

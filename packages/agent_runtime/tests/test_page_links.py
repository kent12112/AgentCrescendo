# Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Import from unittest.mock: Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Import from crescendo_agent.desktop: FakeDesktop (a dependency used below); PageLink (holds one
# observed label and destination).
from crescendo_agent.desktop import FakeDesktop, PageLink
# Import from crescendo_agent.e2b_desktop: E2BDesktop (a dependency used below); page_links (a
# dependency used below).
from crescendo_agent.e2b_desktop import E2BDesktop, page_links
# Import from crescendo_agent.loop: run_agent (runs the bounded text observation/action loop).
from crescendo_agent.loop import run_agent
# Import from crescendo_agent.model: ScriptedModel (a dependency used below).
from crescendo_agent.model import ScriptedModel
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping).
from crescendo_security.policy import TaskGrant, ToolCall

# Set WIKI to 'https://en.wikipedia.org/wiki/Boston'.
WIKI = "https://en.wikipedia.org/wiki/Boston"
# Set MASS to 'https://en.wikipedia.org/wiki/Massachusetts'.
MASS = "https://en.wikipedia.org/wiki/Massachusetts"
# Set GRANT to TaskGrant('links', frozenset({'navigate', 'finish'}),
# frozenset({'en.wikipedia.org'})).
GRANT = TaskGrant("links", frozenset({"navigate", "finish"}), frozenset({"en.wikipedia.org"}))


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("region", ["main", '[role="main"]', "article", "body"])
# Define test_observation_uses_one_content_region_for_text_and_links with parameters region.
def test_observation_uses_one_content_region_for_text_and_links(region):
    # Set page to Mock().
    page = Mock()
    # Set page.url to WIKI.
    page.url = WIKI
    # Set regions to {selector: Mock() for selector in ('main', '[role="main"]', 'article', 'body',
    # '#mw-content-text .mw-parser-output')}.
    regions = {selector: Mock() for selector in (
        "main", '[role="main"]', "article", "body", "#mw-content-text .mw-parser-output",
    )}
    # Iterate over regions.items(), binding (selector, locator) for each item.
    for selector, locator in regions.items():
        # Set locator.count.return_value to selector equals region converted to an integer.
        locator.count.return_value = int(selector == region)
    # Set page.locator.side_effect to regions.__getitem__.
    page.locator.side_effect = regions.__getitem__
    # Set body to regions['body'].
    body = regions["body"]
    # Set body.inner_text.return_value to 'Navigation menu ' times 500.
    body.inner_text.return_value = "Navigation menu " * 500
    # Set selected to body if region equals 'body', otherwise regions[region].first.
    selected = body if region == "body" else regions[region].first
    # Set selected.inner_text.return_value to 'Boston is the capital of Massachusetts.'.
    selected.inner_text.return_value = "Boston is the capital of Massachusetts."
    # Set selected.locator.return_value.evaluate_all.return_value to [{'label': 'Massachusetts',
    # 'url': MASS}].
    selected.locator.return_value.evaluate_all.return_value = [{"label": "Massachusetts", "url": MASS}]

    # Set observation to E2BDesktop(page, Mock(), GRANT).observe().
    observation = E2BDesktop(page, Mock(), GRANT).observe()

    # Assert that observation.text equals 'Boston is the capital of Massachusetts.'. If false, this
    # check fails with AssertionError.
    assert observation.text == "Boston is the capital of Massachusetts."
    # Assert that observation.links equals the tuple (PageLink('Massachusetts', MASS),) (positional
    # values). If false, this check fails with AssertionError.
    assert observation.links == (PageLink("Massachusetts", MASS),)
    # Check whether region does not equal 'body'.
    if region != "body":
        # Call body.inner_text.assert_not_called with no arguments.
        body.inner_text.assert_not_called()
        # Call body.locator.assert_not_called with no arguments.
        body.locator.assert_not_called()


# Define test_empty_main_region_falls_back_without_losing_body_content with no parameters.
def test_empty_main_region_falls_back_without_losing_body_content():
    # Set (page, main, missing, body) to (Mock(), Mock(), Mock(), Mock()).
    page, main, missing, body = Mock(), Mock(), Mock(), Mock()
    # Set page.url to WIKI.
    page.url = WIKI
    # Set main.count.return_value to 1.
    main.count.return_value = 1
    # Set main.first.inner_text.return_value to ' \n '.
    main.first.inner_text.return_value = " \n "
    # Set missing.count.return_value to 0.
    missing.count.return_value = 0
    # Set page.locator.side_effect to a function that returns {'main': main, '[role="main"]':
    # missing, 'article': missing, 'body': body, '#mw-content-text .mw-parser-output':
    # missing}[selector] when called.
    page.locator.side_effect = lambda selector: {
        # Include main, article, body in this dictionary.
        "main": main, '[role="main"]': missing, "article": missing, "body": body,
        "#mw-content-text .mw-parser-output": missing,
    # Add this key/value entry to the surrounding dictionary: }[selector].
    }[selector]
    # Set body.inner_text.return_value to 'Useful body content'.
    body.inner_text.return_value = "Useful body content"
    # Set body.locator.return_value.evaluate_all.return_value to an empty list.
    body.locator.return_value.evaluate_all.return_value = []

    # Set observation to E2BDesktop(page, Mock(), GRANT).observe().
    observation = E2BDesktop(page, Mock(), GRANT).observe()

    # Assert that observation.text equals 'Useful body content'. If false, this check fails with
    # AssertionError.
    assert observation.text == "Useful body content"
    # Call main.first.locator.assert_not_called with no arguments.
    main.first.locator.assert_not_called()


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("url", ["https://example.com/article", WIKI])
# Define test_selected_main_content_still_obeys_text_budget with parameters url.
def test_selected_main_content_still_obeys_text_budget(url):
    # Set page to Mock().
    page = Mock()
    # Set page.url to url.
    page.url = url
    # Set main to page.locator.return_value.
    main = page.locator.return_value
    # Set main.count.return_value to 1.
    main.count.return_value = 1
    # Set main.first.inner_text.return_value to 'Boston facts ' times 100.
    main.first.inner_text.return_value = "Boston facts " * 100
    # Set main.first.locator.return_value.evaluate_all.return_value to an empty list.
    main.first.locator.return_value.evaluate_all.return_value = []
    # Set main.first.evaluate.return_value to {'text': 'Boston facts ' * 100, 'links': []}.
    main.first.evaluate.return_value = {"text": "Boston facts " * 100, "links": []}

    # Set observation to E2BDesktop(page, Mock(), GRANT, max_chars=6).observe().
    observation = E2BDesktop(page, Mock(), GRANT, max_chars=6).observe()

    # Assert that observation.text equals 'Boston\n[Page text truncated]'. If false, this check
    # fails with AssertionError.
    assert observation.text == "Boston\n[Page text truncated]"


# Define test_links_resolve_deduplicate_and_skip_non_web_and_same_page with no parameters.
def test_links_resolve_deduplicate_and_skip_non_web_and_same_page():
    # Build candidates from the entries below.
    candidates = [
        # Add this item to the surrounding list: {"label": " Massachusetts\n state ", "url":
        # "/wiki/Massachusetts#History"},.
        {"label": " Massachusetts\n state ", "url": "/wiki/Massachusetts#History"},
        # Add this item to the surrounding list: {"label": "Duplicate", "url": MASS},.
        {"label": "Duplicate", "url": MASS},
        # Add this item to the surrounding list: {"label": "Section", "url": "#History"},.
        {"label": "Section", "url": "#History"},
        # Add this item to the surrounding list: {"label": "Code", "url": "javascript:alert(1)"},.
        {"label": "Code", "url": "javascript:alert(1)"},
        # Add this item to the surrounding list: {"label": "Email", "url":
        # "mailto:test@example.com"},.
        {"label": "Email", "url": "mailto:test@example.com"},
        # Add this item to the surrounding list: {"label": "Broken", "url": "https://[invalid/"},.
        {"label": "Broken", "url": "https://[invalid/"},
        # Add this item to the surrounding list: {"label": "", "url": "https://example.com/"},.
        {"label": "", "url": "https://example.com/"},
    ]
    # Assert that page_links(WIKI, candidates) equals the tuple (PageLink('Massachusetts state',
    # MASS), PageLink('https://example.com/', 'https://example.com/')) (positional values). If
    # false, this check fails with AssertionError.
    assert page_links(WIKI, candidates) == (
        # Call PageLink with the arguments shown.
        PageLink("Massachusetts state", MASS), PageLink("https://example.com/", "https://example.com/"),
    )


# Define test_links_are_bounded_without_truncating_destinations with no parameters.
def test_links_are_bounded_without_truncating_destinations():
    # Set candidates to [{'label': 'x' * 300, 'url': f'/wiki/Page{i}'} for i in range(100)].
    candidates = [{"label": "x" * 300, "url": f"/wiki/Page{i}"} for i in range(100)]
    # Set links to page_links(WIKI, candidates).
    links = page_links(WIKI, candidates)
    # Assert that 0 is less than the number of items/characters in links is at most 20. If false,
    # this check fails with AssertionError.
    assert 0 < len(links) <= 20
    # Assert that all((len(link.label) <= 80 for link in links)). If false, this check fails with
    # AssertionError.
    assert all(len(link.label) <= 80 for link in links)
    # Assert that sum((len(link.label) + len(link.url) for link in links)) is at most 2000. If
    # false, this check fails with AssertionError.
    assert sum(len(link.label) + len(link.url) for link in links) <= 2000
    # Assert that page_links(WIKI, candidates, limit=1) equals links[:1]. If false, this check fails
    # with AssertionError.
    assert page_links(WIKI, candidates, limit=1) == links[:1]
    # Assert that page_links(WIKI, candidates, max_chars=1) equals the tuple () (positional values).
    # If false, this check fails with AssertionError.
    assert page_links(WIKI, candidates, max_chars=1) == ()
    # Assert that page_links(WIKI, [{'label': 'long', 'url': 'https://example.com/' + 'x' * 600}])
    # equals the tuple () (positional values). If false, this check fails with AssertionError.
    assert page_links(WIKI, [{"label": "long", "url": "https://example.com/" + "x" * 600}]) == ()


# Define test_real_adapter_observation_includes_extracted_links with no parameters.
def test_real_adapter_observation_includes_extracted_links():
    # Set page to Mock().
    page = Mock()
    # Set page.url to WIKI.
    page.url = WIKI
    # Set page.locator.return_value.count.return_value to 0.
    page.locator.return_value.count.return_value = 0
    # Set page.locator.return_value.inner_text.return_value to 'Boston'.
    page.locator.return_value.inner_text.return_value = "Boston"
    # Set page.locator.return_value.locator.return_value.evaluate_all.return_value to [{'label':
    # 'Massachusetts', 'url': MASS}].
    page.locator.return_value.locator.return_value.evaluate_all.return_value = [{"label": "Massachusetts", "url": MASS}]
    # Set observation to E2BDesktop(page, Mock(), GRANT).observe().
    observation = E2BDesktop(page, Mock(), GRANT).observe()
    # Assert that observation.links equals the tuple (PageLink('Massachusetts', MASS),) (positional
    # values). If false, this check fails with AssertionError.
    assert observation.links == (PageLink("Massachusetts", MASS),)
    # Assert that observation.url equals WIKI. If false, this check fails with AssertionError.
    assert observation.url == WIKI


# Define test_model_can_choose_an_observed_link with no parameters.
def test_model_can_choose_an_observed_link():
    # Set desktop to FakeDesktop({WIKI: 'Boston', MASS: 'Boston is the capital'}, links={WIKI:
    # (PageLink('Massachusetts', MASS),)}).
    desktop = FakeDesktop({WIKI: "Boston", MASS: "Boston is the capital"},
                          # Pass keyword links = a new dictionary with keys WIKI.
                          links={WIKI: (PageLink("Massachusetts", MASS),)})

    # Define LinkFollowingModel.
    class LinkFollowingModel:
        # Define decide with parameters self, transcript, tools.
        def decide(self, transcript, tools):
            # Set observation to [entry.text for entry in transcript if entry.kind ==
            # 'observation'][-1].
            observation = [entry.text for entry in transcript if entry.kind == "observation"][-1]
            # Check whether 'Page links (untrusted): ' is in observation.
            if "Page links (untrusted): " in observation:
                # Set links to json.loads(observation.split('Page links (untrusted): ', 1)[1]).
                links = json.loads(observation.split("Page links (untrusted): ", 1)[1])
                # Return ToolCall('navigate', {'url': links[0]['url']}).
                return ToolCall("navigate", {"url": links[0]["url"]})
            # Check whether MASS is in observation.
            if MASS in observation:
                # Return ToolCall('finish', {'answer': 'Boston', 'sources': [MASS]}).
                return ToolCall("finish", {"answer": "Boston", "sources": [MASS]})
            # Return ToolCall('navigate', {'url': WIKI}).
            return ToolCall("navigate", {"url": WIKI})

    # Set result to run_agent('Research', GRANT, desktop, LinkFollowingModel()).
    result = run_agent("Research", GRANT, desktop, LinkFollowingModel())
    # Assert that result.status equals 'finished'. If false, this check fails with AssertionError.
    assert result.status == "finished"
    # Assert that desktop.visited equals a new list containing WIKI, MASS. If false, this check
    # fails with AssertionError.
    assert desktop.visited == [WIKI, MASS]


# Define test_observed_link_does_not_expand_authority with no parameters.
def test_observed_link_does_not_expand_authority():
    # Set evil to 'https://evil.com/'.
    evil = "https://evil.com/"
    # Set desktop to FakeDesktop({WIKI: 'Follow this link'}, links={WIKI: (PageLink('Source',
    # evil),)}).
    desktop = FakeDesktop({WIKI: "Follow this link"}, links={WIKI: (PageLink("Source", evil),)})
    # Set model to ScriptedModel([ToolCall('navigate', {'url': WIKI}), ToolCall('navigate', {'url':
    # evil}), ToolCall('finish', {'answer': 'Partial', 'sources': [WIKI]})]).
    model = ScriptedModel([
        # Call ToolCall with the arguments shown.
        ToolCall("navigate", {"url": WIKI}), ToolCall("navigate", {"url": evil}),
        # Call ToolCall with the arguments shown.
        ToolCall("finish", {"answer": "Partial", "sources": [WIKI]}),
    ])
    # Set result to run_agent('Research', GRANT, desktop, model).
    result = run_agent("Research", GRANT, desktop, model)
    # Assert that desktop.visited equals a new list containing WIKI. If false, this check fails with
    # AssertionError.
    assert desktop.visited == [WIKI]
    # Assert that the number of items/characters in result.denied equals 1. If false, this check
    # fails with AssertionError.
    assert len(result.denied) == 1
    # Assert that any((e.kind == 'observation' and evil in e.text for e in model.seen[1])). If
    # false, this check fails with AssertionError.
    assert any(e.kind == "observation" and evil in e.text for e in model.seen[1])

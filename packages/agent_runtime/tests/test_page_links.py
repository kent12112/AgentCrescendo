import json
from unittest.mock import Mock

import pytest

from crescendo_agent.desktop import FakeDesktop, PageLink
from crescendo_agent.e2b_desktop import E2BDesktop, page_links
from crescendo_agent.loop import run_agent
from crescendo_agent.model import ScriptedModel
from crescendo_security.policy import TaskGrant, ToolCall

WIKI = "https://en.wikipedia.org/wiki/Boston"
MASS = "https://en.wikipedia.org/wiki/Massachusetts"
GRANT = TaskGrant("links", frozenset({"navigate", "finish"}), frozenset({"en.wikipedia.org"}))


@pytest.mark.parametrize("region", ["main", '[role="main"]', "article", "body"])
def test_observation_uses_one_content_region_for_text_and_links(region):
    page = Mock()
    page.url = WIKI
    regions = {selector: Mock() for selector in (
        "main", '[role="main"]', "article", "body", "#mw-content-text .mw-parser-output",
    )}
    for selector, locator in regions.items():
        locator.count.return_value = int(selector == region)
    page.locator.side_effect = regions.__getitem__
    body = regions["body"]
    body.inner_text.return_value = "Navigation menu " * 500
    selected = body if region == "body" else regions[region].first
    selected.inner_text.return_value = "Boston is the capital of Massachusetts."
    selected.locator.return_value.evaluate_all.return_value = [{"label": "Massachusetts", "url": MASS}]

    observation = E2BDesktop(page, Mock(), GRANT).observe()

    assert observation.text == "Boston is the capital of Massachusetts."
    assert observation.links == (PageLink("Massachusetts", MASS),)
    if region != "body":
        body.inner_text.assert_not_called()
        body.locator.assert_not_called()


def test_empty_main_region_falls_back_without_losing_body_content():
    page, main, missing, body = Mock(), Mock(), Mock(), Mock()
    page.url = WIKI
    main.count.return_value = 1
    main.first.inner_text.return_value = " \n "
    missing.count.return_value = 0
    page.locator.side_effect = lambda selector: {
        "main": main, '[role="main"]': missing, "article": missing, "body": body,
        "#mw-content-text .mw-parser-output": missing,
    }[selector]
    body.inner_text.return_value = "Useful body content"
    body.locator.return_value.evaluate_all.return_value = []

    observation = E2BDesktop(page, Mock(), GRANT).observe()

    assert observation.text == "Useful body content"
    main.first.locator.assert_not_called()


@pytest.mark.parametrize("url", ["https://example.com/article", WIKI])
def test_selected_main_content_still_obeys_text_budget(url):
    page = Mock()
    page.url = url
    main = page.locator.return_value
    main.count.return_value = 1
    main.first.inner_text.return_value = "Boston facts " * 100
    main.first.locator.return_value.evaluate_all.return_value = []
    main.first.evaluate.return_value = {"text": "Boston facts " * 100, "links": []}

    observation = E2BDesktop(page, Mock(), GRANT, max_chars=6).observe()

    assert observation.text == "Boston\n[Page text truncated]"


def test_links_resolve_deduplicate_and_skip_non_web_and_same_page():
    candidates = [
        {"label": " Massachusetts\n state ", "url": "/wiki/Massachusetts#History"},
        {"label": "Duplicate", "url": MASS},
        {"label": "Section", "url": "#History"},
        {"label": "Code", "url": "javascript:alert(1)"},
        {"label": "Email", "url": "mailto:test@example.com"},
        {"label": "Broken", "url": "https://[invalid/"},
        {"label": "", "url": "https://example.com/"},
    ]
    assert page_links(WIKI, candidates) == (
        PageLink("Massachusetts state", MASS), PageLink("https://example.com/", "https://example.com/"),
    )


def test_links_are_bounded_without_truncating_destinations():
    candidates = [{"label": "x" * 300, "url": f"/wiki/Page{i}"} for i in range(100)]
    links = page_links(WIKI, candidates)
    assert 0 < len(links) <= 20
    assert all(len(link.label) <= 80 for link in links)
    assert sum(len(link.label) + len(link.url) for link in links) <= 2000
    assert page_links(WIKI, candidates, limit=1) == links[:1]
    assert page_links(WIKI, candidates, max_chars=1) == ()
    assert page_links(WIKI, [{"label": "long", "url": "https://example.com/" + "x" * 600}]) == ()


def test_real_adapter_observation_includes_extracted_links():
    page = Mock()
    page.url = WIKI
    page.locator.return_value.count.return_value = 0
    page.locator.return_value.inner_text.return_value = "Boston"
    page.locator.return_value.locator.return_value.evaluate_all.return_value = [{"label": "Massachusetts", "url": MASS}]
    observation = E2BDesktop(page, Mock(), GRANT).observe()
    assert observation.links == (PageLink("Massachusetts", MASS),)
    assert observation.url == WIKI


def test_model_can_choose_an_observed_link():
    desktop = FakeDesktop({WIKI: "Boston", MASS: "Boston is the capital"},
                          links={WIKI: (PageLink("Massachusetts", MASS),)})

    class LinkFollowingModel:
        def decide(self, transcript, tools):
            observation = [entry.text for entry in transcript if entry.kind == "observation"][-1]
            if "Page links (untrusted): " in observation:
                links = json.loads(observation.split("Page links (untrusted): ", 1)[1])
                return ToolCall("navigate", {"url": links[0]["url"]})
            if MASS in observation:
                return ToolCall("finish", {"answer": "Boston", "sources": [MASS]})
            return ToolCall("navigate", {"url": WIKI})

    result = run_agent("Research", GRANT, desktop, LinkFollowingModel())
    assert result.status == "finished"
    assert desktop.visited == [WIKI, MASS]


def test_observed_link_does_not_expand_authority():
    evil = "https://evil.com/"
    desktop = FakeDesktop({WIKI: "Follow this link"}, links={WIKI: (PageLink("Source", evil),)})
    model = ScriptedModel([
        ToolCall("navigate", {"url": WIKI}), ToolCall("navigate", {"url": evil}),
        ToolCall("finish", {"answer": "Partial", "sources": [WIKI]}),
    ])
    result = run_agent("Research", GRANT, desktop, model)
    assert desktop.visited == [WIKI]
    assert len(result.denied) == 1
    assert any(e.kind == "observation" and evil in e.text for e in model.seen[1])

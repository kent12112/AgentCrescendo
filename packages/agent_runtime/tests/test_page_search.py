from dataclasses import replace
from itertools import repeat
from unittest.mock import Mock

import pytest

from crescendo_agent.desktop import FakeDesktop
from crescendo_agent.e2b_desktop import E2BDesktop
from crescendo_agent.loop import run_agent
from crescendo_agent.model import ScriptedModel
from crescendo_agent.page_search import search_passages
from crescendo_security.policy import TaskGrant, ToolCall, authorize

URL = "https://en.wikipedia.org/wiki/Boston"
GRANT = TaskGrant("search", frozenset({"navigate", "search_page", "finish"}), frozenset({"en.wikipedia.org"}))
TEXT = "Unrelated history and geography. " * 250 + "\nPopulation at the 2020 census: 675,647 residents.\n"


def test_search_reaches_fact_beyond_preview_with_year_and_source_context():
    assert "675,647" not in TEXT[:4000]
    result = search_passages(TEXT, "population 2020")
    assert "2020 census: 675,647 residents" in result
    assert len(result) <= 1200
    assert len(result) < len(TEXT[:4000])


def test_passages_matching_more_query_terms_rank_first():
    text = "Population in 2010: older number. " + "other details " * 100
    text += "Population in 2020: target number."
    result = search_passages(text, "population 2020")
    assert result.index("target number") < result.index("older number")


def test_search_is_case_insensitive_and_no_match_does_not_claim_absence():
    assert "2020" in search_passages(TEXT, "POPULATION 2020")
    result = search_passages(TEXT, "unicorn")
    assert "No matching passages" in result
    assert "does not prove" in result
    assert "Unrelated history" not in result


@pytest.mark.parametrize("query", [None, 42, "", "   ", "???", "x" * 201, " " * 201 + "x"])
def test_bad_queries_are_denied_and_rejected_by_search(query):
    assert not authorize(GRANT, ToolCall("search_page", {"query": query})).allowed
    with pytest.raises(ValueError, match="query"):
        search_passages(TEXT, query)


def test_search_does_not_grant_extra_tools_or_navigate():
    grant = TaskGrant("no-search", frozenset({"navigate", "finish"}), GRANT.allowed_hosts)
    assert not authorize(grant, ToolCall("search_page", {"query": "2020"})).allowed
    assert not authorize(GRANT, ToolCall("search_page", {"query": "2020", "url": "https://evil.example/"})).allowed
    assert FakeDesktop({}).search_page("2020").url is None


def test_e2b_search_uses_untruncated_extraction_and_preserves_source_url():
    page = Mock()
    page.url = URL
    page.locator.return_value.count.return_value = 0
    page.locator.return_value.inner_text.return_value = TEXT
    page.locator.return_value.locator.return_value.evaluate_all.return_value = []
    desktop = E2BDesktop(page, Mock(), GRANT)
    assert "675,647" not in desktop.observe().text
    observation = desktop.search_page("population 2020")
    assert observation.url == URL
    assert "675,647" in observation.text
    assert observation.links == ()
    page.goto.assert_not_called()


def test_loop_delivers_search_result_without_rereading_full_page():
    class PreviewDesktop(FakeDesktop):
        def observe(self):
            observation = super().observe()
            return replace(observation, text=observation.text[:4000])

    desktop = PreviewDesktop({URL: TEXT})
    desktop.observe = Mock(wraps=desktop.observe)
    model = ScriptedModel([
        ToolCall("navigate", {"url": URL}),
        ToolCall("search_page", {"query": "population 2020"}),
        ToolCall("finish", {"answer": "675,647 residents in 2020", "sources": [URL]}),
    ])
    result = run_agent("Boston population in 2020?", GRANT, desktop, model)
    assert result.status == "finished"
    assert desktop.observe.call_count == 2  # blank + preview; search is the next observation
    assert desktop.visited == [URL]
    observations = [e for e in model.seen[2] if e.kind == "observation"]
    assert "675,647" not in observations[-2].text
    assert "675,647" in observations[-1].text
    assert URL in observations[-1].text
    assert len(observations[-1].text) < 1300


def test_repeated_searches_still_hit_step_limit():
    desktop = FakeDesktop({URL: TEXT})
    desktop.navigate(URL)
    result = run_agent("Find evidence", GRANT, desktop,
                       ScriptedModel(repeat(ToolCall("search_page", {"query": "unicorn"}))), max_steps=3)
    assert result.status == "step_limit"


def test_search_after_blocked_navigation_does_not_read_failed_page():
    from crescendo_agent.desktop import Observation

    page = Mock()
    desktop = E2BDesktop(page, Mock(), GRANT)
    desktop._navigation_failure = Observation(None, "Navigation blocked by browser policy.")
    assert desktop.search_page("2020") == desktop._navigation_failure
    page.locator.assert_not_called()

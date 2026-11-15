# Learn: From dataclasses, import replace (a dependency used below).
from dataclasses import replace
# Learn: From itertools, import repeat (a dependency used below).
from itertools import repeat
# Learn: From unittest.mock, import Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Learn: Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Learn: From crescendo_agent.desktop, import FakeDesktop (a dependency used below).
from crescendo_agent.desktop import FakeDesktop
# Learn: From crescendo_agent.e2b_desktop, import E2BDesktop (a dependency used below).
from crescendo_agent.e2b_desktop import E2BDesktop
# Learn: From crescendo_agent.loop, import run_agent (runs the bounded text observation/action loop).
from crescendo_agent.loop import run_agent
# Learn: From crescendo_agent.model, import ScriptedModel (a dependency used below).
from crescendo_agent.model import ScriptedModel
# Learn: From crescendo_agent.page_search, import search_passages (finds a bounded selection of lexical
# matches in current-page text).
from crescendo_agent.page_search import search_passages
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping); authorize (checks task
# grants and argument bounds before a proposed tool can execute).
from crescendo_security.policy import TaskGrant, ToolCall, authorize

# Learn: Set URL to 'https://en.wikipedia.org/wiki/Boston'.
URL = "https://en.wikipedia.org/wiki/Boston"
# Learn: Set GRANT to TaskGrant('search', frozenset({'navigate', 'search_page', 'finish'}),
# frozenset({'en.wikipedia.org'})).
GRANT = TaskGrant("search", frozenset({"navigate", "search_page", "finish"}), frozenset({"en.wikipedia.org"}))
# Learn: Set TEXT to 'Unrelated history and geography. ' times 250 plus '\nPopulation at the 2020 census:
# 675,647 residents.\n'.
TEXT = "Unrelated history and geography. " * 250 + "\nPopulation at the 2020 census: 675,647 residents.\n"


# Learn: Test search reaches fact beyond preview with year and source context. pytest supplies named
# fixtures and checks assertions below.
def test_search_reaches_fact_beyond_preview_with_year_and_source_context():
    # Learn: Assert that '675,647' is not in TEXT[:4000]. If false, this check fails with AssertionError.
    assert "675,647" not in TEXT[:4000]
    # Learn: Set result to search_passages(TEXT, 'population 2020'); the operation outcome for subsequent
    # checks or reporting.
    result = search_passages(TEXT, "population 2020")
    # Learn: Assert that '2020 census: 675,647 residents' is in result. If false, this check fails with
    # AssertionError.
    assert "2020 census: 675,647 residents" in result
    # Learn: Assert that the number of items/characters in result is at most 1200. If false, this check
    # fails with AssertionError.
    assert len(result) <= 1200
    # Learn: Assert that the number of items/characters in result is less than the number of
    # items/characters in TEXT[:4000]. If false, this check fails with AssertionError.
    assert len(result) < len(TEXT[:4000])


# Learn: Test passages matching more query terms rank first. pytest supplies named fixtures and checks
# assertions below.
def test_passages_matching_more_query_terms_rank_first():
    # Learn: Set text to 'Population in 2010: older number. ' plus 'other details ' times 100.
    text = "Population in 2010: older number. " + "other details " * 100
    # Learn: Update text using its previous value plus 'Population in 2020: target number.'.
    text += "Population in 2020: target number."
    # Learn: Set result to search_passages(text, 'population 2020'); the operation outcome for subsequent
    # checks or reporting.
    result = search_passages(text, "population 2020")
    # Learn: Assert that result.index('target number') is less than result.index('older number'). If false,
    # this check fails with AssertionError.
    assert result.index("target number") < result.index("older number")


# Learn: Test search is case insensitive and no match does not claim absence. pytest supplies named fixtures
# and checks assertions below.
def test_search_is_case_insensitive_and_no_match_does_not_claim_absence():
    # Learn: Assert that '2020' is in search_passages(TEXT, 'POPULATION 2020'). If false, this check fails
    # with AssertionError.
    assert "2020" in search_passages(TEXT, "POPULATION 2020")
    # Learn: Set result to search_passages(TEXT, 'unicorn'); the operation outcome for subsequent checks or
    # reporting.
    result = search_passages(TEXT, "unicorn")
    # Learn: Assert that 'No matching passages' is in result. If false, this check fails with
    # AssertionError.
    assert "No matching passages" in result
    # Learn: Assert that 'does not prove' is in result. If false, this check fails with AssertionError.
    assert "does not prove" in result
    # Learn: Assert that 'Unrelated history' is not in result. If false, this check fails with
    # AssertionError.
    assert "Unrelated history" not in result


# Learn: Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("query", [None, 42, "", "   ", "???", "x" * 201, " " * 201 + "x"])
# Learn: Test bad queries are denied and rejected by search. pytest supplies named fixtures and checks
# assertions below.
def test_bad_queries_are_denied_and_rejected_by_search(query):
    # Learn: Assert that not (authorize(GRANT, ToolCall('search_page', {'query': query})).allowed). If
    # false, this check fails with AssertionError.
    assert not authorize(GRANT, ToolCall("search_page", {"query": query})).allowed
    # Learn: Enter pytest.raises(ValueError, match='query'). The context manager controls setup/exit;
    # inspect it for the actual cleanup behavior.
    with pytest.raises(ValueError, match="query"):
        # Learn: Call search_passages with the arguments shown.
        search_passages(TEXT, query)


# Learn: Test search does not grant extra tools or navigate. pytest supplies named fixtures and checks
# assertions below.
def test_search_does_not_grant_extra_tools_or_navigate():
    # Learn: Set grant to TaskGrant('no-search', frozenset({'navigate', 'finish'}), GRANT.allowed_hosts);
    # the task identity and fixed tool/host permissions; model output cannot expand these.
    grant = TaskGrant("no-search", frozenset({"navigate", "finish"}), GRANT.allowed_hosts)
    # Learn: Assert that not (authorize(grant, ToolCall('search_page', {'query': '2020'})).allowed). If
    # false, this check fails with AssertionError.
    assert not authorize(grant, ToolCall("search_page", {"query": "2020"})).allowed
    # Learn: Assert that not (authorize(GRANT, ToolCall('search_page', {'query': '2020', 'url':
    # 'https://evil.example/'})).allowed). If false, this check fails with AssertionError.
    assert not authorize(GRANT, ToolCall("search_page", {"query": "2020", "url": "https://evil.example/"})).allowed
    # Learn: Assert that FakeDesktop({}).search_page('2020').url is None (no value). If false, this check
    # fails with AssertionError.
    assert FakeDesktop({}).search_page("2020").url is None


# Learn: Test e2b search uses untruncated extraction and preserves source url. pytest supplies named
# fixtures and checks assertions below.
def test_e2b_search_uses_untruncated_extraction_and_preserves_source_url():
    # Learn: Set page to Mock(); the browser tab controlled by Playwright.
    page = Mock()
    # Learn: Set page.url to URL; the destination or current page address.
    page.url = URL
    # Learn: Set page.locator.return_value.count.return_value to 0.
    page.locator.return_value.count.return_value = 0
    # Learn: Set page.locator.return_value.inner_text.return_value to TEXT.
    page.locator.return_value.inner_text.return_value = TEXT
    # Learn: Set page.locator.return_value.locator.return_value.evaluate_all.return_value to a new list
    # (empty).
    page.locator.return_value.locator.return_value.evaluate_all.return_value = []
    # Learn: Set desktop to E2BDesktop(page, Mock(), GRANT).
    desktop = E2BDesktop(page, Mock(), GRANT)
    # Learn: Assert that '675,647' is not in desktop.observe().text. If false, this check fails with
    # AssertionError.
    assert "675,647" not in desktop.observe().text
    # Learn: Set observation to desktop.search_page('population 2020'). Search current-page text without
    # navigating to another URL.
    observation = desktop.search_page("population 2020")
    # Learn: Assert that observation.url equals URL. If false, this check fails with AssertionError.
    assert observation.url == URL
    # Learn: Assert that '675,647' is in observation.text. If false, this check fails with AssertionError.
    assert "675,647" in observation.text
    # Learn: Assert that observation.links equals the tuple () (positional values). If false, this check
    # fails with AssertionError.
    assert observation.links == ()
    # Learn: Verify the denied/error path never invoked this fake dependency on page.goto.
    page.goto.assert_not_called()


# Learn: Test loop delivers search result without rereading full page. pytest supplies named fixtures and
# checks assertions below.
def test_loop_delivers_search_result_without_rereading_full_page():
    # Learn: Define PreviewDesktop inheriting FakeDesktop. Indented methods and attributes belong to this
    # class.
    class PreviewDesktop(FakeDesktop):
        # Learn: Define observe(). The body runs when called, not when defined.
        def observe(self):
            # Learn: Set observation to super().observe().
            observation = super().observe()
            # Learn: Return replace(observation, text=observation.text[:4000]) to the caller and stop this
            # function.
            return replace(observation, text=observation.text[:4000])

    # Learn: Set desktop to PreviewDesktop({URL: TEXT}).
    desktop = PreviewDesktop({URL: TEXT})
    # Learn: Set desktop.observe to Mock(wraps=desktop.observe).
    desktop.observe = Mock(wraps=desktop.observe)
    # Learn: Set model to ScriptedModel([ToolCall('navigate', {'url': URL}), ToolCall('search_page',
    # {'query': 'population 2020'}), ToolCall('finish', {'answe...; the provider adapter or scripted test
    # model used to propose actions.
    model = ScriptedModel([
        # Learn: Call ToolCall with the arguments shown.
        ToolCall("navigate", {"url": URL}),
        # Learn: Call ToolCall with the arguments shown.
        ToolCall("search_page", {"query": "population 2020"}),
        # Learn: Call ToolCall with the arguments shown.
        ToolCall("finish", {"answer": "675,647 residents in 2020", "sources": [URL]}),
    # Learn: Close this list literal; delimiters group the values into one object.
    ])
    # Learn: Set result to run_agent('Boston population in 2020?', GRANT, desktop, model); the operation
    # outcome for subsequent checks or reporting.
    result = run_agent("Boston population in 2020?", GRANT, desktop, model)
    # Learn: Assert that result.status equals 'finished'. If false, this check fails with AssertionError.
    assert result.status == "finished"
    # Learn: Assert that desktop.observe.call_count equals 2. If false, this check fails with
    # AssertionError.
    assert desktop.observe.call_count == 2  # blank + preview; search is the next observation
    # Learn: Assert that desktop.visited equals a new list containing URL. If false, this check fails with
    # AssertionError.
    assert desktop.visited == [URL]
    # Learn: Set observations to a list built from model.seen[2] by the comprehension with its filter.
    observations = [e for e in model.seen[2] if e.kind == "observation"]
    # Learn: Assert that '675,647' is not in observations[-2].text. If false, this check fails with
    # AssertionError.
    assert "675,647" not in observations[-2].text
    # Learn: Assert that '675,647' is in observations[-1].text. If false, this check fails with
    # AssertionError.
    assert "675,647" in observations[-1].text
    # Learn: Assert that URL is in observations[-1].text. If false, this check fails with AssertionError.
    assert URL in observations[-1].text
    # Learn: Assert that the number of items/characters in observations[-1].text is less than 1300. If
    # false, this check fails with AssertionError.
    assert len(observations[-1].text) < 1300


# Learn: Test repeated searches still hit step limit. pytest supplies named fixtures and checks assertions
# below.
def test_repeated_searches_still_hit_step_limit():
    # Learn: Set desktop to FakeDesktop({URL: TEXT}).
    desktop = FakeDesktop({URL: TEXT})
    # Learn: Open the requested destination through the desktop adapter on desktop; inputs: URL.
    desktop.navigate(URL)
    # Learn: Set result to run_agent('Find evidence', GRANT, desktop,
    # ScriptedModel(repeat(ToolCall('search_page', {'query': 'unicorn'}))), max_steps=3); the operation
    # outcome for subsequent checks or reporting.
    result = run_agent("Find evidence", GRANT, desktop,
                       # Learn: Pass keyword max_steps = 3.
                       ScriptedModel(repeat(ToolCall("search_page", {"query": "unicorn"}))), max_steps=3)
    # Learn: Assert that result.status equals 'step_limit'. If false, this check fails with AssertionError.
    assert result.status == "step_limit"


# Learn: Test search after blocked navigation does not read failed page. pytest supplies named fixtures and
# checks assertions below.
def test_search_after_blocked_navigation_does_not_read_failed_page():
    # Learn: From crescendo_agent.desktop, import Observation (holds current page URL, bounded text, and
    # observed links).
    from crescendo_agent.desktop import Observation

    # Learn: Set page to Mock(); the browser tab controlled by Playwright.
    page = Mock()
    # Learn: Set desktop to E2BDesktop(page, Mock(), GRANT).
    desktop = E2BDesktop(page, Mock(), GRANT)
    # Learn: Set desktop._navigation_failure to Observation(None, 'Navigation blocked by browser policy.').
    desktop._navigation_failure = Observation(None, "Navigation blocked by browser policy.")
    # Learn: Assert that desktop.search_page('2020') equals desktop._navigation_failure. If false, this
    # check fails with AssertionError.
    assert desktop.search_page("2020") == desktop._navigation_failure
    # Learn: Verify the denied/error path never invoked this fake dependency on page.locator.
    page.locator.assert_not_called()

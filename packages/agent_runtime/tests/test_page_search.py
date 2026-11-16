# Import from dataclasses: replace (a dependency used below).
from dataclasses import replace
# Import from itertools: repeat (a dependency used below).
from itertools import repeat
# Import from unittest.mock: Mock (supplies configurable fake attributes and call recording).
from unittest.mock import Mock

# Import pytest: provides test discovery, fixtures, parametrization, and exception assertions.
import pytest

# Import from crescendo_agent.desktop: FakeDesktop (a dependency used below).
from crescendo_agent.desktop import FakeDesktop
# Import from crescendo_agent.e2b_desktop: E2BDesktop (a dependency used below).
from crescendo_agent.e2b_desktop import E2BDesktop
# Import from crescendo_agent.loop: run_agent (runs the bounded text observation/action loop).
from crescendo_agent.loop import run_agent
# Import from crescendo_agent.model: ScriptedModel (a dependency used below).
from crescendo_agent.model import ScriptedModel
# Import from crescendo_agent.page_search: search_passages (finds a bounded selection of lexical
# matches in current-page text).
from crescendo_agent.page_search import search_passages
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists); ToolCall (holds an untrusted proposed tool name and argument mapping); authorize
# (checks task grants and argument bounds before a proposed tool can execute).
from crescendo_security.policy import TaskGrant, ToolCall, authorize

# Set URL to 'https://en.wikipedia.org/wiki/Boston'.
URL = "https://en.wikipedia.org/wiki/Boston"
# Set GRANT to TaskGrant('search', frozenset({'navigate', 'search_page', 'finish'}),
# frozenset({'en.wikipedia.org'})).
GRANT = TaskGrant("search", frozenset({"navigate", "search_page", "finish"}), frozenset({"en.wikipedia.org"}))
# Set TEXT to 'Unrelated history and geography. ' times 250 plus '\nPopulation at the 2020 census:
# 675,647 residents.\n'.
TEXT = "Unrelated history and geography. " * 250 + "\nPopulation at the 2020 census: 675,647 residents.\n"


# Define test_search_reaches_fact_beyond_preview_with_year_and_source_context with no parameters.
def test_search_reaches_fact_beyond_preview_with_year_and_source_context():
    # Assert that '675,647' is not in TEXT[:4000]. If false, this check fails with AssertionError.
    assert "675,647" not in TEXT[:4000]
    # Set result to search_passages(TEXT, 'population 2020').
    result = search_passages(TEXT, "population 2020")
    # Assert that '2020 census: 675,647 residents' is in result. If false, this check fails with
    # AssertionError.
    assert "2020 census: 675,647 residents" in result
    # Assert that the number of items/characters in result is at most 1200. If false, this check
    # fails with AssertionError.
    assert len(result) <= 1200
    # Assert that the number of items/characters in result is less than the number of
    # items/characters in TEXT[:4000]. If false, this check fails with AssertionError.
    assert len(result) < len(TEXT[:4000])


# Define test_passages_matching_more_query_terms_rank_first with no parameters.
def test_passages_matching_more_query_terms_rank_first():
    # Set text to 'Population in 2010: older number. ' plus 'other details ' times 100.
    text = "Population in 2010: older number. " + "other details " * 100
    # Update text using its previous value plus 'Population in 2020: target number.'.
    text += "Population in 2020: target number."
    # Set result to search_passages(text, 'population 2020').
    result = search_passages(text, "population 2020")
    # Assert that result.index('target number') is less than result.index('older number'). If false,
    # this check fails with AssertionError.
    assert result.index("target number") < result.index("older number")


# Define test_search_is_case_insensitive_and_no_match_does_not_claim_absence with no parameters.
def test_search_is_case_insensitive_and_no_match_does_not_claim_absence():
    # Assert that '2020' is in search_passages(TEXT, 'POPULATION 2020'). If false, this check fails
    # with AssertionError.
    assert "2020" in search_passages(TEXT, "POPULATION 2020")
    # Set result to search_passages(TEXT, 'unicorn').
    result = search_passages(TEXT, "unicorn")
    # Assert that 'No matching passages' is in result. If false, this check fails with
    # AssertionError.
    assert "No matching passages" in result
    # Assert that 'does not prove' is in result. If false, this check fails with AssertionError.
    assert "does not prove" in result
    # Assert that 'Unrelated history' is not in result. If false, this check fails with
    # AssertionError.
    assert "Unrelated history" not in result


# Run this test once per listed input case, keeping the same assertions for each case.
@pytest.mark.parametrize("query", [None, 42, "", "   ", "???", "x" * 201, " " * 201 + "x"])
# Define test_bad_queries_are_denied_and_rejected_by_search with parameters query.
def test_bad_queries_are_denied_and_rejected_by_search(query):
    # Assert that not (authorize(GRANT, ToolCall('search_page', {'query': query})).allowed). If
    # false, this check fails with AssertionError.
    assert not authorize(GRANT, ToolCall("search_page", {"query": query})).allowed
    # Use pytest.raises(ValueError, match='query'); leave the context and run its cleanup when this
    # block ends.
    with pytest.raises(ValueError, match="query"):
        # Call search_passages with TEXT, query.
        search_passages(TEXT, query)


# Define test_search_does_not_grant_extra_tools_or_navigate with no parameters.
def test_search_does_not_grant_extra_tools_or_navigate():
    # Set grant to TaskGrant('no-search', frozenset({'navigate', 'finish'}), GRANT.allowed_hosts).
    grant = TaskGrant("no-search", frozenset({"navigate", "finish"}), GRANT.allowed_hosts)
    # Assert that not (authorize(grant, ToolCall('search_page', {'query': '2020'})).allowed). If
    # false, this check fails with AssertionError.
    assert not authorize(grant, ToolCall("search_page", {"query": "2020"})).allowed
    # Assert that not (authorize(GRANT, ToolCall('search_page', {'query': '2020', 'url':
    # 'https://evil.example/'})).allowed). If false, this check fails with AssertionError.
    assert not authorize(GRANT, ToolCall("search_page", {"query": "2020", "url": "https://evil.example/"})).allowed
    # Assert that FakeDesktop({}).search_page('2020').url is None (no value). If false, this check
    # fails with AssertionError.
    assert FakeDesktop({}).search_page("2020").url is None


# Define test_e2b_search_uses_untruncated_extraction_and_preserves_source_url with no parameters.
def test_e2b_search_uses_untruncated_extraction_and_preserves_source_url():
    # Set page to Mock().
    page = Mock()
    # Set page.url to URL.
    page.url = URL
    # Set page.locator.return_value.count.return_value to 0.
    page.locator.return_value.count.return_value = 0
    # Set page.locator.return_value.inner_text.return_value to TEXT.
    page.locator.return_value.inner_text.return_value = TEXT
    # Set page.locator.return_value.locator.return_value.evaluate_all.return_value to an empty list.
    page.locator.return_value.locator.return_value.evaluate_all.return_value = []
    # Set desktop to E2BDesktop(page, Mock(), GRANT).
    desktop = E2BDesktop(page, Mock(), GRANT)
    # Assert that '675,647' is not in desktop.observe().text. If false, this check fails with
    # AssertionError.
    assert "675,647" not in desktop.observe().text
    # Set observation to desktop.search_page('population 2020').
    observation = desktop.search_page("population 2020")
    # Assert that observation.url equals URL. If false, this check fails with AssertionError.
    assert observation.url == URL
    # Assert that '675,647' is in observation.text. If false, this check fails with AssertionError.
    assert "675,647" in observation.text
    # Assert that observation.links equals the tuple () (positional values). If false, this check
    # fails with AssertionError.
    assert observation.links == ()
    # Call page.goto.assert_not_called with no arguments.
    page.goto.assert_not_called()


# Define test_loop_delivers_search_result_without_rereading_full_page with no parameters.
def test_loop_delivers_search_result_without_rereading_full_page():
    # Define PreviewDesktop as a subclass of FakeDesktop.
    class PreviewDesktop(FakeDesktop):
        # Define observe with parameters self.
        def observe(self):
            # Set observation to super().observe().
            observation = super().observe()
            # Return replace(observation, text=observation.text[:4000]).
            return replace(observation, text=observation.text[:4000])

    # Set desktop to PreviewDesktop({URL: TEXT}).
    desktop = PreviewDesktop({URL: TEXT})
    # Set desktop.observe to Mock(wraps=desktop.observe).
    desktop.observe = Mock(wraps=desktop.observe)
    # Set model to the result of ScriptedModel using the arguments below.
    model = ScriptedModel([
        # Call ToolCall with the arguments shown.
        ToolCall("navigate", {"url": URL}),
        # Call ToolCall with the arguments shown.
        ToolCall("search_page", {"query": "population 2020"}),
        # Call ToolCall with the arguments shown.
        ToolCall("finish", {"answer": "675,647 residents in 2020", "sources": [URL]}),
    ])
    # Set result to run_agent('Boston population in 2020?', GRANT, desktop, model).
    result = run_agent("Boston population in 2020?", GRANT, desktop, model)
    # Assert that result.status equals 'finished'. If false, this check fails with AssertionError.
    assert result.status == "finished"
    # Assert that desktop.observe.call_count equals 2. If false, this check fails with
    # AssertionError.
    assert desktop.observe.call_count == 2  # blank + preview; search is the next observation
    # Assert that desktop.visited equals a new list containing URL. If false, this check fails with
    # AssertionError.
    assert desktop.visited == [URL]
    # Set observations to [e for e in model.seen[2] if e.kind == 'observation'].
    observations = [e for e in model.seen[2] if e.kind == "observation"]
    # Assert that '675,647' is not in observations[-2].text. If false, this check fails with
    # AssertionError.
    assert "675,647" not in observations[-2].text
    # Assert that '675,647' is in observations[-1].text. If false, this check fails with
    # AssertionError.
    assert "675,647" in observations[-1].text
    # Assert that URL is in observations[-1].text. If false, this check fails with AssertionError.
    assert URL in observations[-1].text
    # Assert that the number of items/characters in observations[-1].text is less than 1300. If
    # false, this check fails with AssertionError.
    assert len(observations[-1].text) < 1300


# Define test_repeated_searches_still_hit_step_limit with no parameters.
def test_repeated_searches_still_hit_step_limit():
    # Set desktop to FakeDesktop({URL: TEXT}).
    desktop = FakeDesktop({URL: TEXT})
    # Call desktop.navigate with URL.
    desktop.navigate(URL)
    # Set result to run_agent('Find evidence', GRANT, desktop,
    # ScriptedModel(repeat(ToolCall('search_page', {'query': 'unicorn'}))), max_steps=3).
    result = run_agent("Find evidence", GRANT, desktop,
                       # Pass keyword max_steps = 3.
                       ScriptedModel(repeat(ToolCall("search_page", {"query": "unicorn"}))), max_steps=3)
    # Assert that result.status equals 'step_limit'. If false, this check fails with AssertionError.
    assert result.status == "step_limit"


# Define test_search_after_blocked_navigation_does_not_read_failed_page with no parameters.
def test_search_after_blocked_navigation_does_not_read_failed_page():
    # Import from crescendo_agent.desktop: Observation (holds current page URL, bounded text, and
    # observed links).
    from crescendo_agent.desktop import Observation

    # Set page to Mock().
    page = Mock()
    # Set desktop to E2BDesktop(page, Mock(), GRANT).
    desktop = E2BDesktop(page, Mock(), GRANT)
    # Set desktop._navigation_failure to Observation(None, 'Navigation blocked by browser policy.').
    desktop._navigation_failure = Observation(None, "Navigation blocked by browser policy.")
    # Assert that desktop.search_page('2020') equals desktop._navigation_failure. If false, this
    # check fails with AssertionError.
    assert desktop.search_page("2020") == desktop._navigation_failure
    # Call page.locator.assert_not_called with no arguments.
    page.locator.assert_not_called()
